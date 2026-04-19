from weekforge.config import ConfigError
from weekforge.config.env import settings
from weekforge.models.user_profile import UserProfile
from weekforge.tools.notion_api_gateway import fetch
from weekforge.tools.notion_markdown_converter import convert_blocks_to_markdown


def load_user_profile() -> UserProfile:
    page_id = settings.notion_user_profile_page_id
    page_data = fetch(page_id)
    markdown = convert_blocks_to_markdown(page_data["content"])

    if not markdown.strip():
        raise ConfigError("User profile page is empty. Add your profile content.")

    return UserProfile(page_id=page_id, markdown=markdown)
