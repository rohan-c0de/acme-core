#!/usr/bin/env python3
"""Deny reading files that look like secrets or credential stores.

Deterministic policy check with no network access.
"""

from __future__ import annotations

import json
import sys


def is_secret_path(file_path: str) -> bool:
    path = file_path.replace("\\", "/").lower()
    # Normalize so relative paths like ".env" still match "/.env" patterns.
    check = path if path.startswith("/") else f"/{path}"

    for segment in check.split("/"):
        if segment == ".env" or segment.startswith(".env."):
            return True

    if "/.ssh/" in check:
        return True
    if "/.aws/" in check:
        return True
    if "/.gnupg/" in check:
        return True
    if check.endswith(".pem") or check.endswith(".key"):
        return True
    if "/secret/" in check or "/secrets/" in check:
        return True
    if "/.netrc" in check:
        return True
    if "credentials" in check:
        return True
    return False


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, TypeError, ValueError):
        json.dump(
            {
                "permission": "deny",
                "user_message": "Invalid hook payload; file read blocked.",
                "agent_message": "beforeReadFile hook received non-JSON stdin; denying.",
            },
            sys.stdout,
        )
        print()
        return 0

    file_path = payload.get("file_path", "")
    if not isinstance(file_path, str):
        file_path = str(file_path) if file_path is not None else ""

    if is_secret_path(file_path):
        json.dump(
            {
                "permission": "deny",
                "user_message": "Reading this path is blocked because it may contain secrets.",
                "agent_message": (
                    "Denied by deny_secrets.py: file_path matched a secret-path pattern."
                ),
            },
            sys.stdout,
        )
        print()
        return 0

    json.dump({"permission": "allow"}, sys.stdout)
    print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
