#!/usr/bin/env python3
"""Deny shell commands that target the upstream NetworkX remote or blocked hosts.

Deterministic policy check with no network access.
"""

from __future__ import annotations

import json
import sys


DENY_SUBSTRINGS = (
    "github.com/networkx/networkx",
    "github.com:networkx/networkx",
    "push-blocked.invalid",
    "git push upstream",
    "git remote set-url upstream",
)


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, TypeError, ValueError):
        json.dump(
            {
                "permission": "deny",
                "user_message": "Invalid hook payload; shell command blocked.",
                "agent_message": "beforeShellExecution hook received non-JSON stdin; denying.",
            },
            sys.stdout,
        )
        print()
        return 0

    command = payload.get("command", "")
    if not isinstance(command, str):
        command = str(command) if command is not None else ""

    lowered = command.lower()
    for needle in DENY_SUBSTRINGS:
        if needle in lowered:
            json.dump(
                {
                    "permission": "deny",
                    "user_message": (
                        "This command is blocked: it targets the upstream NetworkX "
                        "remote or a push-blocked host."
                    ),
                    "agent_message": (
                        "Denied by deny_upstream.py: command matched a blocked "
                        f"pattern ({needle!r})."
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
