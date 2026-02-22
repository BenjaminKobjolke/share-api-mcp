"""Data models for the Share API MCP server."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

_IMAGE_EXTENSIONS = frozenset(
    {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".webp", ".svg", ".tiff", ".ico"}
)


def _is_image_file(filename: str) -> bool:
    """Check if a filename has a common image extension."""
    dot = filename.rfind(".")
    if dot < 0:
        return False
    return filename[dot:].lower() in _IMAGE_EXTENSIONS


@dataclass(frozen=True)
class Attachment:
    """A single attachment on an entry."""

    id: int
    type: str
    body: dict[str, Any] = field(default_factory=dict)
    filename: str = ""
    file_size: int = 0
    file_url: str = ""


@dataclass(frozen=True)
class Entry:
    """A shared entry from the API."""

    id: int
    type: str
    subject: str
    body: dict[str, Any] = field(default_factory=dict)
    filename: str = ""
    file_size: int = 0
    file_url: str = ""
    attachments: tuple[Attachment, ...] = ()


@dataclass(frozen=True)
class FailedDownload:
    """A file attachment that could not be downloaded."""

    attachment_id: int
    filename: str
    error: str


@dataclass(frozen=True)
class DownloadedFile:
    """A file that was downloaded from the API."""

    attachment_id: int
    filename: str
    file_path: str
    file_size: int


@dataclass(frozen=True)
class EntryResult:
    """Combined result of fetching an entry and downloading its files."""

    entry: Entry
    downloaded_files: tuple[DownloadedFile, ...] = ()
    failed_downloads: tuple[FailedDownload, ...] = ()
    content_md_path: str = ""

    def generate_content_markdown(self) -> str:
        """Generate markdown content for the entry with embedded images."""
        lines: list[str] = []
        lines.append(f"# {self.entry.subject}")
        lines.append("")

        for value in self.entry.body.values():
            text = str(value).strip()
            if text:
                lines.append(text)
                lines.append("")

        if self.entry.filename and _is_image_file(self.entry.filename):
            lines.append(f"![{self.entry.filename}]({self.entry.filename})")
            lines.append("")

        for att in self.entry.attachments:
            if att.type == "text":
                for value in att.body.values():
                    text = str(value).strip()
                    if text:
                        lines.append(text)
                        lines.append("")
            elif att.type == "file" and att.filename and _is_image_file(att.filename):
                lines.append(f"![{att.filename}]({att.filename})")
                lines.append("")

        return "\n".join(lines)

    def format_output(self) -> str:
        """Format the entry and downloaded files for display."""
        lines: list[str] = []
        lines.append(f"Entry #{self.entry.id}: {self.entry.subject}")
        lines.append(f"Type: {self.entry.type}")

        if self.entry.body:
            lines.append("")
            lines.append("Body:")
            for key, value in self.entry.body.items():
                lines.append(f"  {key}: {value}")

        if self.entry.filename:
            lines.append(f"File: {self.entry.filename} ({self.entry.file_size} bytes)")

        if self.entry.attachments:
            lines.append("")
            lines.append(f"Attachments ({len(self.entry.attachments)}):")
            for att in self.entry.attachments:
                if att.filename:
                    lines.append(f"  [{att.id}] {att.type}: {att.filename} ({att.file_size} bytes)")
                else:
                    lines.append(f"  [{att.id}] {att.type}")
                if att.body:
                    for key, value in att.body.items():
                        lines.append(f"    {key}: {value}")

        if self.downloaded_files:
            lines.append("")
            lines.append("Downloaded files:")
            for df in self.downloaded_files:
                lines.append(f"  {df.filename} -> {df.file_path} ({df.file_size} bytes)")

        if self.failed_downloads:
            lines.append("")
            lines.append("Failed downloads:")
            for fd in self.failed_downloads:
                lines.append(f"  [{fd.attachment_id}] {fd.filename}: {fd.error}")

        if self.content_md_path:
            lines.append("")
            lines.append(f"Content markdown: {self.content_md_path}")

        return "\n".join(lines)
