import os
import secrets
import warnings
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import model_validator

class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite:///./compliance.db"
    REDIS_URL: str = "redis://localhost:6379/0"
    OPENSEARCH_URL: str = "http://localhost:9200"
    SMTP_HOST: str = "localhost"
    SMTP_PORT: int = 1025
    SMTP_TLS: bool = False
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    EMAILS_FROM_EMAIL: str = "noreply@yufeed.local"
    EMAILS_FROM_NAME: str = "Yufeed Sentinel"
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
    ANTHROPIC_MODEL: str = "claude-3-5-sonnet-20241022"
    ANTHROPIC_MAX_TOKENS_POLICY: int = 2000
    ANTHROPIC_MAX_TOKENS_EXTRACTION: int = 4000
    AI_DAILY_COST_THRESHOLD_USD: float = 10.0
    AI_COST_CHECK_SCHEDULE: str = "0 7 * * *"
    CONTENT_BACKFILL_SCHEDULE: str = "0 2 1 * *"

    # RAG Configuration
    RAG_INDEX_NAME: str = "legal_chunks"
    RAG_INDEX_ENABLED: bool = True
    RAG_EMBEDDING_PROVIDER: str = "sentence_transformers"  # sentence_transformers | disabled
    RAG_EMBEDDING_MODEL: str = "BAAI/bge-m3"
    RAG_EMBEDDING_DIM: int = 1024
    RAG_CHUNK_SIZE: int = 2000  # characters
    RAG_CHUNK_OVERLAP: int = 200  # characters
    RAG_HYBRID_ALPHA: float = 0.5  # 0=vector only, 1=BM25 only

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

    model_config = SettingsConfigDict(env_file=".env", extra="allow")

    @model_validator(mode="after")
    def validate_security_settings(self):
        """Validate security-critical settings."""
        is_production = self.ENVIRONMENT.lower() == "production"

        # SECRET_KEY validation
        if not self.SECRET_KEY:
            if is_production:
                raise ValueError(
                    "SECRET_KEY is required in production. "
                    "Generate one with: python -c \"import secrets; print(secrets.token_hex(32))\""
                )
            # Generate a random key for development (warn about it)
            self.SECRET_KEY = secrets.token_hex(32)
            warnings.warn(
                "SECRET_KEY not set - using auto-generated key. "
                "This is OK for development but MUST be set in production.",
                UserWarning
            )
        elif len(self.SECRET_KEY) < 32:
            if is_production:
                raise ValueError("SECRET_KEY must be at least 32 characters in production")
            warnings.warn("SECRET_KEY is too short. Use at least 32 characters.", UserWarning)

        return self

settings = Settings()
