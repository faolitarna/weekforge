from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    notion_token: str
    notion_test_db_id: str

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


# Module-level instantiation = fail-fast: missing vars crash at import, not inside a workflow.
# Side effect: tests that import this module require a .env or env vars to be set.
settings = Settings()  # type: ignore[call-arg]
