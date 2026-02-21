# share-api-mcp

MCP server for the media-file-explorer-share PHP API. Fetches shared entries by ID, downloads file attachments, and returns structured content.

## Installation

1. Ensure you have [uv](https://github.com/astral-sh/uv) installed
2. Clone this repository
3. Copy `.env.example` to `.env` and fill in your values:
   ```bash
   cp .env.example .env
   ```
4. Install dependencies:
   ```bash
   uv sync
   ```

## Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `SHARE_API_BASE_URL` | Yes (or pass as tool arg) | Base URL of the share API |
| `SHARE_API_DOWNLOAD_DIR` | No | Directory for downloaded files (default: `./downloads`) |
| `SHARE_API_AUTH_USER` | No | HTTP Basic Auth username |
| `SHARE_API_AUTH_PASSWORD` | No | HTTP Basic Auth password |

## MCP Tool

### `fetch_shared_entry`

Fetches a shared entry by ID and downloads all file attachments.

**Parameters:**
- `entry_id` (int, required) - The numeric ID of the shared entry
- `base_url` (string, optional) - Overrides `SHARE_API_BASE_URL`
- `download_dir` (string, optional) - Overrides `SHARE_API_DOWNLOAD_DIR`

## Running

```bash
# Via start.bat
start.bat

# Via uv directly
uv run share-api-mcp
```

## Testing

```bash
tools\tests.bat
# or
uv run pytest tests/ -v
```

### Testing Connection

Verify API connectivity and auth without the MCP tool interface:

```bash
tools\test_connection.bat
# or with a specific entry ID
tools\test_connection.bat --entry-id 42
# or with a base URL override
tools\test_connection.bat --base-url https://example.com
```

## Linting & Type Checking

```bash
uv run ruff check src/ tests/
uv run mypy src/
```
