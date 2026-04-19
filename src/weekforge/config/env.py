from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    notion_token: str
    notion_test_db_id: str
    openai_api_key: str
    notion_db_training_sessions: str
    notion_db_training_week_summaries: str
    notion_db_training_templates: str
    notion_user_profile_page_id: str
    fast_profile: str = "gpt-5.4-nano"
    reasoning_profile: str = "gpt-5.4"
    caveman_mode: bool = False

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore"
    )


# Module-level instantiation = fail-fast: missing vars crash at import, not inside a workflow.
# Side effect: tests that import this module require a .env or env vars to be set.
settings = Settings()  # type: ignore[call-arg]
