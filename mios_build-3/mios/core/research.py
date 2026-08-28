"""
The research pipeline.

    plan -> retrieve -> qualify -> extract -> compose -> reconcile

Each stage is pure and independently testable. `run_research` is the only
function the UI needs; it yields progress so the interface can show what
is happening instead of a spinner.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Callable, Dict, Iterator, List, Optional, Sequence

from . import llm, narrative, search
from .domains import DOMAIN_IDS, DOMAINS, Domain, priority_label
from .extract import ExtractionBundle, extract_all, dedupe_money, dedupe_rates, dedupe_shares
from .reconcile import ReconciliationReport, reconcile
from .sources import Source, evidence_metrics, executive_set, industry_terms, qualify
from .text import rank_sentences


@dataclass
class DomainResult:
    domain_id: int
    domain: Domain
    question: str
    priority: str
    sources: List[Source] = field(default_factory=list)
    metrics: Dict[str, int] = field(default_factory=dict)
    extraction: ExtractionBundle = field(default_factory=ExtractionBundle)
    findings: List[str] = field(default_factory=list)
    finding_refs: List[str] = field(default_factory=list)
    implication: str = ""
    mechanism: str = ""
    grade: str = "PROVISIONAL"
    limitation: str = ""
    confidence: int = 0
    mode: str = "DETERMINISTIC"
    raw_count: int = 0
    errors: List[str] = field(default_factory=list)

    @property
    def name(self) -> str:
        return self.domain.name

    @property
    def code(self) -> str:
        return self.domain.code

    @property
    def lens(self) -> str:
        return self.domain.lens

    @property
    def source_count(self) -> int:
        return len(self.sources)

    @property
    def quantified(self) -> bool:
        return not self.extraction.is_empty


@dataclass
class ResearchRun:
    industry: str
    geography: str
    objective: str
    results: List[DomainResult] = field(default_factory=list)
    reconciliation: Optional[ReconciliationReport] = None
    all_money: List = field(default_factory=list)
    all_rates: List = field(default_factory=list)
    all_shares: List = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    used_model: bool = False

    def by_id(self, domain_id: int) -> Optional[DomainResult]:
        return next((r for r in self.results if r.domain_id == domain_id), None)

    def metric(self, domain_id: int, key: str, default: int = 35) -> int:
        result = self.by_id(domain_id)
        if not result:
            return default
        return result.metrics.get(key, default)

    @property
    def covered_domains(self) -> int:
        return sum(1 for r in self.results if r.source_count)

    @property
    def total_sources(self) -> int:
        return sum(r.source_count for r in self.results)

    @property
    def total_retrieved(self) -> int:
        return sum(r.raw_count for r in self.results)

    @property
    def independent_publishers(self) -> int:
        return len({s.host for r in self.results for s in r.sources if s.host})

    @property
    def mean_confidence(self) -> int:
        scored = [r.confidence for r in self.results if r.confidence]
        return round(sum(scored) / len(scored)) if scored else 0

    @property
    def quantified_domains(self) -> int:
        return sum(1 for r in self.results if r.quantified)


# ----------------------------------------------------------------------
# Plan
# ----------------------------------------------------------------------

def build_question(domain: Domain, industry: str, geography: str, objective: str) -> str:
    return (
        f"For {industry} in {geography}, what does the evidence show on "
        f"{domain.scope}, and how does it change this decision: {domain.decision}"
    )


def build_plan(industry: str, geography: str, objective: str) -> Dict[int, str]:
    return {
        d: build_question(DOMAINS[d], industry, geography, objective)
        for d in DOMAIN_IDS
    }


# ----------------------------------------------------------------------
# Single domain
# ----------------------------------------------------------------------

def research_domain(
    domain_id: int,
    industry: str,
    geography: str,
    objective: str,
    use_model: bool = True,
) -> DomainResult:
    domain = DOMAINS[domain_id]
    question = build_question(domain, industry, geography, objective)

    result = DomainResult(
        domain_id=domain_id,
        domain=domain,
        question=question,
        priority=priority_label(domain_id),
    )

    raw, errors = search.gather(industry, geography, objective, domain_id)
    result.raw_count = len(raw)
    result.errors = errors
    result.sources = qualify(raw, question, industry, domain_id)
    result.metrics = evidence_metrics(result.sources)

    keywords = industry_terms(industry) + domain.signals
    picked = executive_set(result.sources, 6)

    findings: List[str] = []
    refs: List[str] = []

    for source in picked:
        ranked = rank_sentences(source.content, keywords, limit=5, min_signal=28)
        source.sentences = [s.text for s in ranked]
        if not ranked:
            continue

        bundle = extract_all(
            [s.text for s in ranked],
            source.ref,
            geography,
            source.host,
            source.url,
            document=f"{source.title} {source.content[:1500]}",
        )
        result.extraction.extend(bundle)

        findings.append(ranked[0].text)
        refs.append(source.ref)

    result.extraction.money = dedupe_money(result.extraction.money)
    result.extraction.rates = dedupe_rates(result.extraction.rates)
    result.extraction.shares = dedupe_shares(result.extraction.shares)

    result.findings = findings[:4]
    result.finding_refs = refs[:4]

    composed = narrative.compose(
        domain,
        result.findings,
        result.metrics,
        result.extraction,
        result.sources,
        industry,
        geography,
    )
    result.implication = str(composed["implication"])
    result.grade = str(composed["grade"])
    result.limitation = str(composed["limitation"])
    result.confidence = int(composed["confidence"])

    if use_model and llm.available() and result.findings:
        prompt = narrative.build_prompt(
            domain, question, result.findings, result.finding_refs, industry, geography
        )
        raw_text = llm.complete(prompt, max_tokens=650)
        parsed = narrative.parse_model_output(raw_text or "")
        if parsed:
            result.findings = [str(f) for f in parsed["findings"]]
            result.mechanism = str(parsed.get("mechanism") or "")
            so_what = str(parsed.get("so_what") or "").strip()
            if so_what:
                result.implication = so_what
            result.mode = "MODEL"

    return result


# ----------------------------------------------------------------------
# Full run
# ----------------------------------------------------------------------

def run_research(
    industry: str,
    geography: str,
    objective: str,
    use_model: bool = True,
    on_progress: Optional[Callable[[int, int, str], None]] = None,
) -> ResearchRun:
    llm.reset_budget()
    run = ResearchRun(industry=industry, geography=geography, objective=objective)

    total = len(DOMAIN_IDS)
    for index, domain_id in enumerate(DOMAIN_IDS, start=1):
        if on_progress:
            on_progress(index, total, DOMAINS[domain_id].name)
        result = research_domain(domain_id, industry, geography, objective, use_model)
        run.results.append(result)
        run.errors.extend(result.errors)
        if result.mode == "MODEL":
            run.used_model = True

    for result in run.results:
        run.all_money.extend(result.extraction.money)
        run.all_rates.extend(result.extraction.rates)
        run.all_shares.extend(result.extraction.shares)

    run.all_money = dedupe_money(run.all_money)
    run.all_rates = dedupe_rates(run.all_rates)
    run.all_shares = dedupe_shares(run.all_shares)
    run.reconciliation = reconcile(run.all_money, run.all_rates)

    return run


def iter_research(
    industry: str,
    geography: str,
    objective: str,
    use_model: bool = True,
) -> Iterator[DomainResult]:
    """Streaming variant for callers that render incrementally."""
    llm.reset_budget()
    for domain_id in DOMAIN_IDS:
        yield research_domain(domain_id, industry, geography, objective, use_model)


__all__ = [
    "DomainResult",
    "ResearchRun",
    "build_plan",
    "build_question",
    "iter_research",
    "research_domain",
    "run_research",
]
