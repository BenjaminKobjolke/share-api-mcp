"""Tests for the MCP server tool function."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from share_api_mcp.models import (
    Attachment,
    AuthInfo,
    CustomField,
    CustomFieldExportResult,
    CustomFieldListResult,
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


def test_fetch_shared_entry_no_base_url() -> None:
    with patch.dict("os.environ", {}, clear=True):
        from share_api_mcp.mcp_server import fetch_shared_entry

        result = fetch_shared_entry(entry_id=1, base_url="", download_dir="")
    assert "Error" in result
    assert "base_url" in result.lower() or "base_url" in result


def test_fetch_shared_entry_success() -> None:
    entry = Entry(id=42, type="note", subject="Test Note", body={"content": "Hello"})
    entry_result = EntryResult(entry=entry)

    mock_client = MagicMock()
    mock_client.fetch_entry_with_files.return_value = entry_result

    with (
        patch.dict("os.environ", {"SHARE_API_BASE_URL": "http://example.com"}, clear=True),
        patch("share_api_mcp.mcp_server.ShareApiClient", return_value=mock_client),
    ):
        from share_api_mcp.mcp_server import fetch_shared_entry

        result = fetch_shared_entry(entry_id=42)

    assert "Entry #42: Test Note" in result
    assert "content: Hello" in result


def test_fetch_shared_entry_tool_arg_overrides_env() -> None:
    entry = Entry(id=1, type="note", subject="X")
    entry_result = EntryResult(entry=entry)

    mock_client = MagicMock()
    mock_client.fetch_entry_with_files.return_value = entry_result

    with (
        patch.dict(
            "os.environ",
            {"SHARE_API_BASE_URL": "http://env-url.com"},
            clear=True,
        ),
        patch("share_api_mcp.mcp_server.ShareApiClient", return_value=mock_client),
    ):
        from share_api_mcp.mcp_server import fetch_shared_entry

        fetch_shared_entry(entry_id=1, base_url="http://arg-url.com")

    mock_client.fetch_entry_with_files.assert_called_once_with(
        "http://arg-url.com", 1, "./downloads"
    )


def test_fetch_shared_entry_exception_returns_error() -> None:
    mock_client = MagicMock()
    mock_client.fetch_entry_with_files.side_effect = RuntimeError("connection failed")

    with (
        patch.dict("os.environ", {"SHARE_API_BASE_URL": "http://example.com"}, clear=True),
        patch("share_api_mcp.mcp_server.ShareApiClient", return_value=mock_client),
    ):
        from share_api_mcp.mcp_server import fetch_shared_entry

        result = fetch_shared_entry(entry_id=99)

    assert "Error" in result
    assert "connection failed" in result


def test_fetch_shared_entry_partial_success_shows_failed_downloads() -> None:
    att = Attachment(id=8, type="file", filename="missing.png", file_size=5000)
    entry = Entry(
        id=19, type="share", subject="Partial", attachments=(att,)
    )
    fd = FailedDownload(
        attachment_id=8,
        filename="missing.png",
        error="File not available on server",
    )
    entry_result = EntryResult(entry=entry, failed_downloads=(fd,))

    mock_client = MagicMock()
    mock_client.fetch_entry_with_files.return_value = entry_result

    with (
        patch.dict(
            "os.environ",
            {"SHARE_API_BASE_URL": "http://example.com"},
            clear=True,
        ),
        patch("share_api_mcp.mcp_server.ShareApiClient", return_value=mock_client),
    ):
        from share_api_mcp.mcp_server import fetch_shared_entry

        result = fetch_shared_entry(entry_id=19)

    assert "Entry #19: Partial" in result
    assert "Failed downloads:" in result
    assert "[8] missing.png: File not available on server" in result


# --- list_entries ---


def test_list_entries_success() -> None:
    entries = (
        EntrySummary(id=1, type="note", subject="A"),
        EntrySummary(id=2, type="file", subject="B"),
    )
    entry_list = EntryListResult(entries=entries, total=2, page=1, per_page=20)

    mock_client = MagicMock()
    mock_client.list_entries.return_value = entry_list

    with (
        patch.dict("os.environ", {"SHARE_API_BASE_URL": "http://example.com"}, clear=True),
        patch("share_api_mcp.mcp_server.ShareApiClient", return_value=mock_client),
    ):
        from share_api_mcp.mcp_server import list_entries

        result = list_entries()

    assert "page 1" in result
    assert "[1] A" in result


def test_list_entries_error() -> None:
    mock_client = MagicMock()
    mock_client.list_entries.side_effect = RuntimeError("fail")

    with (
        patch.dict("os.environ", {"SHARE_API_BASE_URL": "http://example.com"}, clear=True),
        patch("share_api_mcp.mcp_server.ShareApiClient", return_value=mock_client),
    ):
        from share_api_mcp.mcp_server import list_entries

        result = list_entries()

    assert "Error" in result


def test_list_entries_invalid_filters_json() -> None:
    with patch.dict("os.environ", {"SHARE_API_BASE_URL": "http://example.com"}, clear=True):
        from share_api_mcp.mcp_server import list_entries

        result = list_entries(filters="not json")

    assert "Error" in result
    assert "Invalid filters JSON" in result


# --- update_entry ---


def test_update_entry_success() -> None:
    entry = Entry(id=42, type="note", subject="Updated")

    mock_client = MagicMock()
    mock_client.update_entry.return_value = entry

    with (
        patch.dict("os.environ", {"SHARE_API_BASE_URL": "http://example.com"}, clear=True),
        patch("share_api_mcp.mcp_server.ShareApiClient", return_value=mock_client),
    ):
        from share_api_mcp.mcp_server import update_entry

        result = update_entry(entry_id=42, subject="Updated")

    assert "Updated entry #42" in result


def test_update_entry_invalid_body_json() -> None:
    with patch.dict("os.environ", {"SHARE_API_BASE_URL": "http://example.com"}, clear=True):
        from share_api_mcp.mcp_server import update_entry

        result = update_entry(entry_id=1, body="not json")

    assert "Error" in result
    assert "Invalid body JSON" in result


# --- delete_entry ---


def test_delete_entry_success() -> None:
    mock_client = MagicMock()
    mock_client.delete_entry.return_value = MessageResult(message="Entry deleted")

    with (
        patch.dict("os.environ", {"SHARE_API_BASE_URL": "http://example.com"}, clear=True),
        patch("share_api_mcp.mcp_server.ShareApiClient", return_value=mock_client),
    ):
        from share_api_mcp.mcp_server import delete_entry

        result = delete_entry(entry_id=42)

    assert "Entry deleted" in result


# --- list_custom_fields ---


def test_list_custom_fields_success() -> None:
    fields = (CustomField(name="status", sort_order=1, option_count=3),)
    mock_client = MagicMock()
    mock_client.list_custom_fields.return_value = CustomFieldListResult(fields=fields)

    with (
        patch.dict("os.environ", {"SHARE_API_BASE_URL": "http://example.com"}, clear=True),
        patch("share_api_mcp.mcp_server.ShareApiClient", return_value=mock_client),
    ):
        from share_api_mcp.mcp_server import list_custom_fields

        result = list_custom_fields()

    assert "status" in result


# --- create_custom_field ---


def test_create_custom_field_success() -> None:
    mock_client = MagicMock()
    mock_client.create_custom_field.return_value = CustomField(name="priority", sort_order=2)

    with (
        patch.dict("os.environ", {"SHARE_API_BASE_URL": "http://example.com"}, clear=True),
        patch("share_api_mcp.mcp_server.ShareApiClient", return_value=mock_client),
    ):
        from share_api_mcp.mcp_server import create_custom_field

        result = create_custom_field(name="priority", sort_order=2)

    assert "priority" in result


# --- update_custom_field ---


def test_update_custom_field_success() -> None:
    mock_client = MagicMock()
    mock_client.update_custom_field.return_value = CustomField(name="status", description="Updated")

    with (
        patch.dict("os.environ", {"SHARE_API_BASE_URL": "http://example.com"}, clear=True),
        patch("share_api_mcp.mcp_server.ShareApiClient", return_value=mock_client),
    ):
        from share_api_mcp.mcp_server import update_custom_field

        result = update_custom_field(name="status", description="Updated")

    assert "status" in result


# --- delete_custom_field ---


def test_delete_custom_field_success() -> None:
    mock_client = MagicMock()
    mock_client.delete_custom_field.return_value = MessageResult(message="Custom field deleted")

    with (
        patch.dict("os.environ", {"SHARE_API_BASE_URL": "http://example.com"}, clear=True),
        patch("share_api_mcp.mcp_server.ShareApiClient", return_value=mock_client),
    ):
        from share_api_mcp.mcp_server import delete_custom_field

        result = delete_custom_field(name="status")

    assert "Custom field deleted" in result


# --- export_custom_fields ---


def test_export_custom_fields_success() -> None:
    fields = (ExportedField(name="status", options=("open", "closed")),)
    mock_client = MagicMock()
    mock_client.export_custom_fields.return_value = CustomFieldExportResult(fields=fields)

    with (
        patch.dict("os.environ", {"SHARE_API_BASE_URL": "http://example.com"}, clear=True),
        patch("share_api_mcp.mcp_server.ShareApiClient", return_value=mock_client),
    ):
        from share_api_mcp.mcp_server import export_custom_fields

        result = export_custom_fields()

    assert "status" in result
    assert "open" in result


# --- import_custom_fields ---


def test_import_custom_fields_success() -> None:
    mock_client = MagicMock()
    mock_client.import_custom_fields.return_value = ImportResult(
        fields_created=2, options_created=5,
    )

    with (
        patch.dict("os.environ", {"SHARE_API_BASE_URL": "http://example.com"}, clear=True),
        patch("share_api_mcp.mcp_server.ShareApiClient", return_value=mock_client),
    ):
        from share_api_mcp.mcp_server import import_custom_fields

        result = import_custom_fields(fields_json='{"fields": []}')

    assert "2 fields created" in result
    assert "5 options created" in result


def test_import_custom_fields_invalid_json() -> None:
    with patch.dict("os.environ", {"SHARE_API_BASE_URL": "http://example.com"}, clear=True):
        from share_api_mcp.mcp_server import import_custom_fields

        result = import_custom_fields(fields_json="not json")

    assert "Error" in result
    assert "Invalid fields_json" in result


# --- list_field_options ---


def test_list_field_options_success() -> None:
    opts = (FieldOption(id=1, field_name="status", name="open", entry_count=5),)
    mock_client = MagicMock()
    mock_client.list_field_options.return_value = FieldOptionListResult(
        field_name="status", options=opts
    )

    with (
        patch.dict("os.environ", {"SHARE_API_BASE_URL": "http://example.com"}, clear=True),
        patch("share_api_mcp.mcp_server.ShareApiClient", return_value=mock_client),
    ):
        from share_api_mcp.mcp_server import list_field_options

        result = list_field_options(field_name="status")

    assert "status" in result
    assert "open" in result


# --- create_field_option ---


def test_create_field_option_success() -> None:
    mock_client = MagicMock()
    mock_client.create_field_option.return_value = FieldOption(
        id=10, field_name="status", name="pending"
    )

    with (
        patch.dict("os.environ", {"SHARE_API_BASE_URL": "http://example.com"}, clear=True),
        patch("share_api_mcp.mcp_server.ShareApiClient", return_value=mock_client),
    ):
        from share_api_mcp.mcp_server import create_field_option

        result = create_field_option(field_name="status", name="pending")

    assert "pending" in result


# --- update_field_option ---


def test_update_field_option_success() -> None:
    mock_client = MagicMock()
    mock_client.update_field_option.return_value = FieldOption(
        id=5, field_name="status", name="renamed"
    )

    with (
        patch.dict("os.environ", {"SHARE_API_BASE_URL": "http://example.com"}, clear=True),
        patch("share_api_mcp.mcp_server.ShareApiClient", return_value=mock_client),
    ):
        from share_api_mcp.mcp_server import update_field_option

        result = update_field_option(field_name="status", option_id=5, name="renamed")

    assert "renamed" in result


# --- delete_field_option ---


def test_delete_field_option_success() -> None:
    mock_client = MagicMock()
    mock_client.delete_field_option.return_value = MessageResult(message="Option deleted")

    with (
        patch.dict("os.environ", {"SHARE_API_BASE_URL": "http://example.com"}, clear=True),
        patch("share_api_mcp.mcp_server.ShareApiClient", return_value=mock_client),
    ):
        from share_api_mcp.mcp_server import delete_field_option

        result = delete_field_option(field_name="status", option_id=5)

    assert "Option deleted" in result


# --- delete_attachment ---


def test_delete_attachment_success() -> None:
    mock_client = MagicMock()
    mock_client.delete_attachment.return_value = MessageResult(message="Attachment deleted")

    with (
        patch.dict("os.environ", {"SHARE_API_BASE_URL": "http://example.com"}, clear=True),
        patch("share_api_mcp.mcp_server.ShareApiClient", return_value=mock_client),
    ):
        from share_api_mcp.mcp_server import delete_attachment

        result = delete_attachment(attachment_id=99)

    assert "Attachment deleted" in result


# --- get_auth_info ---


def test_get_auth_info_success() -> None:
    mock_client = MagicMock()
    mock_client.get_auth_info.return_value = AuthInfo(method="basic")

    with (
        patch.dict("os.environ", {"SHARE_API_BASE_URL": "http://example.com"}, clear=True),
        patch("share_api_mcp.mcp_server.ShareApiClient", return_value=mock_client),
    ):
        from share_api_mcp.mcp_server import get_auth_info

        result = get_auth_info()

    assert "basic" in result


# --- list_fields ---


def test_list_fields_success() -> None:
    fields = (
        FieldDescriptor(name="subject", type="string", description="Entry subject"),
    )
    mock_client = MagicMock()
    mock_client.list_fields.return_value = FieldListResult(fields=fields)

    with (
        patch.dict("os.environ", {"SHARE_API_BASE_URL": "http://example.com"}, clear=True),
        patch("share_api_mcp.mcp_server.ShareApiClient", return_value=mock_client),
    ):
        from share_api_mcp.mcp_server import list_fields

        result = list_fields()

    assert "subject" in result
    assert "string" in result


# --- create_entry ---


def test_create_entry_success() -> None:
    mock_client = MagicMock()
    mock_client.create_entry.return_value = "123"

    with (
        patch.dict("os.environ", {"SHARE_API_BASE_URL": "http://example.com"}, clear=True),
        patch("share_api_mcp.mcp_server.ShareApiClient", return_value=mock_client),
    ):
        from share_api_mcp.mcp_server import create_entry

        result = create_entry(text_or_url="Hello")

    assert "123" in result


def test_create_entry_invalid_extra_fields_json() -> None:
    with patch.dict("os.environ", {"SHARE_API_BASE_URL": "http://example.com"}, clear=True):
        from share_api_mcp.mcp_server import create_entry

        result = create_entry(extra_fields="not json")

    assert "Error" in result
    assert "Invalid extra_fields JSON" in result


def test_create_entry_error() -> None:
    mock_client = MagicMock()
    mock_client.create_entry.side_effect = RuntimeError("fail")

    with (
        patch.dict("os.environ", {"SHARE_API_BASE_URL": "http://example.com"}, clear=True),
        patch("share_api_mcp.mcp_server.ShareApiClient", return_value=mock_client),
    ):
        from share_api_mcp.mcp_server import create_entry

        result = create_entry(text_or_url="Hello")

    assert "Error" in result
    assert "fail" in result


# --- Missing base_url ---


def test_tool_missing_base_url() -> None:
    with patch.dict("os.environ", {}, clear=True):
        from share_api_mcp.mcp_server import list_entries

        result = list_entries()

    assert "Error" in result
    assert "base_url" in result.lower() or "base_url" in result
