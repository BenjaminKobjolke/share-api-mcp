"""Tests for data models."""

from share_api_mcp.models import (
    Attachment,
    DownloadedFile,
    Entry,
    EntryResult,
    FailedDownload,
    _is_image_file,
)


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
    assert entry.file_url == ""
    assert entry.attachments == ()


def test_attachment_defaults() -> None:
    att = Attachment(id=1, type="text")
    assert att.body == {}
    assert att.filename == ""
    assert att.file_size == 0
    assert att.file_url == ""


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


def test_failed_download_is_frozen() -> None:
    fd = FailedDownload(attachment_id=1, filename="a.png", error="not found")
    try:
        fd.attachment_id = 2  # type: ignore[misc]
        raise AssertionError("Should be frozen")
    except AttributeError:
        pass


def test_entry_result_format_output_with_failed_downloads() -> None:
    att = Attachment(id=8, type="file", filename="missing.png", file_size=1000)
    entry = Entry(id=19, type="share", subject="Broken", attachments=(att,))
    fd = FailedDownload(
        attachment_id=8, filename="missing.png", error="File not available on server"
    )
    result = EntryResult(entry=entry, failed_downloads=(fd,))
    output = result.format_output()
    assert "Entry #19: Broken" in output
    assert "Failed downloads:" in output
    assert "[8] missing.png: File not available on server" in output


def test_is_image_file_with_images() -> None:
    assert _is_image_file("photo.png") is True
    assert _is_image_file("photo.jpg") is True
    assert _is_image_file("photo.jpeg") is True
    assert _is_image_file("photo.gif") is True
    assert _is_image_file("photo.bmp") is True
    assert _is_image_file("photo.webp") is True
    assert _is_image_file("photo.svg") is True
    assert _is_image_file("photo.tiff") is True
    assert _is_image_file("photo.ico") is True
    assert _is_image_file("PHOTO.PNG") is True


def test_is_image_file_with_non_images() -> None:
    assert _is_image_file("report.pdf") is False
    assert _is_image_file("data.csv") is False
    assert _is_image_file("script.py") is False
    assert _is_image_file("noextension") is False
    assert _is_image_file("") is False


def test_content_md_path_default_is_empty() -> None:
    entry = Entry(id=1, type="note", subject="Test")
    result = EntryResult(entry=entry)
    assert result.content_md_path == ""


def test_generate_content_markdown_with_text_body_and_image() -> None:
    att_text = Attachment(id=1, type="text", body={"content": "A comment"})
    att_image = Attachment(
        id=2, type="file", filename="photo.png", file_size=1024, file_url="http://x"
    )
    entry = Entry(
        id=10,
        type="share",
        subject="My Share",
        body={"content": "Hello world"},
        attachments=(att_text, att_image),
    )
    result = EntryResult(entry=entry)
    md = result.generate_content_markdown()
    assert md.startswith("# My Share\n")
    assert "Hello world" in md
    assert "A comment" in md
    assert "![photo.png](photo.png)" in md


def test_generate_content_markdown_with_only_text_attachments() -> None:
    att = Attachment(id=1, type="text", body={"content": "Just text"})
    entry = Entry(
        id=5,
        type="share",
        subject="Text Only",
        body={"content": "Body text"},
        attachments=(att,),
    )
    result = EntryResult(entry=entry)
    md = result.generate_content_markdown()
    assert "# Text Only" in md
    assert "Body text" in md
    assert "Just text" in md
    assert "![" not in md


def test_generate_content_markdown_with_text_or_url_body_key() -> None:
    att = Attachment(id=1, type="text", body={"text_or_url": "https://example.com"})
    entry = Entry(
        id=6,
        type="share",
        subject="URL Entry",
        body={"text_or_url": "entry level text"},
        attachments=(att,),
    )
    result = EntryResult(entry=entry)
    md = result.generate_content_markdown()
    assert "entry level text" in md
    assert "https://example.com" in md


def test_generate_content_markdown_with_description_body_key() -> None:
    entry = Entry(
        id=22,
        type="file",
        subject="File: screenshot.png",
        body={"description": "screenshot with description!"},
        filename="screenshot.png",
        file_url="http://x",
    )
    result = EntryResult(entry=entry)
    md = result.generate_content_markdown()
    assert "screenshot with description!" in md
    assert "![screenshot.png](screenshot.png)" in md


def test_generate_content_markdown_with_entry_level_image() -> None:
    entry = Entry(
        id=7,
        type="file",
        subject="Image Entry",
        filename="banner.jpg",
        file_url="http://x",
    )
    result = EntryResult(entry=entry)
    md = result.generate_content_markdown()
    assert "![banner.jpg](banner.jpg)" in md


def test_generate_content_markdown_entry_level_non_image_skipped() -> None:
    entry = Entry(
        id=7,
        type="file",
        subject="Doc Entry",
        filename="doc.pdf",
        file_url="http://x",
    )
    result = EntryResult(entry=entry)
    md = result.generate_content_markdown()
    assert "![" not in md


def test_format_output_shows_content_md_path() -> None:
    entry = Entry(id=1, type="note", subject="Test")
    result = EntryResult(entry=entry, content_md_path="/tmp/1/content.md")
    output = result.format_output()
    assert "Content markdown: /tmp/1/content.md" in output


def test_format_output_hides_content_md_path_when_empty() -> None:
    entry = Entry(id=1, type="note", subject="Test")
    result = EntryResult(entry=entry)
    output = result.format_output()
    assert "Content markdown" not in output
