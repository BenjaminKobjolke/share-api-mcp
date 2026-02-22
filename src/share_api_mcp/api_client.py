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
    DownloadedFile,
    Entry,
    EntryResult,
    FailedDownload,
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


class ShareApiClient:
    """Client for the media-file-explorer-share API."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._auth: httpx.BasicAuth | None = None
        if settings.auth_user and settings.auth_password:
            self._auth = httpx.BasicAuth(settings.auth_user, settings.auth_password)

    def _normalize_url(self, base_url: str) -> str:
        """Strip trailing slashes from the base URL."""
        return base_url.rstrip("/")

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
