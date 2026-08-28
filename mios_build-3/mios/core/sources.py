"""
Source qualification.

Every retrieved document is scored on four independent axes before it is
allowed near a finding:

  authority       - who published it
  relevance       - does it answer the question asked
  direct_support  - does it contain the kind of claim the question needs
  industry_fit    - is it about this industry, or an adjacent one

These stay separate on purpose. A government statistics page can be high
authority and low relevance; a vendor blog can be the reverse. Averaging
them early destroys the signal the analyst needs.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Sequence

from .text import clean, host, is_chrome, scrub

# ----------------------------------------------------------------------
# Publisher tiers
# ----------------------------------------------------------------------

TIER_OFFICIAL = (
    ".gov", ".gov.in", ".nic.in", ".gov.uk", ".europa.eu",
    "rbi.org.in", "sebi.gov.in", "niti.gov.in", "mospi.gov.in",
    "pib.gov.in", "dpiit.gov.in", "meity.gov.in", "trai.gov.in",
    "investindia.gov.in", "worldbank.org", "imf.org", "oecd.org",
    "iea.org", "who.int", "icao.int", "iata.org", "un.org",
    "trade.gov", "census.gov", "eurostat", "bis.org",
)

TIER_PEER_REVIEWED = (
    "ncbi.nlm.nih.gov", "pmc.ncbi.nlm.nih.gov", "nature.com",
    "sciencedirect.com", "springer.com", "jstor.org", "ssrn.com",
    "nber.org", "arxiv.org",
)

TIER_PRESS_ADVISORY = (
    "reuters.com", "bloomberg.com", "ft.com", "wsj.com", "economist.com",
    "mckinsey.com", "bcg.com", "bain.com", "deloitte.com", "pwc.com",
    "ey.com", "kpmg.com", "accenture.com", "hbr.org",
    "economictimes.indiatimes.com", "livemint.com", "business-standard.com",
)

TIER_RESEARCH_HOUSE = (
    "ibef.org", "statista.com", "grandviewresearch.com",
    "marketsandmarkets.com", "fortunebusinessinsights.com",
    "kenresearch.com", "researchandmarkets.com", "imarcgroup.com",
    "mordorintelligence.com", "globaldata.com", "gartner.com",
    "forrester.com", "idc.com", "crisil.com", "redseer.com",
    "holoniq.com", "tracxn.com",
)

BLOCKED_HOSTS = {
    "pinterest.com", "quora.com", "facebook.com", "instagram.com",
    "tiktok.com", "twitter.com", "x.com", "slideshare.net",
    "scribd.com", "reddit.com", "medium.com", "wattpad.com",
}

# Social and self-published hosts are not blocked outright — a LinkedIn
# post from an industry analyst can be a legitimate signal — but they are
# capped so they can never outrank a primary source.
CAPPED_HOSTS = {"linkedin.com": 40, "substack.com": 42, "blogspot.com": 32,
                "wordpress.com": 32, "openpr.com": 30, "prnewswire.com": 38}


@dataclass
class Source:
    title: str
    url: str
    content: str
    authority: int = 0
    tier: str = "Unclassified"
    publisher_type: str = "Other"
    relevance: int = 0
    direct_support: int = 0
    industry_fit: int = 0
    specificity: int = 0
    quality: int = 0
    executive: bool = False
    ref: str = ""
    sentences: List[str] = field(default_factory=list)

    @property
    def host(self) -> str:
        return host(self.url)

    def to_row(self) -> Dict[str, object]:
        return {
            "ref": self.ref,
            "title": self.title,
            "host": self.host,
            "url": self.url,
            "tier": self.tier,
            "authority": self.authority,
            "relevance": self.relevance,
            "direct_support": self.direct_support,
            "industry_fit": self.industry_fit,
            "quality": self.quality,
            "executive": self.executive,
        }


# ----------------------------------------------------------------------
# Industry vocabulary
# ----------------------------------------------------------------------

ALIASES: Dict[str, List[str]] = {
    "telecom": ["telecom", "telecommunications", "mobile network", "wireless",
                "broadband", "fibre", "fiber", "5g", "spectrum", "tower"],
    "aviation": ["aviation", "airline", "airport", "aircraft", "aerospace",
                 "mro", "flight", "air travel", "passenger traffic"],
    "electric vehicle": ["electric vehicle", "ev", "battery electric",
                         "charging", "charger", "two-wheeler", "three-wheeler"],
    "automotive": ["automotive", "vehicle", "car", "truck", "oem",
                   "aftermarket", "commercial vehicle"],
    "banking": ["bank", "banking", "lending", "deposit", "loan", "credit",
                "fintech", "payments", "nbfc"],
    "insurance": ["insurance", "insurer", "premium", "claims", "underwriting",
                  "policyholder", "reinsurance"],
    "pharma": ["pharma", "pharmaceutical", "drug", "medicine", "therapeutic",
               "clinical", "api", "biosimilar", "formulation"],
    "healthcare": ["healthcare", "hospital", "clinic", "patient", "diagnostic",
                   "medical device", "health services"],
    "medical devices": ["medical device", "surgical", "implant", "diagnostic",
                        "operating room", "hospital equipment", "neuromonitoring"],
    "retail": ["retail", "retailer", "store", "commerce", "marketplace",
               "consumer goods", "fmcg"],
    "ecommerce": ["ecommerce", "e-commerce", "online shopping", "marketplace",
                  "digital commerce", "quick commerce"],
    "edtech": ["edtech", "education technology", "online education",
               "online learning", "elearning", "e-learning", "digital learning",
               "learning platform", "test prep", "test preparation",
               "upskilling", "k-12", "coaching", "school", "learner"],
    "saas": ["saas", "software as a service", "subscription software", "arr",
             "cloud software", "b2b software"],
    "semiconductor": ["semiconductor", "chip", "wafer", "fab", "foundry",
                      "integrated circuit", "packaging"],
    "renewable energy": ["renewable", "solar", "wind", "clean energy",
                         "photovoltaic", "green hydrogen"],
    "energy": ["energy", "power", "electricity", "generation", "utility",
               "grid", "fuel"],
    "logistics": ["logistics", "freight", "warehouse", "supply chain",
                  "last mile", "shipping", "3pl"],
    "real estate": ["real estate", "property", "housing", "residential",
                    "commercial real estate", "office space"],
    "agritech": ["agritech", "agriculture", "farming", "crop", "farmer",
                 "agri input"],
}


def industry_family(industry: str) -> Optional[str]:
    low = (industry or "").lower().strip()
    if not low:
        return None
    for family, words in ALIASES.items():
        if family in low or any(w in low for w in words):
            return family
    return None


def industry_terms(industry: str) -> List[str]:
    """Vocabulary used to test whether a document is on-industry."""
    low = (industry or "").lower().strip()
    terms = {t for t in re.split(r"[^a-z0-9+]+", low) if len(t) > 2}
    family = industry_family(industry)
    if family:
        terms.update(ALIASES[family])
    terms.add(low)
    return sorted(t for t in terms if t)


STOPWORDS = {
    "the", "and", "for", "with", "what", "which", "how", "are", "is", "of",
    "in", "on", "to", "a", "an", "that", "this", "its", "by", "from", "at",
    "be", "as", "it", "or", "we", "our", "their", "has", "have", "will",
}

# Words that appear in every research question we generate and therefore
# carry no discriminating power. Leaving them in makes relevance scores
# uniformly low and starves the executive set.
QUESTION_FRAMING = {
    "evidence", "show", "shows", "does", "decision", "change", "changes",
    "enough", "justify", "whether", "question", "domain", "analysis",
    "large", "actually", "really", "sets", "would", "much", "many",
}


def keywords(text: str, limit: int = 14) -> List[str]:
    words = [w for w in re.split(r"[^a-z0-9]+", (text or "").lower()) if len(w) > 2]
    out: List[str] = []
    for w in words:
        if w in STOPWORDS or w in QUESTION_FRAMING or w in out:
            continue
        out.append(w)
        if len(out) >= limit:
            break
    return out


# ----------------------------------------------------------------------
# Scoring
# ----------------------------------------------------------------------

def authority(url: str) -> tuple[int, str, str]:
    h = host(url)
    if not h:
        return 20, "Unclassified", "Other"
    if any(marker in h for marker in TIER_OFFICIAL):
        return 100, "T1 · Official", "Government / multilateral"
    if any(marker in h for marker in TIER_PEER_REVIEWED):
        return 92, "T1 · Peer reviewed", "Academic"
    if any(marker in h for marker in TIER_PRESS_ADVISORY):
        return 76, "T2 · Press / advisory", "Business press or advisory"
    if any(marker in h for marker in TIER_RESEARCH_HOUSE):
        return 62, "T3 · Research house", "Commercial research"
    for capped, ceiling in CAPPED_HOSTS.items():
        if capped in h:
            return ceiling, "T4 · Self-published", "Self-published"
    if h.endswith(".edu") or h.endswith(".ac.in") or h.endswith(".ac.uk"):
        return 84, "T1 · Academic", "Academic"
    if h.endswith(".org"):
        return 54, "T3 · Institutional", "Institutional"
    return 44, "T4 · Trade / vendor", "Trade or vendor"


def relevance(question: str, source: Source) -> int:
    """
    Share of the question's discriminating vocabulary present in the
    document, with credit for stem matches so "forecasting" counts
    toward "forecast", and a bonus when the match lands in the title.
    """
    qk = keywords(question)
    if not qk:
        return 40

    blob = f"{source.title} {source.content}".lower()
    title = source.title.lower()

    hits = 0.0
    title_hits = 0
    for k in qk:
        if k in blob:
            hits += 1.0
        elif len(k) > 5 and k[:-2] in blob:   # cheap stem match
            hits += 0.6
        if k in title:
            title_hits += 1

    score = round(100 * hits / len(qk))
    return max(0, min(100, score + title_hits * 5))


DIRECT_CUES = (
    "%", "cagr", "billion", "million", "crore", "usd", "inr", "share",
    "growth", "forecast", "market size", "revenue", "margin", "players",
)


def direct_support(question: str, source: Source) -> int:
    """Does the document contain claims of the type the question needs?"""
    blob = source.content.lower()
    cue_hits = sum(1 for cue in DIRECT_CUES if cue in blob)
    numeric = len(re.findall(r"\d[\d,.]*\s*(?:%|billion|million|crore|bn|mn)", blob))
    score = min(100, cue_hits * 7 + numeric * 6)
    if len(blob) < 200:
        score = int(score * 0.6)
    return score


def industry_fit(industry: str, source: Source) -> int:
    terms = industry_terms(industry)
    if not terms:
        return 50
    blob = f"{source.title} {source.content}".lower()
    hits = sum(1 for t in terms if t in blob)
    title_hit = any(t in source.title.lower() for t in terms)
    score = min(100, 25 + hits * 11 + (22 if title_hit else 0))
    return score


def specificity(source: Source) -> int:
    """Rewards documents with concrete, checkable claims."""
    blob = source.content
    numbers = len(re.findall(r"\d[\d,.]*", blob))
    years = len(re.findall(r"\b(?:19|20)\d{2}\b", blob))
    named = len(re.findall(r"\b[A-Z][a-z]+(?:\s[A-Z][a-z]+)+\b", blob))
    density = numbers / max(1, len(blob.split()) / 100)
    return max(0, min(100, round(density * 9 + years * 4 + min(named, 12) * 2)))


def qualify(
    raw_results: Iterable[dict],
    question: str,
    industry: str,
    domain_id: int,
) -> List[Source]:
    """Turn raw search hits into scored, de-duplicated Source objects."""
    unique: Dict[str, Source] = {}

    for raw in raw_results or []:
        url = (raw.get("url") or raw.get("href") or "").split("#")[0].rstrip("/")
        if not url:
            continue
        h = host(url)
        if h in BLOCKED_HOSTS:
            continue

        body = scrub(
            raw.get("raw_content")
            or raw.get("content")
            or raw.get("snippet")
            or raw.get("body")
            or ""
        )
        if len(body) < 120 or is_chrome(body[:200]):
            continue

        source = Source(title=clean(raw.get("title", "")) or h, url=url, content=body)
        auth, tier, ptype = authority(url)
        source.authority = auth
        source.tier = tier
        source.publisher_type = ptype
        source.relevance = relevance(question, source)
        source.direct_support = direct_support(question, source)
        source.industry_fit = industry_fit(industry, source)
        source.specificity = specificity(source)

        source.quality = round(
            0.28 * source.authority
            + 0.24 * source.relevance
            + 0.20 * source.direct_support
            + 0.16 * source.specificity
            + 0.12 * source.industry_fit
        )
        # A document is "executive" when it is on-industry, on-question and
        # carries checkable claims. Two of the three at a good level will
        # also pass, so a strong primary source is not lost to one weak axis.
        axes = [
            source.industry_fit >= 48,
            source.relevance >= 30,
            source.direct_support >= 25,
        ]
        source.executive = (
            len(body) >= 180
            and source.industry_fit >= 35
            and (all(axes) or (sum(axes) >= 2 and source.authority >= 60))
        )
        unique[url] = source

    ordered = sorted(
        unique.values(),
        key=lambda s: (s.executive, s.industry_fit, s.quality, s.authority),
        reverse=True,
    )
    for index, source in enumerate(ordered, start=1):
        source.ref = f"D{domain_id}/S{index}"
    return ordered


def executive_set(sources: Sequence[Source], limit: int = 6) -> List[Source]:
    """The subset a partner would actually put in front of a client."""
    hard = [s for s in sources if s.executive]
    picked = list(hard[:limit])

    # Top the set up with near-misses rather than discarding them. A
    # competing size estimate that failed one threshold by two points is
    # exactly the document reconciliation needs to see.
    if len(picked) < limit:
        seen = {s.url for s in picked}
        soft = [
            s for s in sources
            if s.url not in seen and s.industry_fit >= 40 and s.relevance >= 20
        ]
        picked += soft[: limit - len(picked)]

    return picked or list(sources)[:limit]


def evidence_metrics(sources: Sequence[Source]) -> Dict[str, int]:
    picked = executive_set(sources, 8)
    if not picked:
        return {
            "quality": 0, "relevance": 0, "direct_support": 0,
            "industry_fit": 0, "authority": 0,
            "independent_domains": 0, "source_count": 0,
        }

    def mean(attr: str) -> int:
        return round(sum(getattr(s, attr) for s in picked) / len(picked))

    return {
        "quality": mean("quality"),
        "relevance": mean("relevance"),
        "direct_support": mean("direct_support"),
        "industry_fit": mean("industry_fit"),
        "authority": mean("authority"),
        "independent_domains": len({s.host for s in picked}),
        "source_count": len(picked),
    }


__all__ = [
    "ALIASES",
    "BLOCKED_HOSTS",
    "Source",
    "authority",
    "direct_support",
    "evidence_metrics",
    "executive_set",
    "industry_family",
    "industry_fit",
    "industry_terms",
    "keywords",
    "qualify",
    "relevance",
    "specificity",
]
