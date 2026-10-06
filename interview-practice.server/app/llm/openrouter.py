"""Minimal OpenRouter chat-completions client.

Framework-free on purpose (no Flask import): the base URL and key are passed in, so
the client can be tested with a fake transport.
No LangChain (ADR 0005). Every failure becomes an `ApiError` subclass, so routes just
let it propagate and the error handlers produce the JSON contract.
"""

import base64
import binascii
import json
import logging
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any, Literal, TypeVar

import httpx
from pydantic import BaseModel, ValidationError

from app.errors.exceptions import (
    InputRejectedError,
    LlmTimeoutError,
    LlmUnavailableError,
    LlmUpstreamError,
)

logger = logging.getLogger(__name__)

T = TypeVar("T", bound=BaseModel)


@dataclass(frozen=True)
class ChatMessage:
    role: Literal["system", "user", "assistant"]
    content: str


@dataclass(frozen=True)
class CompletionSettings:
    """Per-call overrides; None means omitted, so the provider default applies."""

    temperature: float | None = None
    max_tokens: int | None = None
    reasoning_effort: str | None = None


@dataclass(frozen=True)
class GeneratedImage:
    data: bytes
    extension: str  # "png" | "jpg" | "webp", from the bytes themselves


MAX_IMAGE_BYTES = 10 * 1024 * 1024
IMAGE_TIMEOUT_SECONDS = 120.0


def _sniff_extension(data: bytes) -> str | None:
    """The image type by its magic bytes; the provider's `media_type` isn't trusted."""
    if data.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if data.startswith(b"\xff\xd8\xff"):
        return "jpg"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "webp"
    return None  # anything else (SVG included) is refused


@dataclass(frozen=True)
class ChatResult:
    content: str
    model: str
    prompt_tokens: int | None
    completion_tokens: int | None


class OpenRouterClient:
    def __init__(
        self,
        *,
        base_url: str,
        api_key: Callable[[], str | None],
        timeout: float = 60.0,
        transport: httpx.BaseTransport | None = None,
    ) -> None:
        # The key is looked up per call (not at startup) so the app boots without one
        # and a rotated secret is picked up without a restart.
        self._api_key = api_key
        self._http = httpx.Client(
            base_url=base_url.rstrip("/"), timeout=timeout, transport=transport
        )

    def chat(
        self,
        model: str,
        messages: list[ChatMessage],
        settings: CompletionSettings = CompletionSettings(),  # noqa: B008
        *,
        json_mode: bool = False,
    ) -> ChatResult:
        body: dict[str, Any] = {
            "model": model,
            "messages": [{"role": m.role, "content": m.content} for m in messages],
        }
        if settings.temperature is not None:
            body["temperature"] = settings.temperature
        if settings.max_tokens is not None:
            body["max_tokens"] = settings.max_tokens
        if settings.reasoning_effort is not None:
            body["reasoning"] = {"effort": settings.reasoning_effort}
        if json_mode:
            body["response_format"] = {"type": "json_object"}

        payload = self._post("/chat/completions", body)
        return self._parse_chat(payload, model)

    def chat_structured(
        self,
        schema: type[T],
        model: str,
        messages: list[ChatMessage],
        settings: CompletionSettings = CompletionSettings(),  # noqa: B008
    ) -> T:
        """Chat in JSON mode and validate the reply against a Pydantic model."""
        result = self.chat(model, messages, settings, json_mode=True)
        try:
            return schema.model_validate_json(result.content)
        except ValidationError as exc:
            logger.error("Model %s broke the %s contract: %s", model, schema, exc)
            raise LlmUpstreamError("The model returned an unusable response.") from exc

    def generate_image(self, model: str, prompt: str) -> GeneratedImage:
        """One image from OpenRouter's image API (`POST /images`, base64 reply)."""
        payload = self._post(
            "/images",
            {"model": model, "prompt": prompt, "n": 1},
            timeout=IMAGE_TIMEOUT_SECONDS,
        )
        try:
            encoded = payload["data"][0]["b64_json"]
            data = base64.b64decode(encoded, validate=True)
        except (KeyError, IndexError, TypeError, binascii.Error) as exc:
            raise LlmUpstreamError("The image service returned no image.") from exc
        extension = _sniff_extension(data)
        if extension is None or len(data) > MAX_IMAGE_BYTES:
            logger.error("Image from %s refused: %d bytes", model, len(data))
            raise LlmUpstreamError("The image service returned an unusable image.")
        return GeneratedImage(data=data, extension=extension)

    # -- internals ---------------------------------------------------------------

    def _post(
        self, path: str, body: dict[str, Any], *, timeout: float | None = None
    ) -> dict[str, Any]:
        key = self._api_key()
        if not key:
            logger.error("OpenRouter API key is not configured.")
            raise LlmUnavailableError("The AI service is not available right now.")
        try:
            response = self._http.post(
                path,
                json=body,
                headers={"Authorization": f"Bearer {key}"},
                timeout=timeout if timeout is not None else httpx.USE_CLIENT_DEFAULT,
            )
        except httpx.TimeoutException as exc:
            raise LlmTimeoutError("The AI service took too long to respond.") from exc
        except httpx.HTTPError as exc:
            logger.error("OpenRouter request failed: %s", exc)
            raise LlmUpstreamError("The AI service could not be reached.") from exc

        payload = self._json(response)
        if response.status_code >= 400:
            self._raise_for_error(response, payload)
        return payload

    @staticmethod
    def _json(response: httpx.Response) -> dict[str, Any]:
        try:
            payload = response.json()
        except ValueError:
            payload = None
        if isinstance(payload, dict):
            return payload
        if response.status_code >= 400:
            return {}
        raise LlmUpstreamError("The model returned an unusable response.")

    @staticmethod
    def _raise_for_error(response: httpx.Response, payload: dict[str, Any]) -> None:
        error = payload.get("error")
        error = error if isinstance(error, dict) else {}
        status = response.status_code
        # Upstream detail goes to our log only; the candidate gets a generic message.
        logger.error("OpenRouter %s: %s", status, error.get("message", "<no message>"))

        # Provider-side moderation flagged the text: same outcome, for the candidate,
        # as our own guard rejecting it.
        metadata = error.get("metadata")
        if status == 403 and isinstance(metadata, dict) and "reasons" in metadata:
            raise InputRejectedError(
                "The AI provider declined this text. Please rephrase it and try again.",
                details={"reason": "moderation"},
            )
        if status in (401, 402, 403, 429, 503):
            # Not the candidate's doing (our key/credits/quota) or worth a retry.
            details = None
            retry_after = response.headers.get("Retry-After")
            if retry_after and retry_after.isdigit():
                details = {"retryAfterSeconds": int(retry_after)}
            raise LlmUnavailableError(
                "The AI service is busy or unavailable. Please try again shortly.",
                details=details,
            )
        if status == 408:
            raise LlmTimeoutError("The AI service took too long to respond.")
        raise LlmUpstreamError("The AI service returned an error.")

    @staticmethod
    def _parse_chat(payload: dict[str, Any], model: str) -> ChatResult:
        try:
            choice = payload["choices"][0]
            content = choice["message"]["content"]
        except (KeyError, IndexError, TypeError) as exc:
            raise LlmUpstreamError("The model returned an unusable response.") from exc
        # Providers can fail mid-generation yet answer 200 (finish_reason "error").
        if choice.get("finish_reason") == "error" or not isinstance(content, str):
            logger.error(
                "Model %s finished with an error: %s", model, json.dumps(choice)
            )
            raise LlmUpstreamError("The model returned an unusable response.")
        usage = payload.get("usage") or {}
        return ChatResult(
            content=content,
            model=str(payload.get("model", model)),
            prompt_tokens=usage.get("prompt_tokens"),
            completion_tokens=usage.get("completion_tokens"),
        )
