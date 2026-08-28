"""
The interface skin.

Direction: warm paper. An off-white field with a hint of warmth so the
screen does not glare over a long reading session, panels of near-white
glass lifted off it by soft shadow and a hairline edge, and muted natural
accents that stay quiet until they need to mean something.

Density is the other half of the job. Cards breathe, the type scale has
only four steps, and rules are used sparingly — the previous dark build
was legible but cluttered, and clutter in an analytical product reads as
noise in the analysis itself.
"""

from __future__ import annotations

from .viz import palette as P

FONT_IMPORT = (
    "@import url('https://fonts.googleapis.com/css2?"
    "family=Fraunces:opsz,wght@9..144,400;9..144,600;9..144,700"
    "&family=Inter+Tight:wght@300;400;500;600"
    "&family=JetBrains+Mono:wght@400;500&display=swap');"
)


def css() -> str:
    return f"""
<style>
{FONT_IMPORT}

:root {{
  --paper: {P.PAPER};
  --paper-deep: {P.PAPER_DEEP};
  --surface: {P.SURFACE};
  --surface-alt: {P.SURFACE_ALT};
  --glass: {P.GLASS};
  --glass-strong: {P.GLASS_STRONG};
  --edge: {P.GLASS_EDGE};
  --edge-soft: {P.GLASS_EDGE_SOFT};
  --text: {P.TEXT};
  --muted: {P.TEXT_MUTED};
  --faint: {P.TEXT_FAINT};
  --teal: {P.TEAL};
  --sage: {P.SAGE};
  --slate: {P.SLATE};
  --plum: {P.PLUM};
  --clay: {P.CLAY};
  --amber: {P.AMBER};
  --font-display: {P.FONT_DISPLAY};
  --font-body: {P.FONT_BODY};
  --font-mono: {P.FONT_MONO};
  --r-lg: 18px;
  --r-md: 14px;
  --shadow: 0 1px 2px rgba(28,32,40,0.04), 0 8px 24px rgba(28,32,40,0.06);
  --shadow-lift: 0 2px 4px rgba(28,32,40,0.05), 0 16px 40px rgba(28,32,40,0.09);
}}

/* ---------- field ---------- */

.stApp {{
  background:
    radial-gradient(900px 500px at 8% -10%, rgba(63,125,120,0.055), transparent 60%),
    radial-gradient(760px 440px at 95% 2%, rgba(91,124,153,0.045), transparent 58%),
    var(--paper);
  color: var(--text);
  font-family: var(--font-body);
}}

.block-container {{ padding: 1.6rem 2.6rem 5rem; max-width: 1400px; }}
#MainMenu, footer, header {{ visibility: hidden; }}

/* ---------- type ---------- */

h1, h2, h3 {{
  font-family: var(--font-display) !important;
  color: var(--text) !important;
  letter-spacing: -0.012em;
}}
h1 {{ font-weight: 600; font-size: 2.5rem; line-height: 1.08; }}
h2 {{ font-weight: 600; font-size: 1.4rem; }}
h3 {{ font-weight: 600; font-size: 1.05rem; }}
p, li, span, label {{ font-family: var(--font-body); color: var(--text); }}

.eyebrow {{
  font-family: var(--font-mono);
  font-size: 0.62rem;
  font-weight: 500;
  letter-spacing: 0.14em;
  text-transform: uppercase;
  color: var(--teal);
  display: block;
  margin-bottom: 0.4rem;
}}
.eyebrow.dim {{ color: var(--faint); }}

.section-head {{ margin: 2.6rem 0 1.1rem; }}
.section-head h2 {{ margin: 0 0 0.25rem; }}
.section-head .sub {{
  color: var(--muted); font-size: 0.92rem; margin: 0;
  max-width: 72ch; line-height: 1.55;
}}

/* ---------- plain-language copy ---------- */

/* The one-sentence conclusion at the top of a screen. */
.lead {{
  font-family: var(--font-display);
  font-size: 1.28rem;
  font-weight: 600;
  line-height: 1.44;
  letter-spacing: -0.012em;
  color: var(--text);
  max-width: 68ch;
  margin: 0 0 0.85rem;
}}

/* Supporting explanation under a lead. */
.prose {{
  font-size: 0.97rem;
  line-height: 1.7;
  color: var(--text);
  max-width: 74ch;
  margin: 0 0 1rem;
}}
.prose-muted {{
  font-size: 0.93rem;
  line-height: 1.68;
  color: var(--muted);
  max-width: 74ch;
  margin: 0 0 1rem;
}}

/* "How to read this" note, sitting directly under a chart. */
.readnote {{
  font-size: 0.85rem;
  line-height: 1.6;
  color: var(--muted);
  max-width: 72ch;
  margin: 0.4rem 0 1.6rem;
  padding-left: 0.8rem;
  border-left: 2px solid rgba(63,125,120,0.28);
}}

/* Plain-language explainer that sits above a chart. */
.readout {{
  font-size: 0.95rem;
  line-height: 1.68;
  color: var(--text);
  max-width: 74ch;
  margin: 0 0 1rem;
}}
.readout b {{ font-weight: 600; }}
.readout .num {{
  font-family: var(--font-mono);
  font-size: 0.90em;
  background: rgba(63,125,120,0.09);
  padding: 1px 5px;
  border-radius: 4px;
}}

/* ---------- glass ---------- */

.glass {{
  background: var(--glass);
  backdrop-filter: blur(18px) saturate(120%);
  -webkit-backdrop-filter: blur(18px) saturate(120%);
  border: 1px solid var(--edge-soft);
  border-radius: var(--r-lg);
  box-shadow: var(--shadow);
  padding: 1.25rem 1.45rem;
}}
.glass.tight {{ padding: 0.9rem 1.1rem; }}

/* ---------- hero ---------- */

.hero {{
  background:
    linear-gradient(135deg, rgba(63,125,120,0.07), rgba(91,124,153,0.04) 46%, transparent 76%),
    var(--glass-strong);
  border: 1px solid var(--edge-soft);
  border-radius: 22px;
  padding: 2.2rem 2.4rem 2rem;
  box-shadow: var(--shadow-lift);
}}
.hero h1 {{ margin: 0.3rem 0 0.7rem; }}
.hero .lede {{
  color: var(--muted); font-size: 1.02rem;
  max-width: 70ch; line-height: 1.68; margin: 0;
}}

/* ---------- evidence spine ---------- */

.spine {{ display: flex; gap: 5px; align-items: flex-end; margin: 1.1rem 0 0.2rem; }}
.spine-node {{
  flex: 1; height: 40px; border-radius: 5px; position: relative;
  background: rgba(28,32,40,0.045);
  border: 1px solid var(--edge-soft);
  overflow: hidden;
}}
.spine-fill {{ position: absolute; left: 0; right: 0; bottom: 0; border-radius: 4px; }}
.spine-label {{
  font-family: var(--font-mono); font-size: 0.56rem;
  color: var(--faint); text-align: center; margin-top: 0.3rem;
}}
.spine-legend {{
  display: flex; gap: 1.1rem; flex-wrap: wrap;
  font-family: var(--font-body); font-size: 0.72rem;
  color: var(--muted); margin-top: 0.75rem;
}}
.spine-legend i {{
  width: 8px; height: 8px; border-radius: 2px;
  display: inline-block; margin-right: 6px; vertical-align: 0;
}}

/* ---------- metrics ---------- */

.kpi {{
  background: var(--surface);
  border: 1px solid var(--edge-soft);
  border-radius: var(--r-md);
  padding: 1rem 1.1rem 1.05rem;
  height: 100%;
  box-shadow: var(--shadow);
}}
.kpi .k-label {{
  font-family: var(--font-body); font-size: 0.76rem; font-weight: 500;
  color: var(--muted);
}}
.kpi .k-value {{
  font-family: var(--font-display); font-size: 2rem; font-weight: 600;
  line-height: 1.05; margin: 0.3rem 0 0.2rem; letter-spacing: -0.02em;
}}
.kpi .k-note {{ font-size: 0.8rem; color: var(--muted); line-height: 1.45; }}
.kpi .k-bar {{
  height: 3px; border-radius: 2px; margin-top: 0.75rem;
  background: rgba(28,32,40,0.07); overflow: hidden;
}}
.kpi .k-bar span {{ display: block; height: 100%; border-radius: 2px; }}

/* ---------- chips ---------- */

.chip {{
  display: inline-flex; align-items: center;
  font-family: var(--font-body); font-size: 0.72rem; font-weight: 500;
  padding: 3px 10px; border-radius: 999px;
  border: 1px solid currentColor; margin: 0 5px 5px 0;
  background: rgba(255,255,255,0.6);
}}

/* ---------- domain card ---------- */

.dcard {{
  background: var(--surface);
  border: 1px solid var(--edge-soft);
  border-top: 2px solid var(--teal);
  border-radius: var(--r-md);
  padding: 1.15rem 1.25rem 1.2rem;
  height: 100%;
  box-shadow: var(--shadow);
}}
.dcard h3 {{ margin: 0.3rem 0 0.6rem; font-size: 1.02rem; }}
.dcard .finding {{
  font-size: 0.87rem; color: var(--text); line-height: 1.6;
  margin-bottom: 0.6rem;
}}
.dcard .ref {{ font-family: var(--font-mono); font-size: 0.66rem; color: var(--faint); }}
.dcard .imp {{
  font-size: 0.86rem; color: var(--text); line-height: 1.62;
  margin-top: 0.85rem; padding-top: 0.75rem;
  border-top: 1px solid var(--edge-soft);
}}

/* ---------- reasoning chain ---------- */

.chain-step {{ padding: 0.55rem 0 0.55rem 0.95rem; border-left: 2px solid; }}
.chain-step .step-label {{
  font-family: var(--font-body); font-size: 0.72rem; font-weight: 600;
  margin-bottom: 0.22rem;
}}
.chain-step .step-body {{ font-size: 0.88rem; line-height: 1.62; color: var(--text); }}

/* ---------- conflict ---------- */

.conflict {{
  background: rgba(181,101,79,0.045);
  border: 1px solid rgba(181,101,79,0.22);
  border-radius: var(--r-md);
  padding: 1rem 1.15rem;
  margin-bottom: 0.75rem;
}}
.conflict .c-head {{
  font-size: 0.9rem; font-weight: 600; color: var(--clay);
  margin-bottom: 0.4rem;
}}
.conflict .c-body {{ font-size: 0.87rem; color: var(--text); line-height: 1.62; }}

/* ---------- verdict ---------- */

.verdict {{
  background: linear-gradient(135deg, rgba(107,143,113,0.08), transparent 62%), var(--surface);
  border: 1px solid var(--edge-soft);
  border-radius: 20px;
  padding: 1.9rem 2.1rem;
  box-shadow: var(--shadow-lift);
}}
.verdict .v-word {{
  font-family: var(--font-display); font-size: 2.6rem; font-weight: 600;
  letter-spacing: -0.02em; line-height: 1; margin: 0.4rem 0 0.25rem;
}}
.verdict .v-posture {{ font-size: 0.95rem; color: var(--muted); }}
.verdict .v-reason {{
  margin-top: 1.1rem; font-size: 0.97rem; line-height: 1.7;
  color: var(--text); max-width: 74ch;
}}

/* ---------- source row ---------- */

.srow {{
  display: flex; gap: 0.9rem; align-items: baseline;
  padding: 0.65rem 0.2rem; border-bottom: 1px solid var(--edge-soft);
}}
.srow .s-ref {{ font-family: var(--font-mono); font-size: 0.68rem; color: var(--faint); min-width: 56px; }}
.srow .s-title {{ font-size: 0.9rem; }}
.srow .s-host {{ font-size: 0.76rem; color: var(--muted); margin-top: 0.15rem; }}
.srow a {{ color: var(--teal); text-decoration: none; }}
.srow a:hover {{ text-decoration: underline; }}

/* ---------- streamlit overrides ---------- */

section[data-testid="stSidebar"] > div {{
  background: var(--surface-alt);
  border-right: 1px solid var(--edge-soft);
}}

.stButton > button {{
  width: 100%;
  background: var(--teal);
  color: #fff; border: none; border-radius: 10px;
  padding: 0.68rem 1rem; font-family: var(--font-body);
  font-weight: 500; font-size: 0.9rem;
  box-shadow: 0 2px 6px rgba(63,125,120,0.22);
  transition: background 140ms ease;
}}
.stButton > button:hover {{ background: #346B67; }}

.stTabs [data-baseweb="tab-list"] {{
  gap: 2px; background: transparent;
  border-bottom: 1px solid var(--edge-soft);
  border-radius: 0; padding: 0;
}}
.stTabs [data-baseweb="tab"] {{
  height: 40px; border-radius: 0; padding: 0 16px;
  font-family: var(--font-body); font-size: 0.88rem; font-weight: 500;
  color: var(--muted); border-bottom: 2px solid transparent;
}}
.stTabs [aria-selected="true"] {{
  color: var(--text) !important;
  border-bottom: 2px solid var(--teal) !important;
  background: transparent !important;
}}

div[data-testid="stExpander"] {{
  background: var(--surface);
  border: 1px solid var(--edge-soft);
  border-radius: var(--r-md);
  box-shadow: none;
}}
div[data-testid="stExpander"] summary {{ font-size: 0.88rem; color: var(--muted); }}

.stTextInput input, .stSelectbox div[data-baseweb="select"] > div {{
  background: var(--surface) !important;
  border: 1px solid var(--edge) !important;
  border-radius: 9px !important;
  color: var(--text) !important;
}}

div[data-testid="stDataFrame"] {{
  border: 1px solid var(--edge-soft); border-radius: var(--r-md); overflow: hidden;
}}

hr {{ border-color: var(--edge-soft); }}

@media (prefers-reduced-motion: reduce) {{
  * {{ transition: none !important; animation: none !important; }}
}}

@media (max-width: 820px) {{
  .block-container {{ padding: 1rem 1rem 3rem; }}
  h1 {{ font-size: 1.9rem; }}
  .hero {{ padding: 1.5rem 1.4rem; }}
  .spine-node {{ height: 30px; }}
}}
</style>
"""


__all__ = ["css"]
