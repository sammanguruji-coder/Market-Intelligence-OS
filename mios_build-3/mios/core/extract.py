"""
Quantitative extraction.

The previous build never parsed a number. It pasted "US 7.5 billion
(IAMAI)" next to "US 10.5 billion (IMARC)" and let the reader sort it
out. Those two figures differ by 40% and the difference is almost
entirely definitional — one counts India online education, the other
counts India EdTech including hardware.

This module turns prose into typed, comparable datapoints so the
reconciliation engine can group like with like and refuse to average
across incompatible scopes.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from datetime import date
from typing import Dict, List, Optional, Sequence

from .text import clean, clip

CURRENT_YEAR = date.today().year

# Rupee conversion is a display convenience only; every point keeps its
# native currency so the UI can always show the figure as published.
INR_PER_USD = 83.5
EUR_PER_USD = 0.92

# Multipliers to normalise everything to millions of the native currency.
MAGNITUDE = {
    "trillion": 1_000_000.0,
    "tn": 1_000_000.0,
    "billion": 1_000.0,
    "bn": 1_000.0,
    "million": 1.0,
    "mn": 1.0,
    "crore": 10.0,        # 1 crore = 10 million (INR context)
    "lakh": 0.1,          # 1 lakh = 0.1 million
    "thousand": 0.001,
}

CURRENCY_TOKENS = {
    "usd": "USD", "us$": "USD", "$": "USD", "dollar": "USD", "dollars": "USD",
    "inr": "INR", "₹": "INR", "rs": "INR", "rs.": "INR", "rupee": "INR",
    "rupees": "INR", "eur": "EUR", "€": "EUR", "euro": "EUR",
}

GLOBAL_MARKERS = ("global", "worldwide", "world ", "international market")

FORECAST_MARKERS = (
    "forecast", "projected", "project to", "expected", "will reach",
    "set to reach", "estimated to reach", "by 20", "outlook", "poised to",
    "anticipated",
)

SCOPE_GLOBAL = "global"
SCOPE_TARGET = "target"
SCOPE_UNSPECIFIED = "unspecified"

KIND_ACTUAL = "actual"
KIND_FORECAST = "forecast"

# What a money figure actually measures. Without this, a USD 1.1B venture
# funding total gets reconciled against a USD 12.1B market size and the
# engine reports a 1,000% "conflict" that does not exist.
MEASURE_SIZE = "market_size"
MEASURE_FUNDING = "funding"
MEASURE_COMPANY = "company_revenue"
MEASURE_UNIT = "unit_value"
MEASURE_OTHER = "other"

SIZE_CUES = ("market", "industry", "sector", "segment", "opportunity",
             "addressable", "tam", "market size", "valued at")
FUNDING_CUES = ("funding", "raised", "venture", "investment into",
                "invested in", "capital raised", "round", "series a",
                "series b", "disclosed funding")
COMPANY_CUES = ("company revenue", "combined revenue", "revenue of the top",
                "reported revenue", "its revenue", "annual revenue of",
                "turnover")
UNIT_CUES = ("per learner", "per user", "per customer", "per student",
             "acquisition cost", "cac", "arpu", "per hour", "per seat",
             "average spend", "spend per", "ticket size", "per unit")


# ----------------------------------------------------------------------
# Datapoint containers
# ----------------------------------------------------------------------

@dataclass(frozen=True)
class MoneyPoint:
    value_millions: float          # in native currency, millions
    currency: str
    year: Optional[int]
    kind: str                      # actual | forecast
    scope: str                     # target | global | unspecified
    measure: str                   # market_size | funding | company_revenue | unit_value | other
    snippet: str
    ref: str                       # e.g. "D1/S2"
    source_host: str = ""
    source_url: str = ""

    @property
    def usd_millions(self) -> float:
        if self.currency == "INR":
            return self.value_millions / INR_PER_USD
        if self.currency == "EUR":
            return self.value_millions / EUR_PER_USD
        return self.value_millions

    @property
    def usd_billions(self) -> float:
        return self.usd_millions / 1000.0

    @property
    def label(self) -> str:
        b = self.usd_billions
        if b >= 1:
            return f"US${b:,.1f}B"
        return f"US${self.usd_millions:,.0f}M"


@dataclass(frozen=True)
class RatePoint:
    """A CAGR or growth-rate observation."""
    percent: float
    start_year: Optional[int]
    end_year: Optional[int]
    scope: str
    snippet: str
    ref: str
    source_host: str = ""

    @property
    def period(self) -> str:
        if self.start_year and self.end_year:
            return f"{self.start_year}–{self.end_year}"
        if self.end_year:
            return f"to {self.end_year}"
        return "period not stated"


@dataclass(frozen=True)
class SharePoint:
    """A percentage share attributed to a named subject."""
    percent: float
    subject: str
    year: Optional[int]
    snippet: str
    ref: str
    source_host: str = ""


@dataclass
class ExtractionBundle:
    money: List[MoneyPoint] = field(default_factory=list)
    rates: List[RatePoint] = field(default_factory=list)
    shares: List[SharePoint] = field(default_factory=list)

    def extend(self, other: "ExtractionBundle") -> None:
        self.money.extend(other.money)
        self.rates.extend(other.rates)
        self.shares.extend(other.shares)

    @property
    def is_empty(self) -> bool:
        return not (self.money or self.rates or self.shares)


# ----------------------------------------------------------------------
# Pattern library
# ----------------------------------------------------------------------

_NUM = r"\d{1,3}(?:,\d{3})*(?:\.\d+)?|\d+(?:\.\d+)?"
_MAG = r"trillion|billion|million|thousand|crore|lakh|bn|mn|tn"
_CUR = r"US\$|USD|INR|EUR|Rs\.?|₹|€|\$"

MONEY_RE = re.compile(
    rf"(?:(?P<cur1>{_CUR})\s*)?"
    rf"(?P<num>{_NUM})\s*"
    rf"(?P<mag>{_MAG})?"
    rf"(?:\s*(?P<cur2>{_CUR}|dollars|rupees|euros))?",
    re.I,
)

CAGR_RE = re.compile(
    rf"(?:cagr[^.%]{{0,40}}?(?P<p1>{_NUM})\s*%)"
    rf"|(?:(?P<p2>{_NUM})\s*%\s*cagr)"
    rf"|(?:(?:grow|growing|expand|increase)\w*\s+at\s+(?:a|an|around|approximately)?\s*"
    rf"(?P<p3>{_NUM})\s*%)",
    re.I,
)

PERIOD_RE = re.compile(r"\b(19|20)\d{2}\b")

SHARE_RE = re.compile(
    rf"(?P<subject>[A-Za-z][A-Za-z0-9&/\- ]{{2,40}}?)\s+"
    rf"(?:dominates? the market with a share of|accounted for|"
    rf"holds? an estimated share of|holds? an estimated|held a share of|"
    rf"has a share of|represented|contributed|contributes?|commands?|"
    rf"accounts? for|held|holds?|share of|at)\s+"
    rf"(?:approximately|about|around|roughly|~)?\s*(?P<pct>{_NUM})\s*%",
    re.I,
)

# Trailing words that mean the regex over-captured into the verb phrase.
SUBJECT_TAIL = re.compile(
    r"\s+(held|holds|has|have|is|are|was|were|an?|the|estimated|of|for|"
    r"with|at|to|reached|stood|represents?)$",
    re.I,
)


def _to_float(raw: str) -> Optional[float]:
    try:
        return float(str(raw).replace(",", ""))
    except (TypeError, ValueError):
        return None


def _detect_currency(match: re.Match, sentence: str) -> str:
    for group in ("cur1", "cur2"):
        token = (match.groupdict().get(group) or "").strip().lower()
        if token:
            token = token.rstrip(".")
            if token in CURRENCY_TOKENS:
                return CURRENCY_TOKENS[token]
            if token in ("dollars",):
                return "USD"
            if token in ("rupees",):
                return "INR"
            if token in ("euros",):
                return "EUR"
    low = sentence.lower()
    if "crore" in low or "lakh" in low or "₹" in sentence or "inr" in low:
        return "INR"
    if "€" in sentence or "eur" in low:
        return "EUR"
    return "USD"


def _detect_scope(sentence: str, geography: str, document: str = "") -> str:
    """
    Scope is judged at sentence level first, because that is where the
    figure lives. When the sentence is silent, the document decides — a
    report titled "India EdTech market" does not repeat "India" in every
    line, and treating those figures as unscoped would throw away most of
    the series.
    """
    low = sentence.lower()
    geo = (geography or "").strip().lower()

    if geo and geo in low:
        return SCOPE_TARGET
    if any(marker in low for marker in GLOBAL_MARKERS):
        return SCOPE_GLOBAL

    if document:
        doc_low = document.lower()
        doc_global = any(marker in doc_low for marker in GLOBAL_MARKERS)
        doc_target = bool(geo) and geo in doc_low
        # Only inherit when the document is unambiguous about its own scope.
        if doc_target and not doc_global:
            return SCOPE_TARGET
        if doc_global and not doc_target:
            return SCOPE_GLOBAL

    return SCOPE_UNSPECIFIED


def _detect_kind(sentence: str, year: Optional[int]) -> str:
    low = sentence.lower()
    if year and year > CURRENT_YEAR:
        return KIND_FORECAST
    if any(marker in low for marker in FORECAST_MARKERS):
        return KIND_FORECAST
    return KIND_ACTUAL


def _detect_measure(sentence: str) -> str:
    """What the figure is counting. Order matters: the narrow, unambiguous
    categories are tested before the broad one."""
    low = sentence.lower()
    if any(cue in low for cue in UNIT_CUES):
        return MEASURE_UNIT
    if any(cue in low for cue in FUNDING_CUES):
        return MEASURE_FUNDING
    if any(cue in low for cue in COMPANY_CUES):
        return MEASURE_COMPANY
    if any(cue in low for cue in SIZE_CUES):
        return MEASURE_SIZE
    return MEASURE_OTHER


def _nearest_year(sentence: str, span_start: int) -> Optional[int]:
    """The year token closest to the figure, which is usually its year."""
    best: Optional[int] = None
    best_distance = 10**6
    for m in PERIOD_RE.finditer(sentence):
        year = int(m.group(0))
        if not (1990 <= year <= CURRENT_YEAR + 25):
            continue
        distance = abs(m.start() - span_start)
        if distance < best_distance:
            best, best_distance = year, distance
    return best


# ----------------------------------------------------------------------
# Public extraction
# ----------------------------------------------------------------------

def extract_money(
    sentence: str,
    ref: str,
    geography: str,
    source_host: str = "",
    source_url: str = "",
    document: str = "",
) -> List[MoneyPoint]:
    out: List[MoneyPoint] = []
    scope = _detect_scope(sentence, geography, document)

    for m in MONEY_RE.finditer(sentence):
        magnitude = (m.group("mag") or "").lower()
        currency_present = bool(m.group("cur1") or m.group("cur2"))

        # Require either an explicit magnitude word or a currency symbol;
        # otherwise "12.3" in "12.3% CAGR" would be read as money.
        if not magnitude and not currency_present:
            continue
        if not magnitude:
            continue

        value = _to_float(m.group("num"))
        if value is None or value <= 0:
            continue

        millions = value * MAGNITUDE.get(magnitude, 1.0)
        if millions < 0.5 or millions > 50_000_000:
            continue

        # A percentage immediately after the number is not money.
        tail = sentence[m.end(): m.end() + 2]
        if tail.strip().startswith("%"):
            continue

        currency = _detect_currency(m, sentence)
        year = _nearest_year(sentence, m.start())

        out.append(
            MoneyPoint(
                value_millions=millions,
                currency=currency,
                year=year,
                kind=_detect_kind(sentence, year),
                scope=scope,
                measure=_detect_measure(sentence),
                snippet=clip(sentence, 240),
                ref=ref,
                source_host=source_host,
                source_url=source_url,
            )
        )
    return out


def extract_rates(
    sentence: str,
    ref: str,
    geography: str,
    source_host: str = "",
    document: str = "",
) -> List[RatePoint]:
    out: List[RatePoint] = []
    scope = _detect_scope(sentence, geography, document)
    years = sorted({int(m.group(0)) for m in PERIOD_RE.finditer(sentence)})

    for m in CAGR_RE.finditer(sentence):
        raw = m.group("p1") or m.group("p2") or m.group("p3")
        percent = _to_float(raw)
        if percent is None or not (0.1 <= percent <= 120):
            continue
        out.append(
            RatePoint(
                percent=percent,
                start_year=years[0] if years else None,
                end_year=years[-1] if len(years) > 1 else (years[0] if years else None),
                scope=scope,
                snippet=clip(sentence, 240),
                ref=ref,
                source_host=source_host,
            )
        )
    return out


def extract_shares(sentence: str, ref: str, source_host: str = "") -> List[SharePoint]:
    out: List[SharePoint] = []
    years = [int(m.group(0)) for m in PERIOD_RE.finditer(sentence)]

    for m in SHARE_RE.finditer(sentence):
        percent = _to_float(m.group("pct"))
        subject = clean(m.group("subject"))
        if percent is None or not (0.5 <= percent <= 100):
            continue
        # Drop subjects that are really sentence connectives.
        if len(subject) < 3 or subject.lower() in {"the", "a", "it", "which", "that"}:
            continue
        subject = re.sub(
            r"^(the|a|an|and|in|of|for|with|by)\s+", "", subject, flags=re.I
        ).strip()
        for _ in range(4):                      # peel repeated verb tails
            trimmed = SUBJECT_TAIL.sub("", subject).strip()
            if trimmed == subject:
                break
            subject = trimmed
        if len(subject) < 3:
            continue
        out.append(
            SharePoint(
                percent=percent,
                subject=subject[:48],
                year=years[-1] if years else None,
                snippet=clip(sentence, 240),
                ref=ref,
                source_host=source_host,
            )
        )
    return out


def extract_all(
    sentences: Sequence[str],
    ref: str,
    geography: str,
    source_host: str = "",
    source_url: str = "",
    document: str = "",
) -> ExtractionBundle:
    """Run every extractor over a source's best sentences."""
    bundle = ExtractionBundle()
    for sentence in sentences:
        bundle.money.extend(
            extract_money(sentence, ref, geography, source_host, source_url, document)
        )
        bundle.rates.extend(
            extract_rates(sentence, ref, geography, source_host, document)
        )
        bundle.shares.extend(extract_shares(sentence, ref, source_host))
    return bundle


def dedupe_money(points: Sequence[MoneyPoint]) -> List[MoneyPoint]:
    """Collapse the same figure reported by the same host repeatedly."""
    seen: Dict[tuple, MoneyPoint] = {}
    for p in points:
        key = (round(p.usd_millions, 1), p.year, p.source_host, p.scope, p.measure)
        seen.setdefault(key, p)
    return sorted(seen.values(), key=lambda p: (p.year or 0, p.usd_millions))


def dedupe_rates(points: Sequence[RatePoint]) -> List[RatePoint]:
    seen: Dict[tuple, RatePoint] = {}
    for p in points:
        key = (round(p.percent, 2), p.start_year, p.end_year, p.source_host)
        seen.setdefault(key, p)
    return sorted(seen.values(), key=lambda p: p.percent, reverse=True)


def dedupe_shares(points: Sequence[SharePoint]) -> List[SharePoint]:
    seen: Dict[tuple, SharePoint] = {}
    for p in points:
        key = (p.subject.lower(), round(p.percent, 1))
        seen.setdefault(key, p)
    return sorted(seen.values(), key=lambda p: p.percent, reverse=True)


__all__ = [
    "CURRENT_YEAR",
    "ExtractionBundle",
    "KIND_ACTUAL",
    "KIND_FORECAST",
    "MoneyPoint",
    "RatePoint",
    "SCOPE_GLOBAL",
    "SCOPE_TARGET",
    "SCOPE_UNSPECIFIED",
    "SharePoint",
    "dedupe_money",
    "dedupe_rates",
    "dedupe_shares",
    "extract_all",
    "extract_money",
    "extract_rates",
    "extract_shares",
]
