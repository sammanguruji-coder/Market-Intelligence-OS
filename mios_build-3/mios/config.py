"""
Runtime configuration for Market Intelligence OS.

Everything environment-dependent lives here so no other module has to
touch os.getenv. Import `SETTINGS` and read attributes.
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent.parent


def _find_env() -> Path | None:
    """
    Find the .env file wherever the user reasonably put it.

    People drop .env next to app.py, inside the package folder, or in the
    folder they launched Streamlit from, and any of those should work.
    Searching in a fixed order beats making someone debug why their keys
    are being ignored.
    """
    candidates = [
        BASE_DIR / ".env",                    # project root, next to app.py
        BASE_DIR / "mios" / ".env",           # inside the package
        Path.cwd() / ".env",                  # wherever streamlit was launched
        Path.cwd().parent / ".env",
    ]
    for path in candidates:
        try:
            if path.is_file():
                return path
        except OSError:
            continue
    return None


ENV_PATH = _find_env()
if ENV_PATH:
    # override=True so editing .env and restarting actually takes effect,
    # even if a stale variable is already in the shell environment.
    load_dotenv(ENV_PATH, override=True)


def _int(name: str, default: int, floor: int = 0) -> int:
    try:
        return max(floor, int(os.getenv(name, str(default))))
    except (TypeError, ValueError):
        return default


def _float(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except (TypeError, ValueError):
        return default


@dataclass(frozen=True)
class Settings:
    """Immutable snapshot of runtime configuration."""

    app_name: str = "Market Intelligence OS"
    tagline: str = "Research → Evidence → Reconciliation → Decision"

    tavily_key: str = field(default_factory=lambda: os.getenv("TAVILY_API_KEY", "").strip())
    groq_key: str = field(default_factory=lambda: os.getenv("GROQ_API_KEY", "").strip())
    # Groq retired llama-3.3-70b-versatile in June 2026. Defaulting to a
    # retired ID means every call fails with model-not-found, so the
    # default is a current production model and `llm.resolve_model()`
    # upgrades retired IDs automatically.
    groq_model: str = field(
        default_factory=lambda: os.getenv("GROQ_MODEL", "openai/gpt-oss-120b").strip()
    )

    search_results: int = field(default_factory=lambda: _int("TAVILY_RESULTS", 6, 4))
    search_depth: str = field(
        default_factory=lambda: os.getenv("TAVILY_DEPTH", "advanced").strip() or "advanced"
    )
    time_range: str = field(
        default_factory=lambda: os.getenv("TAVILY_TIME_RANGE", "").strip()
    )
    use_news_topic: bool = field(
        default_factory=lambda: os.getenv("TAVILY_NEWS_TOPIC", "1").strip() not in ("0", "false", "")
    )
    source_limit: int = field(default_factory=lambda: _int("EXECUTIVE_SOURCE_LIMIT", 6, 3))
    llm_input_chars: int = field(default_factory=lambda: _int("GROQ_INPUT_CHARS", 5000, 2500))
    max_llm_calls: int = field(default_factory=lambda: _int("MAX_GROQ_CALLS", 15, 0))
    search_delay: float = field(default_factory=lambda: _float("SEARCH_DELAY", 0.10))

    cache_ttl_seconds: int = field(default_factory=lambda: _int("CACHE_TTL", 21600, 60))

    @property
    def has_search(self) -> bool:
        return bool(self.tavily_key)

    @property
    def has_llm(self) -> bool:
        return bool(self.groq_key)


SETTINGS = Settings()


# ----------------------------------------------------------------------
# Optional dependency detection
# ----------------------------------------------------------------------
# These are checked once at import so the UI can report a precise,
# actionable message instead of silently degrading.

def _probe(module: str) -> bool:
    try:
        __import__(module)
        return True
    except Exception:
        return False


HAS_PLOTLY = _probe("plotly")
HAS_TAVILY = _probe("tavily")
HAS_GROQ = _probe("groq")

PYTHON_EXECUTABLE = sys.executable
ENV_LOADED = ENV_PATH is not None
ENV_LOCATION = str(ENV_PATH) if ENV_PATH else "no .env file found"

INSTALL_HINT = (
    f'"{PYTHON_EXECUTABLE}" -m pip install -r requirements.txt'
)

# Where the keys came from, so the sidebar can say so plainly rather
# than leaving the user guessing why a pasted .env had no effect.
ENV_SOURCE = str(ENV_PATH) if ENV_PATH else "no .env file found"
EXPECTED_ENV_PATH = str(BASE_DIR / ".env")

__all__ = [
    "SETTINGS",
    "BASE_DIR",
    "ENV_PATH",
    "ENV_SOURCE",
    "EXPECTED_ENV_PATH",
    "ENV_PATH",
    "ENV_LOADED",
    "ENV_LOCATION",
    "ENV_PATH",
    "HAS_PLOTLY",
    "HAS_TAVILY",
    "HAS_GROQ",
    "PYTHON_EXECUTABLE",
    "INSTALL_HINT",
]
