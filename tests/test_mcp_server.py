"""Tests for the MCP server tool function."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from share_api_mcp.models import Attachment, Entry, EntryResult, FailedDownload


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
