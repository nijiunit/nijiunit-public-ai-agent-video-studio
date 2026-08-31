from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAX_SCAN_BYTES = 10_000_000

USER_PLACEHOLDER = r"(?:\[user\]|\[username\]|<user>|<username>|USERNAME|USERPROFILE|YourName)"
MAC_USER_ROOT = "/" + "Users/"
LINUX_USER_ROOT = "/" + "home/"
SECRET_PATTERNS = {
    "Windows user path": re.compile(
        r"[A-Za-z]:\\{1,2}Users\\{1,2}(?!"
        + USER_PLACEHOLDER
        + r"(?:\\{1,2}|$))[^\\\r\n]+(?:\\{1,2}|$)",
        re.IGNORECASE,
    ),
    "macOS user path": re.compile(
        re.escape(MAC_USER_ROOT)
        + r"(?!"
        + USER_PLACEHOLDER
        + r"(?:/|$))[^/\r\n]+(?:/|$)",
        re.IGNORECASE,
    ),
    "Linux user path": re.compile(
        re.escape(LINUX_USER_ROOT)
        + r"(?!"
        + USER_PLACEHOLDER
        + r"(?:/|$))[^/\r\n]+(?:/|$)",
        re.IGNORECASE,
    ),
    "Google API key": re.compile("AI" + r"za[0-9A-Za-z_-]{30,}"),
    "PEM private key": re.compile("BEGIN " + r"(?:RSA |EC |OPENSSH )?PRIVATE KEY"),
    "GitHub token": re.compile(
        r"(?:github_pat_[0-9A-Za-z_]{20,}|gh" + r"[pousr]_[0-9A-Za-z]{20,})"
    ),
    "OpenAI key": re.compile("sk" + r"-(?:proj-)?[0-9A-Za-z_-]{20,}"),
    "AWS access key": re.compile(r"\bAK" + r"IA[0-9A-Z]{16}\b"),
    "Slack token": re.compile("xo" + r"x[baprs]-[0-9A-Za-z-]{10,}"),
    "Stripe live key": re.compile(r"(?:sk|rk)_" + r"live_[0-9A-Za-z]{16,}"),
    "Azure account key": re.compile("Account" + r"Key=[0-9A-Za-z+/=]{20,}"),
    "Credential in URL": re.compile(r"https?://[^\s/:@]+:[^\s/@]+@"),
}


def is_local_env(path: Path) -> bool:
    return path.name.startswith(".env") and path.name != ".env.example"


def _git_files(root: Path, *arguments: str) -> list[Path]:
    result = subprocess.run(
        ["git", "ls-files", "-z", *arguments],
        cwd=root,
        capture_output=True,
        check=True,
    )
    return [
        root / relative
        for relative in result.stdout.decode("utf-8").split("\0")
        if relative
    ]


def tracked_files(root: Path = ROOT) -> list[Path]:
    return _git_files(root, "--cached")


def publishable_files(root: Path = ROOT) -> list[Path]:
    return _git_files(root, "--cached", "--others", "--exclude-standard")


def scan_publishable_files(root: Path = ROOT) -> list[str]:
    issues: list[str] = []
    for path in publishable_files(root):
        if not path.is_file():
            continue
        relative = path.relative_to(root)
        if path.is_symlink():
            issues.append(f"{relative}: symbolic link requires manual review")
            continue
        size = path.stat().st_size
        if size > MAX_SCAN_BYTES:
            issues.append(
                f"{relative}: file exceeds {MAX_SCAN_BYTES} bytes and requires manual review"
            )
            continue
        text = path.read_bytes().decode("latin-1")
        for label, pattern in SECRET_PATTERNS.items():
            if pattern.search(text):
                issues.append(f"{relative}: possible {label}")
    return issues


def validate_publishable_profiles(root: Path = ROOT) -> list[str]:
    issues: list[str] = []
    for path in (root / "examples").glob("**/profile.json"):
        data = json.loads(path.read_text(encoding="utf-8"))
        if data.get("publishable") is not True:
            issues.append(f"{path.relative_to(root)}: publishable must be true")
        if not data.get("asset_license"):
            issues.append(f"{path.relative_to(root)}: asset_license is missing")
        if data.get("source_type") not in {"original", "generated", "third_party"}:
            issues.append(f"{path.relative_to(root)}: source_type is not reviewed")
    return issues


def validate_local_secret_ignores(root: Path = ROOT) -> list[str]:
    gitignore = (root / ".gitignore").read_text(encoding="utf-8").splitlines()
    rules = {line.strip() for line in gitignore if line.strip()}
    required = {
        ".env",
        ".env.*",
        "!.env.example",
        "characters/*",
        "!characters/README.md",
        "/temp*.md",
        "/会話履歴*.md",
    }
    missing = sorted(required - rules)
    return [f".gitignore is missing required rule: {rule}" for rule in missing]


def validate_no_tracked_local_env(root: Path = ROOT) -> list[str]:
    return [
        f"{path.relative_to(root)}: local environment file must not be tracked"
        for path in tracked_files(root)
        if is_local_env(path)
    ]


def validate_no_tracked_private_characters(root: Path = ROOT) -> list[str]:
    allowed = Path("characters/README.md")
    return [
        f"{path.relative_to(root).as_posix()}: private character data must not be tracked"
        for path in tracked_files(root)
        if path.relative_to(root).parts[:1] == ("characters",)
        and path.relative_to(root) != allowed
    ]


def main() -> int:
    issues = (
        scan_publishable_files()
        + validate_publishable_profiles()
        + validate_local_secret_ignores()
        + validate_no_tracked_local_env()
        + validate_no_tracked_private_characters()
    )
    if issues:
        print("Public-repository safety check failed:")
        for issue in issues:
            print(f"- {issue}")
        return 1
    print("Public-repository safety check passed.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
