"""
Narrative composition.

Every domain card in the previous build ended with the same paragraph:
"The domain affects Edtech through changes in demand, customer value,
cost, capacity, access or competitive structure." Thirteen times. That
sentence is true of every domain in every industry, which is another way
of saying it carries no information.

Here the implication is computed from what the domain actually returned —
how many independent publishers agreed, what numbers were extracted,
whether they conflict — so two domains never say the same thing unless
the evidence is genuinely the same.
"""

from __future__ import annotations

import statistics
from typing import Dict, List, Optional, Sequence

from .domains import Domain
from .extract import ExtractionBundle
from .sources import Source
from .text import clip


def _independent(sources: Sequence[Source]) -> int:
    return len({s.host for s in sources if s.host})


def evidence_grade(metrics: Dict[str, int], extraction: ExtractionBundle) -> str:
    """A label an analyst can defend in a review."""
    quality = metrics.get("quality", 0)
    independent = metrics.get("independent_domains", 0)
    quantified = not extraction.is_empty

    if quality >= 70 and independent >= 3 and quantified:
        return "SOURCE-BACKED"
    if quality >= 55 and independent >= 2:
        return "PARTIALLY SUPPORTED"
    if quality >= 40:
        return "DIRECTIONAL"
    return "PROVISIONAL"


def confidence_score(metrics: Dict[str, int], extraction: ExtractionBundle) -> int:
    """0-100 confidence in the domain's evidence, independent of how
    attractive the underlying market happens to be."""
    if not metrics.get("source_count"):
        return 0

    score = (
        0.34 * metrics.get("quality", 0)
        + 0.22 * metrics.get("direct_support", 0)
        + 0.18 * metrics.get("industry_fit", 0)
        + 0.14 * metrics.get("authority", 0)
    )
    score += min(12, metrics.get("independent_domains", 0) * 4)
    if extraction.money or extraction.rates:
        score += 6
    if extraction.shares:
        score += 3
    return max(0, min(100, round(score)))


def _quantified_line(extraction: ExtractionBundle) -> Optional[str]:
    """One sentence describing what numbers came out, in plain words."""
    parts: List[str] = []

    if extraction.money:
        # Global figures are excluded from the headline range. Mixing a
        # worldwide number into a country range is the single most
        # misleading thing a summary like this can do.
        local = [p for p in extraction.money
                 if p.usd_billions > 0 and p.scope != "global"]
        globals_ = [p for p in extraction.money
                    if p.usd_billions > 0 and p.scope == "global"]
        values = sorted(p.usd_billions for p in local)
        if globals_:
            parts.append(
                f"{len(globals_)} worldwide figure(s), held separate from "
                f"the local ones"
            )
        if values:
            if len(values) == 1:
                parts.append(f"one size figure, US${values[0]:,.1f}B")
            else:
                parts.append(
                    f"{len(values)} size figures, US${values[0]:,.1f}B–"
                    f"US${values[-1]:,.1f}B"
                )

    if extraction.rates:
        rates = [r.percent for r in extraction.rates]
        median = statistics.median(rates)
        if len(rates) == 1:
            parts.append(f"one growth rate of {median:.1f}% a year")
        else:
            parts.append(
                f"{len(rates)} growth rates averaging {median:.1f}% a year "
                f"(the lowest is {min(rates):.1f}%, the highest {max(rates):.1f}%)"
            )

    if extraction.shares:
        top = max(extraction.shares, key=lambda s: s.percent)
        parts.append(f"{top.subject} put at {top.percent:.0f}% of the market")

    if not parts:
        return None

    # Two facts is the readable limit for a card. The rest is on the
    # Market size tab, where there is room to lay it out properly.
    head = parts[:2]
    extra = len(parts) - len(head)
    line = "Found: " + "; ".join(head) + "."
    if extra:
        line += f" Plus {extra} more, on the Market size tab."
    return line


def implication(
    domain: Domain,
    metrics: Dict[str, int],
    extraction: ExtractionBundle,
    sources: Sequence[Source],
    industry: str,
    geography: str,
) -> str:
    """
    The 'so what', written the way you would say it out loud.

    The rule for every sentence here: no consulting vocabulary that a
    smart reader outside the industry would have to decode. Not
    "structural demand converts to monetisable usage" but "people want
    it and some of them are paying". Short sentences, one idea each.
    """
    independent = _independent(sources)
    grade = evidence_grade(metrics, extraction)

    if not sources:
        return (
            f"We found nothing usable here. That does not mean there is "
            f"nothing to find — it means this question needs someone to go "
            f"and ask it directly."
        )

    quantified = _quantified_line(extraction)

    if grade == "PROVISIONAL":
        spine = (
            f"The pages we found talk about {industry.lower()} in {geography}, "
            f"but none of them says anything specific enough to check."
        )
    elif independent <= 1:
        spine = (
            f"Everything here comes from one publisher. That makes it one "
            f"company's view, not what the market agrees on."
        )
    elif independent == 2:
        spine = (
            f"Two publishers say broadly the same thing. That is enough to "
            f"take the direction seriously, but not enough to bet a number on."
        )
    else:
        spine = (
            f"{independent} publishers who do not appear to be copying each "
            f"other agree on the direction here. The direction is safe to use; "
            f"the individual numbers still are not."
        )

    tail = f"It answers one question. {domain.decision.strip()}"

    if quantified:
        return f"{spine} {quantified} {tail}"
    return (
        f"{spine} Nobody published a figure we could pull out, so this can "
        f"shape the thinking but cannot go into a model. {tail}"
    )


def limitation(metrics: Dict[str, int], extraction: ExtractionBundle) -> str:
    bits: List[str] = []
    if metrics.get("independent_domains", 0) < 3:
        bits.append("too few separate publishers to call this a consensus")
    if metrics.get("authority", 0) < 55:
        bits.append("no government, academic or official source in the mix")
    if extraction.is_empty:
        bits.append("no hard numbers could be extracted")
    if metrics.get("direct_support", 0) < 45:
        bits.append("the sources circle the question rather than answering it")
    if not bits:
        return "Nothing here needs a caveat beyond the usual lag in published data."
    if len(bits) == 1:
        return f"Worth knowing: {bits[0]}."
    return f"Worth knowing: {', '.join(bits[:-1])}, and {bits[-1]}."


def compose(
    domain: Domain,
    findings: Sequence[str],
    metrics: Dict[str, int],
    extraction: ExtractionBundle,
    sources: Sequence[Source],
    industry: str,
    geography: str,
) -> Dict[str, object]:
    """The deterministic writer. Always available, no model required."""
    return {
        "findings": [clip(f, 300) for f in findings],
        "implication": implication(
            domain, metrics, extraction, sources, industry, geography
        ),
        "grade": evidence_grade(metrics, extraction),
        "limitation": limitation(metrics, extraction),
        "confidence": confidence_score(metrics, extraction),
    }


def build_prompt(
    domain: Domain,
    question: str,
    findings: Sequence[str],
    refs: Sequence[str],
    industry: str,
    geography: str,
) -> str:
    evidence = "\n".join(
        f"[{ref}] {text}" for ref, text in zip(refs, findings)
    )
    return f"""Industry: {industry}
Geography: {geography}
Domain: {domain.name} — {domain.scope}
Decision this domain must change: {domain.decision}

Question: {question}

Evidence (the only material you may use):
{evidence}

Write exactly three sections, no headings other than these:

FINDING
Two to four bullets. Each bullet is one sentence, states a specific
claim, and ends with its reference tag in square brackets. Prefer
bullets that carry a number. Do not repeat the same claim twice.

MECHANISM
Two sentences on the causal or economic mechanism linking this evidence
to the decision above. Be specific to {industry}; a sentence that would
be true of any industry is a failed sentence.

SO WHAT
Two sentences naming what a decision-maker should do differently, and
what would have to be true for that to change.
"""


def parse_model_output(text: str) -> Optional[Dict[str, object]]:
    """Split model prose back into the card's fields. None if malformed."""
    if not text:
        return None

    upper = text.upper()
    if "FINDING" not in upper:
        return None

    def section(name: str, nxt: Sequence[str]) -> str:
        start = upper.find(name)
        if start < 0:
            return ""
        start += len(name)
        end = len(text)
        for candidate in nxt:
            pos = upper.find(candidate, start)
            if pos > 0:
                end = min(end, pos)
        return text[start:end].strip(" :\n-")

    finding_block = section("FINDING", ["MECHANISM", "SO WHAT"])
    mechanism = section("MECHANISM", ["SO WHAT"])
    so_what = section("SO WHAT", [])

    bullets = [
        line.strip(" -•*")
        for line in finding_block.splitlines()
        if len(line.strip(" -•*")) > 25
    ]
    if not bullets:
        return None

    return {
        "findings": bullets[:4],
        "mechanism": mechanism,
        "so_what": so_what,
    }


__all__ = [
    "build_prompt",
    "compose",
    "confidence_score",
    "evidence_grade",
    "implication",
    "limitation",
    "parse_model_output",
]
