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

- `GET {base_url}/api.php/entries` - Paginated entry list
- `GET {base_url}/api.php/entries/{id}` - Fetch entry with attachments
- `PUT {base_url}/api.php/entries/{id}` - Update entry
- `DELETE {base_url}/api.php/entries/{id}` - Delete entry (cascade)
- `GET {base_url}/api.php/custom-fields` - List custom fields
- `POST {base_url}/api.php/custom-fields` - Create custom field
- `PUT {base_url}/api.php/custom-fields/{name}` - Update custom field
- `DELETE {base_url}/api.php/custom-fields/{name}` - Delete custom field (cascade)
- `GET {base_url}/api.php/custom-fields/export` - Export fields with options
- `POST {base_url}/api.php/custom-fields/import` - Import fields (merge mode)
- `GET {base_url}/api.php/field-options/{field}` - List field options
- `POST {base_url}/api.php/field-options/{field}` - Create option
- `PUT {base_url}/api.php/field-options/{field}/{id}` - Rename option
- `DELETE {base_url}/api.php/field-options/{field}/{id}` - Delete option (cascade)
- `GET {base_url}/api.php/files/{id}` - Download attachment file
- `DELETE {base_url}/api.php/attachments/{id}` - Delete attachment
- `GET {base_url}/api.php/auth` - Auth method discovery
- `GET {base_url}/api.php/fields` - Schema/field discovery
- `POST {base_url}/share.php` - Webhook (create entry)

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
