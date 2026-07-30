"""Vercel ASGI entrypoint for the Monopoly AI FastAPI backend.

The Vercel project currently uses ``frontend`` as its Root Directory. The
build preparation script copies the repository's backend package into that
directory so this function can expose the complete API on the same domain.
"""

from __future__ import annotations

import os


os.environ.setdefault("AQ_ENV", "production")
os.environ.setdefault("AQ_AUTH_REQUIRED", "false")
os.environ.setdefault("AQ_ALLOW_REGISTRATION", "false")
os.environ.setdefault("AQ_MARKET_DATA_AUTO_REFRESH", "false")
os.environ.setdefault("AQ_PORTFOLIO_DB_PATH", "/tmp/monopoly-portfolio.sqlite3")

from backend.app.main import app  # noqa: E402,F401
