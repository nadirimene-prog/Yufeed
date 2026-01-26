from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    DATABASE_URL: str = "sqlite:///./compliance.db"
    REDIS_URL: str = "redis://localhost:6379/0"
    OPENSEARCH_URL: str = "http://localhost:9200"
    SMTP_HOST: str = "localhost"
    SMTP_PORT: int = 1025
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

    # Authentication - IMPORTANT: Change SECRET_KEY in production!
    SECRET_KEY: str = "change-this-to-a-random-secret-key-in-production-use-openssl-rand-hex-32"

    model_config = SettingsConfigDict(env_file=".env", extra="allow")

settings = Settings()
