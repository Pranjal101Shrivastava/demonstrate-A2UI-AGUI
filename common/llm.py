"""The "model" used by every example.

Default: a SCRIPTED model. Each example passes a `scripted` function that
returns exactly what a model would return for the prompt. This keeps every
demo offline, free, deterministic and testable.

Live mode: set GENUX_LIVE=1 and ANTHROPIC_API_KEY (pip install anthropic).
The same system prompt + user prompt is then sent to Claude, and the example
validates whatever comes back exactly as it validates the scripted output.
"""
import os
import time
from typing import Callable, Iterator

MODEL = os.environ.get("GENUX_MODEL", "claude-opus-5-5")


def is_live() -> bool:
    return os.environ.get("GENUX_LIVE") == "1" and bool(os.environ.get("ANTHROPIC_API_KEY"))


def complete(system: str, user: str, scripted: Callable[[str], str]) -> str:
    """Return the model's full text reply."""
    if not is_live():
        return scripted(user)
    import anthropic  # optional dependency, only needed in live mode

    client = anthropic.Anthropic()
    resp = client.beta.messages.create(
        model=MODEL,
        max_tokens=16000,
        system=system,
        messages=[{"role": "user", "content": user}],
        betas=["server-side-fallback-2026-07-01"],
        fallbacks="default",
    )
    if resp.stop_reason == "refusal":
        raise RuntimeError("model refused the request")
    return "".join(b.text for b in resp.content if b.type == "text")


def stream_chunks(text: str, size: int = 24, delay: float = 0.0) -> Iterator[str]:
    """Split text into chunks to imitate token streaming."""
    for i in range(0, len(text), size):
        if delay:
            time.sleep(delay)
        yield text[i : i + size]


def strip_fences(text: str) -> str:
    """Models often wrap output in ```json fences; remove them."""
    t = text.strip()
    if t.startswith("```"):
        t = t.split("\n", 1)[1] if "\n" in t else ""
        if t.rstrip().endswith("```"):
            t = t.rstrip()[:-3]
    return t.strip()
