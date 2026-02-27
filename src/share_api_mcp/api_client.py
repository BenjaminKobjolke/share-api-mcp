"""HTTP client for the media-file-explorer-share PHP API."""

from __future__ import annotations

import logging
import os
from dataclasses import replace
from typing import Any

import httpx

from share_api_mcp.config.settings import Settings
from share_api_mcp.models import (
    Attachment,
    AuthInfo,
    CustomField,
    CustomFieldExportResult,
    CustomFieldListResult,
    DownloadedFile,
    Entry,
    EntryListResult,
    EntryResult,
    EntrySummary,
    ExportedField,
    FailedDownload,
    FieldDescriptor,
    FieldListResult,
    FieldOption,
    FieldOptionListResult,
    ImportResult,
    MessageResult,
)

logger = logging.getLogger("share-api-mcp")


def _parse_attachment(data: dict[str, Any]) -> Attachment:
    """Parse a single attachment from API JSON."""
    return Attachment(
        id=int(data.get("id") or 0),
        type=str(data.get("type") or ""),
        body=dict(data.get("body") or {}),
        filename=str(data.get("filename") or ""),
        file_size=int(data.get("file_size") or 0),
        file_url=str(data.get("file_url") or ""),
    )


def _parse_entry(data: dict[str, Any]) -> Entry:
    """Parse an entry from API JSON."""
    raw_attachments = data.get("attachments", [])
    attachments = tuple(_parse_attachment(a) for a in raw_attachments)
    return Entry(
        id=int(data.get("id") or 0),
        type=str(data.get("type") or ""),
        subject=str(data.get("subject") or ""),
        body=dict(data.get("body") or {}),
        filename=str(data.get("filename") or ""),
        file_size=int(data.get("file_size") or 0),
        file_url=str(data.get("file_url") or ""),
        attachments=attachments,
    )


def _parse_entry_summary(data: dict[str, Any]) -> EntrySummary:
    """Parse an entry summary from the list endpoint."""
    return EntrySummary(
        id=int(data.get("id") or 0),
        type=str(data.get("type") or ""),
        subject=str(data.get("subject") or ""),
        body=str(data.get("body") or ""),
        filename=str(data.get("filename") or ""),
        file_size=int(data.get("file_size") or 0),
        attachment_count=int(data.get("attachment_count") or 0),
        created_at=str(data.get("created_at") or ""),
    )


def _parse_custom_field(data: dict[str, Any]) -> CustomField:
    """Parse a custom field from API JSON."""
    return CustomField(
        name=str(data.get("name") or ""),
        description=str(data.get("description") or ""),
        sort_order=int(data.get("sort_order") or 0),
        option_count=int(data.get("option_count") or 0),
        created_at=str(data.get("created_at") or ""),
    )


def _parse_field_option(data: dict[str, Any], field_name: str = "") -> FieldOption:
    """Parse a field option from API JSON."""
    return FieldOption(
        id=int(data.get("id") or 0),
        field_name=str(data.get("field_name") or field_name),
        name=str(data.get("name") or ""),
        created_at=str(data.get("created_at") or ""),
        entry_count=int(data.get("entry_count") or 0),
    )


def _parse_exported_field(data: dict[str, Any]) -> ExportedField:
    """Parse an exported field from API JSON."""
    raw_options = data.get("options", [])
    options = tuple(str(o) for o in raw_options)
    return ExportedField(
        name=str(data.get("name") or ""),
        description=str(data.get("description") or ""),
        sort_order=int(data.get("sort_order") or 0),
        options=options,
    )


def _parse_field_descriptor(data: dict[str, Any]) -> FieldDescriptor:
    """Parse a field descriptor from the schema endpoint."""
    return FieldDescriptor(
        name=str(data.get("name") or ""),
        type=str(data.get("type") or ""),
        description=str(data.get("description") or ""),
        resource_path=str(data.get("resource_path") or ""),
    )


class ShareApiClient:
    """Client for the media-file-explorer-share API."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._auth: httpx.BasicAuth | None = None
        if settings.auth_user and settings.auth_password:
            self._auth = httpx.BasicAuth(settings.auth_user, settings.auth_password)

    def _normalize_url(self, base_url: str) -> str:
        """Strip trailing slashes and replace localhost with 127.0.0.1."""
        url = base_url.replace("://localhost", "://127.0.0.1")
        return url.rstrip("/")

    def fetch_entry(self, base_url: str, entry_id: int) -> Entry:
        """Fetch an entry by ID from the API."""
        url = f"{self._normalize_url(base_url)}/api.php/entries/{entry_id}"
        logger.info("Fetching entry from %s", url)
        with httpx.Client(auth=self._auth) as client:
            response = client.get(url)
            response.raise_for_status()
            data = response.json()
        return _parse_entry(data)

    def download_file(
        self, base_url: str, attachment_id: int, filename: str, download_dir: str
    ) -> DownloadedFile:
        """Download a file attachment from the API."""
        url = f"{self._normalize_url(base_url)}/api.php/files/{attachment_id}"
        logger.info("Downloading file %s from %s", filename, url)

        os.makedirs(download_dir, exist_ok=True)
        file_path = os.path.join(download_dir, filename)

        with httpx.Client(auth=self._auth) as client:
            with client.stream("GET", url) as response:
                response.raise_for_status()
                file_size = 0
                with open(file_path, "wb") as f:
                    for chunk in response.iter_bytes():
                        f.write(chunk)
                        file_size += len(chunk)

        logger.info("Downloaded %s (%d bytes)", file_path, file_size)
        return DownloadedFile(
            attachment_id=attachment_id,
            filename=filename,
            file_path=file_path,
            file_size=file_size,
        )

    def download_entry_file(
        self, base_url: str, entry_id: int, filename: str, download_dir: str
    ) -> DownloadedFile:
        """Download an entry-level file from the API."""
        url = f"{self._normalize_url(base_url)}/api.php/entries/{entry_id}/file"
        logger.info("Downloading entry file %s from %s", filename, url)

        os.makedirs(download_dir, exist_ok=True)
        file_path = os.path.join(download_dir, filename)

        with httpx.Client(auth=self._auth) as client:
            with client.stream("GET", url) as response:
                response.raise_for_status()
                file_size = 0
                with open(file_path, "wb") as f:
                    for chunk in response.iter_bytes():
                        f.write(chunk)
                        file_size += len(chunk)

        logger.info("Downloaded %s (%d bytes)", file_path, file_size)
        return DownloadedFile(
            attachment_id=entry_id,
            filename=filename,
            file_path=file_path,
            file_size=file_size,
        )

    def fetch_entry_with_files(
        self, base_url: str, entry_id: int, download_dir: str | None = None
    ) -> EntryResult:
        """Fetch an entry and download all file attachments."""
        if download_dir is None:
            download_dir = self._settings.download_dir
        download_dir = os.path.abspath(download_dir)

        entry_dir = os.path.join(download_dir, str(entry_id))

        entry = self.fetch_entry(base_url, entry_id)

        downloaded: list[DownloadedFile] = []
        failed: list[FailedDownload] = []

        # Download entry-level file if present
        if entry.file_url and entry.filename:
            try:
                df = self.download_entry_file(
                    base_url, entry.id, entry.filename, entry_dir
                )
                downloaded.append(df)
            except Exception as exc:
                logger.warning(
                    "Failed to download entry file %d (%s): %s",
                    entry.id,
                    entry.filename,
                    exc,
                )
                failed.append(
                    FailedDownload(
                        attachment_id=entry.id,
                        filename=entry.filename,
                        error=str(exc),
                    )
                )

        for att in entry.attachments:
            if att.type == "file" and att.filename:
                if not att.file_url:
                    logger.warning(
                        "Skipping attachment %d (%s): file not available on server",
                        att.id,
                        att.filename,
                    )
                    failed.append(
                        FailedDownload(
                            attachment_id=att.id,
                            filename=att.filename,
                            error="File not available on server",
                        )
                    )
                    continue
                try:
                    df = self.download_file(
                        base_url, att.id, att.filename, entry_dir
                    )
                    downloaded.append(df)
                except Exception as exc:
                    logger.warning(
                        "Failed to download attachment %d (%s): %s",
                        att.id,
                        att.filename,
                        exc,
                    )
                    failed.append(
                        FailedDownload(
                            attachment_id=att.id,
                            filename=att.filename,
                            error=str(exc),
                        )
                    )

        result = EntryResult(
            entry=entry,
            downloaded_files=tuple(downloaded),
            failed_downloads=tuple(failed),
        )

        # Generate and write content.md
        content_md = result.generate_content_markdown()
        os.makedirs(entry_dir, exist_ok=True)
        content_md_path = os.path.join(entry_dir, "content.md")
        with open(content_md_path, "w", encoding="utf-8") as f:
            f.write(content_md)
        logger.info("Wrote content markdown to %s", content_md_path)

        return replace(result, content_md_path=content_md_path)

    # --- Entry Management ---

    def list_entries(
        self,
        base_url: str,
        page: int = 1,
        per_page: int = 20,
        filters: dict[str, Any] | None = None,
    ) -> EntryListResult:
        """List entries with pagination and optional filters."""
        url = f"{self._normalize_url(base_url)}/api.php/entries"
        params: dict[str, Any] = {"page": page, "per_page": per_page}
        if filters:
            params.update(filters)
        logger.info("Listing entries from %s (page=%d)", url, page)
        with httpx.Client(auth=self._auth) as client:
            response = client.get(url, params=params)
            response.raise_for_status()
            data = response.json()
        entries = tuple(_parse_entry_summary(e) for e in data.get("entries", []))
        return EntryListResult(
            entries=entries,
            total=int(data.get("total", 0)),
            page=int(data.get("page", page)),
            per_page=int(data.get("per_page", per_page)),
        )

    def update_entry(
        self, base_url: str, entry_id: int, payload: dict[str, Any]
    ) -> Entry:
        """Update an entry by ID."""
        url = f"{self._normalize_url(base_url)}/api.php/entries/{entry_id}"
        logger.info("Updating entry %d at %s", entry_id, url)
        with httpx.Client(auth=self._auth) as client:
            response = client.put(url, json=payload)
            response.raise_for_status()
            data = response.json()
        return _parse_entry(data)

    def delete_entry(self, base_url: str, entry_id: int) -> MessageResult:
        """Delete an entry by ID."""
        url = f"{self._normalize_url(base_url)}/api.php/entries/{entry_id}"
        logger.info("Deleting entry %d at %s", entry_id, url)
        with httpx.Client(auth=self._auth) as client:
            response = client.delete(url)
            response.raise_for_status()
            data = response.json()
        return MessageResult(message=str(data.get("message", "Entry deleted")))

    # --- Custom Fields CRUD ---

    def list_custom_fields(self, base_url: str) -> CustomFieldListResult:
        """List all custom fields."""
        url = f"{self._normalize_url(base_url)}/api.php/custom-fields"
        logger.info("Listing custom fields from %s", url)
        with httpx.Client(auth=self._auth) as client:
            response = client.get(url)
            response.raise_for_status()
            data = response.json()
        fields = tuple(_parse_custom_field(f) for f in data.get("data", []))
        return CustomFieldListResult(fields=fields)

    def create_custom_field(
        self, base_url: str, name: str, description: str = "", sort_order: int = 0
    ) -> CustomField:
        """Create a new custom field."""
        url = f"{self._normalize_url(base_url)}/api.php/custom-fields"
        payload = {"name": name, "description": description, "sort_order": sort_order}
        logger.info("Creating custom field '%s' at %s", name, url)
        with httpx.Client(auth=self._auth) as client:
            response = client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
        return _parse_custom_field(data)

    def update_custom_field(
        self, base_url: str, name: str, payload: dict[str, Any]
    ) -> CustomField:
        """Update a custom field by name."""
        url = f"{self._normalize_url(base_url)}/api.php/custom-fields/{name}"
        logger.info("Updating custom field '%s' at %s", name, url)
        with httpx.Client(auth=self._auth) as client:
            response = client.put(url, json=payload)
            response.raise_for_status()
            data = response.json()
        return _parse_custom_field(data)

    def delete_custom_field(self, base_url: str, name: str) -> MessageResult:
        """Delete a custom field by name."""
        url = f"{self._normalize_url(base_url)}/api.php/custom-fields/{name}"
        logger.info("Deleting custom field '%s' at %s", name, url)
        with httpx.Client(auth=self._auth) as client:
            response = client.delete(url)
            response.raise_for_status()
            data = response.json()
        return MessageResult(message=str(data.get("message", "Custom field deleted")))

    # --- Custom Fields Import/Export ---

    def export_custom_fields(self, base_url: str) -> CustomFieldExportResult:
        """Export all custom fields with their options."""
        url = f"{self._normalize_url(base_url)}/api.php/custom-fields/export"
        logger.info("Exporting custom fields from %s", url)
        with httpx.Client(auth=self._auth) as client:
            response = client.get(url)
            response.raise_for_status()
            data = response.json()
        fields = tuple(_parse_exported_field(f) for f in data.get("data", []))
        return CustomFieldExportResult(fields=fields)

    def import_custom_fields(
        self, base_url: str, fields_json: dict[str, Any]
    ) -> ImportResult:
        """Import custom fields from a JSON structure."""
        url = f"{self._normalize_url(base_url)}/api.php/custom-fields/import"
        logger.info("Importing custom fields to %s", url)
        with httpx.Client(auth=self._auth) as client:
            response = client.post(url, json=fields_json)
            response.raise_for_status()
            data = response.json()
        return ImportResult(
            fields_created=int(data.get("fields_created", 0)),
            options_created=int(data.get("options_created", 0)),
        )

    # --- Field Options CRUD ---

    def list_field_options(
        self, base_url: str, field_name: str
    ) -> FieldOptionListResult:
        """List options for a custom field."""
        url = f"{self._normalize_url(base_url)}/api.php/field-options/{field_name}"
        logger.info("Listing options for field '%s' from %s", field_name, url)
        with httpx.Client(auth=self._auth) as client:
            response = client.get(url)
            response.raise_for_status()
            data = response.json()
        options = tuple(
            _parse_field_option(o, field_name) for o in data.get("data", [])
        )
        return FieldOptionListResult(field_name=field_name, options=options)

    def create_field_option(
        self, base_url: str, field_name: str, name: str
    ) -> FieldOption:
        """Create a new option for a custom field."""
        url = f"{self._normalize_url(base_url)}/api.php/field-options/{field_name}"
        payload = {"name": name}
        logger.info("Creating option '%s' for field '%s' at %s", name, field_name, url)
        with httpx.Client(auth=self._auth) as client:
            response = client.post(url, json=payload)
            response.raise_for_status()
            data = response.json()
        return _parse_field_option(data, field_name)

    def update_field_option(
        self, base_url: str, field_name: str, option_id: int, name: str
    ) -> FieldOption:
        """Update a field option by ID."""
        url = f"{self._normalize_url(base_url)}/api.php/field-options/{field_name}/{option_id}"
        payload = {"name": name}
        logger.info("Updating option %d for field '%s' at %s", option_id, field_name, url)
        with httpx.Client(auth=self._auth) as client:
            response = client.put(url, json=payload)
            response.raise_for_status()
            data = response.json()
        return _parse_field_option(data, field_name)

    def delete_field_option(
        self, base_url: str, field_name: str, option_id: int
    ) -> MessageResult:
        """Delete a field option by ID."""
        url = f"{self._normalize_url(base_url)}/api.php/field-options/{field_name}/{option_id}"
        logger.info("Deleting option %d for field '%s' at %s", option_id, field_name, url)
        with httpx.Client(auth=self._auth) as client:
            response = client.delete(url)
            response.raise_for_status()
            data = response.json()
        return MessageResult(message=str(data.get("message", "Option deleted")))

    # --- Attachments ---

    def delete_attachment(self, base_url: str, attachment_id: int) -> MessageResult:
        """Delete an attachment by ID."""
        url = f"{self._normalize_url(base_url)}/api.php/attachments/{attachment_id}"
        logger.info("Deleting attachment %d at %s", attachment_id, url)
        with httpx.Client(auth=self._auth) as client:
            response = client.delete(url)
            response.raise_for_status()
            data = response.json()
        return MessageResult(message=str(data.get("message", "Attachment deleted")))

    # --- Schema/Discovery ---

    def get_auth_info(self, base_url: str) -> AuthInfo:
        """Get authentication method info."""
        url = f"{self._normalize_url(base_url)}/api.php/auth"
        logger.info("Getting auth info from %s", url)
        with httpx.Client(auth=self._auth) as client:
            response = client.get(url)
            response.raise_for_status()
            data = response.json()
        return AuthInfo(method=str(data.get("method", "")))

    def list_fields(self, base_url: str) -> FieldListResult:
        """List all field descriptors from the schema endpoint."""
        url = f"{self._normalize_url(base_url)}/api.php/fields"
        logger.info("Listing fields from %s", url)
        with httpx.Client(auth=self._auth) as client:
            response = client.get(url)
            response.raise_for_status()
            data = response.json()
        fields = tuple(_parse_field_descriptor(f) for f in data.get("data", []))
        return FieldListResult(fields=fields)

    # --- Webhook ---

    def create_entry(
        self,
        base_url: str,
        text_or_url: str = "",
        file_path: str = "",
        extra_fields: dict[str, str] | None = None,
    ) -> str:
        """Create a new entry via the webhook endpoint.

        Returns the entry ID as a string on success.
        """
        url = f"{self._normalize_url(base_url)}/share.php"
        logger.info("Creating entry at %s", url)

        with httpx.Client(auth=self._auth) as client:
            if file_path:
                with open(file_path, "rb") as fh:
                    files = {"file": (os.path.basename(file_path), fh)}
                    data: dict[str, str] = {}
                    if text_or_url:
                        data["text_or_url"] = text_or_url
                    if extra_fields:
                        data.update(extra_fields)
                    response = client.post(url, data=data, files=files)
            else:
                json_body: dict[str, str] = {}
                if text_or_url:
                    json_body["text_or_url"] = text_or_url
                if extra_fields:
                    json_body.update(extra_fields)
                response = client.post(url, json=json_body)
            response.raise_for_status()

        return response.text.strip()
