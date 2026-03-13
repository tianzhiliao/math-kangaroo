from __future__ import annotations

from http.client import HTTPResponse
import json
import socket
import urllib.error
import urllib.request


class TTSUpstreamError(Exception):
    def __init__(self, message: str, *, status_code: int) -> None:
        super().__init__(message)
        self.status_code = status_code


class OpenAITTSClient:
    def __init__(
        self,
        *,
        api_key: str,
        model: str,
        voice: str,
        response_format: str,
        timeout_seconds: float,
    ) -> None:
        self._api_key = api_key
        self._model = model
        self._voice = voice
        self._response_format = response_format
        self._timeout_seconds = timeout_seconds
        self._url = "https://api.openai.com/v1/audio/speech"

    def open_stream(self, text: str) -> HTTPResponse:
        payload = json.dumps(
            {
                "model": self._model,
                "voice": self._voice,
                "input": text,
                "response_format": self._response_format,
            }
        ).encode("utf-8")

        request = urllib.request.Request(
            self._url,
            data=payload,
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
                "Accept": "audio/wav",
            },
            method="POST",
        )

        try:
            return urllib.request.urlopen(request, timeout=self._timeout_seconds)
        except urllib.error.HTTPError as exc:
            detail = self._extract_error_detail(exc.read())
            status_code = 504 if exc.code in {408, 504} else 502
            raise TTSUpstreamError(
                f"OpenAI TTS request failed: {detail or f'HTTP {exc.code}'}",
                status_code=status_code,
            ) from exc
        except urllib.error.URLError as exc:
            is_timeout = isinstance(exc.reason, (TimeoutError, socket.timeout))
            raise TTSUpstreamError(
                "OpenAI TTS request timed out." if is_timeout else "OpenAI TTS request could not be completed.",
                status_code=504 if is_timeout else 502,
            ) from exc

    @staticmethod
    def _extract_error_detail(payload: bytes) -> str:
        if not payload:
            return ""

        try:
            data = json.loads(payload.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            return payload.decode("utf-8", errors="ignore").strip()[:200]

        error = data.get("error")
        if isinstance(error, dict):
            message = error.get("message")
            if isinstance(message, str):
                return message

        if isinstance(error, str):
            return error

        return ""
