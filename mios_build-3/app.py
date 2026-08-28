"""
Market Intelligence OS — application entry point.

Run with:
    streamlit run app.py

This file is deliberately thin. It owns page config, the sidebar, the run
button and the tab layout; every piece of analysis lives in `mios.core`
and every pixel lives in `mios.ui` and `mios.viz`.
"""

from __future__ import annotations

import streamlit as st

st.set_page_config(
    page_title="Market Intelligence OS",
    page_icon="◈",
    layout="wide",
    initial_sidebar_state="expanded",
)

from mios import theme                                     # noqa: E402
from mios.config import (  # noqa: E402
    ENV_LOADED, ENV_LOCATION, HAS_PLOTLY, INSTALL_HINT,
    PYTHON_EXECUTABLE, SETTINGS,
)
from mios.core import (                                    # noqa: E402
    analytics, crossdomain, demo, llm, pools as pools_mod,
    report as report_mod, research, search,
)
from mios.ui import components as C, sections              # noqa: E402
from mios.viz import palette as P                          # noqa: E402

st.markdown(theme.css(), unsafe_allow_html=True)


# ----------------------------------------------------------------------
# Analysis bundle
# ----------------------------------------------------------------------

def build_bundle(run) -> dict:
    """Everything the UI needs, computed once per research run."""
    attract = analytics.attractiveness(run)
    pools = pools_mod.growth_pools(run, attract.scores.get("Risk headroom", 50))
    links = crossdomain.build_links(run)
    rep = report_mod.build_report(run, attract, pools, links)

    risk_points = [
        (name, max(10, 100 - score), int(weight * 260))
        for name, _fn, weight in analytics.DIMENSIONS
        for score in [attract.scores.get(name, 50)]
    ]

    funnel = [
        ("Retrieved", run.total_retrieved, "Documents returned by search"),
        ("Qualified", run.total_sources, "Passed authority, relevance and fit gates"),
        ("Quoted", sum(len(r.findings) for r in run.results), "Sentences that cleared the signal threshold"),
        ("Quantified", len(run.all_money) + len(run.all_rates) + len(run.all_shares),
         "Figures extracted and typed"),
        ("Pools", len(pools), "Candidates surviving corroboration"),
    ]

    return {
        "run": run,
        "attract": attract,
        "pools": pools,
        "pool_sets": pools_mod.overlap_sets(pools),
        "links": links,
        "report": rep,
        "matrix": crossdomain.linkage_matrix(run),
        "domain_rows": analytics.domain_table(run),
        "lens": analytics.lens_scores(run),
        "forces": analytics.five_forces(run, attract),
        "gaps": analytics.evidence_gaps(run),
        "risks": risk_points,
        "funnel": funnel,
    }


# ----------------------------------------------------------------------
# Sidebar
# ----------------------------------------------------------------------

with st.sidebar:
    st.markdown(
        f"""<div style="padding:0.4rem 0 1rem">
              <span class="eyebrow">Market Intelligence OS</span>
              <div style="font-family:var(--font-display);font-size:1.25rem;
                          font-weight:700;letter-spacing:-0.02em">
                Command centre
              </div>
              <div style="font-size:0.78rem;color:var(--faint);margin-top:0.3rem">
                Research the market, check the evidence, decide.
              </div>
            </div>""",
        unsafe_allow_html=True,
    )

    industry = st.text_input("Industry", value="Edtech")
    geography = st.text_input("Geography", value="India")
    objective = st.selectbox(
        "Strategic objective",
        ["Industry Analysis", "Market Entry", "Investment Screen",
         "Competitive Response", "Portfolio Review"],
    )

    st.write("")
    demo_mode = st.toggle(
        "Demo mode",
        value=not SETTINGS.has_search,
        help="Runs the full pipeline against a bundled fixture corpus. "
             "No network, no API keys, no quota. The figures are synthetic "
             "and must never be quoted as sourced fact.",
    )
    use_model = st.toggle(
        "Model-assisted prose",
        value=SETTINGS.has_llm,
        disabled=not SETTINGS.has_llm,
        help="The model only rewrites evidence that has already been "
             "qualified. It never supplies facts.",
    )

    st.write("")
    run_clicked = st.button("Run 13-domain research", type="primary",
                            key="run_research")

    st.write("")
    st.markdown('<span class="eyebrow">Connections</span>', unsafe_allow_html=True)

    if not ENV_LOADED:
        st.warning(
            "No .env file found. Put yours in the same folder as app.py, "
            "then restart Streamlit — edits to .env are only read at startup."
        )
    elif not (SETTINGS.tavily_key or SETTINGS.groq_key):
        st.warning(
            f"Found .env at {ENV_LOCATION} but neither key is set. Check the "
            "lines read TAVILY_API_KEY=... with no quotes and no spaces."
        )

    def status(label: str, ok: bool, note: str) -> None:
        colour = P.MINT if ok else P.AMBER
        st.markdown(
            f"""<div style="font-family:var(--font-mono);font-size:0.66rem;
                        color:{colour};margin-bottom:0.35rem">
                  ● {label}
                  <span style="color:var(--faint)"> — {note}</span>
                </div>""",
            unsafe_allow_html=True,
        )

    status("Tavily", search.configured(),
           "key loaded" if search.configured()
           else ("package missing" if not search.INSTALLED else "no API key"))
    status("Groq", llm.configured(),
           llm.resolve_model() if llm.configured()
           else ("package missing" if not llm.INSTALLED else "no API key"))
    status("Plotly", HAS_PLOTLY,
           "charts ready" if HAS_PLOTLY else "not importable")

    if ENV_LOADED:
        st.caption(f"Keys loaded from {ENV_LOCATION}")

    if st.button("Test connections"):
        with st.spinner("Calling both APIs"):
            t_ok, t_msg = search.health()
            g_ok, g_msg = llm.health()
        (st.success if t_ok else st.error)(f"Tavily — {t_msg}")
        (st.success if g_ok else st.error)(f"Groq — {g_msg}")

    # The model list comes from Groq itself, so a retired ID can never be
    # offered. Without a key there is nothing to list and the .env value
    # stands.
    catalogue = llm.list_models() if llm.configured() else []
    if catalogue:
        current = llm.resolve_model()
        chosen = st.selectbox(
            "Groq model", catalogue,
            index=catalogue.index(current) if current in catalogue else 0,
            help="Read live from your Groq account. Retired IDs in .env "
                 "are upgraded to their documented successor automatically.",
        )
        if chosen != SETTINGS.groq_model:
            object.__setattr__(SETTINGS, "groq_model", chosen)

    with st.expander("Retrieval settings"):
        depth = st.select_slider(
            "Search depth", options=["basic", "advanced"],
            value=SETTINGS.search_depth if SETTINGS.search_depth in ("basic", "advanced") else "advanced",
            help="Advanced returns full page text, which the extractor needs "
                 "to find figures. Basic is cheaper and returns snippets.",
        )
        results = st.slider("Results per query", 4, 12, SETTINGS.search_results)
        recency = st.selectbox(
            "Recency filter", ["no limit", "year", "month", "week"],
            help="Market size pages are evergreen; competitive and "
                 "regulatory news is not.",
        )
        news_topic = st.toggle(
            "Use the news index for competition, regulation and risk",
            value=SETTINGS.use_news_topic,
        )
        calls = st.slider(
            "Groq call budget", 0, 20, SETTINGS.max_llm_calls,
            help="Thirteen domains plus one synthesis. Below 14 some "
                 "domains fall back to the deterministic writer.",
        )

        object.__setattr__(SETTINGS, "search_depth", depth)
        object.__setattr__(SETTINGS, "search_results", results)
        object.__setattr__(SETTINGS, "time_range",
                           "" if recency == "no limit" else recency)
        object.__setattr__(SETTINGS, "use_news_topic", news_topic)
        object.__setattr__(SETTINGS, "max_llm_calls", calls)

        country = search.country_for(geography)
        st.caption(
            f"Country bias: {country}" if country
            else f"No country bias — Tavily maps country names, and "
                 f"'{geography}' is not one."
        )

    if not HAS_PLOTLY:
        st.warning(
            "Plotly is installed to a different interpreter than the one "
            "running Streamlit. Fix it with the command below, then reload."
        )
        st.code(INSTALL_HINT, language="bash")
        st.caption(f"Current interpreter: {PYTHON_EXECUTABLE}")

# ----------------------------------------------------------------------
# Run
# ----------------------------------------------------------------------

if run_clicked:
    if demo_mode:
        search.clear_cache()
        demo.install(industry, geography, objective)
    elif not SETTINGS.has_search:
        st.error(
            "No search key configured. Add TAVILY_API_KEY to your .env file, "
            "or switch on demo mode in the sidebar to run against the "
            "bundled fixture corpus."
        )
        st.stop()

    search.USAGE.reset()
    llm.reset_budget()
    progress = st.progress(0.0, text="Starting research")

    def on_progress(index: int, total: int, name: str) -> None:
        progress.progress(index / total, text=f"D{index}/{total} · {name}")

    run = research.run_research(
        industry, geography, objective,
        use_model=use_model and not demo_mode,
        on_progress=on_progress,
    )
    progress.empty()

    st.session_state["bundle"] = build_bundle(run)
    st.session_state["demo_used"] = demo_mode
    st.session_state["telemetry"] = {
        "queries": search.USAGE.queries,
        "cached": search.USAGE.cached,
        "search_failed": search.USAGE.failed,
        "search_error": search.USAGE.last_error,
        "llm_used": llm.BUDGET.used,
        "llm_failed": llm.BUDGET.failed,
        "llm_error": llm.BUDGET.last_error,
        "model": llm.resolve_model() if llm.configured() else None,
    }


# ----------------------------------------------------------------------
# Render
# ----------------------------------------------------------------------

bundle = st.session_state.get("bundle")

if not bundle:
    C.hero(
        industry, geography, objective,
        "This researches a market across thirteen topics, pulls the actual "
        "numbers out of what it finds, and checks whether those numbers agree "
        "with each other. It then answers two questions separately: is this "
        "market worth entering, and how much should you trust that answer? "
        "Keeping them apart matters, because an attractive market with weak "
        "evidence needs a different response from an attractive market with "
        "strong evidence.",
    )
    st.write("")

    left, right = st.columns([1, 1], gap="medium")
    with left:
        C.glass(
            """<span class="eyebrow">What it does</span>
               <ul style="margin:0.6rem 0 0;padding-left:1.1rem;
                          font-size:0.88rem;line-height:1.7;color:var(--text)">
                 <li>Reads the actual numbers out of the sources instead of
                     quoting them as text.</li>
                 <li>When two reports disagree about the size of a market, it
                     shows you both rather than averaging them into one
                     figure that is wrong.</li>
                 <li>Checks whether a report's stated growth rate matches its
                     own size figures.</li>
                 <li>Tells you how much to trust the answer, separately from
                     what the answer is.</li>
               </ul>"""
        )
    with right:
        C.glass(
            f"""<span class="eyebrow">Getting started</span>
               <ol style="margin:0.6rem 0 0;padding-left:1.1rem;
                          font-size:0.86rem;line-height:1.65;color:var(--muted)">
                 <li>Set the industry and geography in the sidebar.</li>
                 <li>Leave demo mode on to run against the bundled corpus, or
                     add <code>TAVILY_API_KEY</code> to <code>.env</code> for
                     live retrieval.</li>
                 <li>Press <b>Run 13-domain research</b>.</li>
               </ol>
               <p style="font-size:0.8rem;color:var(--faint);margin-top:0.8rem">
                 {'Keys loaded from ' + ENV_LOCATION if ENV_LOADED
                  else 'No .env file found yet — demo mode works without one.'}
               </p>"""
        )
    st.stop()

run = bundle["run"]

C.hero(
    run.industry, run.geography, run.objective,
    bundle["report"].recommendation.reasoning,
)
st.write("")

if st.session_state.get("demo_used"):
    st.info(
        "Demo mode: figures come from a synthetic fixture corpus and must "
        "not be quoted as sourced fact. The reconciliation conflicts you see "
        "are deliberately planted so the engine has something real to catch."
    )

C.evidence_spine(bundle["domain_rows"])

telemetry = st.session_state.get("telemetry") or {}
if telemetry.get("queries") or telemetry.get("llm_used"):
    parts = [
        f"{telemetry['queries']} live queries",
        f"{telemetry['cached']} served from cache",
    ]
    if telemetry.get("model") and telemetry.get("llm_used"):
        parts.append(f"{telemetry['llm_used']} model calls · {telemetry['model']}")
    if telemetry.get("search_failed"):
        parts.append(f"{telemetry['search_failed']} search failures")
    if telemetry.get("llm_failed"):
        parts.append(f"{telemetry['llm_failed']} model failures")
    st.caption(" · ".join(parts))

if telemetry.get("search_error"):
    st.warning(f"Last search error: {telemetry['search_error']}")
if telemetry.get("llm_error") and telemetry.get("llm_failed"):
    st.warning(
        f"Last model error: {telemetry['llm_error']} — domain prose fell "
        f"back to the deterministic writer. The analysis is unaffected."
    )

st.write("")

tabs = st.tabs([
    "Decision", "Market size", "Research", "Opportunities",
    "Where profit sits", "Connections", "Risks", "Sources", "Full report",
])

renderers = [
    sections.executive, sections.market_size, sections.domains,
    sections.growth_pools, sections.value_chain, sections.cross_domain,
    sections.risk, sections.sources, sections.report,
]

for tab, render in zip(tabs, renderers):
    with tab:
        render(bundle)

st.write("")
st.markdown(
    f"""<div style="text-align:center;padding:2.5rem 0 1rem;
                font-size:0.78rem;color:var(--faint)">
          {run.industry} · {run.geography} — built from {run.total_sources}
          sources across {run.independent_publishers} publishers
        </div>""",
    unsafe_allow_html=True,
)
