@echo off
cd /d "%~dp0.."
uv run python -m share_api_mcp.test_connection %*
