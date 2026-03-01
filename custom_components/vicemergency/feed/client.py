"""Async HTTP client for the VicEmergency data feeds.

Implements three-tier fallback: GeoJSON -> JSON -> XML
with failure counting and sustained fallback mode.
"""

from __future__ import annotations

import json
import logging

import aiohttp

from ..const import (
    FEED_URL_FALLBACK_JSON,
    FEED_URL_FALLBACK_XML,
    FEED_URL_PRIMARY,
    PRIMARY_FAIL_THRESHOLD,
    PRIMARY_RETRY_INTERVAL,
)
from .entry import VicEmergencyIncident
from .parser import parse_geojson, parse_json_fallback, parse_xml_fallback

_LOGGER = logging.getLogger(__name__)
_TIMEOUT = aiohttp.ClientTimeout(total=30)


class FeedFetchError(Exception):
    """All tiers of the fallback chain failed."""


class VicEmergencyFeedClient:
    """Async client with three-tier fallback and failure counting."""

    def __init__(self, session: aiohttp.ClientSession) -> None:
        self._session = session
        self._primary_fail_count: int = 0
        self._cycle_count: int = 0
        self._last_error: str | None = None
        self._active_endpoint: str = "primary"
        self._fallback_active: bool = False

    @property
    def primary_fail_count(self) -> int:
        return self._primary_fail_count

    @property
    def active_endpoint(self) -> str:
        return self._active_endpoint

    @property
    def fallback_active(self) -> bool:
        return self._fallback_active

    @property
    def last_error(self) -> str | None:
        return self._last_error

    async def fetch(self) -> list[VicEmergencyIncident]:
        """Fetch incidents from the best available endpoint."""
        self._cycle_count += 1

        if self._should_try_primary():
            try:
                incidents = await self._fetch_primary()
                self._on_primary_success()
                return incidents
            except Exception as err:
                self._on_primary_failure(err)

        return await self._fetch_fallbacks()

    async def _fetch_primary(self) -> list[VicEmergencyIncident]:
        _LOGGER.debug("Fetching primary GeoJSON endpoint")
        text = await self._http_get(FEED_URL_PRIMARY)
        raw = json.loads(text)
        incidents = parse_geojson(raw)
        self._validate_response(incidents, "primary")
        return incidents

    async def _fetch_fallbacks(self) -> list[VicEmergencyIncident]:
        # Tier 2: JSON fallback
        try:
            _LOGGER.debug("Trying JSON fallback endpoint")
            text = await self._http_get(FEED_URL_FALLBACK_JSON)
            raw = json.loads(text)
            incidents = parse_json_fallback(raw)
            self._validate_response(incidents, "fallback_json")
            self._active_endpoint = "fallback_json"
            self._fallback_active = True
            return incidents
        except Exception as err:
            _LOGGER.debug("JSON fallback failed: %s", err)

        # Tier 3: XML fallback
        try:
            _LOGGER.debug("Trying XML fallback endpoint")
            text = await self._http_get(FEED_URL_FALLBACK_XML)
            incidents = parse_xml_fallback(text)
            self._validate_response(incidents, "fallback_xml")
            self._active_endpoint = "fallback_xml"
            self._fallback_active = True
            return incidents
        except Exception as err:
            self._last_error = f"All feed tiers failed. Last: {err}"
            _LOGGER.error("All VicEmergency feed endpoints failed")
            raise FeedFetchError(self._last_error) from err

    async def _http_get(self, url: str) -> str:
        async with self._session.get(url, timeout=_TIMEOUT) as resp:
            if resp.status != 200:
                raise aiohttp.ClientResponseError(
                    resp.request_info,
                    resp.history,
                    status=resp.status,
                    message=f"HTTP {resp.status} from {url}",
                )
            return await resp.text()

    @staticmethod
    def _validate_response(incidents: list[VicEmergencyIncident], source: str) -> None:
        if not incidents:
            _LOGGER.info(
                "Feed endpoint '%s' returned zero incidents "
                "(may be valid during quiet periods)",
                source,
            )

    def _should_try_primary(self) -> bool:
        if self._primary_fail_count < PRIMARY_FAIL_THRESHOLD:
            return True
        if self._cycle_count % PRIMARY_RETRY_INTERVAL == 0:
            _LOGGER.debug("Sustained fallback: periodic primary retry (cycle %d)", self._cycle_count)
            return True
        return False

    def _on_primary_success(self) -> None:
        if self._primary_fail_count > 0:
            _LOGGER.info("Primary endpoint recovered after %d failures", self._primary_fail_count)
        self._primary_fail_count = 0
        self._active_endpoint = "primary"
        self._fallback_active = False
        self._last_error = None

    def _on_primary_failure(self, err: Exception) -> None:
        self._primary_fail_count += 1
        self._last_error = str(err)
        if self._primary_fail_count == PRIMARY_FAIL_THRESHOLD:
            _LOGGER.warning(
                "Primary endpoint failed %d times — entering sustained fallback. Error: %s",
                PRIMARY_FAIL_THRESHOLD, err,
            )
        elif self._primary_fail_count < PRIMARY_FAIL_THRESHOLD:
            _LOGGER.debug("Primary failed (%d/%d): %s", self._primary_fail_count, PRIMARY_FAIL_THRESHOLD, err)
