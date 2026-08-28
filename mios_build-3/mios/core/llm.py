"""
Language-model layer (Groq).

The model has exactly one job: turning already-qualified evidence into
tight consulting prose. It never supplies facts. Every prompt ships its
evidence inline and forbids anything outside it, and `narrative.py`
produces the same output shape when the model is unavailable, so a
missing or rate-limited key degrades the writing, never the analysis.

Model IDs matter here. Groq retired `llama-3.3-70b-versatile` and
`llama-3.1-8b-instant` in June 2026, so anything pinned to those returns
a model-not-found error on the first call. `PREFERRED_MODELS` is a
fallback chain and `list_models()` reads the live catalogue, so the app
keeps working when the next model is retired too.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import List, Optional, Tuple

from ..config import SETTINGS

try:  # pragma: no cover - optional dependency
    from groq import Groq
    INSTALLED = True
except Exception:  # pragma: no cover
    Groq = None  # type: ignore
    INSTALLED = False

_client = None
_model_cache: List[str] = []

# Tried in order when the configured model is unavailable.
PREFERRED_MODELS = [
    "openai/gpt-oss-120b",
    "qwen/qwen3.6-27b",
    "openai/gpt-oss-20b",
]

# Retired IDs. Silently upgraded rather than failing on the first call.
RETIRED_MODELS = {
    "llama-3.3-70b-versatile": "openai/gpt-oss-120b",
    "llama-3.1-8b-instant": "openai/gpt-oss-20b",
    "qwen/qwen3-32b": "openai/gpt-oss-120b",
    "meta-llama/llama-4-scout-17b-16e-instruct": "openai/gpt-oss-120b",
    "moonshotai/kimi-k2-instruct-0905": "openai/gpt-oss-120b",
}


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
class Budget:
    """Hard ceiling on model calls per research run."""
    limit: int
    used: int = 0
    failed: int = 0
    last_error: Optional[str] = None

    @property
    def remaining(self) -> int:
        return max(0, self.limit - self.used)

    def spend(self) -> bool:
        if self.remaining <= 0:
            return False
        self.used += 1
        return True


BUDGET = Budget(limit=SETTINGS.max_llm_calls)


def reset_budget(limit: Optional[int] = None) -> None:
    global BUDGET
    BUDGET = Budget(limit=SETTINGS.max_llm_calls if limit is None else limit)


def client():
    global _client
    if _client is None and INSTALLED and SETTINGS.groq_key:
        try:
            _client = Groq(api_key=SETTINGS.groq_key, timeout=45.0, max_retries=1)
        except Exception as exc:
            BUDGET.last_error = f"Client init failed: {exc}"
            _client = None
    return _client


def configured() -> bool:
    return bool(SETTINGS.groq_key) and INSTALLED


def available() -> bool:
    return client() is not None and BUDGET.remaining > 0


def list_models(refresh: bool = False) -> List[str]:
    """The live catalogue, so the picker never offers a retired model."""
    global _model_cache
    if _model_cache and not refresh:
        return _model_cache

    api = client()
    if api is None:
        return []

    try:
        response = api.models.list()
        ids = sorted(
            m.id for m in response.data
            if getattr(m, "id", None) and "whisper" not in m.id and "tts" not in m.id
        )
        _model_cache = ids
        return ids
    except Exception as exc:
        BUDGET.last_error = f"Model list failed: {exc}"
        return []


def resolve_model() -> str:
    """
    The model to actually call: the configured one if it is live, its
    documented successor if it was retired, otherwise the best available
    from the preference chain.
    """
    wanted = SETTINGS.groq_model.strip()
    catalogue = list_models()

    if wanted in RETIRED_MODELS:
        wanted = RETIRED_MODELS[wanted]

    if not catalogue:
        return wanted or PREFERRED_MODELS[0]

    if wanted in catalogue:
        return wanted

    for candidate in PREFERRED_MODELS:
        if candidate in catalogue:
            return candidate

    return catalogue[0]


def health() -> Tuple[bool, str]:
    """One cheap round trip, for the sidebar connection test."""
    if not INSTALLED:
        return False, "The groq package is not installed in this interpreter."
    if not SETTINGS.groq_key:
        return False, "GROQ_API_KEY is not set in your .env file."

    api = client()
    if api is None:
        return False, BUDGET.last_error or "Could not create the Groq client."

    model = resolve_model()
    try:
        response = api.chat.completions.create(
            model=model,
            max_tokens=8,
            temperature=0,
            messages=[{"role": "user", "content": "Reply with the word: ready"}],
        )
        reply = (response.choices[0].message.content or "").strip()
        return True, f"{model} responded ({reply[:24] or 'empty reply'})."
    except Exception as exc:
        return False, explain(exc, "Groq")


SYSTEM_PROMPT = (
    "You are a senior market-intelligence consultant writing for an "
    "investment committee. You use only the evidence supplied to you. "
    "You never invent a number, a company name or a date. If the evidence "
    "does not support a claim, you say the evidence is insufficient. "
    "You write in short declarative sentences and you cite every factual "
    "statement with its reference tag. You never use marketing language."
)


def complete(
    prompt: str,
    max_tokens: int = 700,
    temperature: float = 0.2,
    retries: int = 1,
) -> Optional[str]:
    """
    Model text, or None when unavailable, over budget or failing.

    Returning None rather than raising is deliberate: the caller already
    has a deterministic fallback, and a model outage should degrade the
    prose without interrupting a thirteen-domain research run.
    """
    api = client()
    if api is None or not BUDGET.spend():
        return None

    model = resolve_model()

    for attempt in range(retries + 1):
        try:
            response = api.chat.completions.create(
                model=model,
                temperature=temperature,
                max_tokens=max_tokens,
                messages=[
                    {"role": "system", "content": SYSTEM_PROMPT},
                    {"role": "user", "content": prompt[: SETTINGS.llm_input_chars]},
                ],
            )
            text = (response.choices[0].message.content or "").strip()
            if text:
                return text
            BUDGET.last_error = "Model returned an empty response."
            return None

        except Exception as exc:
            message = str(exc)
            BUDGET.last_error = explain(exc, "Groq")

            # Rate limits are worth one backoff; everything else is not.
            transient = any(
                token in message.lower()
                for token in ("rate limit", "429", "timeout", "503", "overloaded")
            )
            if transient and attempt < retries:
                time.sleep(1.5 * (attempt + 1))
                continue

            BUDGET.failed += 1
            return None

    return None


__all__ = [
    "BUDGET", "INSTALLED", "PREFERRED_MODELS", "RETIRED_MODELS",
    "available", "client", "complete", "configured", "health",
    "list_models", "reset_budget", "resolve_model",
]
