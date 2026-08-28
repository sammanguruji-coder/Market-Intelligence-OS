"""
Chart factory.

Every figure in the product is built here so that layout, typography and
colour are decided once. Each function takes plain data and returns a
Plotly figure; none of them touch Streamlit, which keeps them testable
and reusable.

Import is guarded: if Plotly is absent the module still imports and
`AVAILABLE` is False, so the UI can show an install instruction instead
of crashing.
"""

from __future__ import annotations

import math
from typing import Dict, List, Optional, Sequence, Tuple

from . import palette as P

try:  # pragma: no cover - optional dependency
    import plotly.graph_objects as go
    AVAILABLE = True
except Exception:  # pragma: no cover
    go = None  # type: ignore
    AVAILABLE = False


# ----------------------------------------------------------------------
# Shared layout
# ----------------------------------------------------------------------

def _layout(fig, height: int = 380, title: str = "", legend: bool = False, margin=None):
    fig.update_layout(
        height=height,
        margin=margin or dict(l=12, r=12, t=42 if title else 14, b=12),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family=P.FONT_BODY, color=P.TEXT, size=12),
        title=dict(
            text=title,
            font=dict(family=P.FONT_DISPLAY, size=15, color=P.TEXT),
            x=0, xanchor="left", y=0.97,
        ) if title else None,
        showlegend=legend,
        legend=dict(
            orientation="h", yanchor="bottom", y=1.01, x=0,
            bgcolor="rgba(0,0,0,0)",
            font=dict(family=P.FONT_MONO, size=10, color=P.TEXT_MUTED),
        ),
        hoverlabel=dict(
            bgcolor=P.SURFACE_HI,
            bordercolor=P.GLASS_EDGE,
            font=dict(family=P.FONT_BODY, size=12, color=P.TEXT),
        ),
    )
    fig.update_xaxes(
        gridcolor=P.GRID, zerolinecolor=P.GRID, linecolor=P.GRID,
        tickfont=dict(family=P.FONT_MONO, size=10, color=P.TEXT_FAINT),
        title_font=dict(family=P.FONT_MONO, size=10, color=P.TEXT_FAINT),
    )
    fig.update_yaxes(
        gridcolor=P.GRID, zerolinecolor=P.GRID, linecolor=P.GRID,
        tickfont=dict(family=P.FONT_MONO, size=10, color=P.TEXT_FAINT),
        title_font=dict(family=P.FONT_MONO, size=10, color=P.TEXT_FAINT),
    )
    return fig


# ----------------------------------------------------------------------
# 1. Conviction map — the headline decision visual
# ----------------------------------------------------------------------

def conviction_map(attractiveness: int, confidence: int, label: str, quadrant: str):
    """
    Attractiveness against evidence confidence.

    The single chart that fixes the old model's category error: a market
    can be attractive and badly evidenced, and that combination has its
    own name and its own response.
    """
    if not AVAILABLE:
        return None

    fig = go.Figure()

    quads = [
        (0, 0, 58, 60, "PARK", P.AMBER, "Low attractiveness · low confidence"),
        (58, 0, 100, 60, "VALIDATE", P.AQUA, "Attractive · thin evidence"),
        (0, 60, 58, 100, "PASS", P.TEXT_FAINT, "Well evidenced · unattractive"),
        (58, 60, 100, 100, "ACT", P.MINT, "Attractive · well evidenced"),
    ]

    for x0, y0, x1, y1, name, colour, _note in quads:
        active = name == quadrant
        fig.add_shape(
            type="rect", x0=x0, y0=y0, x1=x1, y1=y1,
            line=dict(color=P.GRID, width=1),
            fillcolor=colour, opacity=0.16 if active else 0.045, layer="below",
        )
        fig.add_annotation(
            x=(x0 + x1) / 2, y=y1 - 5, text=name, showarrow=False,
            font=dict(
                family=P.FONT_MONO, size=11 if active else 10,
                color=colour if active else P.TEXT_FAINT,
            ),
        )

    fig.add_trace(
        go.Scatter(
            x=[attractiveness], y=[confidence],
            mode="markers+text",
            marker=dict(
                size=30, color=P.QUADRANT_COLOURS.get(quadrant, P.AQUA),
                line=dict(color="rgba(255,255,255,0.85)", width=2),
                opacity=0.95,
            ),
            text=[label], textposition="top center",
            textfont=dict(family=P.FONT_DISPLAY, size=13, color=P.TEXT),
            hovertemplate=(
                f"<b>{label}</b><br>Attractiveness %{{x}}/100"
                f"<br>Confidence %{{y}}/100<extra></extra>"
            ),
        )
    )

    fig.update_xaxes(range=[0, 100], title="Market attractiveness", dtick=25)
    fig.update_yaxes(range=[0, 100], title="Evidence confidence", dtick=25)
    return _layout(fig, height=420)


# ----------------------------------------------------------------------
# 2. Reconciliation fan — competing size estimates
# ----------------------------------------------------------------------

def reconciliation_fan(buckets, conflicts_years: Sequence[int] = ()):
    """
    Every published size estimate, plotted where it was published, with
    the within-year spread drawn as a band. Deliberately never a single
    line: a single line is the lie the old report told.
    """
    if not AVAILABLE or not buckets:
        return None

    years = [b.year for b in buckets]
    lows = [b.low for b in buckets]
    highs = [b.high for b in buckets]
    medians = [b.median for b in buckets]

    fig = go.Figure()

    fig.add_trace(go.Scatter(
        x=years + years[::-1], y=highs + lows[::-1],
        fill="toself", fillcolor="rgba(110,123,255,0.13)",
        line=dict(color="rgba(0,0,0,0)"), hoverinfo="skip",
        name="Published range", showlegend=True,
    ))

    fig.add_trace(go.Scatter(
        x=years, y=medians, mode="lines",
        line=dict(color=P.INDIGO, width=2, dash="dot"),
        name="Median of published estimates",
        hovertemplate="%{x}: US$%{y:.1f}B median<extra></extra>",
    ))

    for bucket in buckets:
        conflicted = bucket.year in conflicts_years
        for point in bucket.points:
            fig.add_trace(go.Scatter(
                x=[bucket.year], y=[point.usd_billions],
                mode="markers",
                marker=dict(
                    size=13,
                    color=P.CORAL if conflicted else P.AQUA,
                    symbol="diamond" if point.kind == "forecast" else "circle",
                    line=dict(color="rgba(255,255,255,0.6)", width=1),
                    opacity=0.92,
                ),
                showlegend=False,
                hovertemplate=(
                    f"<b>US${point.usd_billions:.1f}B</b> · {bucket.year}"
                    f"<br>{point.source_host or 'source'}"
                    f"<br>{point.kind} · scope: {point.scope}<extra></extra>"
                ),
            ))

    fig.update_xaxes(title="Year", dtick=1)
    fig.update_yaxes(title="Market size (US$ billion)", rangemode="tozero")
    return _layout(fig, height=400, legend=True)


# ----------------------------------------------------------------------
# 3. Attractiveness radar
# ----------------------------------------------------------------------

def attractiveness_radar(scores: Dict[str, int]):
    if not AVAILABLE or not scores:
        return None

    labels = list(scores.keys())
    values = [scores[k] for k in labels]

    fig = go.Figure()
    fig.add_trace(go.Scatterpolar(
        r=values + values[:1], theta=labels + labels[:1],
        fill="toself", fillcolor="rgba(76,224,216,0.17)",
        line=dict(color=P.AQUA, width=2),
        marker=dict(size=7, color=P.AQUA),
        hovertemplate="%{theta}: %{r}/100<extra></extra>",
        name="Score",
    ))
    fig.add_trace(go.Scatterpolar(
        r=[58] * (len(labels) + 1), theta=labels + labels[:1],
        line=dict(color=P.TEXT_FAINT, width=1, dash="dot"),
        hoverinfo="skip", name="Hurdle (58)",
    ))

    fig.update_layout(
        polar=dict(
            bgcolor="rgba(255,255,255,0.025)",
            radialaxis=dict(
                range=[0, 100], gridcolor=P.GRID, linecolor=P.GRID,
                tickfont=dict(family=P.FONT_MONO, size=9, color=P.TEXT_FAINT),
            ),
            angularaxis=dict(
                gridcolor=P.GRID, linecolor=P.GRID,
                tickfont=dict(family=P.FONT_MONO, size=9, color=P.TEXT_MUTED),
            ),
        )
    )
    return _layout(fig, height=400, legend=True)


# ----------------------------------------------------------------------
# 4. Five forces
# ----------------------------------------------------------------------

def five_forces_bars(forces: Dict[str, int]):
    """High bar = force is favourable to a new entrant."""
    if not AVAILABLE or not forces:
        return None

    labels = list(forces.keys())
    values = [forces[k] for k in labels]
    order = sorted(range(len(labels)), key=lambda i: values[i])
    labels = [labels[i] for i in order]
    values = [values[i] for i in order]

    fig = go.Figure(go.Bar(
        x=values, y=labels, orientation="h",
        marker=dict(
            color=[P.band_colour(v) for v in values],
            line=dict(color="rgba(38,50,62,0.12)", width=1),
        ),
        text=[f"{v}" for v in values],
        textposition="outside",
        textfont=dict(family=P.FONT_MONO, size=10, color=P.TEXT_MUTED),
        hovertemplate="%{y}: %{x}/100 favourable<extra></extra>",
    ))
    fig.add_vline(x=58, line=dict(color=P.TEXT_FAINT, width=1, dash="dot"))
    fig.update_xaxes(range=[0, 108], title="Favourable to a new entrant →")
    return _layout(fig, height=330)


# ----------------------------------------------------------------------
# 5. Evidence heatmap
# ----------------------------------------------------------------------

def evidence_heatmap(rows: Sequence[Dict[str, object]]):
    if not AVAILABLE or not rows:
        return None

    metrics = ["quality", "relevance", "direct_support", "industry_fit", "authority"]
    nice = ["Quality", "Relevance", "Direct support", "Industry fit", "Authority"]

    y = [f"{r['code']} · {r['domain']}" for r in rows]
    z = [[int(r.get(m, 0) or 0) for m in metrics] for r in rows]

    fig = go.Figure(go.Heatmap(
        z=z, x=nice, y=y,
        colorscale=P.COLORSCALE, zmin=0, zmax=100,
        xgap=3, ygap=3,
        colorbar=dict(
            thickness=9, len=0.85, outlinewidth=0,
            tickfont=dict(family=P.FONT_MONO, size=9, color=P.TEXT_FAINT),
        ),
        hovertemplate="%{y}<br>%{x}: %{z}/100<extra></extra>",
    ))
    return _layout(fig, height=max(360, 30 * len(rows) + 70))


# ----------------------------------------------------------------------
# 6. Cross-domain linkage matrix
# ----------------------------------------------------------------------

def linkage_heatmap(labels: Sequence[str], matrix: Sequence[Sequence[int]]):
    if not AVAILABLE or not labels:
        return None

    fig = go.Figure(go.Heatmap(
        z=matrix, x=list(labels), y=list(labels),
        colorscale=P.COLORSCALE, zmin=0, zmax=100,
        xgap=2, ygap=2,
        colorbar=dict(
            thickness=9, len=0.8, outlinewidth=0,
            tickfont=dict(family=P.FONT_MONO, size=9, color=P.TEXT_FAINT),
        ),
        hovertemplate="%{y} ↔ %{x}: strength %{z}<extra></extra>",
    ))
    fig.update_yaxes(autorange="reversed")
    return _layout(fig, height=430)


# ----------------------------------------------------------------------
# 7. Growth pool bubble
# ----------------------------------------------------------------------

def pool_bubble(pools):
    """Demand against monetisation; size is evidence, colour is access."""
    if not AVAILABLE or not pools:
        return None

    fig = go.Figure()
    fig.add_shape(
        type="rect", x0=55, y0=50, x1=100, y1=100,
        fillcolor=P.MINT, opacity=0.07, layer="below",
        line=dict(color=P.GRID, width=1),
    )
    fig.add_annotation(
        x=77, y=97, text="INVESTABLE ZONE", showarrow=False,
        font=dict(family=P.FONT_MONO, size=9, color=P.MINT),
    )

    fig.add_trace(go.Scatter(
        x=[p.demand for p in pools],
        y=[p.monetisation for p in pools],
        mode="markers+text",
        marker=dict(
            size=[max(18, p.evidence * 0.55) for p in pools],
            color=[p.access for p in pools],
            colorscale=P.COLORSCALE, cmin=0, cmax=100,
            line=dict(color="rgba(255,255,255,0.55)", width=1.5),
            opacity=0.9,
            colorbar=dict(
                title=dict(
                    text="Access",
                    font=dict(family=P.FONT_MONO, size=9, color=P.TEXT_FAINT),
                ),
                thickness=9, len=0.7, outlinewidth=0,
                tickfont=dict(family=P.FONT_MONO, size=9, color=P.TEXT_FAINT),
            ),
        ),
        text=[p.display for p in pools],
        textposition="top center",
        textfont=dict(family=P.FONT_BODY, size=10, color=P.TEXT_MUTED),
        customdata=[[p.evidence, p.priority] for p in pools],
        hovertemplate=(
            "<b>%{text}</b><br>Demand %{x}/100<br>Monetisation %{y}/100"
            "<br>Evidence %{customdata[0]}/100<br>Priority %{customdata[1]}/100"
            "<extra></extra>"
        ),
    ))

    fig.update_xaxes(range=[0, 105], title="Demand evidence", dtick=25)
    fig.update_yaxes(range=[0, 105], title="Monetisation evidence", dtick=25)
    return _layout(fig, height=420)


# ----------------------------------------------------------------------
# 8. Segment shares
# ----------------------------------------------------------------------

def share_bars(shares, limit: int = 7):
    if not AVAILABLE or not shares:
        return None

    picked = sorted(shares, key=lambda s: s.percent, reverse=True)[:limit]
    picked.reverse()

    fig = go.Figure(go.Bar(
        x=[s.percent for s in picked],
        y=[s.subject for s in picked],
        orientation="h",
        marker=dict(
            color=[P.SPECTRUM[i % len(P.SPECTRUM)] for i in range(len(picked))],
            line=dict(color="rgba(38,50,62,0.12)", width=1),
        ),
        text=[f"{s.percent:.0f}%" for s in picked],
        textposition="outside",
        textfont=dict(family=P.FONT_MONO, size=10, color=P.TEXT_MUTED),
        customdata=[[s.source_host or "source", s.year or "year not stated"] for s in picked],
        hovertemplate="<b>%{y}</b>: %{x:.1f}%<br>%{customdata[0]} · %{customdata[1]}<extra></extra>",
    ))
    fig.update_xaxes(title="Share of market (%) as published", range=[0, 112])
    return _layout(fig, height=max(280, 46 * len(picked) + 80))


# ----------------------------------------------------------------------
# 9. Growth-rate dispersion
# ----------------------------------------------------------------------

def rate_dispersion(rates, implied: Optional[float] = None):
    """Published CAGRs as a strip, with the implied rate marked."""
    if not AVAILABLE or not rates:
        return None

    fig = go.Figure()
    fig.add_trace(go.Scatter(
        x=[r.percent for r in rates],
        y=[0.06 * ((i % 5) - 2) for i in range(len(rates))],
        mode="markers",
        marker=dict(
            size=15, color=[P.AQUA if r.scope != "global" else P.AMBER for r in rates],
            line=dict(color="rgba(255,255,255,0.55)", width=1), opacity=0.9,
        ),
        customdata=[[r.source_host or "source", r.period, r.scope] for r in rates],
        hovertemplate=(
            "<b>%{x:.1f}% CAGR</b><br>%{customdata[0]}"
            "<br>%{customdata[1]} · scope: %{customdata[2]}<extra></extra>"
        ),
        name="Published rate",
    ))

    if implied is not None:
        fig.add_vline(
            x=implied, line=dict(color=P.VIOLET, width=2, dash="dash"),
            annotation_text=f"implied {implied:.1f}%",
            annotation_font=dict(family=P.FONT_MONO, size=10, color=P.VIOLET),
        )

    fig.update_xaxes(title="Compound annual growth rate (%)")
    fig.update_yaxes(range=[-0.4, 0.4], showticklabels=False, showgrid=False)
    return _layout(fig, height=230)


# ----------------------------------------------------------------------
# 10. Risk matrix
# ----------------------------------------------------------------------

def risk_matrix(risks: Sequence[Tuple[str, int, int]]):
    """(label, likelihood 0-100, impact 0-100)."""
    if not AVAILABLE or not risks:
        return None

    fig = go.Figure()
    fig.add_shape(
        type="rect", x0=55, y0=55, x1=100, y1=100,
        fillcolor=P.CORAL, opacity=0.10, layer="below",
        line=dict(color=P.GRID, width=1),
    )
    fig.add_annotation(
        x=77, y=97, text="MANAGE ACTIVELY", showarrow=False,
        font=dict(family=P.FONT_MONO, size=9, color=P.CORAL),
    )

    fig.add_trace(go.Scatter(
        x=[r[1] for r in risks], y=[r[2] for r in risks],
        mode="markers+text",
        marker=dict(
            size=22,
            color=[P.CORAL if (r[1] + r[2]) / 2 >= 60 else P.AMBER for r in risks],
            line=dict(color="rgba(255,255,255,0.5)", width=1.5), opacity=0.88,
        ),
        text=[r[0] for r in risks],
        textposition="bottom center",
        textfont=dict(family=P.FONT_BODY, size=10, color=P.TEXT_MUTED),
        hovertemplate="<b>%{text}</b><br>Likelihood %{x}<br>Impact %{y}<extra></extra>",
    ))

    fig.update_xaxes(range=[0, 105], title="Likelihood (evidence density)", dtick=25)
    fig.update_yaxes(range=[0, 105], title="Impact on the thesis", dtick=25)
    return _layout(fig, height=380)


# ----------------------------------------------------------------------
# 11. Lens confidence bars
# ----------------------------------------------------------------------

def lens_bars(lens: Dict[str, int]):
    if not AVAILABLE or not lens:
        return None

    labels = list(lens.keys())
    values = [lens[k] for k in labels]

    fig = go.Figure(go.Bar(
        x=labels, y=values,
        marker=dict(
            color=[P.LENS_COLOURS.get(k, P.AQUA) for k in labels],
            line=dict(color="rgba(38,50,62,0.12)", width=1),
        ),
        text=[f"{v}" for v in values], textposition="outside",
        textfont=dict(family=P.FONT_MONO, size=10, color=P.TEXT_MUTED),
        hovertemplate="%{x}: %{y}/100 confidence<extra></extra>",
    ))
    fig.update_yaxes(range=[0, 112], title="Evidence confidence")
    return _layout(fig, height=300)


__all__ = [
    "AVAILABLE", "attractiveness_radar", "conviction_map", "evidence_heatmap",
    "five_forces_bars", "lens_bars", "linkage_heatmap", "pool_bubble",
    "rate_dispersion", "reconciliation_fan", "risk_matrix", "share_bars",
]
