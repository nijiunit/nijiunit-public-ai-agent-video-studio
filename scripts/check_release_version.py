from __future__ import annotations

import re
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SEMVER = re.compile(r"^\d+\.\d+\.\d+$")
RELEASE_HEADING = re.compile(
    r"^## (\d+\.\d+\.\d+) - (\d{4}-\d{2}-\d{2})$", re.MULTILINE
)


def project_version(pyproject_path: Path) -> str:
    with pyproject_path.open("rb") as handle:
        data = tomllib.load(handle)
    return str(data["project"]["version"])


def release_issues(pyproject_path: Path, changelog_path: Path) -> list[str]:
    issues: list[str] = []
    version = project_version(pyproject_path)
    changelog = changelog_path.read_text(encoding="utf-8")

    if not SEMVER.fullmatch(version):
        issues.append(
            f"pyproject.toml project.version must use MAJOR.MINOR.PATCH: {version}"
        )

    unreleased_marker = "## Unreleased"
    unreleased_position = changelog.find(unreleased_marker)
    releases = list(RELEASE_HEADING.finditer(changelog))

    if unreleased_position < 0:
        issues.append("CHANGELOG.md must contain a '## Unreleased' section")
    if not releases:
        issues.append("CHANGELOG.md has no dated release heading")
        return issues

    latest = releases[0]
    if unreleased_position > latest.start():
        issues.append("CHANGELOG.md '## Unreleased' must precede released versions")
    if latest.group(1) != version:
        issues.append(
            "pyproject.toml version "
            f"{version} does not match latest CHANGELOG release {latest.group(1)}"
        )

    return issues


def main() -> int:
    issues = release_issues(ROOT / "pyproject.toml", ROOT / "CHANGELOG.md")
    if issues:
        print("Release-version check failed:")
        for issue in issues:
            print(f"- {issue}")
        return 1

    version = project_version(ROOT / "pyproject.toml")
    print(f"Release-version check passed: project={version}, changelog={version}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
