# MCP Server Configuration

This document describes how to configure the Share API MCP server for use with Claude Code.

## Installation

1. Ensure you have [uv](https://github.com/astral-sh/uv) installed
2. Clone this repository to a local directory
3. Copy `.env.example` to `.env` and fill in your values

## Configuration

Add the following to your Claude Code MCP configuration file:

### Windows

```json
{
  "mcpServers": {
    "share-api": {
      "type": "stdio",
      "command": "uv",
      "args": ["--directory", "D:\\GIT\\BenjaminKobjolke\\share-api-mcp", "run", "python", "-m", "share_api_mcp.mcp_server"],
      "env": {
        "SHARE_API_BASE_URL": "https://your-server.com/share",
        "SHARE_API_DOWNLOAD_DIR": "./downloads",
        "SHARE_API_AUTH_USER": "",
        "SHARE_API_AUTH_PASSWORD": "",
        "SHARE_API_PROJECT_ID": ""
      }
    }
  }
}
```

### macOS/Linux

```json
{
  "mcpServers": {
    "share-api": {
      "type": "stdio",
      "command": "uv",
      "args": ["--directory", "/path/to/share-api-mcp", "run", "python", "-m", "share_api_mcp.mcp_server"],
      "env": {
        "SHARE_API_BASE_URL": "https://your-server.com/share",
        "SHARE_API_DOWNLOAD_DIR": "./downloads",
        "SHARE_API_AUTH_USER": "",
        "SHARE_API_AUTH_PASSWORD": "",
        "SHARE_API_PROJECT_ID": ""
      }
    }
  }
}
```

### Per-Project Filtering

Set `SHARE_API_PROJECT_ID` to automatically filter `list_entries` by project. This removes the need to manually look up the project ID via `list_field_options` each session. An explicit `project_id` in the filters argument overrides the env var.

### Direct CLI Registration

You can also register the MCP server directly using the Claude CLI:

**Windows:**
```bash
claude mcp add --scope project --transport stdio share-api -- uv --directory D:\GIT\BenjaminKobjolke\share-api-mcp run python -m share_api_mcp.mcp_server
```

**macOS/Linux:**
```bash
claude mcp add --scope project --transport stdio share-api -- uv --directory /path/to/share-api-mcp run python -m share_api_mcp.mcp_server
```

## Available Tools

### fetch_shared_entry

Fetch a shared entry by ID from the media-file-explorer-share API. Downloads all file attachments and returns the entry content with file paths.

**Parameters:**
- `entry_id` (int, required): The numeric ID of the shared entry to fetch
- `base_url` (string, optional): Base URL of the share API (e.g. `http://host/share`). Falls back to `SHARE_API_BASE_URL` env var if empty.
- `download_dir` (string, optional): Directory to save downloaded files. Falls back to `SHARE_API_DOWNLOAD_DIR` env var or `./downloads`.

## Logging

The MCP server writes logs to `mcp.log` in the project root directory. This file contains detailed information about tool calls and any errors that occur.

## Troubleshooting

### "No base_url provided" error

Ensure `SHARE_API_BASE_URL` is set in your `.env` file or MCP config `env` block, or pass `base_url` as a tool argument.

### Connection fails

1. Verify the share API server is reachable at the configured URL
2. If the API requires authentication, set `SHARE_API_AUTH_USER` and `SHARE_API_AUTH_PASSWORD`
3. Check `mcp.log` for detailed error messages

### Files not downloading

1. Ensure the `SHARE_API_DOWNLOAD_DIR` directory is writable
2. Only file-type attachments are downloaded (text attachments are returned inline)
3. Check `mcp.log` for download errors
