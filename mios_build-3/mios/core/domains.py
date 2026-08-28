"""
The 13-domain research spine.

Each domain carries more than a label: it declares which strategic lens it
feeds, what decision it is supposed to change, and which quantitative
signals we expect to harvest from it. Downstream scoring reads these
declarations instead of hard-coding domain numbers in five places.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List

# Strategic lenses. Every domain maps to exactly one primary lens.
LENS_DEMAND = "Demand"
LENS_SUPPLY = "Supply & Rivalry"
LENS_ECONOMICS = "Economics"
LENS_CONTEXT = "Context & Risk"

LENS_ORDER = [LENS_DEMAND, LENS_SUPPLY, LENS_ECONOMICS, LENS_CONTEXT]


@dataclass(frozen=True)
class Domain:
    id: int
    name: str
    scope: str
    lens: str
    decision: str
    signals: List[str] = field(default_factory=list)
    query_hints: List[str] = field(default_factory=list)

    @property
    def code(self) -> str:
        return f"D{self.id}"


DOMAINS: Dict[int, Domain] = {
    1: Domain(
        id=1,
        name="Market Size & Growth",
        scope="current scale, historical trajectory, forecast range and CAGR",
        lens=LENS_DEMAND,
        decision="Is this market big enough to be worth the cost of entering?",
        signals=["market_size", "cagr", "forecast"],
        query_hints=["market size forecast CAGR", "market value billion 2030"],
    ),
    2: Domain(
        id=2,
        name="Market Segmentation",
        scope="customer, product, use-case and geographic segments",
        lens=LENS_DEMAND,
        decision="Which part of this market could you realistically sell to?",
        signals=["share", "segment"],
        query_hints=["market segmentation by segment share", "segment split percentage"],
    ),
    3: Domain(
        id=3,
        name="Demand Drivers",
        scope="measurable drivers of adoption, usage, spend and willingness to pay",
        lens=LENS_DEMAND,
        decision="Is demand here to stay, or is this just a good year?",
        signals=["growth", "adoption", "penetration"],
        query_hints=["demand drivers adoption growth", "spending willingness to pay"],
    ),
    4: Domain(
        id=4,
        name="Industry Trends",
        scope="structural trends, business-model shifts and economic implications",
        lens=LENS_DEMAND,
        decision="Which way of making money is winning?",
        signals=["trend", "business_model"],
        query_hints=["industry trends business model shift", "structural change outlook"],
    ),
    5: Domain(
        id=5,
        name="Competitive Landscape",
        scope="concentration, shares, incumbent advantages, barriers and rivalry",
        lens=LENS_SUPPLY,
        decision="Can a newcomer get big enough to matter?",
        signals=["share", "concentration", "players"],
        query_hints=["market share leaders concentration", "competitive landscape fragmentation"],
    ),
    6: Domain(
        id=6,
        name="Key Companies",
        scope="participants, capabilities, investments and strategic moves",
        lens=LENS_SUPPLY,
        decision="Who sets prices and expectations today?",
        signals=["players", "revenue", "funding"],
        query_hints=["leading companies revenue", "top players strategy investment"],
    ),
    7: Domain(
        id=7,
        name="Value Chain & Economics",
        scope="inputs, cost pools, bottlenecks, control points and margin pools",
        lens=LENS_ECONOMICS,
        decision="Which part of the business actually keeps the profit?",
        signals=["margin", "cost", "unit_economics"],
        query_hints=["value chain margin cost structure", "unit economics gross margin"],
    ),
    8: Domain(
        id=8,
        name="Regulatory Environment",
        scope="laws, licences, incentives, restrictions and compliance economics",
        lens=LENS_CONTEXT,
        decision="Do the rules help you, or get in the way?",
        signals=["policy", "compliance"],
        query_hints=["regulation policy compliance rules", "government incentive scheme"],
    ),
    9: Domain(
        id=9,
        name="Technology Landscape",
        scope="technology effects on cost, capacity, productivity and adoption",
        lens=LENS_ECONOMICS,
        decision="Does technology meaningfully change costs?",
        signals=["technology", "cost", "adoption"],
        query_hints=["technology adoption cost curve", "platform infrastructure stack"],
    ),
    10: Domain(
        id=10,
        name="Customer Segments",
        scope="buyers, needs, purchase criteria and willingness to pay",
        lens=LENS_DEMAND,
        decision="Who actually pays, and what do they compare you to?",
        signals=["customers", "pricing", "willingness"],
        query_hints=["customer segments buyers pricing", "who pays purchase criteria"],
    ),
    11: Domain(
        id=11,
        name="Industry Attractiveness",
        scope="growth, scale, economics, rivalry, barriers, regulation and returns",
        lens=LENS_ECONOMICS,
        decision="Do the returns justify the money you would put in?",
        signals=["returns", "profitability"],
        query_hints=["industry profitability returns outlook", "investment attractiveness"],
    ),
    12: Domain(
        id=12,
        name="Growth Pools",
        scope="concrete opportunities tested for demand and value capture",
        lens=LENS_DEMAND,
        decision="Which single opportunity should you go after first?",
        signals=["opportunity", "whitespace"],
        query_hints=["growth opportunities whitespace", "fastest growing segment opportunity"],
    ),
    13: Domain(
        id=13,
        name="Key Risks",
        scope="demand, supply, policy, technology, capital and competitive risks",
        lens=LENS_CONTEXT,
        decision="What would kill this, and how early would you see it coming?",
        signals=["risk", "failure", "churn"],
        query_hints=["risks challenges failures", "profitability challenge churn CAC"],
    ),
}

DOMAIN_IDS = sorted(DOMAINS)

# Domains that carry the executive spine. Order is the reading order of
# the priority rail in the UI, not the domain number.
PRIORITY_SPINE = [
    ("P1", 1, "Is the pool big enough?"),
    ("P2", 3, "Is demand structural?"),
    ("P3", 5, "Can we get in?"),
    ("P4", 7, "Where is the margin?"),
    ("P5", 13, "What breaks it?"),
]

SPINE_DOMAIN_IDS = [d for _, d, _ in PRIORITY_SPINE]


def lens_members(lens: str) -> List[int]:
    """Domain ids belonging to a strategic lens."""
    return [d.id for d in DOMAINS.values() if d.lens == lens]


def domain(domain_id: int) -> Domain:
    return DOMAINS[domain_id]


def priority_label(domain_id: int) -> str:
    for code, did, _ in PRIORITY_SPINE:
        if did == domain_id:
            return code
    return f"D{domain_id}"


# ----------------------------------------------------------------------
# Porter's five forces mapped onto the domain spine.
# Each force reads named domains rather than magic numbers.
# ----------------------------------------------------------------------

FIVE_FORCES = {
    "Rivalry": {"domains": [5, 6], "invert": True},
    "New entrants": {"domains": [5, 8], "invert": True},
    "Buyer power": {"domains": [10, 2], "invert": True},
    "Supplier power": {"domains": [7, 9], "invert": True},
    "Substitutes": {"domains": [4, 9], "invert": True},
}

__all__ = [
    "Domain",
    "DOMAINS",
    "DOMAIN_IDS",
    "PRIORITY_SPINE",
    "SPINE_DOMAIN_IDS",
    "LENS_DEMAND",
    "LENS_SUPPLY",
    "LENS_ECONOMICS",
    "LENS_CONTEXT",
    "LENS_ORDER",
    "FIVE_FORCES",
    "lens_members",
    "domain",
    "priority_label",
]
