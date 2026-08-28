"""
Section renderers.

One function per tab. None of them compute anything — the analysis lives
in `core` and the layout lives here.

Two rules govern every screen. First, each one opens with a single
sentence that states what it concluded, so a reader who stops there has
still got the answer. Second, every chart carries a plain-English note
saying how to read it; a chart that needs a paragraph of explanation is a
chart that should be redrawn, and the note is the test.

Detail that is reference rather than finding goes inside a collapsed
expander. That is the main defence against a page feeling text-heavy.
"""

from __future__ import annotations

from typing import Dict, List

import streamlit as st

from ..core import report as report_mod
from ..core.analytics import DIMENSIONS
from ..core.reconcile import contamination_ratio, forecast_share
from ..viz import charts, flows, palette as P, venn
from . import components as C


def _plain_quadrant(quadrant: str) -> str:
    return {
        "ACT": "the market looks good and the evidence backs it up",
        "VALIDATE": "the market looks good but the evidence is too thin to bet on yet",
        "PASS": "the evidence is solid and it says this market is not worth entering",
        "PARK": "neither the market nor the evidence is strong enough to act on",
    }.get(quadrant, "")


# ----------------------------------------------------------------------
# 1. Executive
# ----------------------------------------------------------------------

def executive(bundle) -> None:
    run, attract, pools, rep = (
        bundle["run"], bundle["attract"], bundle["pools"], bundle["report"],
    )

    C.verdict_card(rep.recommendation, attract)

    if rep.synthesis and rep.synthesis_source == "model":
        st.write("")
        C.glass(
            '<span class="eyebrow">Summary</span>'
            f'<p class="prose" style="margin:0.5rem 0 0">{rep.synthesis}</p>'
        )

    st.write("")
    C.kpi_row([
        ("How good is the market?", f"{attract.overall}",
         f"{attract.band.title()} out of 100", attract.overall),
        ("How sure are we?", f"{attract.confidence}",
         "Based on source quality, not on the market", attract.confidence),
        ("Topics covered", f"{run.covered_domains}/{len(run.results)}",
         f"{run.quantified_domains} gave usable numbers",
         round(100 * run.covered_domains / max(1, len(run.results)))),
        ("Separate publishers", f"{run.independent_publishers}",
         f"across {run.total_sources} sources",
         min(100, run.independent_publishers * 4)),
        ("Do the numbers agree?",
         "No" if run.reconciliation and run.reconciliation.conflicts else "Yes",
         "Size estimates compared year by year",
         run.reconciliation.confidence if run.reconciliation else 0),
    ])

    st.write("")
    left, right = st.columns([1, 1], gap="large")

    with left:
        C.section("Decision", "Should we act on this?")
        C.chart(
            charts.conviction_map(
                attract.overall, attract.confidence,
                f"{run.industry}", attract.quadrant,
            ),
            "Left to right is how attractive the market is. Bottom to top is "
            "how much we trust the evidence. The dot lands in "
            f"{attract.quadrant}, meaning {_plain_quadrant(attract.quadrant)}.",
            key="conviction",
        )

    with right:
        C.section("Strengths and weaknesses", "Where this market scores well")
        C.chart(
            charts.attractiveness_radar(attract.scores),
            "Each spoke is one test, scored out of 100. The dotted ring is the "
            "pass mark. Anything inside that ring is a weakness.",
            key="radar",
        )

    C.section("What the evidence says", "")
    C.bullets(rep.situation)

    if rep.flags:
        C.section("Things that do not add up", "")
        for flag in rep.flags:
            st.markdown(
                f'<div class="conflict"><div class="c-body">{flag}</div></div>',
                unsafe_allow_html=True,
            )

    with st.expander("How each score was worked out"):
        for label, _fn, weight in DIMENSIONS:
            score = attract.scores.get(label, 0)
            st.markdown(
                f"""**{label} — {score}/100** *(counts for {weight:.0%})*
{attract.rationale.get(label, '')}
""")


# ----------------------------------------------------------------------
# 2. Market size
# ----------------------------------------------------------------------

def market_size(bundle) -> None:
    run = bundle["run"]
    rec = run.reconciliation

    if not rec or not rec.buckets:
        C.lead("No usable market-size figure came out of the sources.")
        C.prose(
            "The pages found discuss the sector without publishing a number "
            "that can be compared against others. Size this market from "
            "primary sources before relying on anything downstream.",
            muted=True,
        )
        return

    if rec.conflicts:
        worst = max(rec.conflicts, key=lambda c: c.gap_percent)
        C.lead(
            f"Published estimates of this market disagree by up to "
            f"{worst.gap_percent:,.0f}%, so there is no single correct size yet."
        )
    else:
        C.lead("Published estimates of this market broadly agree with each other.")

    contamination = contamination_ratio(run.all_money)

    C.kpi_row([
        ("Size today",
         f"${rec.anchor_value:,.1f}B" if rec.anchor_value else "—",
         f"in {rec.anchor_year}" if rec.anchor_year else "no year given", None),
        ("Size forecast",
         f"${rec.terminal_value:,.1f}B" if rec.terminal_value else "—",
         f"by {rec.terminal_year}" if rec.terminal_year else "no forecast", None),
        ("Implied growth",
         f"{rec.implied_cagr:.1f}%" if rec.implied_cagr is not None else "—",
         "a year, from those two figures", None),
        ("Years that disagree", f"{len(rec.conflicts)}",
         "estimates too far apart to average",
         100 - min(100, len(rec.conflicts) * 30)),
        ("Worldwide figures", f"{contamination:.0f}%",
         f"are global, not {run.geography}-only",
         max(0, 100 - int(contamination * 2))),
    ])

    st.write("")
    C.chart(
        charts.reconciliation_fan(rec.buckets, [c.year for c in rec.conflicts]),
        "Every dot is one published estimate, placed in the year it describes. "
        "Circles are measured figures, diamonds are forecasts. The shaded band "
        "is the gap between the highest and lowest estimate for that year — "
        "where it is wide, the sources disagree. Red dots mark those years.",
        key="fan",
    )

    if rec.conflicts:
        C.section("Where the sources disagree", "")
        C.prose(
            "A gap this large is almost never a measurement error. It usually "
            "means the two reports are counting different things — one may "
            "include hardware where the other counts only software, or one may "
            "quote a forecast as if it were an actual. Averaging them would "
            "hide the problem rather than solve it.",
            muted=True,
        )
        for conflict in rec.conflicts:
            C.conflict_card(conflict)

    if rec.stated_rates:
        C.section("Growth rates", "")
        C.chart(
            charts.rate_dispersion(rec.stated_rates, rec.implied_cagr),
            "Each dot is a growth rate a report states outright. The dashed "
            "line is the growth rate implied by the size figures above. If they "
            "are far apart, at least one report contradicts itself.",
            key="rates",
        )

    if run.all_shares:
        C.section("Market split", "")
        C.chart(
            charts.share_bars(run.all_shares),
            "Shares as each source published them. They come from different "
            "reports, so they will not add to 100% — treat them as separate "
            "readings, not slices of one pie.",
            key="shares",
        )

    with st.expander("Notes on how these figures were compared"):
        for note in rec.notes or ["No additional notes."]:
            st.markdown(f"- {note}")
        st.markdown(
            f"- {forecast_share(run.all_money):.0f}% of the figures found are "
            f"forecasts rather than measured actuals."
        )


# ----------------------------------------------------------------------
# 3. Domains
# ----------------------------------------------------------------------

def domains(bundle) -> None:
    run, rows = bundle["run"], bundle["domain_rows"]

    strong = [r for r in rows if int(r["confidence"]) >= 60]
    C.lead(
        f"{len(strong)} of the {len(rows)} research topics have evidence solid "
        f"enough to rely on."
    )

    C.chart(
        charts.evidence_heatmap(rows),
        "One row per topic. Darker means better. The five columns are separate "
        "tests: overall quality, how well the sources match the question, "
        "whether they make specific claims, whether they are about this "
        "industry, and how authoritative the publisher is.",
        key="heatmap",
    )

    with st.expander("Confidence grouped into four themes"):
        C.chart(charts.lens_bars(bundle["lens"]),
                "The thirteen topics rolled up into the four areas any market "
                "assessment needs to cover.",
                key="lens")

    st.write("")
    C.section("Topic by topic", "Each card ends with what that topic decides")

    columns = st.columns(3, gap="medium")
    for index, result in enumerate(run.results):
        with columns[index % 3]:
            C.domain_card(result)
            st.write("")


# ----------------------------------------------------------------------
# 4. Growth pools
# ----------------------------------------------------------------------

def growth_pools(bundle) -> None:
    pools, sets = bundle["pools"], bundle["pool_sets"]

    if not pools:
        C.lead("No specific opportunity was mentioned often enough to score.")
        C.prose(
            "An opportunity only counts here if two different research topics "
            "or two different publishers both raise it. That bar exists so a "
            "stray phrase in one article cannot become a strategy. Widen the "
            "search and run it again.",
            muted=True,
        )
        return

    passing = [p for p in pools if p.investable]
    if passing:
        C.lead(
            f"{passing[0].display} is the one opportunity that passes all three "
            f"tests: people want it, it can be sold profitably, and it can be reached."
        )
    else:
        C.lead(
            f"{pools[0].display} scores highest, but no opportunity yet passes "
            f"all three tests of demand, profit and reachability."
        )

    left, right = st.columns([1.1, 1], gap="large")

    with left:
        C.chart(
            charts.pool_bubble(pools),
            "Right is stronger demand. Higher is better proof it can be sold "
            "profitably. Bigger bubbles have more evidence behind them. Darker "
            "means easier to enter. The shaded corner is where all of that is true.",
            key="bubble",
        )

    with right:
        C.chart(
            venn.investability_venn(sets),
            "Three tests, three circles. An opportunity in the middle passes "
            "all three. Two out of three is the expensive mistake — strong "
            "demand you cannot profitably reach is not an opportunity.",
            key="venn",
        )

    st.write("")
    for pool in pools:
        passed = [k for k, v in pool.overlap_flags.items() if v]
        st.markdown(
            f"""<div class="glass" style="margin-bottom:0.7rem">
                  <div style="display:flex;justify-content:space-between;
                              align-items:baseline;gap:1rem">
                    <h3 style="margin:0">{pool.rank}. {pool.display}</h3>
                    <span style="color:{P.band_colour(pool.priority)};
                                 font-size:0.85rem">
                      {pool.priority}/100
                    </span>
                  </div>
                  <div style="margin-top:0.55rem">
                    {C.chips([
                        (f"Demand {pool.demand}", P.band_colour(pool.demand)),
                        (f"Can it be sold? {pool.monetisation}",
                         P.band_colour(pool.monetisation)),
                        (f"Can we reach it? {pool.access}", P.band_colour(pool.access)),
                    ])}
                  </div>
                  <p class="prose" style="margin:0.5rem 0 0">{pool.blocker}</p>
                  <p style="font-size:0.8rem;color:var(--faint);margin:0.45rem 0 0">
                    Passes {len(passed)} of 3 tests
                    {'(' + ', '.join(passed).lower() + ')' if passed else ''}
                  </p>
                </div>""",
            unsafe_allow_html=True,
        )


# ----------------------------------------------------------------------
# 5. Value chain
# ----------------------------------------------------------------------

def value_chain(bundle) -> None:
    run = bundle["run"]

    weights = flows.stage_weights_from_run(run)
    margins = flows.margin_bias_from_run(run)
    winner = flows.best_stage(weights, margins)

    C.lead(
        f"Of the five steps it takes to serve this market, the evidence points "
        f"most clearly to profit sitting in \u201c{winner.lower()}\u201d."
    )
    C.prose(
        "Every industry has a chain of steps between making something and "
        "keeping the customer who bought it. Profit is never spread evenly "
        "across them. The aim is to own the step where the money collects and "
        "buy or partner for the rest.",
        muted=True,
    )

    C.chart(
        flows.value_chain(weights, margins),
        "One bar per step. The green part is how much of what the sources say "
        "about that step concerns profit; the brown part concerns cost. Steps "
        "with more green are better places to compete. The bold label is the "
        "strongest one.",
        key="chain",
    )

    with st.expander("How much do we actually know about each step?"):
        C.chart(
            flows.chain_ladder(weights),
            "A high bar means several good sources discussed that step. A low "
            "bar means the conclusion above rests on very little for that step.",
            key="ladder",
        )

    st.write("")
    left, right = st.columns([1, 1], gap="large")

    with left:
        C.section("Competition", "How hard is it to break in?")
        C.chart(
            charts.five_forces_bars(bundle["forces"]),
            "Five standard pressures on a new entrant. Longer bars are better "
            "for you: a long bar means that pressure is weak here. The dotted "
            "line is the pass mark.",
            key="forces",
        )

    with right:
        C.section("Method", "What the research filtered out")
        C.chart(
            flows.decision_flow(bundle["funnel"]),
            "Documents found, then what survived each check. A steep drop "
            "between the first two steps is normal and healthy.",
            key="funnel",
        )


# ----------------------------------------------------------------------
# 6. Cross-domain
# ----------------------------------------------------------------------

def cross_domain(bundle) -> None:
    links, matrix = bundle["links"], bundle["matrix"]
    strong = [l for l in links if l.grade in ("STRONG", "MODERATE")]

    C.lead(
        f"{len(strong)} of {len(links)} connections between research topics are "
        f"solid enough to base a decision on."
    )
    C.prose(
        "A single finding is just research. Strategy appears when two findings "
        "are read against each other — market growth only matters once you know "
        "whether anyone is paying, and so on. Each pair below is graded by how "
        "much evidence sits behind it.",
        muted=True,
    )

    with st.expander("All connections at a glance"):
        C.chart(
            charts.linkage_heatmap(matrix["labels"], matrix["matrix"]),
            "Darker squares mean a stronger link between those two topics. The "
            "diagonal is each topic's own evidence strength.",
            key="linkage",
        )

    st.write("")

    # The strong links carry the argument. The weak ones are shown, but
    # folded away — listing ten equally is how the previous build buried
    # the three that mattered.
    headline = [l for l in links if l.grade in ("STRONG", "MODERATE")][:5]
    rest = [l for l in links if l not in headline]

    for link in headline:
        C.reasoning_chain(link)

    if not headline:
        st.info(
            "No connection between topics is backed by enough evidence to "
            "lead with. The links below are shown for completeness."
        )

    if rest:
        with st.expander(f"{len(rest)} weaker connections"):
            for link in rest:
                C.reasoning_chain(link)


# ----------------------------------------------------------------------
# 7. Risk
# ----------------------------------------------------------------------

def risk(bundle) -> None:
    rep = bundle["report"]
    gaps = bundle["gaps"]

    C.lead("These are the things that would prove this recommendation wrong.")

    left, right = st.columns([1, 1], gap="large")

    with left:
        C.chart(
            charts.risk_matrix(bundle["risks"]),
            "Right means more likely to happen. Higher means it would hurt more. "
            "Anything in the top-right corner needs watching from day one.",
            key="riskmatrix",
        )

    with right:
        C.section("What would change the answer", "")
        C.bullets(rep.falsifiers, P.CLAY)

    if gaps:
        st.write("")
        C.section("Weakest research", f"{len(gaps)} topics need more work")
        for gap in gaps[:6]:
            st.markdown(
                f"""<div class="glass tight" style="margin-bottom:0.5rem">
                      <b style="font-size:0.9rem">{gap['domain']}</b>
                      <span style="color:{P.band_colour(gap['confidence'])};
                                   font-size:0.8rem"> — {gap['confidence']}/100</span>
                      <p style="font-size:0.83rem;color:var(--muted);
                                margin:0.3rem 0 0;line-height:1.55">
                        {'; '.join(gap['reasons']).capitalize()}.
                        This is what it holds up: {gap['decision'].lower()}
                      </p>
                    </div>""",
                unsafe_allow_html=True,
            )


# ----------------------------------------------------------------------
# 8. Sources
# ----------------------------------------------------------------------

def sources(bundle) -> None:
    run = bundle["run"]

    C.lead(
        f"Every claim in this report traces back to one of these "
        f"{run.total_sources} sources."
    )
    C.prose(
        "Sources are scored on four things kept deliberately separate: who "
        "published it, how well it matches the question, whether it makes "
        "specific claims, and whether it is really about this industry.",
        muted=True,
    )

    for result in run.results:
        if not result.sources:
            continue
        with st.expander(f"{result.name} — {result.source_count} sources"):
            for source in result.sources:
                C.source_row(source)


# ----------------------------------------------------------------------
# 9. Report
# ----------------------------------------------------------------------

def report(bundle) -> None:
    run, attract, pools, rep = (
        bundle["run"], bundle["attract"], bundle["pools"], bundle["report"],
    )

    C.verdict_card(rep.recommendation, attract)

    st.write("")
    C.section("The market", "")
    C.prose(rep.size_statement)

    C.section("Where to compete", "")
    C.bullets(rep.where_to_play, P.SLATE)

    C.section("How to win there", "")
    C.bullets(rep.how_to_win, P.SAGE)

    C.section("What would change this decision", "")
    C.bullets(rep.falsifiers, P.CLAY)

    with st.expander("How confident is this, and on what basis?"):
        st.write(rep.evidence_statement)

    st.write("")
    st.download_button(
        "Download the full report",
        data=report_mod.to_markdown(rep, run, attract, pools),
        file_name=f"{run.industry.lower().replace(' ', '-')}-"
                  f"{run.geography.lower().replace(' ', '-')}-report.md",
        mime="text/markdown",
    )


__all__ = [
    "cross_domain", "domains", "executive", "growth_pools", "market_size",
    "report", "risk", "sources", "value_chain",
]
