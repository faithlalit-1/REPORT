#!/usr/bin/env python3
"""Enforce Faith Lalit's identity for faithlalit-1/REPORT only."""

from __future__ import annotations

import json
import os
import re
import subprocess
import sys
from pathlib import Path


EXPECTED_NAME = "faithlalit-1"
EXPECTED_EMAIL = "faith.lalit@gmail.com"
EXPECTED_GITHUB_OWNER = "faithlalit-1"
EXPECTED_GITHUB_REPOSITORY = "REPORT"
CREDENTIAL_KEY = "credential.https://github.com.username"


class PreflightError(RuntimeError):
    pass


def run_git(*args: str, required: bool = True) -> str:
    result = subprocess.run(
        ["git", *args],
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        encoding="utf-8",
        errors="replace",
        check=False,
    )
    if required and result.returncode != 0:
        message = result.stderr.strip() or result.stdout.strip() or "Git command failed"
        raise PreflightError(message)
    return result.stdout.strip() if result.returncode == 0 else ""


def github_repository(remote_url: str) -> tuple[str, str] | None:
    match = re.search(
        r"(?:^|[.@/:])github\.com[/:]([^/]+)/([^/]+?)(?:\.git)?/?$",
        remote_url,
        re.IGNORECASE,
    )
    return (match.group(1), match.group(2)) if match else None


def check_environment_overrides() -> None:
    expected = {
        "GIT_AUTHOR_NAME": EXPECTED_NAME,
        "GIT_AUTHOR_EMAIL": EXPECTED_EMAIL,
        "GIT_COMMITTER_NAME": EXPECTED_NAME,
        "GIT_COMMITTER_EMAIL": EXPECTED_EMAIL,
    }
    conflicts = [
        f"{key}={os.environ[key]!r}"
        for key, value in expected.items()
        if os.environ.get(key) and os.environ[key] != value
    ]
    if conflicts:
        raise PreflightError(
            "Conflicting Git identity environment override(s): " + ", ".join(conflicts)
        )


def set_local_value(key: str, expected: str, changes: list[str]) -> None:
    current = run_git("config", "--local", "--get", key, required=False)
    if current != expected:
        run_git("config", "--local", key, expected)
        changes.append(key)
    verified = run_git("config", "--local", "--get", key)
    if verified != expected:
        raise PreflightError(f"Could not enforce repository-local {key}")


def main() -> int:
    try:
        repository = Path(run_git("rev-parse", "--show-toplevel"))
        branch = run_git("branch", "--show-current")
        if not branch:
            raise PreflightError("Detached HEAD: select the intended branch before committing")

        origin = run_git("remote", "get-url", "--push", "origin", required=False)
        remote_repository = github_repository(origin) if origin else None
        if not origin:
            raise PreflightError("No origin push URL is configured; expected faithlalit-1/REPORT")
        if not remote_repository:
            raise PreflightError("origin is not a recognized github.com repository URL")
        owner, repository_name = remote_repository
        if (
            owner.casefold() != EXPECTED_GITHUB_OWNER.casefold()
            or repository_name.casefold() != EXPECTED_GITHUB_REPOSITORY.casefold()
        ):
            raise PreflightError(
                f"origin is {owner}/{repository_name}, expected "
                f"{EXPECTED_GITHUB_OWNER}/{EXPECTED_GITHUB_REPOSITORY}"
            )

        check_environment_overrides()
        changes: list[str] = []
        set_local_value("user.name", EXPECTED_NAME, changes)
        set_local_value("user.email", EXPECTED_EMAIL, changes)
        set_local_value(CREDENTIAL_KEY, EXPECTED_GITHUB_OWNER, changes)

        print(
            json.dumps(
                {
                    "repository": str(repository),
                    "branch": branch,
                    "author_name": EXPECTED_NAME,
                    "author_email": EXPECTED_EMAIL,
                    "credential_username": EXPECTED_GITHUB_OWNER,
                    "origin": origin,
                    "github_owner": owner,
                    "github_repository": repository_name,
                    "updated_local_config": changes,
                },
                indent=2,
            )
        )
        return 0
    except PreflightError as error:
        print(f"ERROR: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
