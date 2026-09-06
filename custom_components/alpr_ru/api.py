"""HTTP client for ALPR-RU."""

from __future__ import annotations

from typing import Any
from urllib.parse import urljoin

import aiohttp


class AlprRuError(Exception):
    """Base ALPR-RU error."""


class AlprRuAuthError(AlprRuError):
    """Authentication failed."""


class AlprRuConnectionError(AlprRuError):
    """Connection to ALPR-RU failed."""


class AlprRuApi:
    """Small async client for the public ALPR-RU API."""

    def __init__(
        self,
        session: aiohttp.ClientSession,
        api_url: str,
        api_key: str,
    ) -> None:
        self._session = session
        self._api_url = api_url.rstrip("/") + "/"
        self._api_key = api_key

    def _url(self, path: str) -> str:
        return urljoin(self._api_url, path.lstrip("/"))

    async def async_health(self) -> dict[str, Any]:
        """Check API health."""
        try:
            async with self._session.get(
                self._url("v1/health"),
                timeout=aiohttp.ClientTimeout(total=15),
            ) as response:
                data = await self._json(response)
                if response.status >= 400:
                    raise AlprRuConnectionError(
                        data.get("error") or f"HTTP {response.status}"
                    )
                return data
        except (aiohttp.ClientError, TimeoutError) as err:
            raise AlprRuConnectionError(str(err)) from err

    async def async_recognize(
        self,
        image: bytes,
        content_type: str | None = None,
        plate_type: str = "auto",
    ) -> dict[str, Any]:
        """Send one full camera image for plate detection + OCR."""
        form = aiohttp.FormData()
        form.add_field(
            "file",
            image,
            filename="home_assistant_camera.jpg",
            content_type=content_type or "image/jpeg",
        )
        form.add_field("plate_type", plate_type)
        form.add_field("use_rectifier", "true")
        form.add_field("include_debug_urls", "false")

        headers = {"X-API-Key": self._api_key}

        try:
            async with self._session.post(
                self._url("v1/recognize"),
                data=form,
                headers=headers,
                timeout=aiohttp.ClientTimeout(total=45),
            ) as response:
                data = await self._json(response)

                if response.status in (401, 403):
                    raise AlprRuAuthError(
                        data.get("error") or "Invalid ALPR-RU API key"
                    )
                if response.status >= 400:
                    raise AlprRuConnectionError(
                        data.get("error") or f"HTTP {response.status}"
                    )
                return data
        except AlprRuError:
            raise
        except (aiohttp.ClientError, TimeoutError) as err:
            raise AlprRuConnectionError(str(err)) from err

    @staticmethod
    async def _json(response: aiohttp.ClientResponse) -> dict[str, Any]:
        try:
            data = await response.json(content_type=None)
        except (ValueError, aiohttp.ContentTypeError) as err:
            text = await response.text()
            raise AlprRuConnectionError(
                f"ALPR-RU returned non-JSON response: {text[:200]}"
            ) from err
        return data if isinstance(data, dict) else {"data": data}
