"""Runtime configuration for Market Intelligence OS.

Configuration is loaded from a local ``.env`` file when running locally and
from Streamlit Cloud Secrets when deployed.  The rest of the application only
needs to import ``SETTINGS`` from this module.
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent.parent


def _find_env() -> Path | None:
    """Find the project's ``.env`` file in the common launch locations."""
    candidates = (
        BASE_DIR / ".env",
        BASE_DIR / "mios" / ".env",
        Path.cwd() / ".env",
        Path.cwd().parent / ".env",
    )
    for path in candidates:
        try:
            if path.is_file():
                return path
        except OSError:
            continue
    return None


ENV_PATH = _find_env()
if ENV_PATH is not None:
    # Make a changed .env take effect after a normal Streamlit restart.
    load_dotenv(ENV_PATH, override=True)


def _value(name: str, default: str = "") -> str:
    """Read a setting from the environment, then Streamlit Cloud Secrets.

    Importing Streamlit is deliberately lazy: this module remains usable in
    tests and ordinary Python scripts where Streamlit is not installed.
    """
    value = os.getenv(name, "").strip()
    if value:
        return value
    try:
        import streamlit as st

        secret = st.secrets.get(name, default)
        return str(secret).strip()
    except Exception:
        return default


def _int(name: str, default: int, floor: int = 0) -> int:
    try:
        return max(floor, int(_value(name, str(default))))
    except (TypeError, ValueError):
        return default


def _float(name: str, default: float) -> float:
    try:
        return float(_value(name, str(default)))
    except (TypeError, ValueError):
        return default


def _bool(name: str, default: bool = False) -> bool:
    """Parse common true/false spellings without surprising truthiness."""
    raw = _value(name, "1" if default else "0").strip().lower()
    return raw in {"1", "true", "yes", "y", "on"}


@dataclass(frozen=True)
class Settings:
    """Immutable snapshot of runtime configuration."""

    app_name: str = "Market Intelligence OS"
    tagline: str = "Research → Evidence → Reconciliation → Decision"

    tavily_key: str = field(default_factory=lambda: _value("TAVILY_API_KEY"))
    groq_key: str = field(default_factory=lambda: _value("GROQ_API_KEY"))
    # Current default; users can override it with GROQ_MODEL in Secrets/.env.
    groq_model: str = field(
        default_factory=lambda: _value("GROQ_MODEL", "openai/gpt-oss-120b")
    )

    search_results: int = field(default_factory=lambda: _int("TAVILY_RESULTS", 6, 4))
    search_depth: str = field(
        default_factory=lambda: _value("TAVILY_DEPTH", "advanced") or "advanced"
    )
    time_range: str = field(default_factory=lambda: _value("TAVILY_TIME_RANGE"))
    use_news_topic: bool = field(default_factory=lambda: _bool("TAVILY_NEWS_TOPIC", True))
    source_limit: int = field(
        default_factory=lambda: _int("EXECUTIVE_SOURCE_LIMIT", 6, 3)
    )
    llm_input_chars: int = field(
        default_factory=lambda: _int("GROQ_INPUT_CHARS", 5000, 2500)
    )
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


def _probe(module: str) -> bool:
    """Return whether an optional runtime dependency can be imported."""
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
ENV_SOURCE = ENV_LOCATION
EXPECTED_ENV_PATH = str(BASE_DIR / ".env")
INSTALL_HINT = f'"{PYTHON_EXECUTABLE}" -m pip install -r requirements.txt'


__all__ = [
    "SETTINGS",
    "BASE_DIR",
    "ENV_PATH",
    "ENV_LOADED",
    "ENV_LOCATION",
    "ENV_SOURCE",
    "EXPECTED_ENV_PATH",
    "HAS_PLOTLY",
    "HAS_TAVILY",
    "HAS_GROQ",
    "PYTHON_EXECUTABLE",
    "INSTALL_HINT",
]
