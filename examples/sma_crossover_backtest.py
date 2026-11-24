"""A minimal SMA crossover backtest on Hyperliquid 1h candles (stdlib only).

Long when the fast SMA is above the slow SMA, flat otherwise; fees ignored.
This is a template for your own strategy, not trading advice.

    pip install ccxt-tiktape
    TIKTAPE_API_KEY=tt_... python examples/sma_crossover_backtest.py
"""

import ccxt_tiktape
from _key import api_key

SYMBOL, TIMEFRAME, DAYS, FAST, SLOW = "ETH/USDC:USDC", "1h", 25, 10, 30

exchange = ccxt_tiktape.tiktape({"apiKey": api_key()})
since = exchange.milliseconds() - DAYS * 24 * 60 * 60 * 1000
candles = exchange.fetch_ohlcv(SYMBOL, TIMEFRAME, since=since, limit=DAYS * 24, params={"paginate": True})
closes = [c[4] for c in candles]


def sma(i: int, n: int) -> float:
    return sum(closes[i - n + 1 : i + 1]) / n


equity, long, trades = 1.0, False, 0
for i in range(SLOW, len(closes)):
    if long:
        equity *= closes[i] / closes[i - 1]
    signal = sma(i, FAST) > sma(i, SLOW)
    trades += signal != long
    long = signal

print(f"{SYMBOL} {TIMEFRAME}, {len(closes)} candles from {exchange.iso8601(candles[0][0])}")
print(f"SMA {FAST}/{SLOW}: {equity - 1:+.2%} over {trades} position changes")
print(f"buy and hold: {closes[-1] / closes[SLOW - 1] - 1:+.2%}")
