from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class UpdateStatus:
    branch: str
    local_commit: str
    remote_commit: str
    remote_url: str
    dirty_files: int

    @property
    def same_revision(self) -> bool:
        return self.local_commit == self.remote_commit


def _git(root: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", *args],
        cwd=root,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        check=False,
    )
    if result.returncode:
        raise RuntimeError(result.stderr.strip() or result.stdout.strip())
    return result.stdout.strip()


def check_for_updates(root: Path) -> UpdateStatus:
    resolved = root.resolve()
    branch = _git(resolved, "symbolic-ref", "--short", "HEAD")
    local_commit = _git(resolved, "rev-parse", "HEAD")
    remote_url = _git(resolved, "remote", "get-url", "origin")
    remote_ref = f"refs/heads/{branch}"
    remote_line = _git(resolved, "ls-remote", "--heads", "origin", remote_ref)
    if not remote_line:
        raise RuntimeError(f"GitHub側に現在のブランチがありません: {branch}")
    remote_commit = remote_line.split()[0]
    dirty_output = _git(resolved, "status", "--porcelain")
    dirty_files = len([line for line in dirty_output.splitlines() if line.strip()])
    return UpdateStatus(
        branch=branch,
        local_commit=local_commit,
        remote_commit=remote_commit,
        remote_url=remote_url,
        dirty_files=dirty_files,
    )


def format_update_status(status: UpdateStatus, language: str = "ja") -> str:
    if language == "en":
        state = (
            "This installation matches the remote branch."
            if status.same_revision
            else "The local and remote revisions differ. An update may be available."
        )
        action = (
            "Do not update automatically. Explain the release changes and ask the user first."
        )
        dirty = f"Uncommitted local files: {status.dirty_files}"
    else:
        state = (
            "このインストールはGitHubの現在版と一致しています。"
            if status.same_revision
            else "ローカル版とGitHub版が異なります。更新版がある可能性があります。"
        )
        action = "自動更新はしません。変更内容を説明し、利用者に確認してください。"
        dirty = f"未コミットのローカル変更: {status.dirty_files}件"
    return "\n".join(
        (
            state,
            f"branch: {status.branch}",
            f"local:  {status.local_commit}",
            f"remote: {status.remote_commit}",
            f"origin: {status.remote_url}",
            dirty,
            action,
        )
    )
