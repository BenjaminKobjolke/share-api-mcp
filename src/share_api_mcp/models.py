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


@dataclass(frozen=True)
class MessageResult:
    """Simple message response from DELETE or mutation operations."""

    message: str

    def format_output(self) -> str:
        return self.message


@dataclass(frozen=True)
class EntrySummary:
    """An entry summary from the list endpoint."""

    id: int
    type: str
    subject: str
    body: str = ""
    filename: str = ""
    file_size: int = 0
    attachment_count: int = 0
    created_at: str = ""


@dataclass(frozen=True)
class EntryListResult:
    """Paginated list of entry summaries."""

    entries: tuple[EntrySummary, ...] = ()
    total: int = 0
    page: int = 1
    per_page: int = 20

    def format_output(self) -> str:
        lines: list[str] = []
        lines.append(f"Entries (page {self.page}, {self.total} total):")
        for e in self.entries:
            parts = [f"  [{e.id}] {e.subject} ({e.type})"]
            if e.filename:
                parts.append(f" file={e.filename}")
            if e.attachment_count:
                parts.append(f" attachments={e.attachment_count}")
            lines.append("".join(parts))
        return "\n".join(lines)


@dataclass(frozen=True)
class CustomField:
    """A custom field definition."""

    name: str
    description: str = ""
    sort_order: int = 0
    option_count: int = 0
    created_at: str = ""

    def format_output(self) -> str:
        lines = [f"Custom field: {self.name}"]
        if self.description:
            lines.append(f"  Description: {self.description}")
        lines.append(f"  Sort order: {self.sort_order}")
        if self.option_count:
            lines.append(f"  Options: {self.option_count}")
        return "\n".join(lines)


@dataclass(frozen=True)
class CustomFieldListResult:
    """List of custom fields."""

    fields: tuple[CustomField, ...] = ()

    def format_output(self) -> str:
        lines = [f"Custom fields ({len(self.fields)}):"]
        for f in self.fields:
            lines.append(f"  {f.name} (sort={f.sort_order}, options={f.option_count})")
        return "\n".join(lines)


@dataclass(frozen=True)
class FieldOption:
    """An option value for a custom field."""

    id: int
    field_name: str
    name: str
    created_at: str = ""
    entry_count: int = 0

    def format_output(self) -> str:
        return f"Option [{self.id}] {self.field_name}: {self.name} (entries={self.entry_count})"


@dataclass(frozen=True)
class FieldOptionListResult:
    """List of options for a custom field."""

    field_name: str
    options: tuple[FieldOption, ...] = ()

    def format_output(self) -> str:
        lines = [f"Options for '{self.field_name}' ({len(self.options)}):"]
        for o in self.options:
            lines.append(f"  [{o.id}] {o.name} (entries={o.entry_count})")
        return "\n".join(lines)


@dataclass(frozen=True)
class ExportedField:
    """A custom field with its option names for export."""

    name: str
    description: str = ""
    sort_order: int = 0
    options: tuple[str, ...] = ()


@dataclass(frozen=True)
class CustomFieldExportResult:
    """Export of all custom fields with their options."""

    fields: tuple[ExportedField, ...] = ()

    def format_output(self) -> str:
        lines = [f"Exported fields ({len(self.fields)}):"]
        for f in self.fields:
            lines.append(f"  {f.name} (sort={f.sort_order}, options={len(f.options)})")
            for opt in f.options:
                lines.append(f"    - {opt}")
        return "\n".join(lines)


@dataclass(frozen=True)
class ImportResult:
    """Result of importing custom fields."""

    fields_created: int = 0
    options_created: int = 0

    def format_output(self) -> str:
        return (
            f"Import complete: {self.fields_created} fields created, "
            f"{self.options_created} options created"
        )


@dataclass(frozen=True)
class AuthInfo:
    """Authentication method info from the API."""

    method: str

    def format_output(self) -> str:
        return f"Auth method: {self.method}"


@dataclass(frozen=True)
class FieldDescriptor:
    """Schema descriptor for a field."""

    name: str
    type: str = ""
    description: str = ""
    resource_path: str = ""


@dataclass(frozen=True)
class FieldListResult:
    """List of field descriptors from the schema endpoint."""

    fields: tuple[FieldDescriptor, ...] = ()

    def format_output(self) -> str:
        lines = [f"Fields ({len(self.fields)}):"]
        for f in self.fields:
            parts = [f"  {f.name}"]
            if f.type:
                parts.append(f" ({f.type})")
            if f.description:
                parts.append(f" - {f.description}")
            lines.append("".join(parts))
        return "\n".join(lines)
