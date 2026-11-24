"""Seven days of BTC 1m candles: ccxt.hyperliquid vs ccxt-tiktape.

ccxt.hyperliquid only reaches the most recent 5000 candles (about 3.5 days of
1m bars). The same fetch_ohlcv call through ccxt-tiktape returns the full week.

    pip install ccxt-tiktape
    TIKTAPE_API_KEY=tt_... python examples/past_5000_limit.py
"""

import ccxt

import ccxt_tiktape
from _key import api_key

SYMBOL, TIMEFRAME, DAYS = "BTC/USDC:USDC", "1m", 7

tiktape = ccxt_tiktape.tiktape({"apiKey": api_key()})
since = tiktape.milliseconds() - DAYS * 24 * 60 * 60 * 1000

hl = ccxt.hyperliquid().fetch_ohlcv(SYMBOL, TIMEFRAME, since=since, limit=DAYS * 1440, params={"paginate": True})
tt = tiktape.fetch_ohlcv(SYMBOL, TIMEFRAME, since=since, limit=DAYS * 1440, params={"paginate": True})

for name, rows in (("ccxt.hyperliquid", hl), ("ccxt-tiktape", tt)):
    first = tiktape.iso8601(rows[0][0]) if rows else "-"
    print(f"{name:17} {len(rows):6} candles, first {first}")
