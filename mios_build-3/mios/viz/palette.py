"""
One palette, two consumers.

The CSS in `theme.py` and every Plotly figure read their colours from
here, so a chart can never drift out of step with the interface.

Direction: warm paper, not a dashboard. The background is an off-white
with a little warmth in it so the screen does not glare, panels are
near-white glass lifted off it, and the accents are muted naturals —
sage, slate blue, clay, deep teal — at roughly 40% saturation. Nothing
is allowed to be vivid, because in an analytical product saturation
should mean something: clay means a broken assumption and amber means
caution, and they only read as warnings if nothing else competes.
"""

from __future__ import annotations

from typing import Dict, List

# --- base ---------------------------------------------------------------
PAPER = "#F6F4F1"          # warm off-white field
PAPER_DEEP = "#EFEBE6"     # recessed areas
SURFACE = "#FFFFFF"
SURFACE_ALT = "#FAF8F6"

# --- glass --------------------------------------------------------------
GLASS = "rgba(255, 255, 255, 0.72)"
GLASS_STRONG = "rgba(255, 255, 255, 0.88)"
GLASS_EDGE = "rgba(28, 32, 40, 0.10)"
GLASS_EDGE_SOFT = "rgba(28, 32, 40, 0.065)"

# --- type ---------------------------------------------------------------
TEXT = "#1F242C"
TEXT_MUTED = "#5C6673"
TEXT_FAINT = "#8B95A3"

# --- muted naturals -----------------------------------------------------
SAGE = "#6B8F71"           # growth, positive
TEAL = "#3F7D78"           # primary analytical accent
SLATE = "#5B7C99"          # secondary
PLUM = "#8B6F9E"           # tertiary
CLAY = "#B5654F"           # alert, conflict
AMBER = "#C08F4A"          # caution
STONE = "#9AA0A6"          # neutral

# Aliases kept so existing chart code needs no rewiring.
AQUA = TEAL
INDIGO = SLATE
VIOLET = PLUM
MINT = SAGE
CORAL = CLAY

GRID = "rgba(28, 32, 40, 0.07)"
AXIS = "rgba(28, 32, 40, 0.22)"

# Ordered ramp, light to dark. Reads correctly on paper.
SPECTRUM: List[str] = [
    "#A8C0B4", "#7FA79C", TEAL, SLATE, "#4A6B8A", PLUM,
]

# Sequential scale for heatmaps: pale sand through to deep teal, so a
# low score recedes into the page instead of shouting in a bright colour.
COLORSCALE = [
    [0.00, "#F2EDE6"],
    [0.25, "#DCE4DC"],
    [0.50, "#A8C0B4"],
    [0.72, "#6E9A92"],
    [0.88, TEAL],
    [1.00, "#2F5F5C"],
]

DIVERGING = [
    [0.00, CLAY],
    [0.35, AMBER],
    [0.60, "#A8C0B4"],
    [1.00, TEAL],
]

CATEGORICAL: List[str] = [TEAL, SLATE, SAGE, PLUM, AMBER, CLAY, STONE]

LENS_COLOURS: Dict[str, str] = {
    "Demand": TEAL,
    "Supply & Rivalry": SLATE,
    "Economics": PLUM,
    "Context & Risk": AMBER,
}


def band_colour(score: int) -> str:
    if score >= 72:
        return SAGE
    if score >= 58:
        return TEAL
    if score >= 44:
        return AMBER
    return CLAY


def band_label(score: int) -> str:
    if score >= 72:
        return "Strong"
    if score >= 58:
        return "Constructive"
    if score >= 44:
        return "Mixed"
    return "Weak"


GRADE_COLOURS: Dict[str, str] = {
    "SOURCE-BACKED": SAGE,
    "PARTIALLY SUPPORTED": TEAL,
    "DIRECTIONAL": AMBER,
    "PROVISIONAL": CLAY,
    "STRONG": SAGE,
    "MODERATE": TEAL,
    "WEAK": AMBER,
    "UNSUPPORTED": CLAY,
    "RECONCILED": SAGE,
    "CONFLICTED": CLAY,
    "INCONSISTENT": AMBER,
    "INSUFFICIENT": STONE,
}

QUADRANT_COLOURS: Dict[str, str] = {
    "ACT": SAGE,
    "VALIDATE": TEAL,
    "PASS": STONE,
    "PARK": AMBER,
}

FONT_DISPLAY = "Fraunces, Georgia, serif"
FONT_BODY = "Inter Tight, -apple-system, Segoe UI, sans-serif"
FONT_MONO = "JetBrains Mono, SFMono-Regular, Consolas, monospace"

# Back-compat aliases for the old dark names.
INK = TEXT
INK_DEEP = TEXT
SURFACE_HI = SURFACE_ALT

__all__ = [
    "AMBER", "AQUA", "AXIS", "CATEGORICAL", "CLAY", "COLORSCALE", "CORAL",
    "DIVERGING", "FONT_BODY", "FONT_DISPLAY", "FONT_MONO", "GLASS",
    "GLASS_EDGE", "GLASS_EDGE_SOFT", "GLASS_STRONG", "GRADE_COLOURS",
    "GRID", "INDIGO", "INK", "INK_DEEP", "LENS_COLOURS", "MINT", "PAPER",
    "PAPER_DEEP", "PLUM", "QUADRANT_COLOURS", "SAGE", "SLATE", "SPECTRUM",
    "STONE", "SURFACE", "SURFACE_ALT", "SURFACE_HI", "TEAL", "TEXT",
    "TEXT_FAINT", "TEXT_MUTED", "VIOLET", "band_colour", "band_label",
]
