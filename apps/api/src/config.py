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
