# Market Intelligence OS

> **Research -> Evidence -> Reconciliation -> Decision**

An evidence-led market research and decision-support application that turns fragmented industry information into an auditable strategic view. It researches a market across **13 decision domains**, qualifies the sources it retrieves, extracts and reconciles quantitative evidence, and presents a decision-ready recommendation.

**Created by Samman Giri**

[Open the live application](https://market-intelligence-os-1.streamlit.app/)

## Why it exists

Market research can produce an impressive-looking answer without making clear whether the evidence is strong, comparable, or even about the same market. Market Intelligence OS is designed to make that uncertainty visible.

It answers two separate questions:

1. **Is this market strategically attractive?**
2. **How much should we trust that assessment?**

## What the application does

| Capability | What it does |
| --- | --- |
| **13-domain research** | Structures research across demand, competition, economics, regulation, technology, opportunities, and risks. |
| **Source qualification** | Scores retrieved material by authority, relevance, direct support, industry fit, and specificity. |
| **Quantitative extraction** | Identifies market-size figures, growth rates, shares, and other numerical evidence. |
| **Evidence reconciliation** | Surfaces competing estimates, flags conflicts, and checks stated growth rates against implied CAGR. |
| **Decision engine** | Combines market attractiveness, Five Forces, growth pools, risk, evidence gaps, and cross-domain linkages. |
| **Interactive dashboard** | Presents research through nine decision-oriented views, including Sources and a Full Report. |

## The 13-domain research spine

1. Market Size & Growth  
2. Market Segmentation  
3. Demand Drivers  
4. Industry Trends  
5. Competitive Landscape  
6. Key Companies  
7. Value Chain & Economics  
8. Regulatory Environment  
9. Technology Landscape  
10. Customer Segments  
11. Industry Attractiveness  
12. Growth Pools  
13. Key Risks  

## How the workflow works

```text
Industry + Geography + Strategic Objective
                    |
                    v
             13-domain research
                    |
                    v
     Retrieval -> source qualification
                    |
                    v
    Finding and quantitative extraction
                    |
                    v
         Reconciliation and gap checks
                    |
                    v
  Attractiveness + confidence + strategic recommendation
```

The optional language-model layer assists with writing. It only rewrites evidence that has already passed qualification; it is not used to invent or supply factual claims.

## Dashboard views

`Decision` · `Market size` · `Research` · `Opportunities` · `Where profit sits` · `Connections` · `Risks` · `Sources` · `Full report`

## Architecture

```text
app.py                    Streamlit entry point, sidebar, research trigger, dashboard tabs
mios/
  core/
    domains.py            13-domain model and Five Forces mapping
    search.py             Retrieval and caching
    sources.py            Source scoring and qualification
    extract.py            Quantitative figure extraction
    reconcile.py          Estimate comparison and conflict checks
    research.py           Research pipeline orchestration
    analytics.py          Attractiveness, confidence, Five Forces, and evidence gaps
    pools.py              Growth-pool discovery and scoring
    crossdomain.py        Linkage and contradiction analysis
    report.py             Recommendation and report construction
    narrative.py          Evidence-bounded narrative generation
    llm.py                Optional model integration
    demo.py               Offline synthetic fixture corpus
  ui/                      User-interface components and tab renderers
  viz/                     Charts and analytical visualisations
```

## Run locally

```bash
python -m venv .venv

# Windows
.venv\Scripts\activate

python -m pip install -r requirements.txt
streamlit run app.py
```

The application runs in **demo mode** without API keys, using a bundled synthetic corpus.

## Optional live retrieval and model-assisted prose

Create a `.env` file beside `app.py`:

```text
TAVILY_API_KEY=your_tavily_key
GROQ_API_KEY=your_groq_key
GROQ_MODEL=openai/gpt-oss-120b
```

- **Tavily** enables live web retrieval.
- **Groq** enables model-assisted prose based only on already-qualified evidence.
- Never commit `.env` files, API keys, or Streamlit secrets to GitHub.

## Verification note

This repository is structured so that project claims can be traced from interface to implementation:

- `app.py` shows the research trigger, analysis bundle, and nine dashboard views.
- `mios/core/domains.py` defines the 13 research domains.
- `mios/core/sources.py`, `extract.py`, and `reconcile.py` implement the evidence workflow.
- `mios/core/analytics.py`, `pools.py`, `crossdomain.py`, and `report.py` implement the decision framework.

> **Data caveat:** demo-mode figures are synthetic and are for functionality demonstration only. They must not be quoted as real market findings.

## Author

**Samman Giri**  
Creator, Market Intelligence OS
