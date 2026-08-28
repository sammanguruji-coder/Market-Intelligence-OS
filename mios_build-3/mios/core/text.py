"""
Text hygiene.

The single largest quality defect in the previous build was navigation
chrome and markdown scaffolding leaking into the executive report
("### Menu #", "#### For Chief Strategy Officer", "logo logo Card image
cap"). This module is the gate that stops it.

Two stages:
  1. `scrub`   - removes markup, boilerplate and navigation fragments.
  2. `rank_sentences` - scores surviving sentences on how much decision
     signal they carry, so cards quote the best line rather than the
     first line.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Iterable, List, Sequence
from urllib.parse import urlparse

# ----------------------------------------------------------------------
# Boilerplate vocabulary
# ----------------------------------------------------------------------

NAV_PHRASES = (
    "skip to main content", "screen reader access", "sign in", "log in",
    "login", "subscribe", "newsletter", "cookie policy", "privacy policy",
    "terms of use", "all rights reserved", "click here", "read more",
    "follow us", "share tweet", "like comment", "table of contents",
    "request sample", "download sample", "buy now", "report format",
    "report id", "news-id", "views:", "sitemap", "image gallery",
    "other links", "tenders archive", "increase font size",
    "decrease font size", "color blind", "posted on the topic",
    "this title was summarized by ai", "powered by", "logo logo",
    "card image cap", "all the vital news", "curated by our industry experts",
    "media & events", "research case studies", "you can edit or delete",
    "more releases from", "search term was too short", "related reports",
    "speak to an analyst", "get a quote", "toggle navigation",
    "for chief strategy officer", "for academia", "for technology / innovation",
    "achieve mainstream adoption of new ideas",
)

# Marketing-boilerplate sentence openers that never carry a finding.
JUNK_OPENERS = (
    "menu", "home", "about us", "contact", "search", "share",
    "next", "previous", "back to", "browse", "explore our",
)

# Units and cue words that mark a sentence as decision-grade.
NUMERIC_CUE = re.compile(
    r"(\d[\d,.]*\s*(%|percent|bn|billion|mn|million|trillion|crore|lakh|"
    r"cagr|usd|inr|eur|\$|₹|€)|\b(19|20)\d{2}\b)",
    re.I,
)

ANALYTIC_CUE = re.compile(
    r"\b(grow|growth|decline|share|margin|revenue|cost|price|pricing|"
    r"adoption|penetration|forecast|projected|estimate|driver|risk|"
    r"regulat|compliance|competitor|incumbent|churn|acquisition|"
    r"profitab|funding|invest|capacity|demand|supply|segment)\w*\b",
    re.I,
)

HEDGE_CUE = re.compile(
    r"\b(may|might|could|expected|likely|anticipat|potential)\w*\b", re.I
)


# ----------------------------------------------------------------------
# Cleaning
# ----------------------------------------------------------------------

def clean(value: object) -> str:
    """Collapse any raw value into a single tidy line of prose."""
    text = str(value or "")
    text = text.replace("&nbsp;", " ").replace("&amp;", "&")
    text = re.sub(r"<br\s*/?>", " ", text, flags=re.I)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"!\[[^\]]*\]\([^)]*\)", " ", text)          # images
    text = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", text)        # links
    text = re.sub(r"[\r\n\t]+", " ", text)
    text = re.sub(r"\s+", " ", text)
    return text.strip(" |:-–—•")


def strip_markdown_scaffold(text: str) -> str:
    """Remove heading hashes, list bullets, rules and emoji runs."""
    text = re.sub(r"#{1,6}\s*", " ", text)
    text = re.sub(r"[*_]{1,3}", "", text)
    text = re.sub(r"^\s*[-•>]\s*", " ", text, flags=re.M)
    text = re.sub(r"-{3,}|={3,}|\|", " ", text)
    text = re.sub(r"[\U0001F000-\U0001FAFF\u2190-\u2BFF\uFE0F]", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def is_chrome(text: str) -> bool:
    """True when a fragment is navigation or marketing furniture."""
    low = clean(text).lower()
    if len(low) < 45:
        return True
    if any(phrase in low for phrase in NAV_PHRASES):
        return True
    if any(low.startswith(opener) for opener in JUNK_OPENERS):
        return True
    # Fragments dominated by short capitalised menu words.
    words = low.split()
    if len(words) >= 6:
        short = sum(1 for w in words if len(w) <= 3)
        if short / len(words) > 0.55:
            return True
    # Digit soup such as "3336414 1 Standard".
    digits = sum(c.isdigit() for c in low)
    if digits and digits / max(1, len(low)) > 0.30:
        return True
    return False


def scrub(text: str) -> str:
    """Full pipeline: markup out, chrome lines dropped, prose back."""
    text = strip_markdown_scaffold(clean(text))
    if not text:
        return ""
    kept = [part for part in re.split(r"(?<=[.!?])\s+", text) if not is_chrome(part)]
    return " ".join(kept).strip()


def clip(text: str, limit: int = 320) -> str:
    text = clean(text)
    if len(text) <= limit:
        return text
    return text[:limit].rsplit(" ", 1)[0].rstrip(",;:") + "…"


def host(url: str) -> str:
    try:
        return urlparse(str(url)).netloc.lower().replace("www.", "")
    except Exception:
        return ""


def contains(text: str, term: str) -> bool:
    if not text or not term:
        return False
    return re.search(rf"\b{re.escape(term.lower())}\b", text.lower()) is not None


# ----------------------------------------------------------------------
# Sentence ranking
# ----------------------------------------------------------------------

@dataclass(frozen=True)
class Sentence:
    text: str
    signal: int

    def __str__(self) -> str:  # pragma: no cover - convenience
        return self.text


def split_sentences(text: str) -> List[str]:
    text = strip_markdown_scaffold(clean(text))
    raw = re.split(r"(?<=[.!?])\s+(?=[A-Z0-9₹$])", text)
    out: List[str] = []
    for part in raw:
        part = part.strip(" -–—•|")
        if 45 <= len(part) <= 420:
            out.append(part)
    return out


def sentence_signal(sentence: str, keywords: Sequence[str] = ()) -> int:
    """Score 0-100 for how much decision-relevant signal a sentence has."""
    if is_chrome(sentence):
        return 0

    score = 18
    low = sentence.lower()

    numeric_hits = len(NUMERIC_CUE.findall(sentence))
    score += min(34, numeric_hits * 13)

    analytic_hits = len(set(m.group(0).lower() for m in ANALYTIC_CUE.finditer(sentence)))
    score += min(24, analytic_hits * 8)

    for kw in keywords:
        if kw and kw.lower() in low:
            score += 6
    score = min(score, 100)

    # Length sweet spot: enough to be a claim, short enough to be quotable.
    length = len(sentence)
    if length < 70:
        score -= 12
    elif length > 300:
        score -= 10

    if HEDGE_CUE.search(sentence) and numeric_hits == 0:
        score -= 8

    if sentence.count(",") > 6:
        score -= 6

    return max(0, min(100, score))


def rank_sentences(
    text: str,
    keywords: Sequence[str] = (),
    limit: int = 4,
    min_signal: int = 30,
) -> List[Sentence]:
    """Best-first, de-duplicated sentences from a block of source text."""
    seen: set[str] = set()
    scored: List[Sentence] = []

    for raw in split_sentences(text):
        fingerprint = re.sub(r"[^a-z0-9]", "", raw.lower())[:90]
        if not fingerprint or fingerprint in seen:
            continue
        seen.add(fingerprint)
        signal = sentence_signal(raw, keywords)
        if signal >= min_signal:
            scored.append(Sentence(text=raw, signal=signal))

    scored.sort(key=lambda s: s.signal, reverse=True)
    return scored[:limit]


def dedupe(items: Iterable[str], key_length: int = 70) -> List[str]:
    seen: set[str] = set()
    out: List[str] = []
    for item in items:
        k = re.sub(r"[^a-z0-9]", "", str(item).lower())[:key_length]
        if k and k not in seen:
            seen.add(k)
            out.append(item)
    return out


__all__ = [
    "Sentence",
    "clean",
    "clip",
    "contains",
    "dedupe",
    "host",
    "is_chrome",
    "rank_sentences",
    "scrub",
    "sentence_signal",
    "split_sentences",
    "strip_markdown_scaffold",
]
