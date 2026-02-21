# Share API MCP Server

## Architecture

```
src/share_api_mcp/
  mcp_server.py    - FastMCP server, @mcp.tool() entry point
  api_client.py    - httpx client for the share PHP API
  models.py        - Frozen dataclasses: Entry, Attachment, DownloadedFile, EntryResult
  config/
    settings.py    - Frozen Settings from env vars
```

## API Endpoints

- `GET {base_url}/api.php/entries/{id}` - Fetch entry JSON with attachments
- `GET {base_url}/api.php/files/{attachment_id}` - Download file binary

## Rules

- All dataclasses are frozen (immutable)
- Functions return strings on error (no exceptions to caller)
- Logging: file (INFO) + stderr (WARNING) for MCP stdio compatibility
- Tests use `unittest.mock` with `MagicMock(spec=...)` and `patch`
- Run tests: `uv run pytest tests/ -v`
- Run lint: `uv run ruff check src/ tests/`
- Run types: `uv run mypy src/`

## Common Patterns

- Tool args override env vars (base_url, download_dir)
- Only file-type attachments are downloaded (text attachments skipped)
- Files downloaded via streaming to handle large files
- BasicAuth optional, configured via env vars
