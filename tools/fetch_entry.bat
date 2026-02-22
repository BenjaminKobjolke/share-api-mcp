@echo off
cd /d "%~dp0.."
if "%~1"=="" (
    echo Usage: fetch_entry.bat ^<entry_id^>
    exit /b 1
)
uv run python -c "from dotenv import load_dotenv; load_dotenv(); from share_api_mcp.config.settings import Settings; from share_api_mcp.api_client import ShareApiClient; s = Settings.from_env(); c = ShareApiClient(s); r = c.fetch_entry_with_files(s.base_url, %1, s.download_dir); print(r.format_output())"
