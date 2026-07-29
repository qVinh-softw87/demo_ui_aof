from functools import lru_cache
from pathlib import Path
import os


def _load_local_env(project_root: Path) -> None:
    """Load the project-local .env without overriding real environment variables."""

    env_path = project_root / ".env"
    if not env_path.exists():
        return
    for raw_line in env_path.read_text(encoding="utf-8-sig").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("'\"")
        if key:
            os.environ.setdefault(key, value)


class Settings:
    """Environment-backed settings for the self-contained demo."""

    app_name: str = "Monopoly AI Portfolio Lab"
    app_version: str = "2.0.0"
    model_version: str = "aq2026-coupled-cpsat-v2-complexity"
    default_legal_operating_mode: str = "RESEARCH_EDUCATION"
    data_snapshot: str = "MOCK_ASSET_PRODUCT_2026Q3"

    def __init__(self) -> None:
        project_root = Path(__file__).resolve().parents[3]
        _load_local_env(project_root)
        self.project_root = project_root
        self.data_dir = project_root / "backend" / "app" / "data"
        self.frontend_dist = project_root / "frontend" / "dist"
        self.db_path = Path(
            os.getenv(
                "AQ_PORTFOLIO_DB_PATH",
                str(project_root / "backend" / "app" / "data" / "portfolio_demo.sqlite3"),
            )
        )
        self.openai_api_key = os.getenv("OPENAI_API_KEY")
        self.openai_model = os.getenv("OPENAI_MODEL", "gpt-5.6-sol")
        self.groq_api_key = os.getenv("GROQ_API_KEY")
        self.groq_model = os.getenv("GROQ_MODEL", "openai/gpt-oss-20b")
        self.llm_provider = os.getenv("LLM_PROVIDER", "auto").strip().lower()
        self.environment = os.getenv("AQ_ENV", "development").strip().lower()
        self.auth_required = os.getenv("AQ_AUTH_REQUIRED", "false").lower() == "true"
        self.allow_registration = (
            os.getenv("AQ_ALLOW_REGISTRATION", "true").lower() == "true"
        )
        self.auth_secret = os.getenv(
            "AQ_AUTH_SECRET",
            "development-only-change-me-before-production",
        )
        self.auth_token_ttl_seconds = int(
            os.getenv("AQ_AUTH_TOKEN_TTL_SECONDS", "28800")
        )
        self.rate_limit_per_minute = int(
            os.getenv("AQ_RATE_LIMIT_PER_MINUTE", "120")
        )
        self.max_request_bytes = int(
            os.getenv("AQ_MAX_REQUEST_BYTES", "1048576")
        )
        self.market_data_auto_refresh = (
            os.getenv("AQ_MARKET_DATA_AUTO_REFRESH", "true").lower() == "true"
        )
        self.market_data_refresh_seconds = int(
            os.getenv("AQ_MARKET_DATA_REFRESH_SECONDS", "21600")
        )
        self.complexity_config_version = os.getenv(
            "AQ_COMPLEXITY_CONFIG_VERSION", "operational-complexity-v1"
        )
        self.complexity_provider_weight = int(os.getenv("AQ_COMPLEXITY_PROVIDER_WEIGHT", "24"))
        self.complexity_product_weight = int(os.getenv("AQ_COMPLEXITY_PRODUCT_WEIGHT", "16"))
        self.complexity_fragment_weight = int(os.getenv("AQ_COMPLEXITY_FRAGMENT_WEIGHT", "22"))
        self.complexity_maturity_weight = int(os.getenv("AQ_COMPLEXITY_MATURITY_WEIGHT", "10"))
        self.complexity_fragment_threshold_pct = float(
            os.getenv("AQ_COMPLEXITY_FRAGMENT_THRESHOLD_PCT", "0.12")
        )
        self.complexity_normalization_raw = int(
            os.getenv("AQ_COMPLEXITY_NORMALIZATION_RAW", "250")
        )
        self.complexity_warning_threshold = float(
            os.getenv("AQ_COMPLEXITY_WARNING_THRESHOLD", "55")
        )
        self.complexity_small_capital_threshold = int(
            os.getenv("AQ_COMPLEXITY_SMALL_CAPITAL_THRESHOLD", "50000000")
        )
        self.complexity_small_capital_multiplier = float(
            os.getenv("AQ_COMPLEXITY_SMALL_CAPITAL_MULTIPLIER", "2.5")
        )
        self.complexity_objective_scale = int(
            os.getenv("AQ_COMPLEXITY_OBJECTIVE_SCALE", "2")
        )
        self.complexity_resolve_boost = float(
            os.getenv("AQ_COMPLEXITY_RESOLVE_BOOST", "25")
        )
        self.cors_origins = [
            origin.strip()
            for origin in os.getenv(
                "AQ_CORS_ORIGINS",
                "http://localhost:5173,http://127.0.0.1:5173",
            ).split(",")
            if origin.strip()
        ]

    @property
    def active_llm_provider(self) -> str:
        if self.llm_provider == "deterministic":
            return "deterministic"
        if self.llm_provider == "groq":
            return "groq" if self.groq_api_key else "deterministic"
        if self.llm_provider == "openai":
            return "openai" if self.openai_api_key else "deterministic"
        if self.groq_api_key:
            return "groq"
        if self.openai_api_key:
            return "openai"
        return "deterministic"

    @property
    def active_llm_model(self) -> str:
        if self.active_llm_provider == "groq":
            return self.groq_model
        if self.active_llm_provider == "openai":
            return self.openai_model
        return "deterministic-rules"

    @property
    def llm_configured(self) -> bool:
        return self.active_llm_provider != "deterministic"


@lru_cache
def get_settings() -> Settings:
    return Settings()
