from __future__ import annotations

import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKIP_PARTS = {
    ".git",
    ".mypy_cache",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "output",
    "tmp",
    "__pycache__",
}
TEXT_SUFFIXES = {
    "",
    ".cfg",
    ".example",
    ".ini",
    ".json",
    ".md",
    ".py",
    ".toml",
    ".txt",
    ".yaml",
    ".yml",
}


def is_local_env(path: Path) -> bool:
    return path.name.startswith(".env") and path.name != ".env.example"


def text_files() -> list[Path]:
    files: list[Path] = []
    for path in ROOT.rglob("*"):
        if (
            not path.is_file()
            or SKIP_PARTS.intersection(path.parts)
            or any(part.endswith(".egg-info") for part in path.parts)
            or is_local_env(path)
        ):
            continue
        if path.suffix.lower() not in TEXT_SUFFIXES or path.stat().st_size > 2_000_000:
            continue
        files.append(path)
    return files


def scan_text() -> list[str]:
    patterns = {
        "Windows user path": re.compile(r"[A-Za-z]:\\" + r"Users\\"),
        "Google API key": re.compile("AI" + r"za[0-9A-Za-z_-]{30,}"),
        "PEM private key": re.compile("BEGIN " + r"(?:RSA |EC |OPENSSH )?PRIVATE KEY"),
    }
    issues: list[str] = []
    for path in text_files():
        text = path.read_text(encoding="utf-8", errors="replace")
        for label, pattern in patterns.items():
            if pattern.search(text):
                issues.append(f"{path.relative_to(ROOT)}: possible {label}")
    return issues


def validate_publishable_profiles() -> list[str]:
    issues: list[str] = []
    for path in (ROOT / "examples").glob("**/profile.json"):
        data = json.loads(path.read_text(encoding="utf-8"))
        if data.get("publishable") is not True:
            issues.append(f"{path.relative_to(ROOT)}: publishable must be true")
        if not data.get("asset_license"):
            issues.append(f"{path.relative_to(ROOT)}: asset_license is missing")
        if data.get("source_type") not in {"original", "generated", "third_party"}:
            issues.append(f"{path.relative_to(ROOT)}: source_type is not reviewed")
    return issues


def validate_local_secret_ignores() -> list[str]:
    gitignore = (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
    rules = {line.strip() for line in gitignore if line.strip()}
    required = {".env", ".env.*", "!.env.example"}
    missing = sorted(required - rules)
    return [f".gitignore is missing required rule: {rule}" for rule in missing]


def main() -> int:
    issues = (
        scan_text()
        + validate_publishable_profiles()
        + validate_local_secret_ignores()
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
