"""MCP Server for the media-file-explorer-share API."""

from __future__ import annotations

import json
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

mcp = FastMCP(
    "share-api",
    instructions=(
        "This API manages shared entries (notes, files, links) across multiple projects. "
        "IMPORTANT: Always filter entries by project. Do NOT list all entries. "
        "If SHARE_API_PROJECT_ID is configured, entries are automatically filtered by project — "
        "you can skip the manual project lookup and call list_entries directly. "
        "Workflow (only needed when SHARE_API_PROJECT_ID is NOT configured): "
        "1) Call list_field_options with field_name='project' to get all available projects. "
        "2) Call list_field_options with field_name='status' to get all available statuses. "
        "3) Pick the project matching your current context or ask the user which project to use. "
        "4) Store the project_id and status IDs for the rest of the session — do NOT look them up again. "
        "5) Call list_entries with filters='{\"project_id\": <id>}' to list only that project's entries. "
        "You can combine filters, e.g. '{\"project_id\": 1, \"status_id\": 2}'. "
        "Discover all available filter fields via list_fields or list_custom_fields."
    ),
)


def _resolve_base_url(base_url: str, settings: Settings) -> str:
    """Resolve the effective base URL from tool arg or settings."""
    effective = base_url or settings.base_url
    if not effective:
        raise ValueError(
            "No base_url provided. Set SHARE_API_BASE_URL or pass base_url argument."
        )
    return effective


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
        effective_base_url = _resolve_base_url(base_url, settings)
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


@mcp.tool()
def list_entries(
    base_url: str = "",
    page: int = 1,
    per_page: int = 20,
    filters: str = "",
) -> str:
    """List shared entries with pagination and optional filters.

    IMPORTANT: Always filter by project to avoid listing unrelated entries.
    If SHARE_API_PROJECT_ID is set, entries are automatically filtered by that project.
    An explicit project_id in filters overrides the env var.
    If no project_id is configured, call list_field_options(field_name='project') first.

    Args:
        base_url: Base URL of the share API. Falls back to SHARE_API_BASE_URL env var.
        page: Page number (default 1).
        per_page: Entries per page (default 20).
        filters: Optional JSON string of filter key-value pairs.
                 Use custom field filters like project_id, status_id, resolution_id.
                 Example: '{"project_id": 1}' or '{"project_id": 1, "status_id": 2}'.
                 Discover all available filter fields via list_fields or list_custom_fields.
    """
    try:
        settings = Settings.from_env()
        effective_base_url = _resolve_base_url(base_url, settings)

        parsed_filters: dict[str, object] | None = None
        if filters:
            try:
                parsed_filters = json.loads(filters)
            except json.JSONDecodeError as je:
                return f"Error: Invalid filters JSON: {je}"

        if settings.project_id and (
            parsed_filters is None or "project_id" not in parsed_filters
        ):
            if parsed_filters is None:
                parsed_filters = {}
            parsed_filters["project_id"] = int(settings.project_id)

        client = ShareApiClient(settings)
        result = client.list_entries(
            effective_base_url, page=page, per_page=per_page, filters=parsed_filters
        )
        return result.format_output()

    except Exception as e:
        logger.exception("Error listing entries")
        return f"Error: {e}"


@mcp.tool()
def update_entry(
    entry_id: int,
    base_url: str = "",
    subject: str = "",
    body: str = "",
    custom_fields: str = "",
) -> str:
    """Update a shared entry by ID.

    Args:
        entry_id: The numeric ID of the entry to update.
        base_url: Base URL of the share API. Falls back to SHARE_API_BASE_URL env var.
        subject: New subject for the entry.
        body: New body content as JSON string (e.g. '{"content": "text"}').
        custom_fields: Optional JSON string of custom field values to set as top-level keys.
                       Example: '{"status_id": 3}' or '{"status_id": 3, "project_id": 1}'.
    """
    try:
        settings = Settings.from_env()
        effective_base_url = _resolve_base_url(base_url, settings)

        payload: dict[str, object] = {}
        if subject:
            payload["subject"] = subject
        if body:
            try:
                payload["body"] = json.loads(body)
            except json.JSONDecodeError as je:
                return f"Error: Invalid body JSON: {je}"
        if custom_fields:
            try:
                payload.update(json.loads(custom_fields))
            except json.JSONDecodeError as je:
                return f"Error: Invalid custom_fields JSON: {je}"

        client = ShareApiClient(settings)
        entry = client.update_entry(effective_base_url, entry_id, payload)
        return f"Updated entry #{entry.id}: {entry.subject}"

    except Exception as e:
        logger.exception("Error updating entry %d", entry_id)
        return f"Error: {e}"


@mcp.tool()
def delete_entry(
    entry_id: int,
    base_url: str = "",
) -> str:
    """Delete a shared entry by ID (cascades to attachments).

    Args:
        entry_id: The numeric ID of the entry to delete.
        base_url: Base URL of the share API. Falls back to SHARE_API_BASE_URL env var.
    """
    try:
        settings = Settings.from_env()
        effective_base_url = _resolve_base_url(base_url, settings)

        client = ShareApiClient(settings)
        result = client.delete_entry(effective_base_url, entry_id)
        return result.format_output()

    except Exception as e:
        logger.exception("Error deleting entry %d", entry_id)
        return f"Error: {e}"


@mcp.tool()
def list_custom_fields(
    base_url: str = "",
) -> str:
    """List all custom fields.

    Args:
        base_url: Base URL of the share API. Falls back to SHARE_API_BASE_URL env var.
    """
    try:
        settings = Settings.from_env()
        effective_base_url = _resolve_base_url(base_url, settings)

        client = ShareApiClient(settings)
        result = client.list_custom_fields(effective_base_url)
        return result.format_output()

    except Exception as e:
        logger.exception("Error listing custom fields")
        return f"Error: {e}"


@mcp.tool()
def create_custom_field(
    name: str,
    base_url: str = "",
    description: str = "",
    sort_order: int = 0,
) -> str:
    """Create a new custom field.

    Args:
        name: Name of the custom field to create.
        base_url: Base URL of the share API. Falls back to SHARE_API_BASE_URL env var.
        description: Optional description for the field.
        sort_order: Sort order (default 0).
    """
    try:
        settings = Settings.from_env()
        effective_base_url = _resolve_base_url(base_url, settings)

        client = ShareApiClient(settings)
        field = client.create_custom_field(
            effective_base_url, name, description=description, sort_order=sort_order
        )
        return field.format_output()

    except Exception as e:
        logger.exception("Error creating custom field '%s'", name)
        return f"Error: {e}"


@mcp.tool()
def update_custom_field(
    name: str,
    base_url: str = "",
    description: str = "",
    sort_order: int = 0,
) -> str:
    """Update an existing custom field.

    Args:
        name: Name of the custom field to update.
        base_url: Base URL of the share API. Falls back to SHARE_API_BASE_URL env var.
        description: New description for the field.
        sort_order: New sort order.
    """
    try:
        settings = Settings.from_env()
        effective_base_url = _resolve_base_url(base_url, settings)

        payload: dict[str, object] = {"description": description, "sort_order": sort_order}
        client = ShareApiClient(settings)
        field = client.update_custom_field(effective_base_url, name, payload)
        return field.format_output()

    except Exception as e:
        logger.exception("Error updating custom field '%s'", name)
        return f"Error: {e}"


@mcp.tool()
def delete_custom_field(
    name: str,
    base_url: str = "",
) -> str:
    """Delete a custom field by name (cascades to options).

    Args:
        name: Name of the custom field to delete.
        base_url: Base URL of the share API. Falls back to SHARE_API_BASE_URL env var.
    """
    try:
        settings = Settings.from_env()
        effective_base_url = _resolve_base_url(base_url, settings)

        client = ShareApiClient(settings)
        result = client.delete_custom_field(effective_base_url, name)
        return result.format_output()

    except Exception as e:
        logger.exception("Error deleting custom field '%s'", name)
        return f"Error: {e}"


@mcp.tool()
def export_custom_fields(
    base_url: str = "",
) -> str:
    """Export all custom fields with their options.

    Args:
        base_url: Base URL of the share API. Falls back to SHARE_API_BASE_URL env var.
    """
    try:
        settings = Settings.from_env()
        effective_base_url = _resolve_base_url(base_url, settings)

        client = ShareApiClient(settings)
        result = client.export_custom_fields(effective_base_url)
        return result.format_output()

    except Exception as e:
        logger.exception("Error exporting custom fields")
        return f"Error: {e}"


@mcp.tool()
def import_custom_fields(
    fields_json: str,
    base_url: str = "",
) -> str:
    """Import custom fields from a JSON structure (merge mode).

    Args:
        fields_json: JSON string containing the fields to import.
        base_url: Base URL of the share API. Falls back to SHARE_API_BASE_URL env var.
    """
    try:
        settings = Settings.from_env()
        effective_base_url = _resolve_base_url(base_url, settings)

        try:
            parsed = json.loads(fields_json)
        except json.JSONDecodeError as je:
            return f"Error: Invalid fields_json: {je}"

        client = ShareApiClient(settings)
        result = client.import_custom_fields(effective_base_url, parsed)
        return result.format_output()

    except Exception as e:
        logger.exception("Error importing custom fields")
        return f"Error: {e}"


@mcp.tool()
def list_field_options(
    field_name: str,
    base_url: str = "",
) -> str:
    """List all options for a custom field.

    Args:
        field_name: Name of the custom field.
        base_url: Base URL of the share API. Falls back to SHARE_API_BASE_URL env var.
    """
    try:
        settings = Settings.from_env()
        effective_base_url = _resolve_base_url(base_url, settings)

        client = ShareApiClient(settings)
        result = client.list_field_options(effective_base_url, field_name)
        return result.format_output()

    except Exception as e:
        logger.exception("Error listing options for field '%s'", field_name)
        return f"Error: {e}"


@mcp.tool()
def create_field_option(
    field_name: str,
    name: str,
    base_url: str = "",
) -> str:
    """Create a new option for a custom field.

    Args:
        field_name: Name of the custom field.
        name: Name of the option to create.
        base_url: Base URL of the share API. Falls back to SHARE_API_BASE_URL env var.
    """
    try:
        settings = Settings.from_env()
        effective_base_url = _resolve_base_url(base_url, settings)

        client = ShareApiClient(settings)
        option = client.create_field_option(effective_base_url, field_name, name)
        return option.format_output()

    except Exception as e:
        logger.exception("Error creating option for field '%s'", field_name)
        return f"Error: {e}"


@mcp.tool()
def update_field_option(
    field_name: str,
    option_id: int,
    name: str,
    base_url: str = "",
) -> str:
    """Rename a field option.

    Args:
        field_name: Name of the custom field.
        option_id: ID of the option to update.
        name: New name for the option.
        base_url: Base URL of the share API. Falls back to SHARE_API_BASE_URL env var.
    """
    try:
        settings = Settings.from_env()
        effective_base_url = _resolve_base_url(base_url, settings)

        client = ShareApiClient(settings)
        option = client.update_field_option(
            effective_base_url, field_name, option_id, name
        )
        return option.format_output()

    except Exception as e:
        logger.exception("Error updating option %d for field '%s'", option_id, field_name)
        return f"Error: {e}"


@mcp.tool()
def delete_field_option(
    field_name: str,
    option_id: int,
    base_url: str = "",
) -> str:
    """Delete a field option (cascades to entries using it).

    Args:
        field_name: Name of the custom field.
        option_id: ID of the option to delete.
        base_url: Base URL of the share API. Falls back to SHARE_API_BASE_URL env var.
    """
    try:
        settings = Settings.from_env()
        effective_base_url = _resolve_base_url(base_url, settings)

        client = ShareApiClient(settings)
        result = client.delete_field_option(effective_base_url, field_name, option_id)
        return result.format_output()

    except Exception as e:
        logger.exception("Error deleting option %d for field '%s'", option_id, field_name)
        return f"Error: {e}"


@mcp.tool()
def delete_attachment(
    attachment_id: int,
    base_url: str = "",
) -> str:
    """Delete an attachment by ID.

    Args:
        attachment_id: ID of the attachment to delete.
        base_url: Base URL of the share API. Falls back to SHARE_API_BASE_URL env var.
    """
    try:
        settings = Settings.from_env()
        effective_base_url = _resolve_base_url(base_url, settings)

        client = ShareApiClient(settings)
        result = client.delete_attachment(effective_base_url, attachment_id)
        return result.format_output()

    except Exception as e:
        logger.exception("Error deleting attachment %d", attachment_id)
        return f"Error: {e}"


@mcp.tool()
def get_auth_info(
    base_url: str = "",
) -> str:
    """Get authentication method info from the API.

    Args:
        base_url: Base URL of the share API. Falls back to SHARE_API_BASE_URL env var.
    """
    try:
        settings = Settings.from_env()
        effective_base_url = _resolve_base_url(base_url, settings)

        client = ShareApiClient(settings)
        result = client.get_auth_info(effective_base_url)
        return result.format_output()

    except Exception as e:
        logger.exception("Error getting auth info")
        return f"Error: {e}"


@mcp.tool()
def list_fields(
    base_url: str = "",
) -> str:
    """List all field descriptors (schema discovery).

    Args:
        base_url: Base URL of the share API. Falls back to SHARE_API_BASE_URL env var.
    """
    try:
        settings = Settings.from_env()
        effective_base_url = _resolve_base_url(base_url, settings)

        client = ShareApiClient(settings)
        result = client.list_fields(effective_base_url)
        return result.format_output()

    except Exception as e:
        logger.exception("Error listing fields")
        return f"Error: {e}"


@mcp.tool()
def create_entry(
    base_url: str = "",
    text_or_url: str = "",
    file_path: str = "",
    extra_fields: str = "",
) -> str:
    """Create a new entry via the webhook endpoint.

    Args:
        base_url: Base URL of the share API. Falls back to SHARE_API_BASE_URL env var.
        text_or_url: Text content or URL to share.
        file_path: Path to a file to upload.
        extra_fields: Optional JSON string of extra fields (e.g. '{"_status": "open"}').
    """
    try:
        settings = Settings.from_env()
        effective_base_url = _resolve_base_url(base_url, settings)

        parsed_extra: dict[str, str] | None = None
        if extra_fields:
            try:
                parsed_extra = json.loads(extra_fields)
            except json.JSONDecodeError as je:
                return f"Error: Invalid extra_fields JSON: {je}"

        client = ShareApiClient(settings)
        entry_id = client.create_entry(
            effective_base_url,
            text_or_url=text_or_url,
            file_path=file_path,
            extra_fields=parsed_extra,
        )
        return f"Created entry: {entry_id}"

    except Exception as e:
        logger.exception("Error creating entry")
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
