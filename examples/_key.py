"""Shared helper: read the TikTape API key or explain where to get one."""

import os
import sys

GET_KEY_URL = "https://tiktape.xyz/?utm_source=github&utm_medium=example&utm_campaign=ccxt-tiktape-examples#freeKeyCard"


def api_key() -> str:
    key = os.environ.get("TIKTAPE_API_KEY", "").strip()
    if not key:
        sys.exit(f"Set TIKTAPE_API_KEY first. Free key (last 30 days, no card): {GET_KEY_URL}")
    return key
