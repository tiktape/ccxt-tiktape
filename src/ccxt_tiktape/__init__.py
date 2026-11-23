"""ccxt-tiktape: full Hyperliquid OHLCV history through CCXT, served by TikTape."""

__version__ = "0.1.1"

from .tiktape import FREE_KEY_URL, TIKTAPE_BASE_URL, tiktape  # noqa: E402

TikTape = tiktape

__all__ = ["tiktape", "TikTape", "TIKTAPE_BASE_URL", "FREE_KEY_URL", "__version__"]
