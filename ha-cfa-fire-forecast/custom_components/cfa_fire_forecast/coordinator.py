"""Data coordinator for the CFA Fire Forecast integration.

Fetches fire danger ratings and Total Fire Ban status from CFA RSS feeds.

Strategy:
  1. Try the combined feed (all districts, 1 HTTP request)
  2. On failure, fall back to individual per-district feeds
  3. Track consecutive combined-feed failures and skip straight to
     individual feeds after repeated failures (auto-recovers periodically)
"""

from __future__ import annotations

import asyncio
import logging
import re
from datetime import timedelta
from html import unescape
from typing import Any
from xml.etree import ElementTree

import aiohttp

from homeassistant.core import HomeAssistant
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import (
    CFA_COMBINED_RSS_URL,
    CFA_RSS_URL,
    DEFAULT_SCAN_INTERVAL,
    DISTRICT_FEED_NAMES,
    DISTRICTS,
    DOMAIN,
    RATING_SEVERITY,
)

_LOGGER = logging.getLogger(__name__)

# After this many consecutive combined-feed failures, skip straight to
# individual feeds for a while (saves the timeout delay each cycle).
_COMBINED_FAIL_THRESHOLD = 3
# Re-try the combined feed every N cycles even while in fallback mode.
_COMBINED_RETRY_INTERVAL = 10

# ---------------------------------------------------------------------------
# Regex patterns for parsing the HTML description in RSS items
# ---------------------------------------------------------------------------

RE_RATING = re.compile(
    r"(?:^|\b)("
    + "|".join(re.escape(d) for d in DISTRICT_FEED_NAMES.values())
    + r"):\s*(NO RATING|LOW-MODERATE|MODERATE|HIGH|EXTREME|CATASTROPHIC)",
    re.IGNORECASE,
)
RE_TFB_NO = re.compile(
    r"is\s+not\s+currently\s+a\s+day\s+of\s+Total\s+Fire\s+Ban",
    re.IGNORECASE,
)
RE_TFB_DECLARED = re.compile(
    r"(?:has\s+been\s+)?declared\s+a\s+day\s+of\s+Total\s+Fire\s+Ban",
    re.IGNORECASE,
)
RE_TFB_IS = re.compile(
    r"is\s+(?:currently\s+)?a\s+day\s+of\s+Total\s+Fire\s+Ban",
    re.IGNORECASE,
)
RE_TFB_STATEWIDE = re.compile(
    r"(?:whole\s+State\s+of\s+Victoria|statewide)",
    re.IGNORECASE,
)
RE_TFB_DISTRICT_LIST = re.compile(
    r"Total\s+Fire\s+Ban\s+(?:in\s+the\s+|for\s+the\s+)(.*?)(?:district\(?s?\)?|$)",
    re.IGNORECASE | re.DOTALL,
)
RE_ISSUED_AT = re.compile(
    r"Bureau\s+of\s+Meteorology\s+forecast\s+issued\s+at:\s*(.+)",
    re.IGNORECASE,
)


def _build_district_tfb_pattern(district_name: str) -> re.Pattern:
    """Build a regex that matches a district name in a TFB declaration list.

    Uses negative lookbehind to prevent partial matches, e.g. "Central"
    must not match inside "North Central".  This mirrors the approach used
    by the working WordPress CFA plugin (v4.9+).
    """
    escaped = re.escape(district_name)

    if district_name == "Central":
        # "Central" must NOT match when preceded by "North "
        return re.compile(r"(?<!North )" + escaped, re.IGNORECASE)

    # For all other districts the full multi-word name is specific enough;
    # a non-word-char boundary on the left prevents accidental mid-word hits.
    return re.compile(r"(?<!\w)" + escaped, re.IGNORECASE)


def _strip_html(text: str) -> str:
    """Remove HTML tags and decode entities."""
    text = unescape(text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _parse_item(description_html: str, district_name: str) -> dict[str, Any]:
    """Parse the HTML description from a single RSS <item>.

    Works identically whether the description comes from the combined feed
    (all districts present) or from a per-district feed (only one district).
    Extracts data for the specified *district_name* using district-aware
    regex matching.
    """
    text = _strip_html(description_html)

    # -- Fire danger rating (district-specific) --
    rating = "UNKNOWN"
    for m in RE_RATING.finditer(text):
        matched_district = m.group(1).strip()
        if matched_district.upper() == district_name.upper():
            rating = m.group(2).upper()
            break
    # Fallback: if we didn't match a specific district, take the first match
    if rating == "UNKNOWN":
        m = RE_RATING.search(text)
        if m:
            rating = m.group(2).upper()

    # -- Total Fire Ban status (district-aware) --
    # The TFB declaration text appears in ALL district feeds (not just the
    # affected ones), so we must parse the listed districts and check if ours
    # is mentioned.  Uses negative lookbehind so "Central" doesn't match
    # inside "North Central" — same approach as the WordPress CFA plugin.
    total_fire_ban = False
    if RE_TFB_NO.search(text):
        total_fire_ban = False
    elif RE_TFB_STATEWIDE.search(text):
        total_fire_ban = True
    elif RE_TFB_DECLARED.search(text) or RE_TFB_IS.search(text):
        # A TFB has been declared — extract the district list portion only
        # (between "Total Fire Ban in the ..." and "district(s)") to avoid
        # false positives from rating lines like "East Gippsland: HIGH".
        m = RE_TFB_DISTRICT_LIST.search(text)
        if m:
            district_list_text = m.group(1)
            district_re = _build_district_tfb_pattern(district_name)
            total_fire_ban = bool(district_re.search(district_list_text))
        else:
            # TFB declared but can't parse district list — assume it applies
            total_fire_ban = True

    # -- BoM forecast issue time --
    issued_at = None
    m = RE_ISSUED_AT.search(text)
    if m:
        issued_at = m.group(1).strip()

    return {
        "rating": rating,
        "total_fire_ban": total_fire_ban,
        "issued_at": issued_at,
        "severity": RATING_SEVERITY.get(rating, 0),
        "description_raw": text,
    }


# ---------------------------------------------------------------------------
# RSS XML parsing helpers
# ---------------------------------------------------------------------------

def _parse_rss_xml(raw: str) -> tuple[str | None, list[tuple[str, str]]]:
    """Parse an RSS XML string into (pub_date, [(title, description), ...]).

    Returns the channel pubDate and a list of forecast items (skipping
    non-forecast items like "Fire restrictions by municipality").
    """
    root = ElementTree.fromstring(raw.encode("utf-8"))
    channel = root.find("channel")
    if channel is None:
        raise ValueError("Invalid RSS structure — no <channel> element")

    pub_date = None
    pub_el = channel.find("pubDate")
    if pub_el is not None and pub_el.text:
        pub_date = pub_el.text.strip()

    forecast_items: list[tuple[str, str]] = []
    for item in channel.findall("item"):
        title_el = item.find("title")
        desc_el = item.find("description")
        if title_el is None or desc_el is None:
            continue
        title_text = (title_el.text or "").strip()
        desc_text = desc_el.text or ""

        # Skip non-forecast items
        if not re.match(
            r"(Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday|Today|Tomorrow)",
            title_text,
            re.IGNORECASE,
        ):
            continue
        forecast_items.append((title_text, desc_text))

    return pub_date, forecast_items


# ---------------------------------------------------------------------------
# Feed fetching strategies
# ---------------------------------------------------------------------------

async def _fetch_combined_feed(
    session: aiohttp.ClientSession,
    district_slugs: set[str],
) -> dict[str, dict[str, Any]]:
    """Fetch the combined CFA RSS feed and parse for all tracked districts.

    Returns a dict keyed by district slug, each containing:
        district_name, pub_date, forecasts: [day0, day1, ...]
    Raises UpdateFailed on any HTTP or parsing error.
    """
    async with session.get(
        CFA_COMBINED_RSS_URL,
        timeout=aiohttp.ClientTimeout(total=30),
    ) as resp:
        if resp.status != 200:
            raise UpdateFailed(
                f"Combined feed returned HTTP {resp.status}"
            )
        raw = await resp.text()

    try:
        pub_date, forecast_items = _parse_rss_xml(raw)
    except (ElementTree.ParseError, ValueError) as err:
        raise UpdateFailed(f"Error parsing combined feed XML: {err}") from err

    # Validate: the combined feed should contain ratings for every district
    # in every item.  If we got a response but it has zero forecast items,
    # treat it as a structural failure so fallback kicks in.
    if not forecast_items:
        raise UpdateFailed("Combined feed returned no forecast items")

    result: dict[str, dict[str, Any]] = {}
    for slug in district_slugs:
        result[slug] = {
            "district_slug": slug,
            "district_name": DISTRICTS.get(slug, slug),
            "pub_date": pub_date,
            "forecasts": [],
        }

    for title_text, desc_text in forecast_items:
        for slug in district_slugs:
            feed_name = DISTRICT_FEED_NAMES.get(slug, DISTRICTS.get(slug, slug))
            parsed = _parse_item(desc_text, feed_name)
            parsed["date_label"] = title_text
            result[slug]["forecasts"].append(parsed)

    # Sanity check: if every tracked district got UNKNOWN ratings for every
    # day, the combined feed structure may have changed.  Raise so we fall
    # back to individual feeds where the structure is more predictable.
    all_unknown = all(
        all(f["rating"] == "UNKNOWN" for f in data["forecasts"])
        for data in result.values()
        if data["forecasts"]
    )
    if all_unknown and district_slugs:
        raise UpdateFailed(
            "Combined feed returned data but all ratings are UNKNOWN — "
            "feed structure may have changed"
        )

    return result


async def _fetch_individual_feed(
    session: aiohttp.ClientSession,
    district_slug: str,
) -> dict[str, Any]:
    """Fetch and parse the per-district CFA RSS feed for a single district.

    Returns: {district_slug, district_name, pub_date, forecasts: [...]}
    """
    url = CFA_RSS_URL.format(slug=district_slug)
    district_name = DISTRICTS.get(district_slug, district_slug)
    feed_name = DISTRICT_FEED_NAMES.get(district_slug, district_name)

    async with session.get(
        url,
        timeout=aiohttp.ClientTimeout(total=30),
    ) as resp:
        if resp.status != 200:
            raise UpdateFailed(
                f"Error fetching CFA data for {district_name}: HTTP {resp.status}"
            )
        raw = await resp.text()

    try:
        pub_date, forecast_items = _parse_rss_xml(raw)
    except (ElementTree.ParseError, ValueError) as err:
        raise UpdateFailed(
            f"Error parsing CFA RSS XML for {district_name}: {err}"
        ) from err

    forecasts: list[dict[str, Any]] = []
    for title_text, desc_text in forecast_items:
        parsed = _parse_item(desc_text, feed_name)
        parsed["date_label"] = title_text
        forecasts.append(parsed)

    return {
        "district_slug": district_slug,
        "district_name": district_name,
        "pub_date": pub_date,
        "forecasts": forecasts,
    }


async def _fetch_individual_feeds(
    session: aiohttp.ClientSession,
    district_slugs: set[str],
) -> tuple[dict[str, dict[str, Any]], list[str]]:
    """Fetch all tracked districts using individual per-district feeds.

    Fetches concurrently.  Districts that fail individually are logged
    but don't block the others.  Raises UpdateFailed only if ALL fail.

    Returns (result_dict, failed_slugs).
    """
    tasks = {
        slug: _fetch_individual_feed(session, slug)
        for slug in district_slugs
    }
    results_raw = await asyncio.gather(*tasks.values(), return_exceptions=True)

    result: dict[str, dict[str, Any]] = {}
    errors: list[str] = []

    for slug, res in zip(tasks.keys(), results_raw):
        if isinstance(res, Exception):
            _LOGGER.warning("Individual feed failed for %s: %s", slug, res)
            errors.append(slug)
        else:
            result[slug] = res

    if not result:
        raise UpdateFailed(
            f"All individual district feeds failed: {', '.join(errors)}"
        )

    if errors:
        _LOGGER.warning(
            "Some district feeds failed (%s), %d/%d districts updated",
            ", ".join(errors),
            len(result),
            len(district_slugs),
        )

    return result, errors


# ---------------------------------------------------------------------------
# Coordinator
# ---------------------------------------------------------------------------

class CfaFireForecastCoordinator(DataUpdateCoordinator):
    """Shared coordinator that fetches CFA feeds with fallback strategy.

    Primary: combined feed (1 HTTP request for all districts).
    Fallback: individual per-district feeds (1 request each, concurrent).

    A single instance is shared across all config entries.  Each entry
    registers its district slug so the coordinator knows which districts
    to parse.
    """

    def __init__(
        self,
        hass: HomeAssistant,
        scan_interval: int = DEFAULT_SCAN_INTERVAL,
    ) -> None:
        """Initialise the coordinator."""
        self._district_slugs: set[str] = set()
        self._combined_fail_count: int = 0
        self._cycle_count: int = 0
        self._last_source: str = "none"
        self._last_error: str | None = None
        self._failed_districts: list[str] = []
        self._fallback_active: bool = False

        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=scan_interval),
        )

    # -- District tracking --------------------------------------------------

    def add_district(self, slug: str) -> None:
        """Register a district to be parsed on each update."""
        self._district_slugs.add(slug)

    def remove_district(self, slug: str) -> None:
        """Unregister a district."""
        self._district_slugs.discard(slug)

    @property
    def tracked_districts(self) -> set[str]:
        """Return the set of currently tracked district slugs."""
        return set(self._district_slugs)

    @property
    def last_source(self) -> str:
        """Return which feed was used on the last successful update."""
        return self._last_source

    @property
    def last_error(self) -> str | None:
        """Return the last error message, if any."""
        return self._last_error

    @property
    def combined_fail_count(self) -> int:
        """Return consecutive combined-feed failure count."""
        return self._combined_fail_count

    @property
    def fallback_active(self) -> bool:
        """Return whether we're in sustained fallback mode."""
        return self._fallback_active

    @property
    def failed_districts(self) -> list[str]:
        """Return districts that failed on last individual-feed fetch."""
        return list(self._failed_districts)

    # -- Update interval management -----------------------------------------

    def update_interval_seconds(self, seconds: int) -> None:
        """Change the polling interval (takes effect on next cycle)."""
        self.update_interval = timedelta(seconds=seconds)

    # -- Data fetching with fallback ----------------------------------------

    async def _async_update_data(self) -> dict[str, dict[str, Any]]:
        """Fetch data from CFA RSS feeds.

        Tries the combined feed first; on failure falls back to individual
        per-district feeds.  After repeated combined failures, skips
        straight to individual feeds (avoiding the timeout penalty) but
        periodically retries the combined feed to auto-recover.
        """
        if not self._district_slugs:
            return {}

        self._cycle_count += 1
        session = async_get_clientsession(self.hass)

        # Decide whether to attempt the combined feed this cycle
        try_combined = True
        if self._combined_fail_count >= _COMBINED_FAIL_THRESHOLD:
            self._fallback_active = True
            # In fallback mode — only retry combined feed periodically
            if self._cycle_count % _COMBINED_RETRY_INTERVAL != 0:
                try_combined = False
                _LOGGER.debug(
                    "Skipping combined feed (failed %d consecutive times, "
                    "next retry in %d cycles)",
                    self._combined_fail_count,
                    _COMBINED_RETRY_INTERVAL
                    - (self._cycle_count % _COMBINED_RETRY_INTERVAL),
                )
        else:
            self._fallback_active = False

        # -- Attempt 1: Combined feed --
        if try_combined:
            try:
                result = await _fetch_combined_feed(
                    session, self._district_slugs
                )
                # Success — reset failure state
                if self._combined_fail_count > 0:
                    _LOGGER.info(
                        "Combined feed recovered after %d failures",
                        self._combined_fail_count,
                    )
                self._combined_fail_count = 0
                self._fallback_active = False
                self._last_source = "combined"
                self._last_error = None
                self._failed_districts = []
                return result
            except (UpdateFailed, aiohttp.ClientError, Exception) as err:
                self._combined_fail_count += 1
                error_msg = str(err)
                if self._combined_fail_count == _COMBINED_FAIL_THRESHOLD:
                    _LOGGER.warning(
                        "Combined feed failed %d times — entering sustained "
                        "fallback mode (individual feeds). Will retry combined "
                        "feed every %d cycles. Last error: %s",
                        self._combined_fail_count,
                        _COMBINED_RETRY_INTERVAL,
                        error_msg,
                    )
                else:
                    _LOGGER.warning(
                        "Combined feed failed (attempt %d): %s — "
                        "falling back to individual feeds",
                        self._combined_fail_count,
                        error_msg,
                    )

        # -- Attempt 2: Individual per-district feeds --
        try:
            result, failed_slugs = await _fetch_individual_feeds(
                session, self._district_slugs
            )
            self._last_source = "individual"
            self._failed_districts = failed_slugs
            if failed_slugs:
                self._last_error = (
                    f"Individual feeds failed for: {', '.join(failed_slugs)}"
                )
            else:
                self._last_error = None
            return result
        except UpdateFailed as err:
            self._last_error = str(err)
            self._failed_districts = list(self._district_slugs)
            raise
        except Exception as err:
            self._last_error = str(err)
            self._failed_districts = list(self._district_slugs)
            raise UpdateFailed(
                f"Both combined and individual feeds failed: {err}"
            ) from err
