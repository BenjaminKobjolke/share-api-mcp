"""Tests for the Share API client."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import httpx

from share_api_mcp.api_client import (
    ShareApiClient,
    _parse_attachment,
    _parse_custom_field,
    _parse_entry,
    _parse_entry_summary,
    _parse_exported_field,
    _parse_field_descriptor,
    _parse_field_option,
)
from share_api_mcp.config.settings import Settings


def _make_settings(base_url: str = "http://example.com") -> Settings:
    return Settings(base_url=base_url)


def _sample_entry_json() -> dict:  # type: ignore[type-arg]
    return {
        "id": 42,
        "type": "share",
        "subject": "Test Entry",
        "body": {"content": "Hello world"},
        "filename": "",
        "file_size": 0,
        "attachments": [
            {
                "id": 1,
                "type": "text",
                "body": {"content": "inline note"},
                "filename": "",
                "file_size": 0,
            },
            {
                "id": 2,
                "type": "file",
                "body": {},
                "filename": "report.pdf",
                "file_size": 4096,
                "file_url": "http://example.com/api.php/files/2",
            },
        ],
    }


def test_parse_attachment() -> None:
    data = {"id": 5, "type": "file", "body": {}, "filename": "a.txt", "file_size": 100}
    att = _parse_attachment(data)
    assert att.id == 5
    assert att.type == "file"
    assert att.filename == "a.txt"
    assert att.file_size == 100


def test_parse_entry() -> None:
    entry = _parse_entry(_sample_entry_json())
    assert entry.id == 42
    assert entry.subject == "Test Entry"
    assert len(entry.attachments) == 2
    assert entry.attachments[0].type == "text"
    assert entry.attachments[1].filename == "report.pdf"


def test_fetch_entry_parses_response() -> None:
    settings = _make_settings()
    client = ShareApiClient(settings)

    mock_response = MagicMock()
    mock_response.json.return_value = _sample_entry_json()
    mock_response.raise_for_status = MagicMock()

    with patch("share_api_mcp.api_client.httpx.Client") as mock_httpx:
        mock_http_client = MagicMock()
        mock_http_client.__enter__ = MagicMock(return_value=mock_http_client)
        mock_http_client.__exit__ = MagicMock(return_value=False)
        mock_http_client.get.return_value = mock_response
        mock_httpx.return_value = mock_http_client

        entry = client.fetch_entry("http://example.com", 42)

    assert entry.id == 42
    assert entry.subject == "Test Entry"
    mock_http_client.get.assert_called_once_with(
        "http://example.com/api.php/entries/42"
    )


def test_fetch_entry_replaces_localhost_with_127_0_0_1() -> None:
    settings = _make_settings()
    client = ShareApiClient(settings)

    mock_response = MagicMock()
    mock_response.json.return_value = _sample_entry_json()
    mock_response.raise_for_status = MagicMock()

    with patch("share_api_mcp.api_client.httpx.Client") as mock_httpx:
        mock_http_client = MagicMock()
        mock_http_client.__enter__ = MagicMock(return_value=mock_http_client)
        mock_http_client.__exit__ = MagicMock(return_value=False)
        mock_http_client.get.return_value = mock_response
        mock_httpx.return_value = mock_http_client

        client.fetch_entry("http://localhost/share", 42)

    mock_http_client.get.assert_called_once_with(
        "http://127.0.0.1/share/api.php/entries/42"
    )


def test_fetch_entry_strips_trailing_slash() -> None:
    settings = _make_settings()
    client = ShareApiClient(settings)

    mock_response = MagicMock()
    mock_response.json.return_value = _sample_entry_json()
    mock_response.raise_for_status = MagicMock()

    with patch("share_api_mcp.api_client.httpx.Client") as mock_httpx:
        mock_http_client = MagicMock()
        mock_http_client.__enter__ = MagicMock(return_value=mock_http_client)
        mock_http_client.__exit__ = MagicMock(return_value=False)
        mock_http_client.get.return_value = mock_response
        mock_httpx.return_value = mock_http_client

        client.fetch_entry("http://example.com///", 42)

    mock_http_client.get.assert_called_once_with(
        "http://example.com/api.php/entries/42"
    )


def test_download_creates_directory_and_saves(tmp_path: Path) -> None:
    settings = _make_settings()
    client = ShareApiClient(settings)
    download_dir = str(tmp_path / "new_subdir")

    mock_stream_response = MagicMock()
    mock_stream_response.raise_for_status = MagicMock()
    mock_stream_response.iter_bytes.return_value = [b"file", b"data"]
    mock_stream_response.__enter__ = MagicMock(return_value=mock_stream_response)
    mock_stream_response.__exit__ = MagicMock(return_value=False)

    with patch("share_api_mcp.api_client.httpx.Client") as mock_httpx:
        mock_http_client = MagicMock()
        mock_http_client.__enter__ = MagicMock(return_value=mock_http_client)
        mock_http_client.__exit__ = MagicMock(return_value=False)
        mock_http_client.stream.return_value = mock_stream_response
        mock_httpx.return_value = mock_http_client

        df = client.download_file("http://example.com", 5, "test.bin", download_dir)

    assert df.attachment_id == 5
    assert df.filename == "test.bin"
    assert df.file_size == 8
    assert Path(df.file_path).exists()
    assert Path(df.file_path).read_bytes() == b"filedata"


def test_fetch_entry_with_files_downloads_only_file_attachments(tmp_path: Path) -> None:
    settings = _make_settings()
    client = ShareApiClient(settings)

    mock_response = MagicMock()
    mock_response.json.return_value = _sample_entry_json()
    mock_response.raise_for_status = MagicMock()

    mock_stream_response = MagicMock()
    mock_stream_response.raise_for_status = MagicMock()
    mock_stream_response.iter_bytes.return_value = [b"pdfdata"]
    mock_stream_response.__enter__ = MagicMock(return_value=mock_stream_response)
    mock_stream_response.__exit__ = MagicMock(return_value=False)

    with patch("share_api_mcp.api_client.httpx.Client") as mock_httpx:
        mock_http_client = MagicMock()
        mock_http_client.__enter__ = MagicMock(return_value=mock_http_client)
        mock_http_client.__exit__ = MagicMock(return_value=False)
        mock_http_client.get.return_value = mock_response
        mock_http_client.stream.return_value = mock_stream_response
        mock_httpx.return_value = mock_http_client

        result = client.fetch_entry_with_files(
            "http://example.com", 42, str(tmp_path)
        )

    # Only the file attachment (id=2) should be downloaded, not the text one (id=1)
    assert len(result.downloaded_files) == 1
    assert result.downloaded_files[0].attachment_id == 2
    assert result.downloaded_files[0].filename == "report.pdf"


def test_auth_credentials_used() -> None:
    settings = Settings(
        base_url="http://example.com",
        auth_user="admin",
        auth_password="secret",
    )
    client = ShareApiClient(settings)
    assert client._auth is not None


def test_no_auth_when_empty() -> None:
    settings = Settings(base_url="http://example.com")
    client = ShareApiClient(settings)
    assert client._auth is None


def test_parse_attachment_with_file_url() -> None:
    data = {
        "id": 5,
        "type": "file",
        "body": {},
        "filename": "a.txt",
        "file_size": 100,
        "file_url": "http://example.com/api.php/files/5",
    }
    att = _parse_attachment(data)
    assert att.file_url == "http://example.com/api.php/files/5"


def test_attachment_without_file_url_recorded_as_failed(tmp_path: Path) -> None:
    """Attachment with no file_url is skipped and recorded as FailedDownload."""
    settings = _make_settings()
    client = ShareApiClient(settings)

    entry_json = {
        "id": 19,
        "type": "share",
        "subject": "Missing File",
        "body": {},
        "filename": "",
        "file_size": 0,
        "attachments": [
            {
                "id": 8,
                "type": "file",
                "body": {},
                "filename": "missing.png",
                "file_size": 5000,
                # no file_url — file is unavailable on server
            },
        ],
    }

    mock_response = MagicMock()
    mock_response.json.return_value = entry_json
    mock_response.raise_for_status = MagicMock()

    with patch("share_api_mcp.api_client.httpx.Client") as mock_httpx:
        mock_http_client = MagicMock()
        mock_http_client.__enter__ = MagicMock(return_value=mock_http_client)
        mock_http_client.__exit__ = MagicMock(return_value=False)
        mock_http_client.get.return_value = mock_response
        mock_httpx.return_value = mock_http_client

        result = client.fetch_entry_with_files(
            "http://example.com", 19, str(tmp_path)
        )

    assert result.entry.id == 19
    assert len(result.downloaded_files) == 0
    assert len(result.failed_downloads) == 1
    assert result.failed_downloads[0].attachment_id == 8
    assert result.failed_downloads[0].filename == "missing.png"
    assert "not available" in result.failed_downloads[0].error

    # download_file should never have been called
    mock_http_client.stream.assert_not_called()


def test_http_error_during_download_caught_gracefully(tmp_path: Path) -> None:
    """HTTP error during download is caught; entry data is preserved."""
    settings = _make_settings()
    client = ShareApiClient(settings)

    entry_json = {
        "id": 19,
        "type": "share",
        "subject": "Broken File",
        "body": {},
        "filename": "",
        "file_size": 0,
        "attachments": [
            {
                "id": 8,
                "type": "file",
                "body": {},
                "filename": "broken.png",
                "file_size": 5000,
                "file_url": "http://example.com/api.php/files/8",
            },
        ],
    }

    mock_response = MagicMock()
    mock_response.json.return_value = entry_json
    mock_response.raise_for_status = MagicMock()

    with patch("share_api_mcp.api_client.httpx.Client") as mock_httpx:
        mock_http_client = MagicMock()
        mock_http_client.__enter__ = MagicMock(return_value=mock_http_client)
        mock_http_client.__exit__ = MagicMock(return_value=False)
        mock_http_client.get.return_value = mock_response
        mock_httpx.return_value = mock_http_client

    with patch.object(
        client,
        "download_file",
        side_effect=httpx.HTTPStatusError(
            "Not Found",
            request=MagicMock(),
            response=MagicMock(status_code=404),
        ),
    ):
        with patch.object(client, "fetch_entry", return_value=_parse_entry(entry_json)):
            result = client.fetch_entry_with_files(
                "http://example.com", 19, str(tmp_path)
            )

    assert result.entry.id == 19
    assert result.entry.subject == "Broken File"
    assert len(result.downloaded_files) == 0
    assert len(result.failed_downloads) == 1
    assert result.failed_downloads[0].attachment_id == 8
    assert "Not Found" in result.failed_downloads[0].error


def test_mix_of_successful_and_failed_downloads(tmp_path: Path) -> None:
    """One attachment succeeds, another fails — both are reported."""
    settings = _make_settings()
    client = ShareApiClient(settings)

    entry_json = {
        "id": 50,
        "type": "share",
        "subject": "Mixed",
        "body": {},
        "filename": "",
        "file_size": 0,
        "attachments": [
            {
                "id": 10,
                "type": "file",
                "body": {},
                "filename": "good.pdf",
                "file_size": 1024,
                "file_url": "http://example.com/api.php/files/10",
            },
            {
                "id": 11,
                "type": "file",
                "body": {},
                "filename": "bad.png",
                "file_size": 2048,
                # no file_url
            },
        ],
    }

    mock_response = MagicMock()
    mock_response.json.return_value = entry_json
    mock_response.raise_for_status = MagicMock()

    mock_stream_response = MagicMock()
    mock_stream_response.raise_for_status = MagicMock()
    mock_stream_response.iter_bytes.return_value = [b"pdfdata"]
    mock_stream_response.__enter__ = MagicMock(return_value=mock_stream_response)
    mock_stream_response.__exit__ = MagicMock(return_value=False)

    with patch("share_api_mcp.api_client.httpx.Client") as mock_httpx:
        mock_http_client = MagicMock()
        mock_http_client.__enter__ = MagicMock(return_value=mock_http_client)
        mock_http_client.__exit__ = MagicMock(return_value=False)
        mock_http_client.get.return_value = mock_response
        mock_http_client.stream.return_value = mock_stream_response
        mock_httpx.return_value = mock_http_client

        result = client.fetch_entry_with_files(
            "http://example.com", 50, str(tmp_path)
        )

    assert result.entry.id == 50
    assert len(result.downloaded_files) == 1
    assert result.downloaded_files[0].attachment_id == 10
    assert result.downloaded_files[0].filename == "good.pdf"
    assert len(result.failed_downloads) == 1
    assert result.failed_downloads[0].attachment_id == 11
    assert result.failed_downloads[0].filename == "bad.png"


def test_parse_entry_with_file_url() -> None:
    data = {
        "id": 21,
        "type": "file",
        "subject": "Uploaded Doc",
        "body": {},
        "filename": "doc.pdf",
        "file_size": 9000,
        "file_url": "http://example.com/api.php/entries/21/file",
        "attachments": [],
    }
    entry = _parse_entry(data)
    assert entry.file_url == "http://example.com/api.php/entries/21/file"


def test_entry_file_url_downloaded(tmp_path: Path) -> None:
    """Entry with file_url triggers download of entry-level file."""
    settings = _make_settings()
    client = ShareApiClient(settings)

    entry_json = {
        "id": 21,
        "type": "file",
        "subject": "Uploaded Doc",
        "body": {},
        "filename": "doc.pdf",
        "file_size": 9000,
        "file_url": "http://example.com/api.php/entries/21/file",
        "attachments": [],
    }

    mock_response = MagicMock()
    mock_response.json.return_value = entry_json
    mock_response.raise_for_status = MagicMock()

    mock_stream_response = MagicMock()
    mock_stream_response.raise_for_status = MagicMock()
    mock_stream_response.iter_bytes.return_value = [b"pdfbytes"]
    mock_stream_response.__enter__ = MagicMock(return_value=mock_stream_response)
    mock_stream_response.__exit__ = MagicMock(return_value=False)

    with patch("share_api_mcp.api_client.httpx.Client") as mock_httpx:
        mock_http_client = MagicMock()
        mock_http_client.__enter__ = MagicMock(return_value=mock_http_client)
        mock_http_client.__exit__ = MagicMock(return_value=False)
        mock_http_client.get.return_value = mock_response
        mock_http_client.stream.return_value = mock_stream_response
        mock_httpx.return_value = mock_http_client

        result = client.fetch_entry_with_files(
            "http://example.com", 21, str(tmp_path)
        )

    assert len(result.downloaded_files) == 1
    assert result.downloaded_files[0].attachment_id == 21
    assert result.downloaded_files[0].filename == "doc.pdf"
    assert Path(result.downloaded_files[0].file_path).exists()
    assert Path(result.downloaded_files[0].file_path).read_bytes() == b"pdfbytes"


def test_entry_without_file_url_no_download(tmp_path: Path) -> None:
    """Entry without file_url does not attempt entry-level file download."""
    settings = _make_settings()
    client = ShareApiClient(settings)

    entry_json = {
        "id": 42,
        "type": "text",
        "subject": "Text Entry",
        "body": {"content": "hello"},
        "filename": "",
        "file_size": 0,
        "attachments": [],
    }

    mock_response = MagicMock()
    mock_response.json.return_value = entry_json
    mock_response.raise_for_status = MagicMock()

    with patch("share_api_mcp.api_client.httpx.Client") as mock_httpx:
        mock_http_client = MagicMock()
        mock_http_client.__enter__ = MagicMock(return_value=mock_http_client)
        mock_http_client.__exit__ = MagicMock(return_value=False)
        mock_http_client.get.return_value = mock_response
        mock_httpx.return_value = mock_http_client

        result = client.fetch_entry_with_files(
            "http://example.com", 42, str(tmp_path)
        )

    assert len(result.downloaded_files) == 0
    assert len(result.failed_downloads) == 0
    # stream should never be called (no files to download)
    mock_http_client.stream.assert_not_called()


def test_entry_file_download_error_caught_gracefully(tmp_path: Path) -> None:
    """Error downloading entry-level file is caught and recorded as failed."""
    settings = _make_settings()
    client = ShareApiClient(settings)

    entry_json = {
        "id": 21,
        "type": "file",
        "subject": "Broken Entry File",
        "body": {},
        "filename": "doc.pdf",
        "file_size": 9000,
        "file_url": "http://example.com/api.php/entries/21/file",
        "attachments": [],
    }

    with patch.object(
        client,
        "download_entry_file",
        side_effect=httpx.HTTPStatusError(
            "Server Error",
            request=MagicMock(),
            response=MagicMock(status_code=500),
        ),
    ):
        with patch.object(client, "fetch_entry", return_value=_parse_entry(entry_json)):
            result = client.fetch_entry_with_files(
                "http://example.com", 21, str(tmp_path)
            )

    assert result.entry.id == 21
    assert len(result.downloaded_files) == 0
    assert len(result.failed_downloads) == 1
    assert result.failed_downloads[0].attachment_id == 21
    assert result.failed_downloads[0].filename == "doc.pdf"
    assert "Server Error" in result.failed_downloads[0].error


def test_downloads_go_into_entry_subfolder(tmp_path: Path) -> None:
    """Files are downloaded into {download_dir}/{entry_id}/ subfolder."""
    settings = _make_settings()
    client = ShareApiClient(settings)

    entry_json = {
        "id": 99,
        "type": "share",
        "subject": "Subfolder Test",
        "body": {"content": "hello"},
        "filename": "",
        "file_size": 0,
        "attachments": [
            {
                "id": 3,
                "type": "file",
                "body": {},
                "filename": "pic.png",
                "file_size": 512,
                "file_url": "http://example.com/api.php/files/3",
            },
        ],
    }

    mock_response = MagicMock()
    mock_response.json.return_value = entry_json
    mock_response.raise_for_status = MagicMock()

    mock_stream_response = MagicMock()
    mock_stream_response.raise_for_status = MagicMock()
    mock_stream_response.iter_bytes.return_value = [b"imgdata"]
    mock_stream_response.__enter__ = MagicMock(return_value=mock_stream_response)
    mock_stream_response.__exit__ = MagicMock(return_value=False)

    with patch("share_api_mcp.api_client.httpx.Client") as mock_httpx:
        mock_http_client = MagicMock()
        mock_http_client.__enter__ = MagicMock(return_value=mock_http_client)
        mock_http_client.__exit__ = MagicMock(return_value=False)
        mock_http_client.get.return_value = mock_response
        mock_http_client.stream.return_value = mock_stream_response
        mock_httpx.return_value = mock_http_client

        result = client.fetch_entry_with_files(
            "http://example.com", 99, str(tmp_path)
        )

    entry_dir = tmp_path / "99"
    assert entry_dir.is_dir()
    assert (entry_dir / "pic.png").exists()
    assert result.downloaded_files[0].file_path == str(entry_dir / "pic.png")


def test_content_md_written_to_subfolder(tmp_path: Path) -> None:
    """content.md is written into the entry subfolder."""
    settings = _make_settings()
    client = ShareApiClient(settings)

    entry_json = {
        "id": 77,
        "type": "share",
        "subject": "Content MD Test",
        "body": {"content": "Some text"},
        "filename": "",
        "file_size": 0,
        "attachments": [],
    }

    mock_response = MagicMock()
    mock_response.json.return_value = entry_json
    mock_response.raise_for_status = MagicMock()

    with patch("share_api_mcp.api_client.httpx.Client") as mock_httpx:
        mock_http_client = MagicMock()
        mock_http_client.__enter__ = MagicMock(return_value=mock_http_client)
        mock_http_client.__exit__ = MagicMock(return_value=False)
        mock_http_client.get.return_value = mock_response
        mock_httpx.return_value = mock_http_client

        client.fetch_entry_with_files(
            "http://example.com", 77, str(tmp_path)
        )

    content_md = tmp_path / "77" / "content.md"
    assert content_md.exists()
    text = content_md.read_text(encoding="utf-8")
    assert "# Content MD Test" in text
    assert "Some text" in text


def test_content_md_path_set_on_result(tmp_path: Path) -> None:
    """EntryResult.content_md_path points to the written content.md."""
    settings = _make_settings()
    client = ShareApiClient(settings)

    entry_json = {
        "id": 55,
        "type": "note",
        "subject": "Path Check",
        "body": {},
        "filename": "",
        "file_size": 0,
        "attachments": [],
    }

    mock_response = MagicMock()
    mock_response.json.return_value = entry_json
    mock_response.raise_for_status = MagicMock()

    with patch("share_api_mcp.api_client.httpx.Client") as mock_httpx:
        mock_http_client = MagicMock()
        mock_http_client.__enter__ = MagicMock(return_value=mock_http_client)
        mock_http_client.__exit__ = MagicMock(return_value=False)
        mock_http_client.get.return_value = mock_response
        mock_httpx.return_value = mock_http_client

        result = client.fetch_entry_with_files(
            "http://example.com", 55, str(tmp_path)
        )

    expected_path = str(tmp_path / "55" / "content.md")
    assert result.content_md_path == expected_path
    assert Path(result.content_md_path).exists()


# --- Parser functions ---


def test_parse_entry_summary() -> None:
    data = {
        "id": 10,
        "type": "note",
        "subject": "My Note",
        "body": "raw text",
        "filename": "a.pdf",
        "file_size": 100,
        "attachment_count": 2,
        "created_at": "2024-01-01",
    }
    es = _parse_entry_summary(data)
    assert es.id == 10
    assert es.type == "note"
    assert es.subject == "My Note"
    assert es.body == "raw text"
    assert es.filename == "a.pdf"
    assert es.attachment_count == 2


def test_parse_custom_field() -> None:
    data = {
        "name": "status",
        "description": "Entry status",
        "sort_order": 1,
        "option_count": 3,
        "created_at": "2024-01-01",
    }
    cf = _parse_custom_field(data)
    assert cf.name == "status"
    assert cf.description == "Entry status"
    assert cf.sort_order == 1
    assert cf.option_count == 3


def test_parse_field_option() -> None:
    data = {"id": 5, "field_name": "status", "name": "open", "entry_count": 10}
    fo = _parse_field_option(data)
    assert fo.id == 5
    assert fo.field_name == "status"
    assert fo.name == "open"
    assert fo.entry_count == 10


def test_parse_field_option_with_explicit_field_name() -> None:
    data = {"id": 5, "name": "open"}
    fo = _parse_field_option(data, field_name="priority")
    assert fo.field_name == "priority"


def test_parse_exported_field() -> None:
    data = {
        "name": "status",
        "description": "d",
        "sort_order": 1,
        "options": ["open", "closed"],
    }
    ef = _parse_exported_field(data)
    assert ef.name == "status"
    assert ef.options == ("open", "closed")


def test_parse_field_descriptor() -> None:
    data = {
        "name": "subject",
        "type": "string",
        "description": "Entry subject",
        "resource_path": "/api.php/fields/subject",
    }
    fd = _parse_field_descriptor(data)
    assert fd.name == "subject"
    assert fd.type == "string"
    assert fd.resource_path == "/api.php/fields/subject"


# --- Client method tests ---


def _mock_httpx_client(mock_httpx: MagicMock) -> MagicMock:
    """Create a mock httpx.Client context manager."""
    mock_http_client = MagicMock()
    mock_http_client.__enter__ = MagicMock(return_value=mock_http_client)
    mock_http_client.__exit__ = MagicMock(return_value=False)
    mock_httpx.return_value = mock_http_client
    return mock_http_client


def test_list_entries() -> None:
    settings = _make_settings()
    client = ShareApiClient(settings)

    response_data = {
        "entries": [
            {"id": 1, "type": "note", "subject": "A", "body": "text"},
            {"id": 2, "type": "file", "subject": "B", "filename": "f.pdf"},
        ],
        "total": 2,
        "page": 1,
        "per_page": 20,
    }

    mock_response = MagicMock()
    mock_response.json.return_value = response_data
    mock_response.raise_for_status = MagicMock()

    with patch("share_api_mcp.api_client.httpx.Client") as mock_httpx:
        mock_http_client = _mock_httpx_client(mock_httpx)
        mock_http_client.get.return_value = mock_response

        result = client.list_entries("http://example.com", page=1, per_page=20)

    assert len(result.entries) == 2
    assert result.total == 2
    assert result.entries[0].subject == "A"


def test_update_entry() -> None:
    settings = _make_settings()
    client = ShareApiClient(settings)

    mock_response = MagicMock()
    mock_response.json.return_value = _sample_entry_json()
    mock_response.raise_for_status = MagicMock()

    with patch("share_api_mcp.api_client.httpx.Client") as mock_httpx:
        mock_http_client = _mock_httpx_client(mock_httpx)
        mock_http_client.put.return_value = mock_response

        entry = client.update_entry("http://example.com", 42, {"subject": "Updated"})

    assert entry.id == 42
    mock_http_client.put.assert_called_once_with(
        "http://example.com/api.php/entries/42", json={"subject": "Updated"}
    )


def test_delete_entry() -> None:
    settings = _make_settings()
    client = ShareApiClient(settings)

    mock_response = MagicMock()
    mock_response.json.return_value = {"message": "Entry deleted"}
    mock_response.raise_for_status = MagicMock()

    with patch("share_api_mcp.api_client.httpx.Client") as mock_httpx:
        mock_http_client = _mock_httpx_client(mock_httpx)
        mock_http_client.delete.return_value = mock_response

        result = client.delete_entry("http://example.com", 42)

    assert result.message == "Entry deleted"
    mock_http_client.delete.assert_called_once_with(
        "http://example.com/api.php/entries/42"
    )


def test_list_custom_fields() -> None:
    settings = _make_settings()
    client = ShareApiClient(settings)

    mock_response = MagicMock()
    mock_response.json.return_value = {
        "data": [
            {"name": "status", "sort_order": 1, "option_count": 3},
            {"name": "priority", "sort_order": 2, "option_count": 2},
        ]
    }
    mock_response.raise_for_status = MagicMock()

    with patch("share_api_mcp.api_client.httpx.Client") as mock_httpx:
        mock_http_client = _mock_httpx_client(mock_httpx)
        mock_http_client.get.return_value = mock_response

        result = client.list_custom_fields("http://example.com")

    assert len(result.fields) == 2
    assert result.fields[0].name == "status"


def test_create_custom_field() -> None:
    settings = _make_settings()
    client = ShareApiClient(settings)

    mock_response = MagicMock()
    mock_response.json.return_value = {
        "name": "priority",
        "description": "Task priority",
        "sort_order": 2,
    }
    mock_response.raise_for_status = MagicMock()

    with patch("share_api_mcp.api_client.httpx.Client") as mock_httpx:
        mock_http_client = _mock_httpx_client(mock_httpx)
        mock_http_client.post.return_value = mock_response

        field = client.create_custom_field(
            "http://example.com", "priority",
            description="Task priority", sort_order=2,
        )

    assert field.name == "priority"
    assert field.description == "Task priority"


def test_update_custom_field() -> None:
    settings = _make_settings()
    client = ShareApiClient(settings)

    mock_response = MagicMock()
    mock_response.json.return_value = {"name": "status", "description": "Updated", "sort_order": 5}
    mock_response.raise_for_status = MagicMock()

    with patch("share_api_mcp.api_client.httpx.Client") as mock_httpx:
        mock_http_client = _mock_httpx_client(mock_httpx)
        mock_http_client.put.return_value = mock_response

        field = client.update_custom_field(
            "http://example.com", "status",
            {"description": "Updated", "sort_order": 5},
        )

    assert field.description == "Updated"
    mock_http_client.put.assert_called_once_with(
        "http://example.com/api.php/custom-fields/status",
        json={"description": "Updated", "sort_order": 5},
    )


def test_delete_custom_field() -> None:
    settings = _make_settings()
    client = ShareApiClient(settings)

    mock_response = MagicMock()
    mock_response.json.return_value = {"message": "Custom field deleted"}
    mock_response.raise_for_status = MagicMock()

    with patch("share_api_mcp.api_client.httpx.Client") as mock_httpx:
        mock_http_client = _mock_httpx_client(mock_httpx)
        mock_http_client.delete.return_value = mock_response

        result = client.delete_custom_field("http://example.com", "status")

    assert result.message == "Custom field deleted"


def test_export_custom_fields() -> None:
    settings = _make_settings()
    client = ShareApiClient(settings)

    mock_response = MagicMock()
    mock_response.json.return_value = {
        "data": [
            {"name": "status", "sort_order": 1, "options": ["open", "closed"]},
        ]
    }
    mock_response.raise_for_status = MagicMock()

    with patch("share_api_mcp.api_client.httpx.Client") as mock_httpx:
        mock_http_client = _mock_httpx_client(mock_httpx)
        mock_http_client.get.return_value = mock_response

        result = client.export_custom_fields("http://example.com")

    assert len(result.fields) == 1
    assert result.fields[0].options == ("open", "closed")


def test_import_custom_fields() -> None:
    settings = _make_settings()
    client = ShareApiClient(settings)

    mock_response = MagicMock()
    mock_response.json.return_value = {"fields_created": 2, "options_created": 5}
    mock_response.raise_for_status = MagicMock()

    with patch("share_api_mcp.api_client.httpx.Client") as mock_httpx:
        mock_http_client = _mock_httpx_client(mock_httpx)
        mock_http_client.post.return_value = mock_response

        result = client.import_custom_fields("http://example.com", {"fields": []})

    assert result.fields_created == 2
    assert result.options_created == 5


def test_list_field_options() -> None:
    settings = _make_settings()
    client = ShareApiClient(settings)

    mock_response = MagicMock()
    mock_response.json.return_value = {
        "data": [
            {"id": 1, "field_name": "status", "name": "open", "entry_count": 5},
            {"id": 2, "field_name": "status", "name": "closed", "entry_count": 3},
        ]
    }
    mock_response.raise_for_status = MagicMock()

    with patch("share_api_mcp.api_client.httpx.Client") as mock_httpx:
        mock_http_client = _mock_httpx_client(mock_httpx)
        mock_http_client.get.return_value = mock_response

        result = client.list_field_options("http://example.com", "status")

    assert result.field_name == "status"
    assert len(result.options) == 2
    assert result.options[0].name == "open"


def test_create_field_option() -> None:
    settings = _make_settings()
    client = ShareApiClient(settings)

    mock_response = MagicMock()
    mock_response.json.return_value = {"id": 10, "field_name": "status", "name": "pending"}
    mock_response.raise_for_status = MagicMock()

    with patch("share_api_mcp.api_client.httpx.Client") as mock_httpx:
        mock_http_client = _mock_httpx_client(mock_httpx)
        mock_http_client.post.return_value = mock_response

        option = client.create_field_option("http://example.com", "status", "pending")

    assert option.id == 10
    assert option.name == "pending"


def test_update_field_option() -> None:
    settings = _make_settings()
    client = ShareApiClient(settings)

    mock_response = MagicMock()
    mock_response.json.return_value = {"id": 5, "field_name": "status", "name": "renamed"}
    mock_response.raise_for_status = MagicMock()

    with patch("share_api_mcp.api_client.httpx.Client") as mock_httpx:
        mock_http_client = _mock_httpx_client(mock_httpx)
        mock_http_client.put.return_value = mock_response

        option = client.update_field_option("http://example.com", "status", 5, "renamed")

    assert option.name == "renamed"
    mock_http_client.put.assert_called_once_with(
        "http://example.com/api.php/field-options/status/5",
        json={"name": "renamed"},
    )


def test_delete_field_option() -> None:
    settings = _make_settings()
    client = ShareApiClient(settings)

    mock_response = MagicMock()
    mock_response.json.return_value = {"message": "Option deleted"}
    mock_response.raise_for_status = MagicMock()

    with patch("share_api_mcp.api_client.httpx.Client") as mock_httpx:
        mock_http_client = _mock_httpx_client(mock_httpx)
        mock_http_client.delete.return_value = mock_response

        result = client.delete_field_option("http://example.com", "status", 5)

    assert result.message == "Option deleted"
    mock_http_client.delete.assert_called_once_with(
        "http://example.com/api.php/field-options/status/5"
    )


def test_delete_attachment() -> None:
    settings = _make_settings()
    client = ShareApiClient(settings)

    mock_response = MagicMock()
    mock_response.json.return_value = {"message": "Attachment deleted"}
    mock_response.raise_for_status = MagicMock()

    with patch("share_api_mcp.api_client.httpx.Client") as mock_httpx:
        mock_http_client = _mock_httpx_client(mock_httpx)
        mock_http_client.delete.return_value = mock_response

        result = client.delete_attachment("http://example.com", 99)

    assert result.message == "Attachment deleted"
    mock_http_client.delete.assert_called_once_with(
        "http://example.com/api.php/attachments/99"
    )


def test_get_auth_info() -> None:
    settings = _make_settings()
    client = ShareApiClient(settings)

    mock_response = MagicMock()
    mock_response.json.return_value = {"method": "basic"}
    mock_response.raise_for_status = MagicMock()

    with patch("share_api_mcp.api_client.httpx.Client") as mock_httpx:
        mock_http_client = _mock_httpx_client(mock_httpx)
        mock_http_client.get.return_value = mock_response

        result = client.get_auth_info("http://example.com")

    assert result.method == "basic"
    mock_http_client.get.assert_called_once_with("http://example.com/api.php/auth")


def test_list_fields() -> None:
    settings = _make_settings()
    client = ShareApiClient(settings)

    mock_response = MagicMock()
    mock_response.json.return_value = {
        "data": [
            {"name": "subject", "type": "string", "description": "Entry subject"},
            {"name": "status", "type": "select"},
        ]
    }
    mock_response.raise_for_status = MagicMock()

    with patch("share_api_mcp.api_client.httpx.Client") as mock_httpx:
        mock_http_client = _mock_httpx_client(mock_httpx)
        mock_http_client.get.return_value = mock_response

        result = client.list_fields("http://example.com")

    assert len(result.fields) == 2
    assert result.fields[0].name == "subject"
    mock_http_client.get.assert_called_once_with("http://example.com/api.php/fields")


def test_create_entry_text_mode() -> None:
    settings = _make_settings()
    client = ShareApiClient(settings)

    mock_response = MagicMock()
    mock_response.text = "123"
    mock_response.raise_for_status = MagicMock()

    with patch("share_api_mcp.api_client.httpx.Client") as mock_httpx:
        mock_http_client = _mock_httpx_client(mock_httpx)
        mock_http_client.post.return_value = mock_response

        entry_id = client.create_entry("http://example.com", text_or_url="Hello world")

    assert entry_id == "123"
    mock_http_client.post.assert_called_once_with(
        "http://example.com/share.php",
        json={"text_or_url": "Hello world"},
    )


def test_create_entry_with_extra_fields() -> None:
    settings = _make_settings()
    client = ShareApiClient(settings)

    mock_response = MagicMock()
    mock_response.text = "456"
    mock_response.raise_for_status = MagicMock()

    with patch("share_api_mcp.api_client.httpx.Client") as mock_httpx:
        mock_http_client = _mock_httpx_client(mock_httpx)
        mock_http_client.post.return_value = mock_response

        entry_id = client.create_entry(
            "http://example.com",
            text_or_url="Note",
            extra_fields={"_status": "open"},
        )

    assert entry_id == "456"
    mock_http_client.post.assert_called_once_with(
        "http://example.com/share.php",
        json={"text_or_url": "Note", "_status": "open"},
    )
