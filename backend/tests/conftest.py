from __future__ import annotations

import os


# Unit tests must never consume external API credits or depend on provider uptime.
os.environ["LLM_PROVIDER"] = "deterministic"
os.environ["AQ_MARKET_DATA_AUTO_REFRESH"] = "false"
