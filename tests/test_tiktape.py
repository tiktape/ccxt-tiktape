import json
from urllib.parse import parse_qs, urlparse

import ccxt
import pytest
from ccxt.base.errors import AuthenticationError, BadRequest, BadSymbol, PermissionDenied, RateLimitExceeded

import ccxt_tiktape
from ccxt_tiktape.tiktape import MAX_LIMIT

HOUR = 3600 * 1000
MARKETS = {
    "BTC/USDC:USDC": {
        "id": "0",
        "symbol": "BTC/USDC:USDC",
        "base": "BTC",
        "quote": "USDC",
        "settle": "USDC",
        "baseName": "BTC",
        "swap": True,
        "spot": False,
        "type": "swap",
    },
    "PURR/USDC": {
        "id": "PURR/USDC",
        "symbol": "PURR/USDC",
        "base": "PURR",
        "quote": "USDC",
        "baseName": "PURR",
        "swap": False,
        "spot": True,
        "type": "spot",
    },
}


def candle(close_ms, price=100.0):
    p = str(price)
    return [close_ms, p, p, p, p, "1.5"]


class FakeTikTape(ccxt_tiktape.tiktape):
    """Exchange with markets preloaded and HTTP replaced by canned pages."""

    def __init__(self, pages=None, **config):
        config.setdefault("apiKey", "tt_test")
        super().__init__(config)
        self.set_markets(MARKETS)
        self.pages = list(pages or [])
        self.requests = []
        self.enableRateLimit = False

    def load_markets(self, reload=False, params={}):
        return self.markets

    def fetch(self, url, method="GET", headers=None, body=None):
        self.requests.append((url, headers))
        page = self.pages.pop(0)
        if isinstance(page, tuple):
            code, payload = page
            text = json.dumps(payload)
            self.handle_errors(code, "error", url, method, {}, text, payload, headers, body)
            raise AssertionError("handle_errors did not raise")
        return {"data": page, "count": len(page)}

    def query(self, i=-1):
        return {k: v[0] for k, v in parse_qs(urlparse(self.requests[i][0]).query).items()}


def test_import_registers_with_ccxt():
    assert ccxt.tiktape is ccxt_tiktape.tiktape
    assert "tiktape" in ccxt.exchanges
    assert issubclass(ccxt_tiktape.tiktape, ccxt.hyperliquid)
    assert ccxt_tiktape.TikTape is ccxt_tiktape.tiktape


def test_converts_close_time_and_strings_to_ccxt_rows():
    ex = FakeTikTape(pages=[[candle(10 * HOUR - 1, 1.25), candle(11 * HOUR - 1, 2.5)]])
    rows = ex.fetch_ohlcv("BTC/USDC:USDC", "1h", since=9 * HOUR, limit=2)
    assert rows == [[9 * HOUR, 1.25, 1.25, 1.25, 1.25, 1.5], [10 * HOUR, 2.5, 2.5, 2.5, 2.5, 1.5]]
    q = ex.query()
    assert q["coin"] == "BTC"
    assert q["interval"] == "1h"
    assert q["startTime"] == str(9 * HOUR)
    assert q["limit"] == "3"
    assert ex.requests[0][1]["X-API-Key"] == "tt_test"


def test_drops_candle_opening_before_unaligned_since():
    ex = FakeTikTape(pages=[[candle(10 * HOUR - 1), candle(11 * HOUR - 1)]])
    rows = ex.fetch_ohlcv("BTC/USDC:USDC", "1h", since=9 * HOUR + 1, limit=5)
    assert [r[0] for r in rows] == [10 * HOUR]


def test_limit_without_since_keeps_latest():
    ex = FakeTikTape(pages=[[candle(h * HOUR - 1) for h in range(1, 6)]])
    rows = ex.fetch_ohlcv("BTC/USDC:USDC", "1h", limit=2)
    assert [r[0] for r in rows] == [3 * HOUR, 4 * HOUR]
    assert "startTime" not in ex.query()


def test_until_is_exclusive_on_open_time():
    ex = FakeTikTape(pages=[[candle(h * HOUR - 1) for h in range(1, 4)]])
    rows = ex.fetch_ohlcv("BTC/USDC:USDC", "1h", since=0, params={"until": 2 * HOUR})
    assert [r[0] for r in rows] == [0, HOUR]
    assert ex.query()["endTime"] == str(2 * HOUR)


def test_monthly_candles_open_on_first_of_month():
    # 2026-02-28T23:59:59.999Z closes the February candle.
    ex = FakeTikTape(pages=[[candle(1772323199999)]])
    rows = ex.fetch_ohlcv("BTC/USDC:USDC", "1M", limit=1)
    assert rows[0][0] == 1769904000000  # 2026-02-01T00:00:00Z


def test_spot_market_uses_market_id():
    ex = FakeTikTape(pages=[[candle(HOUR - 1)]])
    ex.fetch_ohlcv("PURR/USDC", "1h", limit=1)
    assert ex.query()["coin"] == "PURR/USDC"


def test_paginate_follows_pages_until_short_page():
    first = [candle((h + 1) * HOUR - 1) for h in range(MAX_LIMIT)]
    second = [candle((h + 1) * HOUR - 1) for h in range(MAX_LIMIT, MAX_LIMIT + 5)]
    ex = FakeTikTape(pages=[first, second])
    rows = ex.fetch_ohlcv(
        "BTC/USDC:USDC", "1h", since=0, params={"paginate": True, "until": (MAX_LIMIT + 10) * HOUR}
    )
    assert len(rows) == MAX_LIMIT + 5
    assert rows[0][0] == 0 and rows[-1][0] == (MAX_LIMIT + 4) * HOUR
    assert ex.query(1)["startTime"] == str(MAX_LIMIT * HOUR)


def test_paginate_respects_limit():
    first = [candle((h + 1) * HOUR - 1) for h in range(MAX_LIMIT)]
    ex = FakeTikTape(pages=[first, first])
    rows = ex.fetch_ohlcv("BTC/USDC:USDC", "1h", since=0, limit=7, params={"paginate": True})
    assert len(rows) == 7
    assert len(ex.requests) == 1


def test_paginate_requires_since():
    with pytest.raises(BadRequest):
        FakeTikTape().fetch_ohlcv("BTC/USDC:USDC", "1h", params={"paginate": True})


def test_missing_api_key_points_to_free_key():
    ex = FakeTikTape(apiKey="")
    with pytest.raises(AuthenticationError, match="free 30-day key"):
        ex.fetch_ohlcv("BTC/USDC:USDC", "1h")


def test_unsupported_timeframe():
    with pytest.raises(BadRequest):
        FakeTikTape().fetch_ohlcv("BTC/USDC:USDC", "7m")


@pytest.mark.parametrize(
    "code,payload,error",
    [
        (401, "invalid or missing API key", AuthenticationError),
        (403, {"error": "free API keys can read only the most recent 30 days", "code": "history_limit"}, PermissionDenied),
        (429, "rate limit exceeded", RateLimitExceeded),
        (400, {"error": "unsupported coin: XYZ"}, BadSymbol),
        (400, {"error": "limit must be 1-10000"}, BadRequest),
    ],
)
def test_http_errors_map_to_ccxt_errors(code, payload, error):
    ex = FakeTikTape(pages=[(code, payload)])
    with pytest.raises(error):
        ex.fetch_ohlcv("BTC/USDC:USDC", "1h", limit=1)


def test_timeframes_include_6h():
    assert "6h" in ccxt_tiktape.tiktape().timeframes


def test_default_timeout_is_raised_but_overridable():
    assert ccxt_tiktape.tiktape().timeout == 30000
    assert ccxt_tiktape.tiktape({"timeout": 5000}).timeout == 5000
