"""
Interface components.

Small, composable renderers so section code reads as layout rather than
as HTML. Every one writes markup that matches the classes defined in
`theme.css()`.
"""

from __future__ import annotations

import html
from typing import Dict, Optional, Sequence

import streamlit as st

from ..viz import palette as P
from ..viz.charts import AVAILABLE as CHARTS_AVAILABLE


def _esc(value: object) -> str:
    return html.escape(str(value or ""))


# ----------------------------------------------------------------------
# Structure
# ----------------------------------------------------------------------

def section(eyebrow: str, title: str, subtitle: str = "") -> None:
    st.markdown(
        f"""<div class="section-head">
              <span class="eyebrow">{_esc(eyebrow)}</span>
              <h2>{_esc(title)}</h2>
              {f'<p class="sub">{_esc(subtitle)}</p>' if subtitle else ''}
            </div>""",
        unsafe_allow_html=True,
    )


def lead(text: str) -> None:
    """One sentence that says what this screen concluded."""
    st.markdown(f'<p class="lead">{_esc(text)}</p>', unsafe_allow_html=True)


def prose(text: str, muted: bool = False) -> None:
    cls = "prose-muted" if muted else "prose"
    st.markdown(f'<p class="{cls}">{_esc(text)}</p>', unsafe_allow_html=True)


def read_note(text: str) -> None:
    """How to read the chart above. Kept short and literal."""
    st.markdown(f'<p class="readnote">{_esc(text)}</p>', unsafe_allow_html=True)


def glass(body_html: str, tight: bool = False) -> None:
    cls = "glass tight" if tight else "glass"
    st.markdown(f'<div class="{cls}">{body_html}</div>', unsafe_allow_html=True)


def chip(label: str, colour: str = P.AQUA) -> str:
    return f'<span class="chip" style="color:{colour}">{_esc(label)}</span>'


def chips(items: Sequence[tuple]) -> str:
    return "".join(chip(label, colour) for label, colour in items)


# ----------------------------------------------------------------------
# Hero and spine
# ----------------------------------------------------------------------

def hero(industry: str, geography: str, objective: str, lede: str) -> None:
    st.markdown(
        f"""<div class="hero">
              <span class="eyebrow">Market intelligence · decision system</span>
              <h1>{_esc(industry)} · {_esc(geography)}</h1>
              <p class="lede">{_esc(lede)}</p>
              <div style="margin-top:1rem">
                {chips([(objective, P.AQUA),
                        ("evidence-led", P.INDIGO),
                        ("reconciled estimates", P.VIOLET)])}
              </div>
            </div>""",
        unsafe_allow_html=True,
    )


def evidence_spine(rows: Sequence[Dict[str, object]]) -> None:
    """
    The signature element: thirteen glass nodes whose fill height and
    colour are each domain's evidence confidence. Reading it left to
    right tells you where the research is thin before you read a word.
    """
    nodes = []
    for row in rows:
        score = int(row.get("confidence", 0) or 0)
        colour = P.LENS_COLOURS.get(str(row.get("lens")), P.AQUA)
        height = max(6, score)
        nodes.append(
            f"""<div class="spine-node" title="{_esc(row['domain'])} — confidence {score}/100">
                  <div class="spine-fill"
                       style="height:{height}%;
                              background:linear-gradient(180deg,{colour},rgba(255,255,255,0.05));
                              opacity:{0.35 + score / 160:.2f}"></div>
                </div>"""
        )

    labels = "".join(
        f'<div class="spine-label" style="flex:1">{_esc(row["code"])}</div>'
        for row in rows
    )
    legend = "".join(
        f'<span><i style="background:{colour}"></i>{_esc(lens)}</span>'
        for lens, colour in P.LENS_COLOURS.items()
    )

    st.markdown(
        f"""<div class="glass">
              <span class="eyebrow dim">Evidence spine · confidence by domain</span>
              <div class="spine">{''.join(nodes)}</div>
              <div style="display:flex;gap:6px">{labels}</div>
              <div class="spine-legend">{legend}</div>
            </div>""",
        unsafe_allow_html=True,
    )


# ----------------------------------------------------------------------
# Metrics
# ----------------------------------------------------------------------

def kpi(label: str, value: str, note: str = "", score: Optional[int] = None) -> None:
    colour = P.band_colour(score) if score is not None else P.TEXT
    bar = ""
    if score is not None:
        bar = (
            f'<div class="k-bar"><span style="width:{max(2, min(100, score))}%;'
            f'background:{colour}"></span></div>'
        )
    st.markdown(
        f"""<div class="kpi">
              <div class="k-label">{_esc(label)}</div>
              <div class="k-value" style="color:{colour}">{_esc(value)}</div>
              <div class="k-note">{_esc(note)}</div>
              {bar}
            </div>""",
        unsafe_allow_html=True,
    )


def kpi_row(items: Sequence[tuple]) -> None:
    """items: (label, value, note, score|None)"""
    columns = st.columns(len(items), gap="small")
    for column, item in zip(columns, items):
        with column:
            kpi(*item)


# ----------------------------------------------------------------------
# Domain card
# ----------------------------------------------------------------------

def domain_card(result) -> None:
    colour = P.LENS_COLOURS.get(result.lens, P.AQUA)
    grade_colour = P.GRADE_COLOURS.get(result.grade, P.TEXT_MUTED)

    # Two findings per card, not four. Thirteen cards times four quotes
    # is a wall nobody reads; the rest stay one click away in the source
    # register, where someone checking a claim would look anyway.
    findings = ""
    shown = list(zip(result.findings, result.finding_refs + [""] * 4))[:2]
    for text, ref in shown:
        snippet = text if len(text) <= 185 else text[:185].rsplit(" ", 1)[0] + "…"
        findings += (
            f'<div class="finding">{_esc(snippet)} '
            f'<span class="ref">[{_esc(ref)}]</span></div>'
        )
    hidden = len(result.findings) - len(shown)
    if hidden > 0:
        findings += (
            f'<div class="finding" style="color:var(--faint);font-size:0.78rem">'
            f'+{hidden} more finding(s) in the Sources tab</div>'
        )
    if not findings:
        findings = (
            '<div class="finding" style="color:var(--faint)">'
            "No claim cleared the signal threshold in this domain.</div>"
        )

    st.markdown(
        f"""<div class="dcard" style="border-left-color:{colour}">
              <span class="eyebrow" style="color:{colour}">
                {_esc(result.code)} · {_esc(result.lens)}
              </span>
              <h3>{_esc(result.name)}</h3>
              <div>
                {chip(result.grade, grade_colour)}
                {chip(f"confidence {result.confidence}", P.band_colour(result.confidence))}
                {chip(f"{result.source_count} sources", P.TEXT_FAINT)}
                {chip("quantified" if result.quantified else "qualitative",
                      P.MINT if result.quantified else P.TEXT_FAINT)}
              </div>
              {findings}
              <div class="imp">{_esc(result.implication)}</div>
            </div>""",
        unsafe_allow_html=True,
    )


# ----------------------------------------------------------------------
# Reasoning chain
# ----------------------------------------------------------------------

def reasoning_chain(link) -> None:
    grade_colour = P.GRADE_COLOURS.get(link.grade, P.TEXT_MUTED)
    because = "<br><br>".join(_esc(b) for b in link.because) or "No usable evidence."
    refs = " ".join(f"[{_esc(r)}]" for r in link.refs)

    st.markdown(
        f"""<div class="glass" style="margin-bottom:0.8rem">
              <div style="display:flex;justify-content:space-between;align-items:center">
                <h3 style="margin:0">{_esc(link.title)}</h3>
                {chip(link.grade, grade_colour)}
              </div>
              <div class="chain">
                <div class="chain-step" style="border-color:{P.AQUA}">
                  <div class="step-label" style="color:{P.AQUA}">Because</div>
                  <div class="step-body">{because}
                    <span class="ref" style="color:{P.VIOLET}">{refs}</span>
                  </div>
                </div>
                <div class="chain-step" style="border-color:{P.VIOLET}">
                  <div class="step-label" style="color:{P.VIOLET}">Therefore</div>
                  <div class="step-body">{_esc(link.proposition)}</div>
                </div>
                <div class="chain-step" style="border-color:{P.MINT}">
                  <div class="step-label" style="color:{P.MINT}">Decision</div>
                  <div class="step-body">{_esc(link.decision)}</div>
                </div>
              </div>
            </div>""",
        unsafe_allow_html=True,
    )


# ----------------------------------------------------------------------
# Conflicts and verdict
# ----------------------------------------------------------------------

def conflict_card(conflict) -> None:
    st.markdown(
        f"""<div class="conflict">
              <div class="c-head">Definitional conflict · {_esc(conflict.year)}</div>
              <div class="c-body">
                <b>{_esc(conflict.headline)}</b><br><br>
                Lower estimate: {_esc(conflict.low_snippet)}<br><br>
                Higher estimate: {_esc(conflict.high_snippet)}<br><br>
                These are not averaged. A gap this size is a difference of
                definition, period or inclusions, and it has to be resolved
                by reading the methodology of each source.
              </div>
            </div>""",
        unsafe_allow_html=True,
    )


def verdict_card(recommendation, attract) -> None:
    colour = P.QUADRANT_COLOURS.get(attract.quadrant, P.AQUA)
    conditions = "".join(
        f'<li style="margin-bottom:0.35rem">{_esc(c)}</li>'
        for c in recommendation.conditions
    )
    conditions_block = (
        f"""<div style="margin-top:1.1rem;padding-top:0.9rem;
                        border-top:1px solid var(--edge-soft)">
              <span class="eyebrow dim">Conditions</span>
              <ul style="margin:0.4rem 0 0;padding-left:1.1rem;
                         font-size:0.84rem;color:var(--muted);line-height:1.55">
                {conditions}
              </ul>
            </div>"""
        if conditions else ""
    )

    st.markdown(
        f"""<div class="verdict">
              <span class="eyebrow">Recommendation</span>
              <div class="v-word" style="color:{colour}">{_esc(recommendation.verdict)}</div>
              <div class="v-posture">{_esc(recommendation.posture)}</div>
              <div style="margin-top:0.9rem">
                {chips([
                    (f"attractiveness {attract.overall}", P.band_colour(attract.overall)),
                    (f"confidence {attract.confidence}", P.band_colour(attract.confidence)),
                    (attract.quadrant, colour),
                ])}
              </div>
              <div class="v-reason">{_esc(recommendation.reasoning)}</div>
              {conditions_block}
            </div>""",
        unsafe_allow_html=True,
    )


# ----------------------------------------------------------------------
# Sources
# ----------------------------------------------------------------------

def source_row(source) -> None:
    st.markdown(
        f"""<div class="srow">
              <div class="s-ref">{_esc(source.ref)}</div>
              <div style="flex:1">
                <div class="s-title">
                  <a href="{_esc(source.url)}" target="_blank">{_esc(source.title)}</a>
                </div>
                <div class="s-host">
                  {_esc(source.host)} · {_esc(source.tier)} ·
                  authority {source.authority} · relevance {source.relevance} ·
                  fit {source.industry_fit}
                </div>
              </div>
            </div>""",
        unsafe_allow_html=True,
    )


# ----------------------------------------------------------------------
# Charts
# ----------------------------------------------------------------------

def readout(text: str) -> None:
    """
    A plain-English sentence saying what the chart above actually shows.

    Charts do not explain themselves. A caption that repeats the axis
    labels is worse than none, so these say what to conclude.
    """
    st.markdown(f'<div class="readout">{text}</div>', unsafe_allow_html=True)


def chart(fig, caption: str = "", key: Optional[str] = None) -> None:
    """Render a figure, or an honest explanation when it cannot render."""
    if fig is None:
        if not CHARTS_AVAILABLE:
            st.info(
                "Charts need Plotly. Install it into the same interpreter "
                "that runs Streamlit, then reload."
            )
        else:
            st.caption("Not enough extracted data to draw this yet.")
        return

    # Streamlit renamed this argument; support both so the app runs on
    # whatever version the user already has installed.
    try:
        st.plotly_chart(fig, width="stretch", key=key,
                        config={"displayModeBar": False})
    except TypeError:
        st.plotly_chart(fig, use_container_width=True, key=key,
                        config={"displayModeBar": False})
    if caption:
        read_note(caption)


def bullets(items: Sequence[str], colour: str = P.AQUA) -> None:
    body = "".join(
        f"""<div style="display:flex;gap:0.7rem;margin-bottom:0.6rem">
              <div style="width:3px;background:{colour};border-radius:2px;
                          flex-shrink:0;opacity:0.7"></div>
              <div style="font-size:0.86rem;line-height:1.58;color:var(--text)">
                {_esc(item)}
              </div>
            </div>"""
        for item in items
    )
    st.markdown(body, unsafe_allow_html=True)


__all__ = [
    "bullets", "chart", "lead", "prose", "read_note", "chip", "chips", "conflict_card", "domain_card",
    "evidence_spine", "glass", "hero", "kpi", "kpi_row", "reasoning_chain",
    "section", "source_row", "verdict_card",
]
