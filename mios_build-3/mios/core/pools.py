"""
Growth pools.

The previous build surfaced pools called "A Multi Billion Dollar
Opportunity" and "and demand for personalized learning solutions" —
fragments of article titles and mid-sentence clauses promoted to
strategic options. The fix is a grammar-aware candidate extractor with
hard quality gates, plus a rule that a candidate must appear in at least
two independent domains before it can be scored at all.

A pool is only investable when three things overlap: demand evidence,
a monetisation mechanism, and reachable competitive access. That
three-way overlap is what the Venn on the Growth Pools tab draws.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, List, Sequence, Set

from .domains import DOMAINS
from .research import DomainResult, ResearchRun
from .sources import STOPWORDS, industry_terms
from .text import clean, clip

# Domains that may nominate a pool.
NOMINATING_DOMAINS = (12, 4, 3, 7, 2, 9, 10)

# Domains that supply each of the three overlap tests.
DEMAND_DOMAINS = (1, 2, 3, 10, 12)
MONETISATION_DOMAINS = (7, 9, 11)
ACCESS_DOMAINS = (5, 6, 8)

# Head nouns that mark the end of an opportunity phrase. Anchoring the
# capture to one to three words immediately before the head noun stops
# the regex from swallowing half a sentence, which is how the previous
# build produced pools like "than a dozen credible providers against a".
_HEAD_NOUNS = (
    r"market|segment|segments|platforms?|services?|solutions?|"
    r"infrastructure|ecosystem|category|channel|content|tooling|"
    r"credentialing|certification|upskilling|expansion|adoption|delivery"
)

_LEAD_VERBS = (
    r"demand for|market for|opportunity in|opportunities in|expansion into|"
    r"shift to|shift toward|shift towards|adoption of|growth in|"
    r"investment in|spending on|underserved in|whitespace in"
)

OPPORTUNITY_PATTERNS = (
    # "demand for personalised learning solutions"
    rf"(?:{_LEAD_VERBS})\s+(?P<phrase>(?:[a-z0-9][a-z0-9\-]{{2,}}\s+){{0,3}}"
    rf"[a-z0-9][a-z0-9\-]{{2,}})",
    # "vernacular content expansion", "assessment and credentialing services"
    rf"(?P<phrase>(?:[a-z0-9][a-z0-9\-]{{2,}}\s+){{1,3}}(?:{_HEAD_NOUNS}))\b",
)

PHRASE_BLOCKLIST = {
    "the market", "this market", "the industry", "the sector", "the report",
    "the company", "the study", "the following", "the above", "the same",
    "our market", "the global", "the overall", "billion dollar",
    "multi billion dollar", "key takeaways", "the post", "the topic",
    "the latest", "the vital news", "the forecast period", "the market size",
}

LEADING_JUNK = re.compile(
    r"^(and|or|but|the|a|an|of|in|on|for|with|by|to|its|their|this|that|"
    r"these|those|which|as|is|are|was|were|has|have|be)\s+",
    re.I,
)


@dataclass
class Pool:
    name: str
    display: str
    supporting_domains: List[int] = field(default_factory=list)
    demand: int = 0
    monetisation: int = 0
    access: int = 0
    evidence: int = 0
    risk_headroom: int = 0
    priority: int = 0
    rank: int = 0
    refs: List[str] = field(default_factory=list)
    quotes: List[str] = field(default_factory=list)

    @property
    def investable(self) -> bool:
        return self.demand >= 55 and self.monetisation >= 50 and self.access >= 45

    @property
    def blocker(self) -> str:
        if self.demand < 55:
            return "Demand evidence is the binding constraint."
        if self.monetisation < 50:
            return "No credible monetisation mechanism is evidenced."
        if self.access < 45:
            return "Competitive access is the binding constraint."
        return "All three tests clear; sequencing is the open question."

    @property
    def overlap_flags(self) -> Dict[str, bool]:
        return {
            "Demand": self.demand >= 55,
            "Monetisation": self.monetisation >= 50,
            "Access": self.access >= 45,
        }


# ----------------------------------------------------------------------
# Candidate extraction
# ----------------------------------------------------------------------

def _normalise(phrase: str) -> str:
    phrase = clean(phrase).lower()
    phrase = LEADING_JUNK.sub("", phrase)
    phrase = re.sub(r"\s+", " ", phrase).strip(" -–—,.")
    return phrase


def _acceptable(phrase: str, industry_vocab: Sequence[str]) -> bool:
    if not phrase or phrase in PHRASE_BLOCKLIST:
        return False
    words = phrase.split()
    if not (2 <= len(words) <= 5):
        return False
    if all(w in STOPWORDS for w in words):
        return False
    if any(len(w) < 2 for w in words):
        return False
    if re.search(r"\d{4,}", phrase):
        return False
    # Phrases that end mid-clause are fragments, not options.
    if words[-1] in STOPWORDS or words[0] in STOPWORDS:
        return False
    if any(w in {"than", "against", "which", "whose", "while", "though",
                 "remain", "remains", "growing", "underserved"} for w in words):
        return False
    # Must carry at least one substantive word.
    substantive = [w for w in words if w not in STOPWORDS and len(w) > 3]
    if len(substantive) < 1:
        return False
    # Reject pure industry restatements ("edtech market").
    if len(substantive) == 1 and substantive[0] in industry_vocab:
        return False
    return True


def discover(run: ResearchRun) -> Dict[str, Set[int]]:
    """
    Candidate phrase -> set of domains that mention it.

    Corroboration gate: a phrase becomes a candidate pool only when it is
    visible from two independent research domains, or from one domain but
    two independent publishers. A phrase seen once, in one place, is a
    sentence fragment — which is exactly how "A Multi Billion Dollar
    Opportunity" became a strategic option in the previous build.
    """
    vocab = set(industry_terms(run.industry))
    domains_seen: Dict[str, Set[int]] = {}
    hosts_seen: Dict[str, Set[str]] = {}

    for result in run.results:
        if result.domain_id not in NOMINATING_DOMAINS:
            continue

        blocks = [(" ".join(result.findings), "")] + [
            (" ".join(s.sentences), s.host) for s in result.sources[:6]
        ]

        for text, host in blocks:
            low = text.lower()
            if not low.strip():
                continue
            for pattern in OPPORTUNITY_PATTERNS:
                for match in re.finditer(pattern, low):
                    phrase = _normalise(match.group("phrase"))
                    if not _acceptable(phrase, vocab):
                        continue
                    domains_seen.setdefault(phrase, set()).add(result.domain_id)
                    if host:
                        hosts_seen.setdefault(phrase, set()).add(host)

    return {
        phrase: domains
        for phrase, domains in domains_seen.items()
        if len(domains) >= 2 or len(hosts_seen.get(phrase, set())) >= 2
    }


# ----------------------------------------------------------------------
# Scoring
# ----------------------------------------------------------------------

def _mentions(run: ResearchRun, phrase: str, domain_ids: Sequence[int]) -> List[DomainResult]:
    out = []
    for domain_id in domain_ids:
        result = run.by_id(domain_id)
        if not result:
            continue
        blob = (" ".join(result.findings) + " " + " ".join(
            " ".join(s.sentences) for s in result.sources[:5]
        )).lower()
        if phrase in blob:
            out.append(result)
    return out


def _axis(run: ResearchRun, phrase: str, domain_ids: Sequence[int], floor: int = 25) -> int:
    hits = _mentions(run, phrase, domain_ids)
    if not hits:
        return floor
    confidence = sum(h.confidence for h in hits) / len(hits)
    breadth = min(100, 40 + len(hits) * 18)
    return round(0.62 * confidence + 0.38 * breadth)


def score(run: ResearchRun, phrase: str, domains: Set[int], attract_risk: int) -> Pool:
    pool = Pool(name=phrase, display=phrase.title())
    pool.supporting_domains = sorted(domains)

    pool.demand = _axis(run, phrase, DEMAND_DOMAINS)
    pool.monetisation = _axis(run, phrase, MONETISATION_DOMAINS)
    pool.access = _axis(run, phrase, ACCESS_DOMAINS, floor=30)
    pool.risk_headroom = attract_risk

    supporting = [run.by_id(d) for d in pool.supporting_domains if run.by_id(d)]
    if supporting:
        publishers = len({s.host for r in supporting for s in r.sources if s.host})
        mean_conf = sum(r.confidence for r in supporting) / len(supporting)
        pool.evidence = round(min(100, 0.6 * mean_conf + min(40, publishers * 6)))
        for result in supporting[:3]:
            for finding in result.findings[:1]:
                if phrase in finding.lower():
                    pool.quotes.append(clip(finding, 220))
            pool.refs.extend(result.finding_refs[:1])

    if not pool.quotes:
        for result in supporting[:2]:
            if result.findings:
                pool.quotes.append(clip(result.findings[0], 220))

    pool.priority = round(
        0.30 * pool.demand
        + 0.26 * pool.monetisation
        + 0.18 * pool.access
        + 0.16 * pool.evidence
        + 0.10 * pool.risk_headroom
    )
    return pool


def growth_pools(run: ResearchRun, risk_headroom: int, limit: int = 6) -> List[Pool]:
    candidates = discover(run)
    pools = [score(run, phrase, domains, risk_headroom) for phrase, domains in candidates.items()]

    # Drop near-duplicate phrasings, keeping the better-evidenced one.
    unique: Dict[str, Pool] = {}
    for pool in sorted(pools, key=lambda p: p.priority, reverse=True):
        key = " ".join(sorted(w for w in pool.name.split() if w not in STOPWORDS)[:3])
        unique.setdefault(key, pool)

    ordered = sorted(unique.values(), key=lambda p: (p.priority, p.evidence), reverse=True)
    for index, pool in enumerate(ordered[:limit], start=1):
        pool.rank = index
    return ordered[:limit]


def overlap_sets(pools: Sequence[Pool]) -> Dict[str, Set[str]]:
    """Pool names grouped by which of the three tests they pass."""
    sets: Dict[str, Set[str]] = {"Demand": set(), "Monetisation": set(), "Access": set()}
    for pool in pools:
        for test, passed in pool.overlap_flags.items():
            if passed:
                sets[test].add(pool.display)
    return sets


__all__ = [
    "ACCESS_DOMAINS",
    "DEMAND_DOMAINS",
    "MONETISATION_DOMAINS",
    "Pool",
    "discover",
    "growth_pools",
    "overlap_sets",
    "score",
]
