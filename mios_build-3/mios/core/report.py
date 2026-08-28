"""
Executive report assembly.

The old report printed the same raw scraped paragraph three times under
three different headings, then ended with a recommendation
("PARTNERSHIP-LED") that no visible piece of logic produced.

Here the recommendation is a function of the conviction quadrant and the
competitive-access score, the falsifiers are generated from the two
weakest scored dimensions, and every section is a short structured object
the UI can lay out — rather than a wall of text.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence

from . import llm
from .analytics import Attractiveness
from .crossdomain import Link, contradiction_check
from .pools import Pool
from .reconcile import ReconciliationReport, contamination_ratio, forecast_share
from .research import ResearchRun
from .text import clip


@dataclass
class Recommendation:
    verdict: str
    posture: str
    reasoning: str
    conditions: List[str] = field(default_factory=list)


@dataclass
class ExecutiveReport:
    industry: str
    geography: str
    objective: str
    recommendation: Optional[Recommendation] = None
    situation: List[str] = field(default_factory=list)
    size_statement: str = ""
    where_to_play: List[str] = field(default_factory=list)
    how_to_win: List[str] = field(default_factory=list)
    falsifiers: List[str] = field(default_factory=list)
    evidence_statement: str = ""
    flags: List[str] = field(default_factory=list)
    synthesis: str = ""
    synthesis_source: str = "deterministic"


# ----------------------------------------------------------------------
# Recommendation
# ----------------------------------------------------------------------

POSTURES = {
    "BUILD": "Go in directly and build it yourself",
    "PARTNER": "Go in with a partner who already reaches these customers",
    "STAGE": "Commit a small amount first, and only continue if it works",
    "MONITOR": "Do not commit yet; keep watching and revisit",
    "DECLINE": "Do not enter this market on what we know today",
}


def recommend(attract: Attractiveness, pools: Sequence[Pool]) -> Recommendation:
    quadrant = attract.quadrant
    access = attract.scores.get("Competitive access", 50)
    capture = attract.scores.get("Value capture", 50)
    risk = attract.scores.get("Risk headroom", 50)
    top = pools[0] if pools else None

    if quadrant == "ACT" and access >= 58 and capture >= 55:
        verdict = "BUILD"
        reasoning = (
            f"The market scores {attract.overall} out of 100 and the evidence "
            f"behind that score is solid at {attract.confidence} out of 100. "
            f"Getting in looks achievable ({access}/100) and there is real "
            f"proof that customers can be served profitably ({capture}/100). "
            f"Nothing here says you need someone else to reach the customer."
        )
    elif quadrant == "ACT":
        verdict = "PARTNER"
        reasoning = (
            f"The market itself is attractive at {attract.overall} out of 100. "
            f"The problem is reaching it: entry difficulty scores {access}/100 "
            f"and proof of profitable selling scores {capture}/100. Going in "
            f"alone would mean paying to build distribution that already "
            f"exists. A partner gives you that reach without the same risk."
        )
    elif quadrant == "VALIDATE":
        verdict = "STAGE"
        reasoning = (
            f"The market looks attractive at {attract.overall} out of 100, but "
            f"we only trust that picture {attract.confidence} out of 100. The "
            f"gap is the problem. Spend a small amount to find out whether the "
            f"attractive version is the true one, and decide properly after that."
        )
    elif quadrant == "PASS":
        verdict = "DECLINE"
        reasoning = (
            f"The evidence is reliable at {attract.confidence} out of 100, and "
            f"it says the market is weak at {attract.overall} out of 100. This "
            f"is a clear no, and a clear no is worth more than a vague maybe."
        )
    else:
        verdict = "MONITOR"
        reasoning = (
            f"The market scores {attract.overall} out of 100 and our confidence "
            f"in that is {attract.confidence} out of 100. Neither is high enough "
            f"to act on. Put nothing in yet, track the two weakest areas, and "
            f"look again when something moves."
        )

    conditions: List[str] = []
    if top:
        conditions.append(
            f"Start with {top.display} only, not the whole market. {top.blocker}"
        )
    if risk < 45:
        conditions.append(
            f"The risk score is low at {risk} out of 100. Agree in advance what "
            f"would make you walk away, before any money is spent."
        )
    if attract.confidence < 55:
        conditions.append(
            "The evidence is not yet strong enough for a board paper. Talk to "
            "real customers and suppliers first."
        )

    return Recommendation(
        verdict=verdict,
        posture=POSTURES[verdict],
        reasoning=reasoning,
        conditions=conditions,
    )


# ----------------------------------------------------------------------
# Sections
# ----------------------------------------------------------------------

def size_statement(report: Optional[ReconciliationReport], run: ResearchRun) -> str:
    if not report or not report.buckets:
        return (
            "No market-size figure survived extraction. Size the market from "
            "primary sources before any further analysis is used in a decision."
        )

    contamination = contamination_ratio(run.all_money)
    forecasts = forecast_share(run.all_money)

    parts: List[str] = []
    if report.anchor_value and report.terminal_value:
        parts.append(
            f"The reconciled series runs from US${report.anchor_value:,.1f}B in "
            f"{report.anchor_year} to US${report.terminal_value:,.1f}B in "
            f"{report.terminal_year}, an implied "
            f"{report.implied_cagr:.1f}% CAGR."
            if report.implied_cagr is not None
            else f"The reconciled series runs from US${report.anchor_value:,.1f}B "
                 f"in {report.anchor_year} to US${report.terminal_value:,.1f}B "
                 f"in {report.terminal_year}."
        )
    else:
        latest = report.buckets[-1]
        parts.append(
            f"Only one usable year survived: {latest.year} at "
            f"US${latest.median:,.1f}B."
        )

    if report.conflicts:
        worst = max(report.conflicts, key=lambda c: c.gap_percent)
        parts.append(
            f"{len(report.conflicts)} year(s) carry conflicting estimates; the "
            f"widest is {worst.gap_percent:,.0f}% in {worst.year}. These are not "
            f"averaged — the spread is definitional and must be resolved by "
            f"checking scope, inclusions and actual/forecast status."
        )
    else:
        parts.append("No year carries a spread beyond measurement tolerance.")

    if contamination >= 25:
        parts.append(
            f"{contamination:.0f}% of extracted figures are global rather than "
            f"{run.geography}-specific. Do not let a worldwide number stand in "
            f"for the addressable market."
        )
    if forecasts >= 60:
        parts.append(
            f"{forecasts:.0f}% of figures are forecasts rather than actuals. "
            f"The series is a projection, not a measurement."
        )

    return " ".join(parts)


def situation(run: ResearchRun, attract: Attractiveness) -> List[str]:
    lines: List[str] = []

    strongest, weakest = attract.strongest, attract.weakest
    if strongest:
        lines.append(
            f"The strongest thing about this market is its "
            f"{strongest.lower()}, scoring {attract.scores[strongest]} out of "
            f"100. {attract.rationale[strongest]}"
        )
    if weakest and weakest != strongest:
        lines.append(
            f"The thing most likely to stop you is {weakest.lower()}, scoring "
            f"only {attract.scores[weakest]} out of 100. "
            f"{attract.rationale[weakest]}"
        )

    lines.append(
        f"The research covered {run.covered_domains} of "
        f"{len(run.results)} topics using {run.independent_publishers} "
        f"different publishers, and {run.quantified_domains} of those topics "
        f"produced hard numbers rather than opinion."
    )
    return lines


def where_to_play(pools: Sequence[Pool], geography: str) -> List[str]:
    if not pools:
        return [
            "No growth pool cleared the two-domain corroboration gate. "
            "Pool definition is the first task of the next work block."
        ]
    lines: List[str] = []
    for pool in pools[:3]:
        lines.append(
            f"{pool.display}, scoring {pool.priority} out of 100. Demand for it "
            f"scores {pool.demand}, evidence that it can be sold profitably "
            f"scores {pool.monetisation}, and how easily you could reach it "
            f"scores {pool.access}. {pool.blocker}"
        )
    return lines


def how_to_win(attract: Attractiveness, pools: Sequence[Pool], links: Sequence[Link]) -> List[str]:
    lines: List[str] = []
    top = pools[0] if pools else None

    if top:
        lines.append(
            f"Build one narrow offer around {top.display}, and own the single "
            f"thing customers cannot get elsewhere. Partner or buy everything "
            f"else rather than building it."
        )
    lines.append(
        f"Expand only when each customer is provably profitable, not when "
        f"demand looks strong. Proof of profitable selling currently scores "
        f"{attract.scores.get('Value capture', 0)} out of 100, and that is the "
        f"number that decides whether growth is worth having at all."
    )

    strong_links = [l for l in links if l.grade in ("STRONG", "MODERATE")][:2]
    for link in strong_links:
        lines.append(f"{link.title}: {link.decision}")

    return lines


def falsifiers(attract: Attractiveness, report: Optional[ReconciliationReport]) -> List[str]:
    """What would have to be observed for this recommendation to be wrong."""
    ordered = sorted(attract.scores.items(), key=lambda kv: kv[1])
    out: List[str] = []

    templates = {
        "Growth momentum": "Observed growth falls below {threshold}% for two "
                           "consecutive reported periods.",
        "Market scale": "The addressable slice, once scope is corrected, is "
                        "less than half the reconciled headline.",
        "Segment depth": "Demand proves concentrated in a single segment "
                         "already served by an incumbent.",
        "Value capture": "Gross margin in the target position lands below the "
                         "cost of serving the customer.",
        "Competitive access": "An incumbent matches the proposition inside two "
                              "quarters at a price we cannot hold.",
        "Policy direction": "A licensing, pricing or data rule raises the cost "
                            "of compliance above the modelled margin.",
        "Risk headroom": "A severe risk marker converts into an observed "
                         "event — funding withdrawal, enforcement or a "
                         "material default.",
    }

    for name, value in ordered[:3]:
        template = templates.get(name, "{name} deteriorates materially.")
        out.append(
            template.format(threshold=max(3, round(value / 6)), name=name)
        )

    if report and report.conflicts:
        out.append(
            "Reconciliation of the conflicting size estimates resolves toward "
            "the lower bound rather than the median."
        )

    return out


def evidence_statement(run: ResearchRun, attract: Attractiveness) -> str:
    report = run.reconciliation
    verdict = report.verdict if report else "INSUFFICIENT"
    plain = {
        "RECONCILED": "the size estimates agree with each other",
        "CONFLICTED": "the size estimates disagree with each other",
        "INCONSISTENT": "some reports contradict their own figures",
        "INSUFFICIENT": "there were not enough figures to compare",
    }.get(verdict, verdict.lower())

    return (
        f"Confidence in this analysis is {attract.confidence} out of 100. It "
        f"draws on {run.total_sources} sources from "
        f"{run.independent_publishers} different publishers, and "
        f"{plain}. Numbers are read directly out of the source text and grouped "
        f"by year and by what they measure. Where two estimates cannot be "
        f"fairly compared, both are shown rather than averaged into one "
        f"misleading figure."
    )


SYNTHESIS_PROMPT = """You are writing the opening paragraph of an
investment committee memo. Everything below has already been computed
from qualified evidence. Do not add facts, numbers or company names that
are not present here.

Industry: {industry}
Geography: {geography}
Objective: {objective}

Recommendation: {verdict} — {posture}
Attractiveness {overall}/100 ({band}). Evidence confidence {confidence}/100.
Conviction quadrant: {quadrant} — {quadrant_meaning}

Strongest dimension: {strongest}
Binding constraint: {weakest}

Market size position: {size}

Top growth pool: {pool}

Consistency flags raised by the audit:
{flags}

Write one paragraph of no more than 130 words that states the decision,
names the single reason for it, and names the single thing most likely to
overturn it. Write for a reader who will act on it. No headings, no
bullets, no hedging, no marketing language."""


def synthesise(
    run: ResearchRun,
    attract: Attractiveness,
    pools: Sequence[Pool],
    rec: Recommendation,
    size: str,
    flags: Sequence[str],
) -> tuple:
    """
    A model-written opening paragraph, when a model is available.

    This is the one place the model adds judgement rather than tidying
    prose, and even here it is handed only computed conclusions. When it
    is unavailable the deterministic reasoning stands on its own, which
    is why the fallback is the recommendation text itself.
    """
    if not llm.available():
        return rec.reasoning, "deterministic"

    top = pools[0].display if pools else "none cleared the corroboration gate"
    prompt = SYNTHESIS_PROMPT.format(
        industry=run.industry,
        geography=run.geography,
        objective=run.objective,
        verdict=rec.verdict,
        posture=rec.posture,
        overall=attract.overall,
        band=attract.band,
        confidence=attract.confidence,
        quadrant=attract.quadrant,
        quadrant_meaning=attract.quadrant_meaning,
        strongest=f"{attract.strongest} ({attract.scores.get(attract.strongest, 0)}/100)",
        weakest=f"{attract.weakest} ({attract.scores.get(attract.weakest, 0)}/100)",
        size=size,
        pool=top,
        flags="\n".join(f"- {f}" for f in flags) or "- none",
    )

    text = llm.complete(prompt, max_tokens=320, temperature=0.25)
    if not text:
        return rec.reasoning, "deterministic"
    return text.strip(), "model"


def build_report(
    run: ResearchRun,
    attract: Attractiveness,
    pools: Sequence[Pool],
    links: Sequence[Link],
) -> ExecutiveReport:
    rec = recommend(attract, pools)
    size = size_statement(run.reconciliation, run)
    flags = contradiction_check(run)
    synthesis, synthesis_source = synthesise(run, attract, pools, rec, size, flags)

    return ExecutiveReport(
        industry=run.industry,
        geography=run.geography,
        objective=run.objective,
        recommendation=rec,
        situation=situation(run, attract),
        size_statement=size,
        where_to_play=where_to_play(pools, run.geography),
        how_to_win=how_to_win(attract, pools, links),
        falsifiers=falsifiers(attract, run.reconciliation),
        evidence_statement=evidence_statement(run, attract),
        flags=flags,
        synthesis=synthesis,
        synthesis_source=synthesis_source,
    )


# ----------------------------------------------------------------------
# Export
# ----------------------------------------------------------------------

def to_markdown(
    report: ExecutiveReport,
    run: ResearchRun,
    attract: Attractiveness,
    pools: Sequence[Pool],
) -> str:
    rec = report.recommendation
    lines: List[str] = [
        f"# {report.industry} — {report.geography}",
        f"_{report.objective} · evidence-led market intelligence_",
        "",
        "## Recommendation",
        f"**{rec.verdict} — {rec.posture}**",
        "",
        report.synthesis or rec.reasoning,
        "",
    ]

    if rec.conditions:
        lines.append("**Conditions**")
        lines.extend(f"- {c}" for c in rec.conditions)
        lines.append("")

    lines += ["## Situation", ""]
    lines.extend(f"- {s}" for s in report.situation)
    lines += ["", "## Market size — reconciled", "", report.size_statement, ""]

    lines += ["## Attractiveness", ""]
    lines.append(f"Overall **{attract.overall}/100** ({attract.band}) · "
                 f"confidence **{attract.confidence}/100** · "
                 f"quadrant **{attract.quadrant}**")
    lines.append("")
    lines.append("| Dimension | Score | Basis |")
    lines.append("| --- | ---: | --- |")
    for name, value in attract.scores.items():
        lines.append(f"| {name} | {value} | {attract.rationale[name]} |")
    lines.append("")

    lines += ["## Where to play", ""]
    lines.extend(f"- {w}" for w in report.where_to_play)
    lines += ["", "## How to win", ""]
    lines.extend(f"- {h}" for h in report.how_to_win)
    lines += ["", "## What would change this decision", ""]
    lines.extend(f"{i}. {f}" for i, f in enumerate(report.falsifiers, 1))

    if report.flags:
        lines += ["", "## Consistency flags", ""]
        lines.extend(f"- {f}" for f in report.flags)

    lines += ["", "## Evidence", "", report.evidence_statement, ""]
    lines += ["### Source register", ""]
    for result in run.results:
        for source in result.sources[:4]:
            lines.append(
                f"- `{source.ref}` {clip(source.title, 110)} — {source.url} "
                f"(authority {source.authority} · relevance {source.relevance} "
                f"· fit {source.industry_fit})"
            )

    return "\n".join(lines)


__all__ = [
    "ExecutiveReport",
    "synthesise",
    "POSTURES",
    "Recommendation",
    "build_report",
    "evidence_statement",
    "falsifiers",
    "how_to_win",
    "recommend",
    "situation",
    "size_statement",
    "to_markdown",
    "where_to_play",
]
