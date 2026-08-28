"""
Cross-domain synthesis.

Isolated domain findings are research. Strategy only appears when two
domains are read against each other. This module builds those pairings
and, importantly, grades each one by whether the underlying evidence
actually supports the inference — the previous build stamped every single
link "MEDIUM", which told the reader nothing.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

from .domains import DOMAINS
from .research import ResearchRun
from .text import clip

# Pairs worth reading together, with the strategic proposition each tests.
PAIRS: List[Tuple[int, int, str, str, str]] = [
    (1, 3, "Market ↔ Demand",
     "Growth only matters when it converts into usage, spend or adoption.",
     "Prioritise demand mechanisms that already monetise."),
    (3, 2, "Demand ↔ Segments",
     "Demand is never evenly distributed across segments.",
     "Concentrate where structural demand and willingness-to-pay overlap."),
    (5, 11, "Competition ↔ Returns",
     "Rivalry and incumbent scale set the ceiling on feasible returns.",
     "Treat competitive intensity as an explicit entry hurdle, not a footnote."),
    (7, 9, "Value chain ↔ Technology",
     "Technology matters when it moves a cost, capacity or control point.",
     "Target the technology-enabled control point, not the whole chain."),
    (8, 11, "Regulation ↔ Economics",
     "Policy sets access, compliance cost, capital need and timing.",
     "Translate every policy line into a number in the model."),
    (10, 12, "Customers ↔ Pools",
     "A pool is investable only when buyer pain and willingness-to-pay meet.",
     "Require customer-level evidence before sizing any pool."),
    (9, 12, "Technology ↔ Pools",
     "Technology creates a pool only when maturity and economics align.",
     "Sequence entry behind the commercial threshold, not the technical one."),
    (13, 12, "Risk ↔ Pools",
     "Upside is destroyed by access, economic and capital risk.",
     "Keep risk-adjusted feasibility separate from headline demand."),
    (2, 5, "Segments ↔ Competition",
     "Attractive segments attract the most capable competitors first.",
     "Enter where segment attractiveness and incumbent attention diverge."),
    (4, 7, "Trends ↔ Economics",
     "Business-model shifts redistribute margin before they redistribute revenue.",
     "Follow where margin is moving, not where revenue currently sits."),
]


@dataclass
class Link:
    left: int
    right: int
    title: str
    proposition: str
    decision: str
    because: List[str] = field(default_factory=list)
    refs: List[str] = field(default_factory=list)
    strength: int = 0

    @property
    def grade(self) -> str:
        if self.strength >= 70:
            return "STRONG"
        if self.strength >= 52:
            return "MODERATE"
        if self.strength >= 34:
            return "WEAK"
        return "UNSUPPORTED"

    @property
    def left_name(self) -> str:
        return DOMAINS[self.left].name

    @property
    def right_name(self) -> str:
        return DOMAINS[self.right].name


def _link_strength(run: ResearchRun, left: int, right: int) -> int:
    a, b = run.by_id(left), run.by_id(right)
    if not a or not b:
        return 0
    if not a.sources or not b.sources:
        return 0

    base = (a.confidence + b.confidence) / 2

    # Independent corroboration: distinct publishers across the pair.
    publishers = len({s.host for s in a.sources[:6]} | {s.host for s in b.sources[:6]})
    breadth = min(22, publishers * 3)

    # Quantification bonus: an inference standing on two numbers is
    # stronger than one standing on two adjectives.
    quantified = sum(1 for r in (a, b) if r.quantified) * 7

    return max(0, min(100, round(base * 0.78 + breadth + quantified)))


def build_links(run: ResearchRun) -> List[Link]:
    links: List[Link] = []
    for left, right, title, proposition, decision in PAIRS:
        a, b = run.by_id(left), run.by_id(right)
        if not a or not b:
            continue

        link = Link(
            left=left,
            right=right,
            title=title,
            proposition=proposition,
            decision=decision,
            strength=_link_strength(run, left, right),
        )
        if a.findings:
            link.because.append(clip(a.findings[0], 150))
            link.refs.extend(a.finding_refs[:1])
        if b.findings:
            link.because.append(clip(b.findings[0], 150))
            link.refs.extend(b.finding_refs[:1])

        links.append(link)

    links.sort(key=lambda l: l.strength, reverse=True)
    return links


def linkage_matrix(run: ResearchRun) -> Dict[str, object]:
    """Symmetric 13x13 strength matrix for the heatmap."""
    ids = [r.domain_id for r in run.results]
    labels = [f"D{i}" for i in ids]
    size = len(ids)
    matrix = [[0 for _ in range(size)] for _ in range(size)]

    index = {domain_id: i for i, domain_id in enumerate(ids)}
    for link in build_links(run):
        if link.left in index and link.right in index:
            i, j = index[link.left], index[link.right]
            matrix[i][j] = link.strength
            matrix[j][i] = link.strength

    for domain_id in ids:
        result = run.by_id(domain_id)
        if result:
            i = index[domain_id]
            matrix[i][i] = result.confidence

    return {"labels": labels, "matrix": matrix, "ids": ids}


def contradiction_check(run: ResearchRun) -> List[str]:
    """
    Cheap consistency tests that a reviewer would run by hand.
    Each returned string is a finding, not a warning to hide.
    """
    flags: List[str] = []
    report = run.reconciliation

    if report and report.conflicts:
        worst = max(report.conflicts, key=lambda c: c.gap_percent)
        flags.append(
            f"Size estimates for {worst.year} differ by "
            f"{worst.gap_percent:,.0f}%. {worst.headline}"
        )

    if report and report.rate_disagreement_pp and report.rate_disagreement_pp > 3:
        flags.append(
            f"Stated growth rates and the published size series disagree by "
            f"{report.rate_disagreement_pp:.1f} percentage points."
        )

    demand = run.by_id(3)
    risk = run.by_id(13)
    if demand and risk and demand.confidence - risk.confidence > 28:
        flags.append(
            "Demand evidence is materially stronger than risk evidence. "
            "The picture is optimistic by construction, not by finding."
        )

    thin = [r for r in run.results if r.sources and r.metrics.get("independent_domains", 0) < 2]
    if len(thin) >= 4:
        flags.append(
            f"{len(thin)} domains rest on a single publisher each. "
            "Independence, not volume, is the weak point of this evidence base."
        )

    unquantified = [r for r in run.results if r.sources and not r.quantified]
    if len(unquantified) >= 7:
        flags.append(
            f"{len(unquantified)} of {len(run.results)} domains produced no "
            "extractable figure. The analysis is directional, not quantitative."
        )

    return flags


__all__ = ["Link", "PAIRS", "build_links", "contradiction_check", "linkage_matrix"]
