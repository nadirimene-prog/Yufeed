from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    DATABASE_URL: str
    REDIS_URL: str
    OPENSEARCH_URL: str
    SMTP_HOST: str
    SMTP_PORT: int = 1025
    CELLAR_BASE_URL: str = "http://publications.europa.eu/resource/cellar"
    RSS_USER_AGENT: str = "Yufeed/1.0"

    # Authentication - IMPORTANT: Change SECRET_KEY in production!
    SECRET_KEY: str = "change-this-to-a-random-secret-key-in-production-use-openssl-rand-hex-32"

    class Config:
        env_file = ".env"

settings = Settings()
