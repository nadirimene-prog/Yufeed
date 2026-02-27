import warnings
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import model_validator
import os

# Load .env file explicitly before Settings is defined
from dotenv import load_dotenv

# Get absolute path to this file
_CURRENT_FILE = os.path.abspath(__file__)

# Path calculation:
# src/config.py -> src/ -> apps/api/ -> project root/
root_env = os.path.join(
    os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(_CURRENT_FILE)))), ".env"
)
api_env = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(_CURRENT_FILE))), ".env")

if os.path.exists(root_env):
    load_dotenv(dotenv_path=root_env, override=False)
else:
    load_dotenv(dotenv_path=api_env, override=False)


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        extra="allow",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    DATABASE_URL: str = ""
    DB_POOL_SIZE: int = 10
    DB_MAX_OVERFLOW: int = 5
    DB_POOL_TIMEOUT: int = 10
    DB_POOL_RECYCLE: int = 300

    REDIS_URL: str = "redis://localhost:6379/0"
    REDIS_SOCKET_TIMEOUT: float = 5.0
    REDIS_SOCKET_CONNECT_TIMEOUT: float = 2.0
    REDIS_MAX_CONNECTIONS: int = 50
    REDIS_RETRY_ON_TIMEOUT: bool = True

    OPENSEARCH_URL: str = "http://localhost:9200"
    SMTP_HOST: str = "localhost"
    SMTP_PORT: int = 1025
    SMTP_TLS: bool = False
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    EMAILS_FROM_EMAIL: str = "noreply@yufeed.local"
    EMAILS_FROM_NAME: str = "Yufeed Sentinel"
    FRONTEND_URL: str = "http://localhost:3000"  # Frontend base URL for email links
    ADMIN_EMAIL: str = ""  # Override for alert notifications
    CELLAR_BASE_URL: str = "http://publications.europa.eu/resource/cellar"
    RSS_USER_AGENT: str = "Yufeed/1.0"
    EURLEX_LANGUAGES: str = "en,fr"
    LEGIFRANCE_JORF_RSS_URL: str = ""
    LEGIFRANCE_API_BASE_URL: str = ""
    LEGIFRANCE_API_TOKEN: str = ""
    REGULATORY_SCOPE_FILTER: str = "psp,eme,vasp"
    EURLEX_SEARCH_TERMS_FR: str = (
        "prestataire de services de paiement;"
        "services de paiement;"
        "etablissement de monnaie electronique;"
        "monnaie electronique;"
        "prestataire de services sur actifs numeriques;"
        "actifs numeriques;"
        "crypto-actifs;"
        "psan;"
        "mica"
    )
    EURLEX_SEARCH_TERMS_EN: str = (
        "payment service provider;"
        "payment services;"
        "electronic money institution;"
        "electronic money;"
        "crypto-asset service provider;"
        "virtual asset service provider;"
        "crypto-assets;"
        "emd2;"
        "psd2;"
        "psd3;"
        "mica;"
        "casp"
    )
    EURLEX_SEARCH_PAGE_SIZE: int = 100
    EURLEX_OJ_START_DATE: str = "2023-10-01"

    # Environment setting
    ENVIRONMENT: str = "development"  # development, staging, production

    # Authentication - SECRET_KEY is REQUIRED in production
    # Generate with: python -c "import secrets; print(secrets.token_hex(32))"
    SECRET_KEY: str = ""  # Must be set via environment variable

    # ===========================================
    # REGULATORY INTELLIGENCE PIPELINE
    # ===========================================

    # AI Configuration (Anthropic Claude)
    ANTHROPIC_API_KEY: str = ""
    ANTHROPIC_MODEL: str = "claude-sonnet-4-20250514"
    ANTHROPIC_MAX_TOKENS_POLICY: int = 2000
    ANTHROPIC_MAX_TOKENS_EXTRACTION: int = 4000
    ANTHROPIC_TIMEOUT_SECONDS: float = 120.0
    # AI Configuration (OpenAI fallback)
    OPENAI_API_KEY: str = ""
    OPENAI_BASE_URL: str = "https://api.openai.com/v1"
    OPENAI_MODEL: str = "gpt-4.1"
    OPENAI_RETRIES: int = 2
    OPENAI_BACKOFF_SECONDS: float = 2.0
    OPENAI_DELAY_SECONDS: float = 0.0
    OPENAI_TIMEOUT_SECONDS: float = 120.0
    AI_DAILY_COST_THRESHOLD_USD: float = 10.0
    AI_COST_CHECK_SCHEDULE: str = "0 7 * * *"
    CONTENT_BACKFILL_SCHEDULE: str = "0 2 1 * *"

    # RAG Configuration
    RAG_INDEX_NAME: str = "legal_chunks"
    RAG_INDEX_ENABLED: bool = True
    RAG_EMBEDDING_PROVIDER: str = "sentence_transformers"  # sentence_transformers | disabled
    RAG_EMBEDDING_MODEL: str = "BAAI/bge-m3"
    RAG_EMBEDDING_DIM: int = 1024
    RAG_CHUNK_SIZE: int = 1500  # characters
    RAG_CHUNK_OVERLAP: int = 300  # characters
    RAG_MAX_CHUNK_CHARS: int = 2000
    RAG_HYBRID_ALPHA: float = 0.5  # 0=vector only, 1=BM25 only

    # Policy matcher configuration
    POLICY_MATCH_HIGH_CONFIDENCE: float = 0.70
    POLICY_MATCH_MEDIUM_CONFIDENCE: float = 0.45
    POLICY_MATCH_ENABLE_LLM_REFINEMENT: bool = True

    # Deadline Monitoring
    DEADLINE_ALERT_THRESHOLDS: str = "90,60,30,7,1"
    DEADLINE_CHECK_SCHEDULE: str = "0 8 * * *"
    OVERDUE_CHECK_SCHEDULE: str = "0 9 * * *"

    # Email Escalation
    ESCALATION_ENABLED: bool = False
    ESCALATION_DAYS_THRESHOLD: int = 7
    MLRO_EMAIL: str = ""

    # Policy Templates
    POLICY_TEMPLATES_AUTO_SEED: bool = True

    # Feature Flags
    FEATURE_AI_POLICY_WRITER: bool = False
    FEATURE_MONITORING_SUGGESTIONS: bool = False
    FEATURE_DEADLINE_ALERTS: bool = True
    FEATURE_AUDIT_TRAIL: bool = True
    FEATURE_SUPERVISORY_INGESTION: bool = True
    FEATURE_SEMANTIC_POLICY_MATCHING: bool = True
    FEATURE_BULK_OBLIGATION_APPROVAL: bool = True
    DASHBOARD_V2_ENABLED: bool = True
    DASHBOARD_AMLCO_V3_ENABLED: bool = True

    @property
    def deadline_thresholds(self) -> list:
        """Parse deadline thresholds from comma-separated string."""
        return [int(x.strip()) for x in self.DEADLINE_ALERT_THRESHOLDS.split(",") if x.strip()]

    @property
    def escalation_enabled(self) -> bool:
        """Check if escalation is enabled."""
        return self.ESCALATION_ENABLED

    @property
    def escalation_days_threshold(self) -> int:
        """Get escalation days threshold."""
        return self.ESCALATION_DAYS_THRESHOLD

    @property
    def mlro_email(self) -> str:
        """Get MLRO email for escalation."""
        return self.MLRO_EMAIL

    @model_validator(mode="after")
    def validate_security_settings(self):
        """Validate security-critical settings."""
        is_production = self.ENVIRONMENT.lower() == "production"

        # Database URL validation/defaulting
        if not self.DATABASE_URL:
            if is_production:
                raise ValueError("DATABASE_URL is required in production")
            self.DATABASE_URL = (
                "postgresql://postgres:postgres@localhost:5432/yufeed"  # pragma: allowlist secret
            )
            warnings.warn("DATABASE_URL not set. Using local development default.", UserWarning)

        # SECRET_KEY validation
        if not self.SECRET_KEY:
            if is_production:
                raise ValueError(
                    "SECRET_KEY is required in production! "
                    'Generate one with: python -c "import secrets; print(secrets.token_hex(32))" '
                    "and set it in your .env file."
                )
            # In development, use a dummy key if none provided
            self.SECRET_KEY = "dev_secret_key_do_not_use_in_production"
            warnings.warn(
                "SECRET_KEY not set. Using insecure default for development only.", UserWarning
            )
        elif len(self.SECRET_KEY) < 32:
            if is_production:
                raise ValueError("SECRET_KEY must be at least 32 characters in production")
            warnings.warn("SECRET_KEY is too short. Use at least 32 characters.", UserWarning)

        return self

    @property
    def redis_connection_kwargs(self) -> dict:
        """Shared Redis connection kwargs for sync clients."""
        return {
            "encoding": "utf-8",
            "decode_responses": True,
            "socket_timeout": self.REDIS_SOCKET_TIMEOUT,
            "socket_connect_timeout": self.REDIS_SOCKET_CONNECT_TIMEOUT,
            "max_connections": self.REDIS_MAX_CONNECTIONS,
            "retry_on_timeout": self.REDIS_RETRY_ON_TIMEOUT,
        }


settings = Settings()
