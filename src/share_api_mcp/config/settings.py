"""Configuration settings loaded from environment variables."""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    """Immutable settings for the Share API MCP server."""

    base_url: str
    download_dir: str = "./downloads"
    auth_user: str = ""
    auth_password: str = ""
    project_id: str = ""

    @classmethod
    def from_env(cls) -> Settings:
        """Create Settings from environment variables."""
        base_url = os.environ.get("SHARE_API_BASE_URL", "")
        download_dir = os.environ.get("SHARE_API_DOWNLOAD_DIR", "./downloads")
        auth_user = os.environ.get("SHARE_API_AUTH_USER", "")
        auth_password = os.environ.get("SHARE_API_AUTH_PASSWORD", "")
        project_id = os.environ.get("SHARE_API_PROJECT_ID", "")
        return cls(
            base_url=base_url,
            download_dir=download_dir,
            auth_user=auth_user,
            auth_password=auth_password,
            project_id=project_id,
        )
