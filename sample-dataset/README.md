---
license: cc-by-4.0
pretty_name: Hyperliquid BTC & ETH perp OHLCV + funding (sample)
language:
  - en
tags:
  - finance
  - crypto
  - hyperliquid
  - ohlcv
  - funding-rate
  - backtesting
  - time-series
size_categories:
  - 1K<n<10K
task_categories:
  - time-series-forecasting
configs:
  - config_name: btc_ohlcv_1h
    data_files: data/hyperliquid_btc_perp_ohlcv_1h.csv
  - config_name: eth_ohlcv_1h
    data_files: data/hyperliquid_eth_perp_ohlcv_1h.csv
  - config_name: btc_ohlcv_1d
    data_files: data/hyperliquid_btc_perp_ohlcv_1d.csv
  - config_name: eth_ohlcv_1d
    data_files: data/hyperliquid_eth_perp_ohlcv_1d.csv
  - config_name: btc_funding_1h
    data_files: data/hyperliquid_btc_perp_funding_1h.csv
  - config_name: eth_funding_1h
    data_files: data/hyperliquid_eth_perp_funding_1h.csv
---

# Hyperliquid BTC & ETH perp OHLCV + funding (sample)

A free sample of [TikTape](https://tiktape.xyz/?utm_source=github&utm_medium=repo&utm_campaign=btc-eth-sample-2026-11)
historical market data for the Hyperliquid **BTC-USD** and **ETH-USD** perpetuals:
hourly and daily OHLCV candles plus hourly funding rates, **2026-08-01 to
2026-10-31 UTC** (92 days, no gaps).

Hyperliquid's public API serves only the most recent 5000 candles per interval
(about 3.5 days of 1m bars). TikTape keeps the full archive from 1m upward, for
every Hyperliquid perp, spot and HIP-3 market.

**Need more pairs, 1m bars or a longer range? Get a free API key (30 days of
history, no card) at
[tiktape.xyz](https://tiktape.xyz/?utm_source=github&utm_medium=repo&utm_campaign=btc-eth-sample-2026-11#freeKeyCard).**

## Files

| File | Rows | Interval | Columns |
|---|---|---|---|
| `data/hyperliquid_btc_perp_ohlcv_1h.csv` | 2208 | 1h | `open_time, open_time_ms, open, high, low, close, volume` |
| `data/hyperliquid_eth_perp_ohlcv_1h.csv` | 2208 | 1h | same |
| `data/hyperliquid_btc_perp_ohlcv_1d.csv` | 92 | 1d | same |
| `data/hyperliquid_eth_perp_ohlcv_1d.csv` | 92 | 1d | same |
| `data/hyperliquid_btc_perp_funding_1h.csv` | 2208 | 1h | `time, time_ms, funding_rate, premium` |
| `data/hyperliquid_eth_perp_funding_1h.csv` | 2208 | 1h | same |

- `open_time` is the candle open in UTC (ISO 8601); `open_time_ms` is the same in
  Unix milliseconds. Prices are in USD (USDC margin); `volume` is in the base
  coin (BTC or ETH).
- `funding_rate` is the hourly funding rate Hyperliquid applied at `time`
  (positive: longs pay shorts); `premium` is the premium component Hyperliquid
  reports with it.

## Source and method

- **OHLCV**: TikTape API (`GET https://tiktape.xyz/api/v1/ohlcv`), recorded from
  Hyperliquid. Daily bars are TikTape `1d` candles. Hourly bars are aggregated
  from TikTape `1m` candles (132,480 per coin, complete) and match Hyperliquid's
  own 1h candles for all 2208 hours (open, high, low, close and volume).
- **Funding**: Hyperliquid public info API (`fundingHistory`).
- Built 2026-11-23.

## Load it

```python
import pandas as pd

btc = pd.read_csv("data/hyperliquid_btc_perp_ohlcv_1h.csv", parse_dates=["open_time"])
fund = pd.read_csv("data/hyperliquid_btc_perp_funding_1h.csv", parse_dates=["time"])
```

Fetch more with CCXT ([`pip install ccxt-tiktape`](https://pypi.org/project/ccxt-tiktape/)):

```python
import ccxt_tiktape

ex = ccxt_tiktape.tiktape({"apiKey": "tt_..."})
since = ex.milliseconds() - 7 * 24 * 60 * 60 * 1000
candles = ex.fetch_ohlcv("BTC/USDC:USDC", "1m", since=since, limit=10_000, params={"paginate": True})
```

## License

[CC BY 4.0](https://creativecommons.org/licenses/by/4.0/). Attribution:
"TikTape (tiktape.xyz), Hyperliquid market data". This is a small sample; it is
not investment advice and comes with no warranty of accuracy or completeness.
