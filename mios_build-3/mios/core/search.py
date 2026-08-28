"""
Retrieval layer (Tavily).

Wraps Tavily behind a cache so re-running a research pass during a
working session costs nothing, and so the UI never has to know whether a
result came from the network or from memory.

The client passes the parameters that actually change result quality for
market research: `topic` to reach news and finance indexes, `country` to
bias toward the target geography, `time_range` to keep forecasts current,
and `include_raw_content="markdown"` because the extractor works far
better on full page text than on search snippets.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

from ..config import SETTINGS
from .domains import DOMAINS

try:  # pragma: no cover - optional dependency
    from tavily import TavilyClient
    INSTALLED = True
except Exception:  # pragma: no cover
    TavilyClient = None  # type: ignore
    INSTALLED = False

_client = None
_cache: Dict[str, List[dict]] = {}


def explain(exc: Exception, service: str) -> str:
    """
    Turn an SDK exception into something a user can act on.

    Both SDKs raise errors whose str() is sometimes empty, so the class
    name has to carry the meaning. An empty "ForbiddenError:" in the
    sidebar tells nobody anything.
    """
    name = type(exc).__name__
    detail = str(exc).strip()
    low = f"{name} {detail}".lower()

    if "not in allowlist" in low or "egress" in low:
        return (f"{name}: this network blocks outbound calls to {service}. "
                f"Run the app from a machine with internet access.")
    if any(k in low for k in ("forbidden", "401", "403", "unauthorized",
                              "permissiondenied", "invalid api key",
                              "authenticationerror")):
        return (f"{name}: {service} rejected the key. Check it is correct, "
                f"active, and pasted into .env without quotes or spaces.")
    if any(k in low for k in ("rate limit", "429", "quota", "credit")):
        return f"{name}: {service} rate limit or quota reached. Wait, or upgrade the tier."
    if any(k in low for k in ("timeout", "connection", "resolve", "network", "dns")):
        return f"{name}: could not reach {service}. Check your connection or proxy."
    if "not found" in low or "does not exist" in low or "decommission" in low:
        return (f"{name}: the model ID was rejected. Pick a current model "
                f"from the sidebar list.")
    return f"{name}: {detail or 'no detail returned by the SDK'}"


@dataclass
class Usage:
    """Live counters, so the sidebar can show what a run actually cost."""
    queries: int = 0
    cached: int = 0
    failed: int = 0
    results: int = 0
    last_error: Optional[str] = None
    errors: List[str] = field(default_factory=list)

    def reset(self) -> None:
        self.queries = self.cached = self.failed = self.results = 0
        self.last_error = None
        self.errors.clear()


USAGE = Usage()

# Country names Tavily accepts, keyed by how people type a geography.
COUNTRY_ALIASES = {
    "india": "india", "usa": "united states", "us": "united states",
    "united states": "united states", "uk": "united kingdom",
    "united kingdom": "united kingdom", "uae": "united arab emirates",
    "germany": "germany", "france": "france", "japan": "japan",
    "china": "china", "brazil": "brazil", "singapore": "singapore",
    "australia": "australia", "canada": "canada", "indonesia": "indonesia",
    "nigeria": "nigeria", "south africa": "south africa", "kenya": "kenya",
    "mexico": "mexico", "vietnam": "vietnam", "philippines": "philippines",
    "saudi arabia": "saudi arabia", "spain": "spain", "italy": "italy",
}


def country_for(geography: str) -> Optional[str]:
    """Tavily only accepts country names, so regions map to nothing."""
    return COUNTRY_ALIASES.get((geography or "").strip().lower())


def client():
    global _client
    if _client is None and INSTALLED and SETTINGS.tavily_key:
        try:
            _client = TavilyClient(api_key=SETTINGS.tavily_key)
        except Exception as exc:
            USAGE.last_error = f"Client init failed: {exc}"
            _client = None
    return _client


def configured() -> bool:
    return bool(SETTINGS.tavily_key) and INSTALLED


def available() -> bool:
    return client() is not None


def health() -> Tuple[bool, str]:
    """One cheap query, for the sidebar connection test."""
    if not INSTALLED:
        return False, "The tavily-python package is not installed in this interpreter."
    if not SETTINGS.tavily_key:
        return False, "TAVILY_API_KEY is not set in your .env file."

    api = client()
    if api is None:
        return False, USAGE.last_error or "Could not create the Tavily client."

    try:
        response = api.search(query="market size report", max_results=1,
                              search_depth="basic")
        count = len(response.get("results", []) or [])
        return True, f"Search responded with {count} result(s)."
    except Exception as exc:
        return False, explain(exc, "Tavily")


def search_once(
    query: str,
    topic: str = "general",
    country: Optional[str] = None,
    time_range: Optional[str] = None,
) -> Tuple[List[dict], Optional[str]]:
    """One query against the index. Cached by the full parameter set."""
    key = f"{topic}|{country}|{time_range}|{query}"
    if key in _cache:
        USAGE.cached += 1
        return _cache[key], None

    api = client()
    if api is None:
        return [], "Search is not configured (TAVILY_API_KEY missing)."

    params = dict(
        query=query,
        search_depth=SETTINGS.search_depth,
        max_results=SETTINGS.search_results,
        include_answer=False,
        include_raw_content="markdown",
        topic=topic,
    )
    if country and topic == "general":
        params["country"] = country
    if time_range:
        params["time_range"] = time_range

    try:
        USAGE.queries += 1
        response = api.search(**params)
        results = response.get("results", []) or []
        USAGE.results += len(results)
        _cache[key] = results
        return results, None

    except TypeError:
        # An older SDK that does not know the newer parameters. Retry
        # with the minimal set rather than failing the whole run.
        try:
            response = api.search(
                query=query,
                search_depth="advanced",
                max_results=SETTINGS.search_results,
                include_answer=False,
                include_raw_content=True,
            )
            results = response.get("results", []) or []
            USAGE.results += len(results)
            _cache[key] = results
            return results, None
        except Exception as exc:
            USAGE.failed += 1
            message = explain(exc, "Tavily")
            USAGE.last_error = message
            USAGE.errors.append(message)
            return [], message

    except Exception as exc:
        USAGE.failed += 1
        message = explain(exc, "Tavily")
        USAGE.last_error = message
        USAGE.errors.append(message)
        return [], message


def build_queries(industry: str, geography: str, objective: str, domain_id: int) -> List[str]:
    d = DOMAINS[domain_id]
    base = f"{industry} {geography}".strip()
    queries = [f"{base} {hint}" for hint in d.query_hints]
    queries.append(f"{base} {d.name} {objective}".strip())
    return queries


# Domains where recent news beats evergreen research pages.
NEWS_DOMAINS = {5, 6, 8, 13}


def gather(
    industry: str,
    geography: str,
    objective: str,
    domain_id: int,
) -> Tuple[List[dict], List[str]]:
    """Run a domain query set and return de-duplicated raw hits."""
    raw: Dict[str, dict] = {}
    errors: List[str] = []

    country = country_for(geography)
    topic = "news" if domain_id in NEWS_DOMAINS and SETTINGS.use_news_topic else "general"
    time_range = SETTINGS.time_range or None

    for query in build_queries(industry, geography, objective, domain_id):
        hits, error = search_once(query, topic=topic, country=country,
                                  time_range=time_range)
        if error:
            errors.append(error)
        for hit in hits:
            url = (hit.get("url") or "").split("#")[0].rstrip("/")
            if url:
                raw.setdefault(url, hit)
        if SETTINGS.search_delay:
            time.sleep(SETTINGS.search_delay)

    return list(raw.values()), errors


def prime_cache(entries: Dict[str, Sequence[dict]]) -> None:
    """Load a fixture corpus so the app runs without network access."""
    for query, results in entries.items():
        # Fixtures are keyed for every parameter combination the demo
        # run might produce, so demo mode never touches the network.
        for topic in ("general", "news"):
            for country in (None, country_for("India"), country_for("india")):
                _cache[f"{topic}|{country}|None|{query}"] = list(results)


def clear_cache() -> None:
    _cache.clear()


def cache_size() -> int:
    return len(_cache)


__all__ = [
    "COUNTRY_ALIASES", "INSTALLED", "NEWS_DOMAINS", "USAGE", "available",
    "build_queries", "cache_size", "clear_cache", "configured",
    "country_for", "gather", "health", "prime_cache", "search_once",
]
