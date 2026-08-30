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
    relation: str

    @property
    def same_revision(self) -> bool:
        return self.local_commit == self.remote_commit

    @property
    def update_available(self) -> bool:
        return self.relation == "local_behind"


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


def _git_returncode(root: Path, *args: str) -> int:
    return subprocess.run(
        ["git", *args],
        cwd=root,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        check=False,
    ).returncode


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
    if _git_returncode(resolved, "cat-file", "-e", f"{remote_commit}^{{commit}}"):
        _git(resolved, "fetch", "--no-tags", "--quiet", "origin", remote_ref)
    if local_commit == remote_commit:
        relation = "same"
    elif not _git_returncode(
        resolved, "merge-base", "--is-ancestor", remote_commit, local_commit
    ):
        relation = "local_ahead"
    elif not _git_returncode(
        resolved, "merge-base", "--is-ancestor", local_commit, remote_commit
    ):
        relation = "local_behind"
    else:
        relation = "diverged"
    dirty_output = _git(resolved, "status", "--porcelain")
    dirty_files = len([line for line in dirty_output.splitlines() if line.strip()])
    return UpdateStatus(
        branch=branch,
        local_commit=local_commit,
        remote_commit=remote_commit,
        remote_url=remote_url,
        dirty_files=dirty_files,
        relation=relation,
    )


def format_update_status(status: UpdateStatus, language: str = "ja") -> str:
    if language == "en":
        states = {
            "same": "This installation matches the GitHub branch.",
            "local_behind": "A newer revision is available on GitHub.",
            "local_ahead": (
                "This local test revision is newer than the GitHub branch. "
                "This is not an available update."
            ),
            "diverged": "The local and GitHub branches have diverged.",
        }
        actions = {
            "same": "Continue with the installed revision.",
            "local_behind": (
                "Do not update automatically. Explain the release changes and ask "
                "the user first."
            ),
            "local_ahead": (
                "Do not offer an update or replace this revision with the older "
                "GitHub revision. Continue the authorized local test."
            ),
            "diverged": (
                "Do not update, merge, or overwrite automatically. Ask the repository "
                "maintainer how to proceed."
            ),
        }
        state = states[status.relation]
        action = actions[status.relation]
        dirty = f"Uncommitted local files: {status.dirty_files}"
    else:
        states = {
            "same": "このインストールはGitHubの現在版と一致しています。",
            "local_behind": "GitHubに新しい更新版があります。",
            "local_ahead": (
                "このローカル検証版はGitHub公開版より新しい状態です。"
                "これは更新候補ではありません。"
            ),
            "diverged": "ローカル版とGitHub版の履歴が分岐しています。",
        }
        actions = {
            "same": "現在の版で続行できます。",
            "local_behind": (
                "自動更新はしません。変更内容を説明し、利用者に確認してください。"
            ),
            "local_ahead": (
                "更新を提案したり、古いGitHub公開版へ戻したりしないでください。"
                "許可済みのローカル通しテストを続行してください。"
            ),
            "diverged": (
                "自動更新、マージ、上書きは行わず、リポジトリ担当者へ確認してください。"
            ),
        }
        state = states[status.relation]
        action = actions[status.relation]
        dirty = f"未コミットのローカル変更: {status.dirty_files}件"
    return "\n".join(
        (
            state,
            f"branch: {status.branch}",
            f"local:  {status.local_commit}",
            f"remote: {status.remote_commit}",
            f"relation: {status.relation}",
            f"origin: {status.remote_url}",
            dirty,
            action,
        )
    )
