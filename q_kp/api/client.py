from __future__ import annotations

from typing import Any

from playwright.async_api import APIResponse, Page

from q_kp.configuration import KP_API_TIMEOUT_MS, KP_BASE_URL


class KpApiError(RuntimeError):
    """Fejl fra KP's interne REST-API."""


class KpApiClient:
    """Asynkron API-klient, der genbruger browser-contextens login-cookies."""

    def __init__(self, page: Page, *, timeout_ms: int = KP_API_TIMEOUT_MS) -> None:
        if page.is_closed():
            raise RuntimeError("KP-siden er lukket.")
        self.page = page
        self.timeout_ms = timeout_ms

    async def get(self, endpoint: str, *, params: dict[str, Any] | None = None) -> Any:
        response = await self.page.request.get(
            self._url(endpoint),
            params=params,
            headers={"Accept": "application/json"},
            timeout=self.timeout_ms,
        )
        return await self._decode(response)

    async def post(self, endpoint: str, *, json_body: dict[str, Any]) -> Any:
        response = await self.page.request.post(
            self._url(endpoint),
            data=json_body,
            headers={"Accept": "application/json", "Content-Type": "application/json"},
            timeout=self.timeout_ms,
        )
        return await self._decode(response)

    async def navigate(self, relative_ui_url: str) -> None:
        await self.page.goto(
            self._url(relative_ui_url),
            wait_until="domcontentloaded",
            timeout=self.timeout_ms,
        )

    @staticmethod
    def _url(endpoint: str) -> str:
        if endpoint.startswith(("http://", "https://")):
            return endpoint
        return f"{KP_BASE_URL}/{endpoint.lstrip('/')}"

    @staticmethod
    async def _decode(response: APIResponse) -> Any:
        if not response.ok:
            body = (await response.text())[:2000]
            raise KpApiError(
                f"KP API returnerede HTTP {response.status} {response.status_text}. "
                f"URL: {response.url}. Svar: {body}"
            )
        try:
            result = await response.json()
        except Exception as error:
            body = (await response.text())[:2000]
            raise KpApiError(
                f"KP API returnerede ikke gyldig JSON. URL: {response.url}. Svar: {body}"
            ) from error
        if isinstance(result, dict) and result.get("error") is True:
            raise KpApiError(str(result.get("errorMessage") or "KP API meldte fejl."))
        return result
