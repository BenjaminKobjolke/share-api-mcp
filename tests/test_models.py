"""Tests for data models."""

from share_api_mcp.models import Attachment, DownloadedFile, Entry, EntryResult


def test_attachment_is_frozen() -> None:
    att = Attachment(id=1, type="text", body={"content": "hello"})
    try:
        att.id = 2  # type: ignore[misc]
        raise AssertionError("Should be frozen")
    except AttributeError:
        pass


def test_entry_is_frozen() -> None:
    entry = Entry(id=1, type="note", subject="Test")
    try:
        entry.id = 2  # type: ignore[misc]
        raise AssertionError("Should be frozen")
    except AttributeError:
        pass


def test_entry_defaults() -> None:
    entry = Entry(id=1, type="note", subject="Test")
    assert entry.body == {}
    assert entry.filename == ""
    assert entry.file_size == 0
    assert entry.attachments == ()


def test_attachment_defaults() -> None:
    att = Attachment(id=1, type="text")
    assert att.body == {}
    assert att.filename == ""
    assert att.file_size == 0


def test_downloaded_file() -> None:
    df = DownloadedFile(
        attachment_id=5,
        filename="report.pdf",
        file_path="/tmp/downloads/report.pdf",
        file_size=1024,
    )
    assert df.attachment_id == 5
    assert df.filename == "report.pdf"


def test_entry_result_format_output_basic() -> None:
    entry = Entry(id=42, type="note", subject="My Note", body={"content": "Hello world"})
    result = EntryResult(entry=entry)
    output = result.format_output()
    assert "Entry #42: My Note" in output
    assert "Type: note" in output
    assert "content: Hello world" in output


def test_entry_result_format_output_with_attachments() -> None:
    att_text = Attachment(id=1, type="text", body={"content": "inline text"})
    att_file = Attachment(id=2, type="file", filename="pic.png", file_size=2048)
    entry = Entry(
        id=10,
        type="share",
        subject="Shared Item",
        attachments=(att_text, att_file),
    )
    df = DownloadedFile(
        attachment_id=2,
        filename="pic.png",
        file_path="/tmp/downloads/pic.png",
        file_size=2048,
    )
    result = EntryResult(entry=entry, downloaded_files=(df,))
    output = result.format_output()
    assert "Attachments (2):" in output
    assert "[1] text" in output
    assert "inline text" in output
    assert "[2] file: pic.png" in output
    assert "Downloaded files:" in output
    assert "pic.png -> /tmp/downloads/pic.png" in output


def test_entry_result_format_output_with_entry_file() -> None:
    entry = Entry(id=1, type="file", subject="A File", filename="doc.pdf", file_size=5000)
    result = EntryResult(entry=entry)
    output = result.format_output()
    assert "File: doc.pdf (5000 bytes)" in output
