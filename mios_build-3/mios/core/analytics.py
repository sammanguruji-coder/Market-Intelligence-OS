"""
Attractiveness and structural analytics.

This module replaces the scoring in the previous build, which had a
category error at its centre: every "market" score was computed from
*evidence quality metrics*. The clearest symptom was

    "Risk-adjusted profile": 100 - quality_of_risk_evidence

which means the better your risk sourcing became, the less attractive
the market appeared. It also meant a market with no risk coverage at all
scored 100 on risk.

Here the two things are kept apart and both are reported:

  ATTRACTIVENESS  - derived from extracted market facts: growth rates,
                    absolute scale, concentration, policy direction,
                    risk density.
  CONFIDENCE      - derived from source metrics: authority, independence,
                    direct support, quantification.

A market can be attractive and poorly evidenced. That combination is a
real state of the world and the conviction map shows it rather than
blending it into one misleading number.
"""

from __future__ import annotations

import math
import statistics
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence

from .domains import FIVE_FORCES, LENS_ORDER, DOMAINS, lens_members
from .research import ResearchRun

# ----------------------------------------------------------------------
# Lexicons
# ----------------------------------------------------------------------

POLICY_SUPPORTIVE = (
    "incentive", "subsidy", "subsidise", "scheme", "mission", "promot",
    "encourag", "support", "liberalis", "liberaliz", "fdi allowed",
    "tax holiday", "grant", "pli", "budget allocation", "national policy",
    "deregulat", "streamlin", "single window",
)

POLICY_RESTRICTIVE = (
    "ban", "prohibit", "restrict", "penalt", "cap on", "licence require",
    "license require", "compliance burden", "moratorium", "crackdown",
    "scrutiny", "investigation", "mandat", "levy", "tariff", "audit",
    "data localis", "data localiz",
)

RISK_SEVERE = (
    "insolven", "bankrupt", "collapse", "fraud", "shut down", "wind down",
    "layoff", "default", "write-off", "writedown", "class action",
    "delisting", "funding winter", "cash burn",
)

RISK_MODERATE = (
    "churn", "customer acquisition cost", "cac", "profitability challenge",
    "margin pressure", "regulatory risk", "competition", "saturation",
    "slowdown", "downturn", "attrition", "discount", "price war",
    "delayed profitability", "unit economics",
)

MARGIN_CUES = (
    "gross margin", "operating margin", "ebitda", "contribution margin",
    "take rate", "unit economics", "arpu", "ltv", "payback",
    "pricing power", "monetis", "monetiz",
)

BARRIER_CUES = (
    "capital intensive", "regulatory approval", "licence", "license",
    "network effect", "switching cost", "brand", "distribution",
    "scale advantage", "patent", "proprietary", "lock-in",
)


def _lexicon_hits(text: str, lexicon: Sequence[str]) -> int:
    low = text.lower()
    return sum(1 for term in lexicon if term in low)


def _domain_text(run: ResearchRun, domain_ids: Sequence[int]) -> str:
    chunks: List[str] = []
    for domain_id in domain_ids:
        result = run.by_id(domain_id)
        if not result:
            continue
        chunks.extend(result.findings)
        for source in result.sources[:6]:
            chunks.append(source.content[:1400])
    return " ".join(chunks)


def _scale(value: float, low: float, high: float, floor: int = 5, ceiling: int = 100) -> int:
    """Linear map with clamping."""
    if high <= low:
        return floor
    ratio = (value - low) / (high - low)
    return int(max(floor, min(ceiling, round(floor + ratio * (ceiling - floor)))))


# ----------------------------------------------------------------------
# Individual dimensions
# ----------------------------------------------------------------------

def growth_momentum(run: ResearchRun) -> tuple[int, str]:
    """From actual growth rates, not from how good the sources were."""
    rates = [r.percent for r in run.all_rates if 0 < r.percent < 90]
    implied = run.reconciliation.implied_cagr if run.reconciliation else None

    pool = list(rates)
    if implied is not None and 0 < implied < 90:
        pool.append(implied)

    if not pool:
        return 35, "No source published a growth rate, so this is scored neutral."

    median = statistics.median(pool)
    # 0% -> 12, 8% -> 50, 20% -> 84, 30%+ -> 100
    score = _scale(median, 0, 30, floor=12, ceiling=100)
    return score, (f"Across {len(pool)} published figures, this market is growing "
                   f"about {median:.1f}% a year.")


def market_scale(run: ResearchRun) -> tuple[int, str]:
    """Absolute addressable scale, log-weighted."""
    report = run.reconciliation
    anchor: Optional[float] = None

    if report and report.anchor_value:
        anchor = report.anchor_value
    else:
        target = [p.usd_billions for p in run.all_money if p.usd_billions > 0]
        if target:
            anchor = statistics.median(target)

    if not anchor or anchor <= 0:
        return 30, "No usable size figure was found, so this scores below neutral."

    # 0.5B -> 25, 5B -> 55, 50B -> 82, 500B -> 100
    score = _scale(math.log10(max(anchor, 0.1)), -0.3, 2.7, floor=25, ceiling=100)
    return score, f"The market is worth roughly ${anchor:,.1f} billion today."


def segment_depth(run: ResearchRun) -> tuple[int, str]:
    """How many distinct, quantified places there are to play."""
    shares = run.all_shares
    distinct = len({s.subject.lower() for s in shares})
    seg_result = run.by_id(2)
    seg_conf = seg_result.confidence if seg_result else 0

    score = _scale(distinct, 0, 8, floor=25, ceiling=95)
    score = round(0.7 * score + 0.3 * seg_conf)
    if distinct == 0:
        return max(20, score), ("No source broke the market into segments with numbers "
                                "attached, so there is no clear picture of where to play.")
    return score, (f"{distinct} different parts of this market have a published "
                   f"size, so there are several places you could choose to compete.")


def value_capture(run: ResearchRun) -> tuple[int, str]:
    """Evidence that margin exists and is discussable, not just revenue."""
    text = _domain_text(run, [7, 11, 10])
    margin_hits = _lexicon_hits(text, MARGIN_CUES)
    barrier_hits = _lexicon_hits(text, BARRIER_CUES)

    score = _scale(margin_hits * 2 + barrier_hits, 0, 18, floor=22, ceiling=95)
    if margin_hits == 0:
        return max(20, score - 8), (
            "The sources talk about revenue but never about profit. Until "
            "someone shows what it costs to serve a customer, making money "
            "here is unproven."
        )
    thing = "thing" if barrier_hits == 1 else "things"
    way = "way" if margin_hits == 1 else "ways"
    return score, (
        f"The sources discuss profitability in {margin_hits} different {way} "
        f"and mention {barrier_hits} {thing} that would make a position hard "
        f"for rivals to copy."
    )


def competitive_access(run: ResearchRun) -> tuple[int, str]:
    """
    High score = a new entrant can reach scale.
    Driven by observed concentration, not by how well we sourced D5.
    """
    shares = [s.percent for s in run.all_shares if s.percent > 0]
    text = _domain_text(run, [5, 6])

    fragmentation_words = ("fragmented", "highly fragmented", "moderately fragmented",
                           "long tail", "many players", "emerging startups")
    concentration_words = ("dominant", "duopoly", "monopoly", "market leader controls",
                           "consolidat", "oligopol")

    frag = _lexicon_hits(text, fragmentation_words)
    conc = _lexicon_hits(text, concentration_words)

    if shares:
        top_share = max(shares)
        # 60%+ to one holder -> hard; 15% -> open
        structural = _scale(100 - top_share, 25, 90, floor=15, ceiling=95)
        detail = (f"The biggest player holds about {top_share:.0f}% of the market, "
                  f"which sets how much room a newcomer has.")
    else:
        structural = 50
        detail = ("No market-share figures were found, so this is judged from how "
                  "the sources describe the competition rather than from numbers.")

    language = _scale(frag - conc, -4, 5, floor=20, ceiling=90)
    score = round(0.62 * structural + 0.38 * language)
    crowding = (
        "Sources mostly describe the market as split among many players."
        if frag > conc else
        "Sources mostly describe the market as dominated by a few players."
        if conc > frag else
        "Sources are split on whether this market is crowded or concentrated."
    )
    return score, f"{detail} {crowding}"


def policy_direction(run: ResearchRun) -> tuple[int, str]:
    text = _domain_text(run, [8])
    supportive = _lexicon_hits(text, POLICY_SUPPORTIVE)
    restrictive = _lexicon_hits(text, POLICY_RESTRICTIVE)

    if supportive == 0 and restrictive == 0:
        return 45, ("Nothing was found about whether regulators help or hinder here, "
                    "so this is scored neutral.")

    net = supportive - restrictive
    score = _scale(net, -6, 8, floor=15, ceiling=95)
    direction = (
        "government policy is helping this market"
        if net > 0 else
        "government policy is holding this market back"
        if net < 0 else
        "government policy cuts both ways here"
    )
    return score, (
        f"On balance, {direction}: {supportive} mentions of support such as "
        f"incentives or schemes, against {restrictive} mentions of "
        f"restrictions such as rules or penalties."
    )


def risk_load(run: ResearchRun) -> tuple[int, str]:
    """
    High score = low risk load. Computed from what the risk evidence
    actually says, so better risk research no longer penalises the market.
    """
    text = _domain_text(run, [13])
    severe = _lexicon_hits(text, RISK_SEVERE)
    moderate = _lexicon_hits(text, RISK_MODERATE)

    risk_result = run.by_id(13)
    if not risk_result or not risk_result.sources:
        return 40, (
            "No usable evidence about risks was found. This scores below "
            "neutral on purpose: finding no risks is not the same as there "
            "being none."
        )

    weighted = severe * 3 + moderate
    score = _scale(-weighted, -24, 0, floor=10, ceiling=92)
    problem = "serious problem" if severe == 1 else "serious problems"
    pressure = "ongoing pressure" if moderate == 1 else "ongoing pressures"
    return score, (
        f"The sources flag {severe} {problem} such as failures or write-offs, "
        f"and {moderate} {pressure} such as customer loss or thin margins."
    )


# ----------------------------------------------------------------------
# Composite
# ----------------------------------------------------------------------

DIMENSIONS = [
    ("Growth momentum", growth_momentum, 0.22),
    ("Market scale", market_scale, 0.16),
    ("Segment depth", segment_depth, 0.10),
    ("Value capture", value_capture, 0.18),
    ("Competitive access", competitive_access, 0.14),
    ("Policy direction", policy_direction, 0.08),
    ("Risk headroom", risk_load, 0.12),
]


@dataclass
class Attractiveness:
    scores: Dict[str, int] = field(default_factory=dict)
    rationale: Dict[str, str] = field(default_factory=dict)
    overall: int = 0
    confidence: int = 0

    @property
    def band(self) -> str:
        if self.overall >= 72:
            return "STRONG"
        if self.overall >= 58:
            return "CONSTRUCTIVE"
        if self.overall >= 44:
            return "MIXED"
        return "WEAK"

    @property
    def quadrant(self) -> str:
        """Conviction map placement."""
        high_a = self.overall >= 58
        high_c = self.confidence >= 60
        if high_a and high_c:
            return "ACT"
        if high_a and not high_c:
            return "VALIDATE"
        if not high_a and high_c:
            return "PASS"
        return "PARK"

    @property
    def quadrant_meaning(self) -> str:
        return {
            "ACT": "The market looks good and the evidence backs it up. "
                   "Start planning how to enter.",
            "VALIDATE": "The market looks good but the evidence is thin. "
                        "Talk to real customers before committing money.",
            "PASS": "The evidence is solid and it says this market is not "
                    "worth entering. That is a useful answer.",
            "PARK": "Neither the market nor the evidence is strong enough to "
                    "act on. Revisit if something changes.",
        }[self.quadrant]

    @property
    def strongest(self) -> str:
        return max(self.scores, key=lambda k: self.scores[k]) if self.scores else ""

    @property
    def weakest(self) -> str:
        return min(self.scores, key=lambda k: self.scores[k]) if self.scores else ""


def evidence_confidence(run: ResearchRun) -> int:
    """Separate axis: how much should we trust the picture above?"""
    if not run.results:
        return 0

    base = run.mean_confidence
    coverage = 100 * run.covered_domains / max(1, len(run.results))
    quantified = 100 * run.quantified_domains / max(1, len(run.results))
    independence = min(100, run.independent_publishers * 4)

    score = (
        0.40 * base
        + 0.20 * coverage
        + 0.22 * quantified
        + 0.18 * independence
    )

    if run.reconciliation:
        if run.reconciliation.verdict == "CONFLICTED":
            score -= 10
        elif run.reconciliation.verdict == "INCONSISTENT":
            score -= 7
        elif run.reconciliation.verdict == "RECONCILED":
            score += 5

    return max(0, min(100, round(score)))


def attractiveness(run: ResearchRun) -> Attractiveness:
    result = Attractiveness()
    total = 0.0

    for label, fn, weight in DIMENSIONS:
        score, why = fn(run)
        result.scores[label] = score
        result.rationale[label] = why
        total += weight * score

    result.overall = max(0, min(100, round(total)))
    result.confidence = evidence_confidence(run)
    return result


# ----------------------------------------------------------------------
# Five forces
# ----------------------------------------------------------------------

def five_forces(run: ResearchRun, attract: Attractiveness) -> Dict[str, int]:
    """
    Scored so that a HIGH number means the force is FAVOURABLE to a new
    entrant — consistent with every other score in the system.
    """
    access = attract.scores.get("Competitive access", 50)
    capture = attract.scores.get("Value capture", 50)
    policy = attract.scores.get("Policy direction", 50)
    growth = attract.scores.get("Growth momentum", 50)

    text_supply = _domain_text(run, [7, 9])
    text_buyer = _domain_text(run, [10, 2])
    text_sub = _domain_text(run, [4, 9])

    supplier_pressure = _lexicon_hits(text_supply, ("supplier", "vendor lock",
                                                    "input cost", "shortage",
                                                    "dependency", "single source"))
    buyer_pressure = _lexicon_hits(text_buyer, ("price sensitive", "discount",
                                                "switching", "free tier",
                                                "bargaining", "churn"))
    substitute_pressure = _lexicon_hits(text_sub, ("alternative", "substitute",
                                                   "replace", "in-house",
                                                   "diy", "open source"))

    return {
        "Rivalry": round(0.7 * access + 0.3 * growth),
        "New entrants": round(0.55 * access + 0.45 * policy),
        "Buyer power": _scale(-buyer_pressure, -10, 0, floor=18, ceiling=88),
        "Supplier power": _scale(-supplier_pressure, -10, 0, floor=20, ceiling=90),
        "Substitutes": round(
            0.5 * _scale(-substitute_pressure, -10, 0, floor=20, ceiling=90)
            + 0.5 * capture
        ),
    }


# ----------------------------------------------------------------------
# Lens roll-up (used by the evidence spine and the Venn)
# ----------------------------------------------------------------------

def lens_scores(run: ResearchRun) -> Dict[str, int]:
    out: Dict[str, int] = {}
    for lens in LENS_ORDER:
        members = lens_members(lens)
        values = [
            run.by_id(d).confidence
            for d in members
            if run.by_id(d) and run.by_id(d).confidence
        ]
        out[lens] = round(sum(values) / len(values)) if values else 0
    return out


def domain_table(run: ResearchRun) -> List[Dict[str, object]]:
    rows: List[Dict[str, object]] = []
    for result in run.results:
        rows.append(
            {
                "code": result.code,
                "domain": result.name,
                "lens": result.lens,
                "confidence": result.confidence,
                "quality": result.metrics.get("quality", 0),
                "relevance": result.metrics.get("relevance", 0),
                "direct_support": result.metrics.get("direct_support", 0),
                "industry_fit": result.metrics.get("industry_fit", 0),
                "authority": result.metrics.get("authority", 0),
                "publishers": result.metrics.get("independent_domains", 0),
                "sources": result.source_count,
                "grade": result.grade,
                "quantified": result.quantified,
            }
        )
    return rows


def evidence_gaps(run: ResearchRun, threshold: int = 55) -> List[Dict[str, object]]:
    """Domains that would not survive a partner review."""
    gaps = []
    for result in run.results:
        reasons = []
        if result.confidence < threshold:
            reasons.append("the evidence is weak overall")
        if result.metrics.get("independent_domains", 0) < 2:
            reasons.append("everything comes from one publisher")
        if not result.quantified:
            reasons.append("no hard numbers were found")
        if result.metrics.get("authority", 0) < 50:
            reasons.append("no official or academic source")
        if reasons:
            gaps.append(
                {
                    "code": result.code,
                    "domain": result.name,
                    "confidence": result.confidence,
                    "reasons": reasons,
                    "decision": DOMAINS[result.domain_id].decision,
                }
            )
    gaps.sort(key=lambda g: g["confidence"])
    return gaps


__all__ = [
    "Attractiveness",
    "DIMENSIONS",
    "attractiveness",
    "domain_table",
    "evidence_confidence",
    "evidence_gaps",
    "five_forces",
    "lens_scores",
]
