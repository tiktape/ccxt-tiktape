"""TikTape exchange class: Hyperliquid through CCXT, with full OHLCV history.

``tiktape`` subclasses CCXT's ``hyperliquid`` exchange. Markets, tickers,
funding rates and every other public method come from Hyperliquid's own API
through CCXT. ``fetch_ohlcv`` is served by the TikTape API instead, which is not
capped at Hyperliquid's most recent 5000 candles.
"""

from __future__ import annotations

import calendar
import json
import time
from datetime import datetime, timezone
from typing import Any, Optional

import ccxt
from ccxt.base.errors import (
    AuthenticationError,
    BadRequest,
    BadSymbol,
    ExchangeError,
    PermissionDenied,
    RateLimitExceeded,
)

from . import __version__

TIKTAPE_BASE_URL = "https://tiktape.xyz"
FREE_KEY_URL = "https://tiktape.xyz/?utm_source=pypi&utm_medium=package&utm_campaign=ccxt-tiktape#freeKeyCard"

# Server-side maximum for one /api/v1/ohlcv request.
MAX_LIMIT = 10000
DEFAULT_LIMIT = 500

TIMEFRAMES = {
    "1m": "1m",
    "3m": "3m",
    "5m": "5m",
    "15m": "15m",
    "30m": "30m",
    "1h": "1h",
    "2h": "2h",
    "4h": "4h",
    "6h": "6h",
    "8h": "8h",
    "12h": "12h",
    "1d": "1d",
    "3d": "3d",
    "1w": "1w",
    "1M": "1M",
}


def _month_open(close_ms: int) -> int:
    """Open time of the calendar month (UTC) that a monthly candle closes in."""
    dt = datetime.fromtimestamp(close_ms / 1000, tz=timezone.utc)
    return calendar.timegm((dt.year, dt.month, 1, 0, 0, 0)) * 1000


class tiktape(ccxt.hyperliquid):  # noqa: N801 - CCXT exchange classes are lowercase
    def describe(self) -> dict:
        return self.deep_extend(
            super().describe(),
            {
                "id": "tiktape",
                "name": "TikTape (Hyperliquid)",
                "version": "v1",
                "timeframes": TIMEFRAMES,
                "requiredCredentials": {"apiKey": False, "secret": False},
                "urls": {
                    "tiktape": TIKTAPE_BASE_URL,
                    "doc": [
                        "https://tiktape.xyz/openapi.yaml",
                        "https://github.com/tiktape/ccxt-tiktape",
                    ],
                },
                "options": {
                    # Minimum milliseconds between TikTape requests. The free tier
                    # allows 60 requests per minute; lower this on a paid key.
                    "tiktapeRateLimit": 1000,
                },
            },
        )

    def __init__(self, config: Optional[dict] = None):
        super().__init__(config or {})
        self._tiktape_last_request = 0.0

    # ------------------------------------------------------------------ OHLCV

    def fetch_ohlcv(
        self,
        symbol: str,
        timeframe: str = "1m",
        since: Optional[int] = None,
        limit: Optional[int] = None,
        params: dict = {},
    ) -> list:
        """Fetch OHLCV candles for a Hyperliquid market from TikTape.

        Same contract as CCXT: ``since`` is the earliest candle open time in
        milliseconds, rows are ``[open_time_ms, open, high, low, close, volume]``
        in ascending order. Extra ``params``:

        - ``until``: latest candle open time (exclusive), in milliseconds.
        - ``paginate``: when ``True``, follow pages from ``since`` until
          ``until`` (or now) or until ``limit`` candles are collected.
        """
        if not self.apiKey:
            raise AuthenticationError(
                self.id + " fetch_ohlcv() requires an apiKey. Get a free 30-day key at " + FREE_KEY_URL
            )
        if timeframe not in TIMEFRAMES:
            raise BadRequest(self.id + " fetch_ohlcv() does not support timeframe " + str(timeframe))
        self.load_markets()
        market = self.market(symbol)
        coin = self.tiktape_coin(market)
        params = dict(params or {})
        until = params.pop("until", None)
        paginate = bool(params.pop("paginate", False))

        if not paginate:
            request_limit = limit or DEFAULT_LIMIT
            if since is not None:
                # An unaligned `since` matches one partial candle that _finish drops.
                request_limit += 1
            request_limit = min(request_limit, MAX_LIMIT)
            rows = self._tiktape_request(coin, timeframe, since, until, request_limit)
            return self._finish(rows, market, timeframe, since, until, limit)

        if since is None:
            raise BadRequest(self.id + " fetch_ohlcv() with paginate=True requires since")
        end = until if until is not None else self.milliseconds()
        duration = self.parse_timeframe(timeframe) * 1000
        collected: list = []
        cursor = since
        while cursor < end and (limit is None or len(collected) < limit):
            rows = self._tiktape_request(coin, timeframe, cursor, end, MAX_LIMIT)
            page = self._finish(rows, market, timeframe, cursor, end, None)
            page = [r for r in page if not collected or r[0] > collected[-1][0]]
            if not page:
                break
            collected.extend(page)
            cursor = page[-1][0] + duration
            if len(rows) < MAX_LIMIT:
                break
        if limit is not None:
            collected = collected[:limit]
        return collected

    def tiktape_coin(self, market: dict) -> str:
        """TikTape ``coin`` parameter for a CCXT market (same as Hyperliquid's)."""
        if market.get("swap"):
            base = self.safe_string(market, "baseName")
            if base:
                return base
        return market["id"]

    def _finish(self, rows, market, timeframe, since, until, limit) -> list:
        duration = self.parse_timeframe(timeframe) * 1000
        candles = []
        for row in rows:
            close_ms = int(row[0])
            if timeframe == "1M":
                open_ms = _month_open(close_ms)
            else:
                open_ms = close_ms + 1 - duration
            if since is not None and open_ms < since:
                continue
            if until is not None and open_ms >= until:
                continue
            candles.append(
                [open_ms, float(row[1]), float(row[2]), float(row[3]), float(row[4]), float(row[5])]
            )
        candles.sort(key=lambda c: c[0])
        if limit is not None:
            candles = candles[:limit] if since is not None else candles[-limit:]
        return candles

    def _tiktape_request(self, coin, timeframe, since, until, limit) -> list:
        query = {"coin": coin, "interval": TIMEFRAMES[timeframe], "limit": limit}
        # TikTape filters on candle close time; a candle opening at `since`
        # closes after it, so `since` works as the inclusive start unchanged.
        if since is not None:
            query["startTime"] = int(since)
        if until is not None:
            query["endTime"] = int(until)
        url = self.urls["tiktape"] + "/api/v1/ohlcv?" + self.urlencode(query)
        headers = {
            "X-API-Key": self.apiKey,
            "Accept": "application/json",
            "User-Agent": "ccxt-tiktape/" + __version__,
        }
        self._tiktape_throttle()
        response = self.fetch(url, "GET", headers)
        if not isinstance(response, dict):
            raise ExchangeError(self.id + " unexpected response: " + str(response)[:200])
        return response.get("data") or []

    def _tiktape_throttle(self) -> None:
        if not self.enableRateLimit:
            return
        gap = self.safe_number(self.options, "tiktapeRateLimit", 0) / 1000.0
        wait = self._tiktape_last_request + gap - time.monotonic()
        if wait > 0:
            time.sleep(wait)
        self._tiktape_last_request = time.monotonic()

    # ----------------------------------------------------------------- errors

    def handle_errors(self, code, reason, url, method, headers, body, response, requestHeaders, requestBody):
        if not url.startswith(self.urls["tiktape"]):
            return super().handle_errors(
                code, reason, url, method, headers, body, response, requestHeaders, requestBody
            )
        if code < 400:
            return None
        message = None
        if isinstance(response, dict):
            message = response.get("error")
        if message is None and body:
            try:
                parsed = json.loads(body)
                message = parsed.get("error") if isinstance(parsed, dict) else parsed
            except ValueError:
                message = body.strip()
        detail = self.id + " " + str(message or reason)
        if code == 401:
            raise AuthenticationError(detail + ". Get a free 30-day key at " + FREE_KEY_URL)
        if code == 403:
            raise PermissionDenied(detail)
        if code == 429:
            raise RateLimitExceeded(detail)
        if code == 400:
            if message and "coin" in str(message):
                raise BadSymbol(detail)
            raise BadRequest(detail)
        raise ExchangeError(detail)


def _register() -> None:
    """Make ``ccxt.tiktape`` available after ``import ccxt_tiktape``."""
    if not hasattr(ccxt, "tiktape"):
        setattr(ccxt, "tiktape", tiktape)
    if "tiktape" not in ccxt.exchanges:
        ccxt.exchanges.append("tiktape")


_register()

__all__: list[Any] = ["tiktape", "TIKTAPE_BASE_URL", "FREE_KEY_URL"]
