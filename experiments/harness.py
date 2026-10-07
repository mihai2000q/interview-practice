"""Calling a model for the benchmark: cached, parallel, and with a hard spend cap.

Every call is appended to `results/<experiment>.jsonl` with its cost (OpenRouter's own
`usage.cost`), latency and token counts. A call whose key is already in the file is
never repeated, so a run can be stopped and resumed, and re-analysing costs nothing.
The key comes from the shell's `OPENROUTER_API_KEY`, never from a file in the repo.
"""

import hashlib
import json
import os
import threading
import time
from collections.abc import Callable, Iterable
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Any, TypeVar

import httpx
from pydantic import BaseModel, ValidationError

RESULTS = Path(__file__).parent / "results"
BASE_URL = os.environ.get("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
# The whole benchmark may spend this much (USD), summed over every results file.
BUDGET_USD = float(os.environ.get("BENCH_BUDGET_USD", "4.2"))
WORKERS = int(os.environ.get("BENCH_WORKERS", "8"))
TIMEOUT_S = 180.0

T = TypeVar("T", bound=BaseModel)
_lock = threading.Lock()
_cache: dict[str, dict[str, Any]] = {}
_spent = 0.0
_loaded = False


class BudgetExceeded(RuntimeError):
    pass


def _load() -> None:
    global _loaded, _spent
    if _loaded:
        return
    RESULTS.mkdir(exist_ok=True)
    for path in RESULTS.glob("*.jsonl"):
        for line in path.read_text().splitlines():
            if line.strip():
                record = json.loads(line)
                _cache[record["key"]] = record
                _spent += record.get("cost") or 0.0
    _loaded = True


def spent() -> float:
    with _lock:
        _load()
        return _spent


def _key(parts: dict[str, Any]) -> str:
    blob = json.dumps(parts, sort_keys=True, ensure_ascii=False)
    return hashlib.sha1(blob.encode()).hexdigest()


def messages_dicts(messages: Iterable[Any]) -> list[dict[str, str]]:
    """The app's `ChatMessage`s (or plain dicts) as API messages."""
    return [
        m if isinstance(m, dict) else {"role": m.role, "content": m.content}
        for m in messages
    ]


def call(
    experiment: str,
    meta: dict[str, Any],
    model: str,
    messages: Iterable[Any],
    *,
    temperature: float | None = None,
    reasoning_effort: str | None = None,
    max_tokens: int | None = None,
    json_mode: bool = True,
) -> dict[str, Any]:
    """One chat completion, or the cached record of the same call.

    `meta` says what the call is for (arm, fixture, run number): it is stored with the
    result and is part of the cache key, so two runs of the same prompt are distinct
    calls when their `run` differs.
    """
    global _spent
    msgs = messages_dicts(messages)
    settings = {
        "temperature": temperature,
        "reasoning_effort": reasoning_effort,
        "max_tokens": max_tokens,
        "json_mode": json_mode,
    }
    key = _key(
        {"e": experiment, "meta": meta, "model": model, "m": msgs, "s": settings}
    )
    with _lock:
        _load()
        if key in _cache:
            return _cache[key]
        if _spent >= BUDGET_USD:
            raise BudgetExceeded(f"spent ${_spent:.2f} of ${BUDGET_USD:.2f}")

    body: dict[str, Any] = {"model": model, "messages": msgs}
    if temperature is not None:
        body["temperature"] = temperature
    if max_tokens is not None:
        body["max_tokens"] = max_tokens
    if reasoning_effort is not None:
        body["reasoning"] = {"effort": reasoning_effort}
    if json_mode:
        body["response_format"] = {"type": "json_object"}

    record: dict[str, Any] = {
        "key": key,
        "experiment": experiment,
        "meta": meta,
        "model": model,
        "settings": settings,
        "content": None,
        "error": None,
        "latency_s": None,
        "prompt_tokens": None,
        "completion_tokens": None,
        "reasoning_tokens": None,
        "cost": 0.0,
    }
    started = time.time()
    for attempt in range(3):
        try:
            response = httpx.post(
                f"{BASE_URL}/chat/completions",
                json=body,
                headers={"Authorization": f"Bearer {os.environ['OPENROUTER_API_KEY']}"},
                timeout=httpx.Timeout(TIMEOUT_S, connect=20.0),
            )
        except httpx.HTTPError as exc:
            record["error"] = f"transport: {type(exc).__name__}"
            time.sleep(2 + attempt * 3)
            continue
        payload = response.json() if response.content else {}
        if response.status_code in (429, 500, 502, 503, 504):
            record["error"] = f"http {response.status_code}"
            time.sleep(3 + attempt * 5)
            continue
        if response.status_code >= 400:
            message = (payload.get("error") or {}).get("message", "")
            record["error"] = f"http {response.status_code}: {message[:200]}"
            break
        try:
            choice = payload["choices"][0]
            if choice.get("finish_reason") == "error":
                record["error"] = "finish_reason error"
                break
            record["content"] = choice["message"]["content"]
            record["error"] = None
            record["finish_reason"] = choice.get("finish_reason")
        except (KeyError, IndexError, TypeError):
            record["error"] = "unusable payload"
            break
        usage = payload.get("usage") or {}
        record["prompt_tokens"] = usage.get("prompt_tokens")
        record["completion_tokens"] = usage.get("completion_tokens")
        details = usage.get("completion_tokens_details") or {}
        record["reasoning_tokens"] = details.get("reasoning_tokens")
        record["cost"] = usage.get("cost") or 0.0
        break
    record["latency_s"] = round(time.time() - started, 2)

    with _lock:
        _spent += record["cost"]
        _cache[key] = record
        with (RESULTS / f"{experiment}.jsonl").open("a") as handle:
            handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    return record


def parse(schema: type[T], record: dict[str, Any]) -> T | None:
    """The reply as the app would parse it (`chat_structured`), or None if the app
    would have answered `502`."""
    if record["content"] is None:
        return None
    try:
        return schema.model_validate_json(record["content"])
    except ValidationError:
        return None


def run_all(jobs: list[Callable[[], Any]], label: str) -> list[Any]:
    """Run `jobs` on a thread pool, in order, stopping cleanly at the budget cap."""
    results: list[Any] = [None] * len(jobs)
    stopped = threading.Event()

    def work(index: int) -> None:
        if stopped.is_set():
            return
        try:
            results[index] = jobs[index]()
        except BudgetExceeded:
            stopped.set()

    started = time.time()
    with ThreadPoolExecutor(max_workers=WORKERS) as pool:
        list(pool.map(work, range(len(jobs))))
    done = sum(r is not None for r in results)
    print(
        f"[{label}] {done}/{len(jobs)} calls in {time.time() - started:.0f}s, "
        f"total spent ${spent():.3f}"
        + (" (STOPPED AT BUDGET CAP)" if stopped.is_set() else "")
    )
    return results
