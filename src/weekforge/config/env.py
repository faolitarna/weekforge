from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """
    Application settings loaded from environment variables or .env file.
    
    Using pydantic_settings enforces our "Fail fast, fail loud" architectural pattern.
    If a required environment variable is missing or incorrectly typed, the application
    will crash immediately at startup with a clear validation error, rather than failing
    deep inside a tool or graph node.
    """
    notion_token: str
    notion_test_db_id: str

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )

# Load settings immediately upon import.
# This ensures fail-fast validation at app startup.
settings = Settings()  # type: ignore[call-arg]
