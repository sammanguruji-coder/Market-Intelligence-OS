"""
Estimate reconciliation.

Market reports disagree. Two published figures for "the India EdTech
market" can differ by 40% because one counts hardware and the other does
not, or because one is a calendar year and the other a fiscal year, or
because one is a forecast quoted as an actual.

The wrong response is to average them. This module does what an analyst
does instead:

  1. Bucket estimates by scope (target geography vs global) and by year.
  2. Measure dispersion inside each bucket.
  3. Flag buckets whose spread exceeds tolerance as definitional conflicts.
  4. Derive a defensible range and an implied CAGR from the surviving
     anchor and terminal points.
  5. Cross-check that implied CAGR against every CAGR the sources state
     outright. When those disagree, at least one published series is
     internally inconsistent — and that is a finding.
"""

from __future__ import annotations

import statistics
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence

from .extract import (
    CURRENT_YEAR,
    KIND_FORECAST,
    MEASURE_OTHER,
    MEASURE_SIZE,
    SCOPE_GLOBAL,
    SCOPE_TARGET,
    SCOPE_UNSPECIFIED,
    MoneyPoint,
    RatePoint,
)

# A bucket whose max/min ratio exceeds this is treated as definitionally
# incompatible rather than as measurement noise.
SPREAD_TOLERANCE = 1.25

# Implied vs stated CAGR gap, in percentage points, above which the
# published series are flagged as inconsistent.
CAGR_TOLERANCE_PP = 3.0


@dataclass
class YearBucket:
    year: int
    scope: str
    points: List[MoneyPoint] = field(default_factory=list)

    @property
    def values(self) -> List[float]:
        return [p.usd_billions for p in self.points]

    @property
    def low(self) -> float:
        return min(self.values) if self.values else 0.0

    @property
    def high(self) -> float:
        return max(self.values) if self.values else 0.0

    @property
    def median(self) -> float:
        return statistics.median(self.values) if self.values else 0.0

    @property
    def spread_ratio(self) -> float:
        if not self.values or self.low <= 0:
            return 1.0
        return self.high / self.low

    @property
    def conflicted(self) -> bool:
        return len(self.points) > 1 and self.spread_ratio > SPREAD_TOLERANCE

    @property
    def hosts(self) -> List[str]:
        return sorted({p.source_host for p in self.points if p.source_host})


@dataclass
class Conflict:
    year: int
    scope: str
    low: float
    high: float
    spread_ratio: float
    low_host: str
    high_host: str
    low_snippet: str
    high_snippet: str

    @property
    def gap_percent(self) -> float:
        if self.low <= 0:
            return 0.0
        return (self.high / self.low - 1) * 100

    @property
    def headline(self) -> str:
        return (
            f"{self.year}: US${self.low:,.1f}B ({self.low_host or 'source A'}) "
            f"vs US${self.high:,.1f}B ({self.high_host or 'source B'}) "
            f"— {self.gap_percent:,.0f}% apart"
        )


@dataclass
class ReconciliationReport:
    scope: str
    buckets: List[YearBucket] = field(default_factory=list)
    conflicts: List[Conflict] = field(default_factory=list)
    stated_rates: List[RatePoint] = field(default_factory=list)
    implied_cagr: Optional[float] = None
    anchor_year: Optional[int] = None
    anchor_value: Optional[float] = None
    terminal_year: Optional[int] = None
    terminal_value: Optional[float] = None
    rate_disagreement_pp: Optional[float] = None
    notes: List[str] = field(default_factory=list)

    @property
    def has_series(self) -> bool:
        return len(self.buckets) >= 2

    @property
    def confidence(self) -> int:
        """0-100 confidence that the size series is decision-grade."""
        if not self.buckets:
            return 0
        score = 46
        score += min(24, len(self.buckets) * 6)
        independent = len({h for b in self.buckets for h in b.hosts})
        score += min(18, independent * 5)
        score -= min(30, len(self.conflicts) * 11)
        if self.rate_disagreement_pp and self.rate_disagreement_pp > CAGR_TOLERANCE_PP:
            score -= 12
        if self.implied_cagr is not None:
            score += 8
        return max(5, min(100, score))

    @property
    def verdict(self) -> str:
        if not self.has_series:
            return "INSUFFICIENT"
        if self.conflicts:
            return "CONFLICTED"
        if self.rate_disagreement_pp and self.rate_disagreement_pp > CAGR_TOLERANCE_PP:
            return "INCONSISTENT"
        return "RECONCILED"


def _implied_cagr(start_value: float, end_value: float, years: int) -> Optional[float]:
    if start_value <= 0 or end_value <= 0 or years <= 0:
        return None
    try:
        return ((end_value / start_value) ** (1 / years) - 1) * 100
    except (ValueError, ZeroDivisionError):
        return None


def reconcile(
    money: Sequence[MoneyPoint],
    rates: Sequence[RatePoint],
    prefer_scope: str = SCOPE_TARGET,
) -> ReconciliationReport:
    """Build a reconciled size series for one scope."""
    report = ReconciliationReport(scope=prefer_scope)

    # Only market-size figures enter the series. Funding totals, company
    # revenues and per-customer values are all money, but comparing them
    # against a market size manufactures conflicts that do not exist.
    usable = [
        p for p in money
        if p.year
        and 1990 <= p.year <= CURRENT_YEAR + 25
        and p.usd_billions > 0
        and p.measure in (MEASURE_SIZE, MEASURE_OTHER)
    ]

    # A lone MEASURE_OTHER point next to classified size points is more
    # likely to be noise than a size estimate, so prefer explicit ones.
    explicit = [p for p in usable if p.measure == MEASURE_SIZE]
    if len(explicit) >= 2:
        usable = explicit

    scoped = [p for p in usable if p.scope == prefer_scope]
    if len(scoped) < 2 and prefer_scope == SCOPE_TARGET:
        # Fall back to unspecified-scope points, but say so plainly.
        widened = [p for p in usable if p.scope in (SCOPE_TARGET, SCOPE_UNSPECIFIED)]
        if len(widened) > len(scoped):
            report.notes.append(
                "Series widened to include figures whose geographic scope is "
                "not stated in the source. Validate scope before use."
            )
            scoped = widened

    if not scoped:
        report.notes.append("No size figures survived extraction for this scope.")
        return report

    by_year: Dict[int, YearBucket] = {}
    for point in scoped:
        bucket = by_year.setdefault(
            point.year, YearBucket(year=point.year, scope=prefer_scope)
        )
        bucket.points.append(point)

    report.buckets = [by_year[y] for y in sorted(by_year)]

    for bucket in report.buckets:
        if not bucket.conflicted:
            continue
        lowest = min(bucket.points, key=lambda p: p.usd_billions)
        highest = max(bucket.points, key=lambda p: p.usd_billions)
        report.conflicts.append(
            Conflict(
                year=bucket.year,
                scope=bucket.scope,
                low=lowest.usd_billions,
                high=highest.usd_billions,
                spread_ratio=bucket.spread_ratio,
                low_host=lowest.source_host,
                high_host=highest.source_host,
                low_snippet=lowest.snippet,
                high_snippet=highest.snippet,
            )
        )

    # Anchor on the most recent non-forecast year available; terminal on
    # the furthest forecast year.
    actuals = [b for b in report.buckets if b.year <= CURRENT_YEAR]
    anchor = actuals[-1] if actuals else report.buckets[0]
    terminal = report.buckets[-1]

    if terminal.year > anchor.year:
        report.anchor_year = anchor.year
        report.anchor_value = anchor.median
        report.terminal_year = terminal.year
        report.terminal_value = terminal.median
        report.implied_cagr = _implied_cagr(
            anchor.median, terminal.median, terminal.year - anchor.year
        )

    report.stated_rates = [
        r for r in rates
        if r.scope in (prefer_scope, SCOPE_UNSPECIFIED) and 0 < r.percent < 100
    ]

    if report.implied_cagr is not None and report.stated_rates:
        stated_median = statistics.median(r.percent for r in report.stated_rates)
        report.rate_disagreement_pp = abs(stated_median - report.implied_cagr)
        if report.rate_disagreement_pp > CAGR_TOLERANCE_PP:
            report.notes.append(
                f"Sources state a median {stated_median:.1f}% CAGR, but the "
                f"published size series implies {report.implied_cagr:.1f}%. "
                "At least one series is internally inconsistent."
            )

    if report.conflicts:
        report.notes.append(
            "Estimates inside the same year differ beyond measurement noise. "
            "Treat as definitional variance — reconcile scope, inclusions and "
            "actual/forecast status before quoting a single number."
        )

    return report


def scope_comparison(money: Sequence[MoneyPoint]) -> Dict[str, float]:
    """Median size by scope, used to show target-vs-global contamination."""
    out: Dict[str, List[float]] = {}
    for point in money:
        if point.usd_billions <= 0:
            continue
        out.setdefault(point.scope, []).append(point.usd_billions)
    return {k: statistics.median(v) for k, v in out.items() if v}


def contamination_ratio(money: Sequence[MoneyPoint]) -> float:
    """
    Share of extracted size figures that are global rather than local.

    A high ratio is the classic failure mode of desk research: the deck
    ends up quoting a worldwide number as if it were the addressable
    market.
    """
    sized = [p for p in money if p.usd_billions > 0]
    if not sized:
        return 0.0
    global_points = sum(1 for p in sized if p.scope == SCOPE_GLOBAL)
    return round(100 * global_points / len(sized), 1)


def forecast_share(money: Sequence[MoneyPoint]) -> float:
    sized = [p for p in money if p.usd_billions > 0]
    if not sized:
        return 0.0
    forecasts = sum(1 for p in sized if p.kind == KIND_FORECAST)
    return round(100 * forecasts / len(sized), 1)


__all__ = [
    "CAGR_TOLERANCE_PP",
    "Conflict",
    "ReconciliationReport",
    "SPREAD_TOLERANCE",
    "YearBucket",
    "contamination_ratio",
    "forecast_share",
    "reconcile",
    "scope_comparison",
]
