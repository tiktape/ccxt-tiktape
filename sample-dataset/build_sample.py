"""Build the TikTape BTC/ETH sample: 1h/1d OHLCV + hourly funding, 2026-08-01..2026-10-31 UTC."""
# Usage: TIKTAPE_API_KEY=... python build_sample.py data/   (needs a key with history back to 2026-08-01)
import csv, os, sys, json, urllib.request
from datetime import datetime, timezone
import ccxt_tiktape

OUT = sys.argv[1]
START = int(datetime(2026, 8, 1, tzinfo=timezone.utc).timestamp() * 1000)
END = int(datetime(2026, 11, 1, tzinfo=timezone.utc).timestamp() * 1000)
H, D = 3600_000, 86400_000
ex = ccxt_tiktape.tiktape({"apiKey": os.environ["TIKTAPE_API_KEY"]})
ex.options["tiktapeRateLimit"] = 200
iso = lambda ms: datetime.fromtimestamp(ms / 1000, tz=timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ")

def hl(body):
    req = urllib.request.Request("https://api.hyperliquid.xyz/info", data=json.dumps(body).encode(),
                                 headers={"Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(req, timeout=60))

def agg(rows, step):
    out = {}
    for t, o, h, l, c, v in rows:
        k = t - t % step
        if k not in out: out[k] = [k, o, h, l, c, v, 1]
        else:
            b = out[k]; b[2] = max(b[2], h); b[3] = min(b[3], l); b[4] = c; b[5] += v; b[6] += 1
    return [b[:6] for k, b in sorted(out.items()) if b[6] == step // 60000]

def write(fn, header, rows):
    with open(os.path.join(OUT, fn), "w", newline="") as f:
        w = csv.writer(f); w.writerow(header); w.writerows(rows)

summary = {}
for coin in ["BTC", "ETH"]:
    sym = f"{coin}/USDC:USDC"
    m1 = ex.fetch_ohlcv(sym, "1m", since=START, params={"paginate": True, "until": END})
    assert len(m1) == (END - START) // 60000, (coin, len(m1))
    h1 = agg(m1, H)
    d1 = ex.fetch_ohlcv(sym, "1d", since=START, params={"paginate": True, "until": END})
    assert len(h1) == (END - START) // H and len(d1) == (END - START) // D
    # cross-check against Hyperliquid's own candles
    ref = {c["t"]: c for c in hl({"type": "candleSnapshot", "req": {"coin": coin, "interval": "1h", "startTime": START, "endTime": END - 1}})}
    cmp = [(b, ref[b[0]]) for b in h1 if b[0] in ref]
    bad_h = sum(1 for b, r in cmp if (b[1], b[2], b[3], b[4]) != (float(r["o"]), float(r["h"]), float(r["l"]), float(r["c"])))
    vol_err = max(abs(b[5] - float(r["v"])) / max(float(r["v"]), 1e-9) for b, r in cmp)
    dagg = {b[0]: b for b in agg(m1, D)}
    bad_d = sum(1 for b in d1 if tuple(b[1:5]) != tuple(dagg[b[0]][1:5]))
    fmt = lambda b: [iso(b[0]), b[0]] + [f"{round(x, 8):.15g}" for x in b[1:]]
    write(f"hyperliquid_{coin.lower()}_perp_ohlcv_1h.csv", ["open_time", "open_time_ms", "open", "high", "low", "close", "volume"], [fmt(b) for b in h1])
    write(f"hyperliquid_{coin.lower()}_perp_ohlcv_1d.csv", ["open_time", "open_time_ms", "open", "high", "low", "close", "volume"], [fmt(b) for b in d1])
    fr, cur = [], START
    while cur < END:
        page = [p for p in hl({"type": "fundingHistory", "coin": coin, "startTime": cur, "endTime": END - 1})
                if p["time"] < END and (not fr or p["time"] > fr[-1]["time"])]
        if not page: break
        fr += page; cur = page[-1]["time"] + 1
    write(f"hyperliquid_{coin.lower()}_perp_funding_1h.csv", ["time", "time_ms", "funding_rate", "premium"],
          [[iso(p["time"] - p["time"] % 1000), p["time"], p["fundingRate"], p["premium"]] for p in fr])
    summary[coin] = dict(m1=len(m1), h1=len(h1), d1=len(d1), h1_vs_hl_compared=len(cmp), h1_ohlc_mismatch=bad_h,
                         h1_max_rel_vol_diff=round(vol_err, 6), d1_vs_1m_agg_mismatch=bad_d, funding=len(fr),
                         funding_first=iso(fr[0]["time"]), funding_last=iso(fr[-1]["time"]))
print(json.dumps(summary, indent=1))
