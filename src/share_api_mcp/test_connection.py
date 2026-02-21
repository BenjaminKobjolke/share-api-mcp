"""Standalone API connection test script.

Usage:
    uv run python -m share_api_mcp.test_connection
    uv run python -m share_api_mcp.test_connection --entry-id 42
    uv run python -m share_api_mcp.test_connection --base-url https://example.com
"""

from __future__ import annotations

import argparse
import sys

import httpx

from share_api_mcp.config.settings import Settings


def _load_dotenv() -> None:
    """Load .env file if python-dotenv is available."""
    try:
        from dotenv import load_dotenv

        load_dotenv()
    except ImportError:
        pass


def _print_ok(msg: str) -> None:
    print(f"  [OK] {msg}")


def _print_fail(msg: str) -> None:
    print(f"  [FAIL] {msg}")


def main(argv: list[str] | None = None) -> int:
    """Run API connection test. Returns 0 on success, 1 on failure."""
    parser = argparse.ArgumentParser(description="Test Share API connection")
    parser.add_argument(
        "--entry-id",
        type=int,
        default=1,
        help="Entry ID to fetch as smoke test (default: 1)",
    )
    parser.add_argument(
        "--base-url",
        type=str,
        default=None,
        help="Override SHARE_API_BASE_URL env var",
    )
    args = parser.parse_args(argv)

    _load_dotenv()
    settings = Settings.from_env()

    base_url = args.base_url or settings.base_url

    print("Share API Connection Test")
    print("=" * 40)

    # Step 1: Check base URL
    print("\n1. Checking configuration...")
    if not base_url:
        _print_fail("SHARE_API_BASE_URL is not set and no --base-url provided")
        return 1
    _print_ok(f"Base URL: {base_url}")

    # Step 2: HTTP GET to entries endpoint
    print(f"\n2. Fetching entry {args.entry_id}...")
    url = f"{base_url.rstrip('/')}/api.php/entries/{args.entry_id}"

    auth: httpx.BasicAuth | None = None
    if settings.auth_user and settings.auth_password:
        auth = httpx.BasicAuth(settings.auth_user, settings.auth_password)
        _print_ok("Using Basic Auth")
    else:
        _print_ok("No auth configured")

    try:
        with httpx.Client(auth=auth, timeout=10.0) as client:
            response = client.get(url)
            response.raise_for_status()
    except httpx.ConnectError as exc:
        _print_fail(f"Connection failed: {exc}")
        return 1
    except httpx.HTTPStatusError as exc:
        _print_fail(f"HTTP {exc.response.status_code}: {exc.response.reason_phrase}")
        return 1
    except httpx.TimeoutException:
        _print_fail("Request timed out after 10 seconds")
        return 1

    _print_ok(f"HTTP {response.status_code}")

    # Step 3: Parse JSON
    print("\n3. Parsing response...")
    try:
        data = response.json()
    except ValueError:
        _print_fail("Response is not valid JSON")
        return 1

    if not isinstance(data, dict):
        _print_fail(f"Expected JSON object, got {type(data).__name__}")
        return 1
    _print_ok("Valid JSON response")

    # Step 4: Print entry info
    print("\n4. Entry details:")
    subject = data.get("subject", "(no subject)")
    attachments = data.get("attachments", [])
    _print_ok(f"Subject: {subject}")
    _print_ok(f"Attachments: {len(attachments)}")

    print("\n" + "=" * 40)
    print("Connection test passed!")
    return 0


if __name__ == "__main__":
    sys.exit(main())
