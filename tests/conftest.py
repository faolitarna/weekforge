"""Set dummy env vars before any test module is imported.

Prevents tests from requiring a real .env file in CI. Real values in .env
take precedence because setdefault only fills gaps.
"""
import os

os.environ.setdefault("NOTION_TOKEN", "test-notion-token")
os.environ.setdefault("NOTION_TEST_DB_ID", "test-db-id")
os.environ.setdefault("OPENAI_API_KEY", "test-openai-key")
