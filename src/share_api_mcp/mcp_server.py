"""MCP Server for the media-file-explorer-share API."""

from __future__ import annotations

import logging
import os
import sys

from mcp.server.fastmcp import FastMCP

from share_api_mcp.api_client import ShareApiClient
from share_api_mcp.config.settings import Settings

# Configure logging
LOG_FORMAT = "%(asctime)s - %(levelname)s - %(message)s"
LOG_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(__file__))), "mcp.log")

logger = logging.getLogger("share-api-mcp")
logger.setLevel(logging.INFO)

# File handler - writes to mcp.log in project root
file_handler = logging.FileHandler(LOG_FILE, encoding="utf-8")
file_handler.setLevel(logging.INFO)
file_handler.setFormatter(logging.Formatter(LOG_FORMAT))
logger.addHandler(file_handler)

# Stderr handler (for MCP stdio compatibility)
stderr_handler = logging.StreamHandler(sys.stderr)
stderr_handler.setLevel(logging.WARNING)
stderr_handler.setFormatter(logging.Formatter(LOG_FORMAT))
logger.addHandler(stderr_handler)

mcp = FastMCP("share-api")


@mcp.tool()
def fetch_shared_entry(
    entry_id: int,
    base_url: str = "",
    download_dir: str = "",
) -> str:
    """Fetch a shared entry by ID from the media-file-explorer-share API.

    Downloads all file attachments and returns the entry content with file paths.

    Args:
        entry_id: The numeric ID of the shared entry to fetch.
        base_url: Base URL of the share API (e.g. http://host/share).
                  Falls back to SHARE_API_BASE_URL env var if empty.
        download_dir: Directory to save downloaded files.
                      Falls back to SHARE_API_DOWNLOAD_DIR env var or ./downloads.
    """
    try:
        settings = Settings.from_env()

        effective_base_url = base_url or settings.base_url
        if not effective_base_url:
            return "Error: No base_url provided. Set SHARE_API_BASE_URL or pass base_url argument."

        effective_download_dir = download_dir or settings.download_dir

        logger.info(
            "Fetching entry %d from %s (download_dir=%s)",
            entry_id,
            effective_base_url,
            effective_download_dir,
        )

        client = ShareApiClient(settings)
        result = client.fetch_entry_with_files(
            effective_base_url, entry_id, effective_download_dir
        )

        output = result.format_output()
        logger.info("Successfully fetched entry %d", entry_id)
        return output

    except Exception as e:
        logger.exception("Error fetching entry %d", entry_id)
        return f"Error: {e}"


def main() -> None:
    """Run the MCP server."""
    from dotenv import load_dotenv

    load_dotenv()

    logger.info("=" * 60)
    logger.info("MCP SERVER STARTING")
    logger.info("Log file: %s", LOG_FILE)
    logger.info("Process ID: %d", os.getpid())
    logger.info("Waiting for Claude Code connection...")
    logger.info("=" * 60)
    mcp.run(transport="stdio")


if __name__ == "__main__":
    main()
