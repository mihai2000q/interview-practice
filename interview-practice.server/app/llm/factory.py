from collections.abc import Callable
from pathlib import Path

from flask import current_app

from app.llm.openrouter import OpenRouterClient


def _key_reader(key_file: str | None, env_key: str | None) -> Callable[[], str | None]:
    """A key lookup that needs no Flask app context, so worker threads can call it.

    Docker passes the key as a secret file (OPENROUTER_API_KEY_FILE); local dev outside
    Docker can set OPENROUTER_API_KEY in the shell. See docs/deployment.md. The file is
    read on every call, so a rotated secret is picked up without a restart.
    """

    def read() -> str | None:
        if key_file:
            path = Path(key_file)
            return path.read_text().strip() if path.is_file() else None
        return env_key

    return read


def get_llm_client() -> OpenRouterClient:
    """The app-wide client, created on first use.

    The single seam for tests: put a client in `app.extensions["llm_client"]` before the
    first call and every use case gets it.
    """
    extensions = current_app.extensions
    if "llm_client" not in extensions:
        config = current_app.config
        extensions["llm_client"] = OpenRouterClient(
            base_url=config["OPENROUTER_BASE_URL"],
            api_key=_key_reader(
                config["OPENROUTER_API_KEY_FILE"], config["OPENROUTER_API_KEY"]
            ),
            timeout=config["LLM_TIMEOUT_SECONDS"],
        )
    client: OpenRouterClient = extensions["llm_client"]
    return client
