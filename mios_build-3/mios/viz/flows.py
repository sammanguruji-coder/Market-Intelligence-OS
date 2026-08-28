"""
Value-chain and process visuals.

The Sankey this replaces was the weakest chart in the product. It showed
flow without showing a conclusion: a reader could study it for a minute
and still not know what to do. Sankeys are good at conservation of
quantity, and nothing here is a conserved quantity — "evidence weight"
splitting into "cost" and "margin" is a metaphor, and drawing a metaphor
as a flow diagram invites the reader to read precision that is not there.

What replaces it answers one question directly: at which step of the
chain does the money end up, and how confident are we? Each step gets a
single horizontal bar split into the share of evidence pointing at margin
versus cost, sorted so the best place to compete sits at the top, with
the winner labelled outright.
"""

from __future__ import annotations

from typing import Dict, List, Sequence

from . import palette as P

try:  # pragma: no cover
    import plotly.graph_objects as go
    AVAILABLE = True
except Exception:  # pragma: no cover
    go = None  # type: ignore
    AVAILABLE = False


def _layout(fig, height: int, title: str = "", legend: bool = False, margin=None):
    fig.update_layout(
        height=height,
        xaxis=dict(gridcolor=P.GRID, linecolor=P.GRID,
                   tickfont=dict(family=P.FONT_BODY, size=11, color=P.TEXT_MUTED),
                   title_font=dict(family=P.FONT_BODY, size=11, color=P.TEXT_MUTED)),
        yaxis=dict(gridcolor="rgba(0,0,0,0)", linecolor=P.GRID,
                   tickfont=dict(family=P.FONT_BODY, size=12, color=P.TEXT)),
        margin=margin or dict(l=8, r=8, t=34 if legend else 14, b=10),
        showlegend=legend,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0,
                    bgcolor="rgba(0,0,0,0)",
                    font=dict(family=P.FONT_BODY, size=11, color=P.TEXT_MUTED)),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family=P.FONT_BODY, color=P.TEXT, size=12),
        hoverlabel=dict(
            bgcolor=P.SURFACE_HI, bordercolor=P.GLASS_EDGE,
            font=dict(family=P.FONT_BODY, size=12, color=P.TEXT),
        ),
    )
    fig.update_xaxes(gridcolor=P.GRID, zerolinecolor=P.GRID, linecolor=P.GRID,
                     tickfont=dict(size=11, color=P.TEXT_MUTED),
                     title_font=dict(size=11, color=P.TEXT_MUTED))
    fig.update_yaxes(gridcolor="rgba(0,0,0,0)", zerolinecolor=P.GRID, linecolor=P.GRID,
                     tickfont=dict(size=12, color=P.TEXT),
                     title_font=dict(size=11, color=P.TEXT_MUTED))
    return fig


STAGES = [
    ("Making the product", "Content, IP, product development"),
    ("Running the platform", "Infrastructure, apps, delivery"),
    ("Winning customers", "Marketing, sales, distribution"),
    ("Proving the outcome", "Assessment, certification, results"),
    ("Keeping customers", "Support, service, renewals"),
]

STAGE_DOMAINS = {
    "Making the product": [4, 9],
    "Running the platform": [9, 7],
    "Winning customers": [10, 5],
    "Proving the outcome": [12, 11],
    "Keeping customers": [13, 10],
}

MARGIN_DOMAINS = {
    "Making the product": [4],
    "Running the platform": [9],
    "Winning customers": [10, 5],
    "Proving the outcome": [12, 11],
    "Keeping customers": [13],
}


def stage_weights_from_run(run) -> Dict[str, int]:
    """How much evidence we have about each step of the chain."""
    out: Dict[str, int] = {}
    for stage, domain_ids in STAGE_DOMAINS.items():
        scores = [
            run.by_id(d).confidence for d in domain_ids
            if run.by_id(d) and run.by_id(d).confidence
        ]
        out[stage] = round(sum(scores) / len(scores)) if scores else 30
    return out


def margin_bias_from_run(run) -> Dict[str, int]:
    """
    How strongly the evidence points at margin rather than cost for each
    step, read from margin vocabulary in the relevant domains rather than
    assumed from a template.
    """
    from ..core.analytics import MARGIN_CUES, _domain_text, _lexicon_hits

    out: Dict[str, int] = {}
    for stage, domain_ids in MARGIN_DOMAINS.items():
        text = _domain_text(run, domain_ids)
        hits = _lexicon_hits(text, MARGIN_CUES)
        out[stage] = max(12, min(88, 25 + hits * 12))
    return out


def best_stage(weights: Dict[str, int], margin_bias: Dict[str, int]) -> str:
    """The step the evidence most supports competing in."""
    if not weights:
        return ""
    return max(
        weights,
        key=lambda s: 0.6 * margin_bias.get(s, 40) + 0.4 * weights.get(s, 30),
    )


def value_chain(weights: Dict[str, int], margin_bias: Dict[str, int]):
    """
    Where cost sits against where margin sits, stage by stage.

    This replaces a Sankey. The Sankey was accurate and unreadable: it
    showed how much evidence flowed into each stage, which is a fact
    about the research rather than about the business. The question a
    reader actually has is "which stage should we own?", and that is
    answered by putting cost and margin on opposite sides of a shared
    zero and letting the reader see which stage leans right.

    Cost extends left, margin extends right. The stage that leans
    furthest right is the control point.
    """
    if not AVAILABLE:
        return None

    stage_names = [s[0] for s in STAGES]
    ordered = list(reversed(stage_names))     # top-to-bottom reading order

    costs, margins, labels = [], [], []
    for name in ordered:
        weight = max(10, weights.get(name, 30))
        bias = max(0, min(100, margin_bias.get(name, 45)))
        margin = weight * (bias / 100)
        costs.append(-(weight - margin))
        margins.append(margin)
        labels.append(name)

    control = max(stage_names, key=lambda n: margin_bias.get(n, 0))

    fig = go.Figure()

    fig.add_trace(go.Bar(
        y=labels, x=costs, orientation="h", name="Cost sits here",
        marker=dict(color=P.AMBER, line=dict(color="rgba(255,255,255,0.8)", width=1)),
        opacity=0.75,
        hovertemplate="<b>%{y}</b><br>Cost weight %{customdata:.0f}<extra></extra>",
        customdata=[abs(c) for c in costs],
    ))
    fig.add_trace(go.Bar(
        y=labels, x=margins, orientation="h", name="Margin sits here",
        marker=dict(color=P.SAGE, line=dict(color="rgba(255,255,255,0.8)", width=1)),
        opacity=0.9,
        hovertemplate="<b>%{y}</b><br>Margin weight %{x:.0f}<extra></extra>",
    ))

    fig.add_vline(x=0, line=dict(color=P.TEXT_MUTED, width=1))

    fig.add_annotation(
        x=max(margins) * 0.95 if margins else 1,
        y=control,
        text="control point",
        showarrow=True, arrowhead=0, ax=42, ay=0,
        font=dict(family=P.FONT_BODY, size=11, color=P.SAGE),
        arrowcolor=P.SAGE,
    )

    fig.update_layout(barmode="relative", bargap=0.42)
    fig.update_xaxes(
        title="← cost concentrates here          margin concentrates here →",
        zeroline=False, showticklabels=False,
    )
    return _layout(fig, 380, legend=True)


def stage_weights_from_run(run) -> Dict[str, int]:
    """How much evidence we have about each step of the chain."""
    out: Dict[str, int] = {}
    for stage, domain_ids in STAGE_DOMAINS.items():
        scores = [
            run.by_id(d).confidence for d in domain_ids
            if run.by_id(d) and run.by_id(d).confidence
        ]
        out[stage] = round(sum(scores) / len(scores)) if scores else 30
    return out


def margin_bias_from_run(run) -> Dict[str, int]:
    """
    How strongly the evidence points at margin rather than cost for each
    step, read from margin vocabulary in the relevant domains rather than
    assumed from a template.
    """
    from ..core.analytics import MARGIN_CUES, _domain_text, _lexicon_hits

    out: Dict[str, int] = {}
    for stage, domain_ids in MARGIN_DOMAINS.items():
        text = _domain_text(run, domain_ids)
        hits = _lexicon_hits(text, MARGIN_CUES)
        out[stage] = max(12, min(88, 25 + hits * 12))
    return out


def best_stage(weights: Dict[str, int], margin_bias: Dict[str, int]) -> str:
    """The step the evidence most supports competing in."""
    if not weights:
        return ""
    return max(
        weights,
        key=lambda s: 0.6 * margin_bias.get(s, 40) + 0.4 * weights.get(s, 30),
    )


def value_chain(weights: Dict[str, int], margin_bias: Dict[str, int]):
    """
    Where the money stays, stage by stage.

    This replaces a Sankey. A Sankey looked impressive and told you
    almost nothing: readers could not tell whether a thick ribbon meant
    "lots of profit here" or "lots of evidence here", and the two got
    visually confused.

    This chart answers one question instead. Each row is a stage of the
    business. The bar runs left for the share of that stage that is cost
    and right for the share that is margin. The further right a stage
    sits, the more of the money it keeps. That is the whole reading.
    """
    if not AVAILABLE:
        return None

    stage_names = [s[0] for s in STAGES]
    rows = list(reversed(stage_names))          # first stage at the top

    margins = [max(0, min(100, margin_bias.get(n, 45))) for n in rows]
    costs = [100 - m for m in margins]

    fig = go.Figure()

    fig.add_trace(go.Bar(
        y=rows, x=[-c for c in costs], orientation="h",
        name="Goes out as cost",
        marker=dict(color=P.AMBER, opacity=0.72,
                    line=dict(color="rgba(255,255,255,0.9)", width=1)),
        hovertemplate="<b>%{y}</b><br>%{customdata}% of the money here is cost<extra></extra>",
        customdata=costs,
    ))
    fig.add_trace(go.Bar(
        y=rows, x=margins, orientation="h",
        name="Stays as margin",
        marker=dict(color=P.MINT, opacity=0.85,
                    line=dict(color="rgba(255,255,255,0.9)", width=1)),
        hovertemplate="<b>%{y}</b><br>%{x}% of the money here stays as margin<extra></extra>",
    ))

    # Name the winner, so the chart states its own conclusion.
    best = max(range(len(rows)), key=lambda i: margins[i])
    fig.add_annotation(
        x=margins[best] + 6, y=rows[best],
        text="best place to sit", showarrow=True, arrowhead=0,
        arrowcolor=P.MINT, ax=42, ay=0,
        font=dict(family=P.FONT_MONO, size=10, color=P.MINT),
    )

    fig.add_vline(x=0, line=dict(color=P.AXIS, width=1))
    fig.update_layout(barmode="relative", bargap=0.35)
    fig.update_xaxes(
        range=[-100, 100],
        tickvals=[-100, -50, 0, 50, 100],
        ticktext=["100% cost", "50%", "break-even", "50%", "100% margin"],
        title="",
    )
    fig.update_yaxes(title="")
    return _layout(fig, 400, legend=True)


def stage_weights_from_run(run) -> Dict[str, int]:
    """How much evidence we have about each step of the chain."""
    out: Dict[str, int] = {}
    for stage, domain_ids in STAGE_DOMAINS.items():
        scores = [
            run.by_id(d).confidence for d in domain_ids
            if run.by_id(d) and run.by_id(d).confidence
        ]
        out[stage] = round(sum(scores) / len(scores)) if scores else 30
    return out


def margin_bias_from_run(run) -> Dict[str, int]:
    """
    How strongly the evidence points at margin rather than cost for each
    step, read from margin vocabulary in the relevant domains rather than
    assumed from a template.
    """
    from ..core.analytics import MARGIN_CUES, _domain_text, _lexicon_hits

    out: Dict[str, int] = {}
    for stage, domain_ids in MARGIN_DOMAINS.items():
        text = _domain_text(run, domain_ids)
        hits = _lexicon_hits(text, MARGIN_CUES)
        out[stage] = max(12, min(88, 25 + hits * 12))
    return out


def best_stage(weights: Dict[str, int], margin_bias: Dict[str, int]) -> str:
    """The step the evidence most supports competing in."""
    if not weights:
        return ""
    return max(
        weights,
        key=lambda s: 0.6 * margin_bias.get(s, 40) + 0.4 * weights.get(s, 30),
    )


def chain_ladder(weights: Dict[str, int]):
    """How much we actually know about each step, as a simple bar."""
    if not AVAILABLE or not weights:
        return None

    stages = list(weights.keys())
    values = [weights[s] for s in stages]

    fig = go.Figure(go.Bar(
        y=stages, x=values, orientation="h",
        marker=dict(color=[P.band_colour(v) for v in values],
                    line=dict(color="rgba(255,255,255,0.9)", width=1)),
        text=[f"{v}" for v in values], textposition="outside",
        textfont=dict(size=11, color=P.TEXT_MUTED),
        hovertemplate="<b>%{y}</b><br>Evidence strength %{x} out of 100<extra></extra>",
    ))
    fig.update_xaxes(range=[0, 112], title="How much we know about this step (0–100)")
    return _layout(fig, 300, margin=dict(l=8, r=8, t=14, b=40))


def decision_flow(stages: Sequence[tuple]):
    """
    How many documents survived each stage of filtering.

    A funnel is the right shape here because this genuinely is a
    conserved quantity being reduced at each step.
    """
    if not AVAILABLE or not stages:
        return None

    labels = [s[0] for s in stages]
    counts = [s[1] for s in stages]
    notes = [s[2] for s in stages]

    fig = go.Figure(go.Funnel(
        y=labels, x=counts,
        textinfo="value",
        textfont=dict(size=12, color=P.TEXT),
        marker=dict(
            color=[P.SPECTRUM[i % len(P.SPECTRUM)] for i in range(len(labels))],
            line=dict(color="rgba(255,255,255,0.9)", width=1),
        ),
        connector=dict(line=dict(color=P.GRID, width=1)),
        customdata=notes,
        hovertemplate="<b>%{y}</b>: %{x}<br>%{customdata}<extra></extra>",
    ))
    return _layout(fig, 330)


__all__ = [
    "AVAILABLE", "MARGIN_DOMAINS", "STAGES", "STAGE_DOMAINS", "best_stage",
    "chain_ladder", "decision_flow", "margin_bias_from_run", "value_chain",
    "stage_weights_from_run",
]
