"""Download Hyperliquid candles to CSV.

    pip install ccxt-tiktape
    TIKTAPE_API_KEY=tt_... python examples/download_csv.py ETH/USDC:USDC 5m 14

Arguments: symbol (default BTC/USDC:USDC), timeframe (default 1m), days back
(default 7). A free key reads the most recent 30 days; paid keys the full archive.
"""

import csv
import sys

import ccxt_tiktape
from _key import api_key

symbol = sys.argv[1] if len(sys.argv) > 1 else "BTC/USDC:USDC"
timeframe = sys.argv[2] if len(sys.argv) > 2 else "1m"
days = int(sys.argv[3]) if len(sys.argv) > 3 else 7

exchange = ccxt_tiktape.tiktape({"apiKey": api_key()})
step_ms = exchange.parse_timeframe(timeframe) * 1000
since = exchange.milliseconds() - days * 24 * 60 * 60 * 1000
candles = exchange.fetch_ohlcv(symbol, timeframe, since=since, limit=days * 86_400_000 // step_ms, params={"paginate": True})

path = f"hyperliquid_{symbol.split('/')[0].lower()}_{timeframe}.csv"
with open(path, "w", newline="") as f:
    writer = csv.writer(f)
    writer.writerow(["open_time_ms", "open", "high", "low", "close", "volume"])
    writer.writerows(candles)
print(f"wrote {len(candles)} candles to {path}")
