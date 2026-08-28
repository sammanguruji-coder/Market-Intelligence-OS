# Market Intelligence OS

An evidence-led market intelligence system. It researches an industry
across thirteen domains, extracts and types every figure it finds,
reconciles competing estimates instead of averaging them, and produces a
recommendation whose reasoning you can audit line by line.

---

## Quick start

**If you already have a `.env` file with your keys:** drop it into the
project folder next to `app.py`, then run the two commands below. The app
searches several locations for it, so it works whether you launch
Streamlit from the project folder or from a parent, and the sidebar tells
you which file it loaded.


**If you already have a `.env` file**, drop it in the project root next to
`app.py` and run the app — it is picked up automatically. The loader also
checks your working directory and its parent, so it works whichever
folder you launch Streamlit from in VS Code.


```bash
python -m venv .venv

# macOS / Linux
source .venv/bin/activate
# Windows
.venv\Scripts\activate

python -m pip install -r requirements.txt
streamlit run app.py
```

### Using your own .env

Drop your `.env` file into the same folder as `app.py` and start the app —
that is the whole setup. The loader also checks `mios/.env` and the folder
you launched Streamlit from, so it will find the file in any of the
obvious places.

Two things to know:

- **Restart Streamlit after editing `.env`.** Environment variables are
  read once at startup, so a hot reload will not pick up a new key.
- **No quotes, no spaces.** `TAVILY_API_KEY=tvly-abc123` works;
  `TAVILY_API_KEY = "tvly-abc123"` does not.

The sidebar shows which file the keys came from, and warns if it cannot
find one or finds one with nothing in it. Press **Test connections** to
make one real call to each API.

The app opens in demo mode, which runs the whole pipeline against a
bundled fixture corpus. No API keys, no network, no quota. Press **Run
13-domain research** and everything renders.

---

## Using Tavily and Groq

Copy `.env.example` to `.env` and add your keys:

```
TAVILY_API_KEY=tvly-...
GROQ_API_KEY=gsk_...
GROQ_MODEL=openai/gpt-oss-120b
```

Both have free tiers: [Tavily](https://app.tavily.com) gives 1,000
credits a month, [Groq](https://console.groq.com) needs no card. Restart
Streamlit after editing `.env`, then press **Test connections** in the
sidebar — it makes one real call to each API and reports exactly what
came back.

**Watch the model ID.** Groq retired `llama-3.3-70b-versatile` and
`llama-3.1-8b-instant` in June 2026. Anything pinned to those returns a
model-not-found error on the first call. Current production models are
`openai/gpt-oss-120b`, `openai/gpt-oss-20b` and `qwen/qwen3.6-27b`. The
app upgrades retired IDs automatically and the sidebar model picker is
populated from your live Groq catalogue, so it can only ever offer models
your account can actually call.

### What each service does

**Tavily** does retrieval. Each of the thirteen domains fires its own
query set, and the client passes the parameters that change result
quality for market research:

| Parameter | Why |
| --- | --- |
| `include_raw_content="markdown"` | The figure extractor needs full page text; snippets rarely carry a number |
| `topic="news"` | Used for competition, regulation and risk, where recency beats evergreen research pages |
| `country` | Biases results toward the target geography — mapped from country names only, so "Southeast Asia" correctly gets no bias |
| `time_range` | Optional recency filter, off by default because market-size pages are evergreen |

Results are cached by the full parameter set, so re-running during a
session costs no credits.

**Groq** does writing, never facts. It rewrites each domain's
already-qualified evidence into consulting prose, and writes one
committee summary from computed conclusions. Every prompt ships its
evidence inline and forbids anything outside it. If Groq is missing,
rate-limited or over budget, `narrative.py` produces the same output
shape deterministically — the prose gets plainer, the analysis is
identical.

The call budget defaults to 15: thirteen domains plus a synthesis, with
one spare. Below 14 some domains silently fall back, which is why the old
default of 8 was wrong.

### When something fails

Failures never interrupt a run. A thirteen-domain pass with a dead key
still completes, still scores, still renders — it just reports zero
sources and tells you why. Errors are translated into instructions
rather than raw SDK output:

```
ForbiddenError: Tavily rejected the key. Check it is correct, active,
and pasted into .env without quotes or spaces.
```

The strip under the evidence spine shows live queries, cache hits, model
calls and the model actually used, so you can see what a run cost.

---

## Fixing "Plotly is not available in this Python environment"

Plotly almost certainly *is* installed — just into a different
interpreter than the one running Streamlit. This is the single most
common Streamlit setup problem and it has nothing to do with your code.

In VS Code:

1. **Ctrl/Cmd + Shift + P** → `Python: Select Interpreter` → choose your
   `.venv`.
2. Open a **new** terminal (the old one still points at the old
   interpreter).
3. Install with the `python -m` prefix, which forces the install into
   the interpreter you just selected:
   ```bash
   python -m pip install -r requirements.txt
   ```
4. Launch from that same terminal:
   ```bash
   python -m streamlit run app.py
   ```

The sidebar shows the interpreter path actually in use, so you can
confirm it matches your venv. If the charts panel still reports Plotly
missing, the path shown there is the one that needs the install.

---

## Architecture

```
app.py                    Entry point: page config, sidebar, tabs. Thin.
mios/
  config.py               Environment, settings, dependency probes
  theme.py                Liquid-glass CSS
  core/
    domains.py            The 13-domain model, lenses, five forces
    text.py               Hygiene + sentence signal scoring
    extract.py            Money / CAGR / share extraction with typing
    sources.py            Authority tiers, relevance, industry fit
    search.py             Tavily wrapper with caching
    llm.py                Model wrapper with a hard call budget
    narrative.py          Deterministic writer; computed implications
    research.py           Pipeline orchestration
    reconcile.py          Estimate reconciliation engine
    analytics.py          Attractiveness, confidence, five forces
    pools.py              Growth pool discovery and scoring
    crossdomain.py        Pairwise synthesis, contradiction checks
    report.py             Recommendation logic, falsifiers, export
    demo.py               Offline fixture corpus
  viz/
    palette.py            One palette, read by both CSS and Plotly
    charts.py             All analytical figures
    flows.py              Value-chain Sankey, decision funnel
    venn.py               Three-set investability Venn
  ui/
    components.py         Glass components
    sections.py           One renderer per tab
```

Every module is importable and testable on its own. Nothing in `core`
imports Streamlit.

---

## What changed from the previous build

**The attractiveness model was measuring the wrong thing.** Every score
was computed from evidence-quality metrics rather than market facts. The
clearest case:

```python
"Risk-adjusted profile": max(0, 100 - dm(results, 13, "quality"))
```

Better risk sourcing made the market look *less* attractive, and a market
with no risk coverage at all scored 100. Attractiveness is now derived
from extracted facts — growth rates, absolute scale, observed
concentration, policy direction, risk density — and evidence confidence
is reported as a **separate axis**. A market can be attractive and badly
evidenced; that combination has its own quadrant and its own answer.

**Nothing parsed a number.** The old report printed `7.5bn (IAMAI)` next
to `10.5bn (IMARC)` and moved on. Those differ by 40% and the gap is
definitional. The extractor now types every figure by currency, year,
actual-vs-forecast, geographic scope, and what it measures — so a venture
funding total is never reconciled against a market size. The reconciler
buckets by scope and year, flags spreads beyond tolerance as conflicts,
and cross-checks the implied CAGR against every published CAGR.

**Web chrome leaked into the executive report.** `### Menu #`,
`#### For Chief Strategy Officer`, `logo logo Card image cap`. The old
`strip_chrome` was a phrase blocklist that never stripped markdown
scaffolding. Text now goes through markdown-scaffold removal plus a
sentence signal scorer, so cards quote the best sentence rather than the
first one.

**Every domain card ended with the same paragraph.** Thirteen times.
Implications are now computed from what each domain actually returned.

**Growth pools were sentence fragments.** "A Multi Billion Dollar
Opportunity" and "and demand for personalized learning solutions" were
being promoted to strategic options. Candidates now come from a
grammar-anchored extractor and must be corroborated across two domains or
two independent publishers before they can be scored.

---

## Reading the interface

The theme is warm paper: an off-white field with near-white cards, and an
accent range drawn from natural pigments — slate blue, sage, plum, ochre
and clay. Nothing is fully saturated, so when a strong colour does appear
it means something. Ochre marks anything unresolved. Clay marks anything
broken or conflicted. Sage marks anything that passed.

Every chart carries a plain-sentence readout underneath saying what to
conclude from it, because a caption that repeats the axis labels is worse
than no caption.

**Evidence spine** — thirteen bars above the tabs, one per research
topic, each as tall as that topic's confidence. Scan it before reading
anything to see where the research is thin.

**Conviction map** — how good the market looks, against how sure we are.

| Quadrant | Meaning | What to do |
| --- | --- | --- |
| Act | Looks good, well evidenced | Move to planning |
| Validate | Looks good, thin evidence | Pay for research before committing |
| Pass | Well evidenced, does not look good | A defensible no |
| Park | Neither | Leave it and revisit |

**Market size** — every published estimate plotted at the year it was
published, never averaged into one line. Where reports disagree, the gap
is shown and named, because a 40% spread between two published figures is
a difference of definition, not of measurement.

**Value chain** — one row per step of the business. The bar runs left for
the share of money that goes out as cost and right for the share that
stays as margin. The further right a step sits, the more it keeps. This
replaced a Sankey diagram that looked impressive and told you almost
nothing, because readers could not tell whether a thick ribbon meant
"lots of profit" or "lots of evidence".

**Opportunities** — demand, monetisation and access as three overlapping
circles. Two out of three is the expensive mistake.

## Scoring notes

- All scores are 0–100 and higher is always better, including the five
  forces (a high bar means the force is *favourable to a new entrant*).
- Estimates that differ by more than 25% inside the same year are treated
  as definitionally incompatible and are never averaged.
- A stated CAGR that differs from the implied CAGR by more than 3
  percentage points is reported as an inconsistency in the published
  series, not smoothed away.
- The language model, when enabled, only rewrites evidence that has
  already been qualified. It never supplies facts, and the deterministic
  writer produces the same output shape without it.

Demo-mode figures are synthetic and must never be quoted as sourced fact.
The conflicts in that corpus are planted deliberately so the
reconciliation engine has something real to catch.
