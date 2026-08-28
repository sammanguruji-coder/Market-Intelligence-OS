"""
The investability Venn.

A growth pool is only worth capital when three things overlap: evidenced
demand, an evidenced monetisation mechanism, and reachable competitive
access. Two out of three is a common and expensive mistake — demand plus
monetisation with no access is how companies walk into an incumbent's
distribution advantage.

Plotly has no Venn primitive, so this draws three circles as shapes and
places counts at the seven regions computed from real set intersections.
"""

from __future__ import annotations

import math
from typing import Dict, List, Sequence, Set

from . import palette as P

try:  # pragma: no cover
    import plotly.graph_objects as go
    AVAILABLE = True
except Exception:  # pragma: no cover
    go = None  # type: ignore
    AVAILABLE = False

RADIUS = 1.0
OFFSET = 0.58

CENTRES = {
    "Demand": (-OFFSET, OFFSET * 0.58),
    "Monetisation": (OFFSET, OFFSET * 0.58),
    "Access": (0.0, -OFFSET * 0.82),
}

FILLS = {
    "Demand": "rgba(76,224,216,0.20)",
    "Monetisation": "rgba(169,112,255,0.20)",
    "Access": "rgba(110,123,255,0.20)",
}

EDGES = {"Demand": P.AQUA, "Monetisation": P.VIOLET, "Access": P.INDIGO}

# Where each of the seven regions gets its label.
REGIONS = {
    ("Demand",): (-1.02, 0.72),
    ("Monetisation",): (1.02, 0.72),
    ("Access",): (0.0, -1.30),
    ("Demand", "Monetisation"): (0.0, 0.80),
    ("Demand", "Access"): (-0.72, -0.42),
    ("Monetisation", "Access"): (0.72, -0.42),
    ("Demand", "Monetisation", "Access"): (0.0, 0.02),
}


def _region_members(sets: Dict[str, Set[str]], keys: Sequence[str]) -> List[str]:
    keys = list(keys)
    inside = set.intersection(*[sets[k] for k in keys]) if keys else set()
    outside = [sets[k] for k in sets if k not in keys]
    for other in outside:
        inside = inside - other
    return sorted(inside)


def investability_venn(sets: Dict[str, Set[str]]):
    """sets: {"Demand": {...}, "Monetisation": {...}, "Access": {...}}"""
    if not AVAILABLE:
        return None

    sets = {k: set(sets.get(k, set())) for k in ("Demand", "Monetisation", "Access")}
    fig = go.Figure()

    for name, (cx, cy) in CENTRES.items():
        fig.add_shape(
            type="circle",
            x0=cx - RADIUS, y0=cy - RADIUS, x1=cx + RADIUS, y1=cy + RADIUS,
            fillcolor=FILLS[name],
            line=dict(color=EDGES[name], width=2),
            layer="below",
        )
        # Set title sits outside its circle, aligned away from the centre.
        fig.add_annotation(
            x=cx * 1.72, y=cy * 1.62 + (0.30 if cy > 0 else -0.30),
            text=f"<b>{name}</b>", showarrow=False,
            font=dict(family=P.FONT_MONO, size=11, color=EDGES[name]),
        )

    for keys, (x, y) in REGIONS.items():
        members = _region_members(sets, keys)
        if not members:
            continue

        core = len(keys) == 3
        shown = members[:2]
        label = "<br>".join(shown)
        if len(members) > 2:
            label += f"<br>+{len(members) - 2} more"

        fig.add_annotation(
            x=x, y=y,
            text=f"<b>{len(members)}</b><br><span style='font-size:9px'>{label}</span>",
            showarrow=False, align="center",
            font=dict(
                family=P.FONT_BODY,
                size=13 if core else 11,
                color=P.MINT if core else P.TEXT_MUTED,
            ),
        )

    passing = _region_members(sets, ("Demand", "Monetisation", "Access"))
    caption = (
        f"{len(passing)} pool(s) clear all three tests"
        if passing else
        "No pool clears all three tests on current evidence"
    )
    fig.add_annotation(
        x=0, y=-1.92, text=caption, showarrow=False,
        font=dict(
            family=P.FONT_MONO, size=10,
            color=P.MINT if passing else P.AMBER,
        ),
    )

    fig.update_xaxes(range=[-2.3, 2.3], visible=False)
    fig.update_yaxes(range=[-2.15, 2.05], visible=False, scaleanchor="x", scaleratio=1)
    fig.update_layout(
        height=440,
        margin=dict(l=10, r=10, t=16, b=10),
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        showlegend=False,
        font=dict(family=P.FONT_BODY, color=P.TEXT),
    )
    return fig


__all__ = ["AVAILABLE", "investability_venn"]
