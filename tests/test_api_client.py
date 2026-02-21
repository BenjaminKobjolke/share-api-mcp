"""Tests for the Share API client."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from share_api_mcp.api_client import ShareApiClient, _parse_attachment, _parse_entry
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
