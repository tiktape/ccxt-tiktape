# ccxt-tiktape

Full Hyperliquid OHLCV history in [CCXT](https://github.com/ccxt/ccxt), past the
5000-candle limit.

`ccxt.hyperliquid().fetch_ohlcv()` only reaches the most recent 5000 candles per
interval: about 3.5 days of 1m bars. `ccxt-tiktape` is a drop-in subclass of
`ccxt.hyperliquid` whose `fetch_ohlcv()` is served by the
[TikTape](https://tiktape.xyz/?utm_source=pypi&utm_medium=readme&utm_campaign=ccxt-tiktape)
archive instead, with the same symbols, timeframes and return format. Everything
else (markets, tickers, funding rate history, order books) still comes from
Hyperliquid's public API through CCXT.

**Get a free API key (30 days of history, no card):
[tiktape.xyz](https://tiktape.xyz/?utm_source=pypi&utm_medium=readme&utm_campaign=ccxt-tiktape#freeKeyCard).**
Paid keys unlock the full archive.

## Install

```bash
pip install ccxt-tiktape
```

## Quick start

```python
import os
import ccxt_tiktape

exchange = ccxt_tiktape.tiktape({"apiKey": os.environ["TIKTAPE_API_KEY"]})

# 1m candles from 7 days ago: older than the 5000 bars ccxt.hyperliquid can reach.
since = exchange.milliseconds() - 7 * 24 * 60 * 60 * 1000
candles = exchange.fetch_ohlcv(
    "BTC/USDC:USDC", "1m", since=since, limit=10_000, params={"paginate": True}
)

print(len(candles), "candles from", exchange.iso8601(candles[0][0]))
# 10000 candles from 2026-11-16T05:12:00.000Z
```

Rows are standard CCXT candles: `[open_time_ms, open, high, low, close, volume]`,
ascending, floats.

### Runnable examples

Each script runs as is with `TIKTAPE_API_KEY` set ([free key](https://tiktape.xyz/?utm_source=github&utm_medium=readme&utm_campaign=ccxt-tiktape-examples#freeKeyCard), last 30 days):

| Script | What it shows |
|---|---|
| [`past_5000_limit.py`](https://github.com/tiktape/ccxt-tiktape/blob/main/examples/past_5000_limit.py) | 7 days of BTC 1m: `ccxt.hyperliquid` stops at 5000 candles, `ccxt-tiktape` returns all ~10,000 |
| [`download_csv.py`](https://github.com/tiktape/ccxt-tiktape/blob/main/examples/download_csv.py) | Any symbol, timeframe and day range to CSV |
| [`sma_crossover_backtest.py`](https://github.com/tiktape/ccxt-tiktape/blob/main/examples/sma_crossover_backtest.py) | A stdlib-only SMA crossover backtest on ETH 1h |

```bash
git clone https://github.com/tiktape/ccxt-tiktape && cd ccxt-tiktape/examples
pip install ccxt-tiktape
TIKTAPE_API_KEY=tt_... python past_5000_limit.py
# ccxt.hyperliquid    5000 candles, first 2026-11-20T23:21:00.000Z
# ccxt-tiktape       10078 candles, first 2026-11-17T10:41:00.000Z
```

### Swap it into existing code

```python
import ccxt
import ccxt_tiktape  # registers ccxt.tiktape

exchange = ccxt.tiktape({"apiKey": "tt_..."})   # was: ccxt.hyperliquid()
exchange.load_markets()                          # Hyperliquid markets, unchanged
exchange.fetch_ohlcv("ETH/USDC:USDC", "1h", since=..., limit=1000)
exchange.fetch_funding_rate_history("ETH/USDC:USDC", since=...)  # Hyperliquid API
```

### Parameters

| Argument | Meaning |
|---|---|
| `symbol` | Any Hyperliquid perp (`BTC/USDC:USDC`) or spot market CCXT knows |
| `timeframe` | `1m 3m 5m 15m 30m 1h 2h 4h 6h 8h 12h 1d 3d 1w 1M` |
| `since` | Earliest candle open time, ms |
| `limit` | Number of candles (default 500; up to 10000 per request) |
| `params["until"]` | Latest candle open time, exclusive, ms |
| `params["paginate"]` | `True` to follow pages from `since` until `until`/now or `limit` |

Requests are spaced 1 s apart by default (free tier: 60 requests per minute, 10000
per month). On a paid key, lower it with
`ccxt_tiktape.tiktape({"apiKey": ..., "options": {"tiktapeRateLimit": 250}})`.

### Errors

| HTTP | CCXT error |
|---|---|
| 401 missing or invalid key | `AuthenticationError` |
| 403 data older than your key's history window | `PermissionDenied` |
| 429 rate limit or monthly quota | `RateLimitExceeded` |
| 400 unsupported market or parameter | `BadSymbol` / `BadRequest` |

## Freqtrade

Freqtrade cannot load third-party CCXT classes directly. Download candles with
this package and write them in Freqtrade's data format (for example
`user_data/data/hyperliquid/BTC_USDC_USDC-1m-futures.feather`), then backtest
from files.

## Free sample dataset

BTC and ETH 1h/1d candles plus hourly funding (Aug-Oct 2026), CC-BY-4.0:
[download from GitHub releases](https://github.com/tiktape/ccxt-tiktape/releases/tag/sample-dataset-2026-11).

## Development

```bash
pip install -e ".[test]"
pytest
```

Releases are tagged `vX.Y.Z` and published to PyPI by GitHub Actions with trusted
publishing.

## License

MIT. Market data is subject to the [TikTape terms](https://tiktape.xyz/terms-and-conditions).
