from __future__ import annotations

from pathlib import Path

from scripts.check_release_version import release_issues


def write_release_files(
    tmp_path: Path, *, version: str, changelog: str
) -> tuple[Path, Path]:
    pyproject = tmp_path / "pyproject.toml"
    pyproject.write_text(
        f'[project]\nname = "example"\nversion = "{version}"\n',
        encoding="utf-8",
    )
    changelog_path = tmp_path / "CHANGELOG.md"
    changelog_path.write_text(changelog, encoding="utf-8")
    return pyproject, changelog_path


def test_release_version_accepts_matching_latest_release(tmp_path: Path) -> None:
    pyproject, changelog = write_release_files(
        tmp_path,
        version="0.6.0",
        changelog=(
            "# Changelog\n\n## Unreleased\n\n"
            "## 0.6.0 - 2026-08-06\n\n- Released.\n"
        ),
    )

    assert release_issues(pyproject, changelog) == []


def test_release_version_rejects_mismatch(tmp_path: Path) -> None:
    pyproject, changelog = write_release_files(
        tmp_path,
        version="0.7.0",
        changelog=(
            "# Changelog\n\n## Unreleased\n\n"
            "## 0.6.0 - 2026-08-06\n\n- Released.\n"
        ),
    )

    issues = release_issues(pyproject, changelog)

    assert any("does not match" in issue for issue in issues)


def test_release_version_requires_unreleased_before_releases(tmp_path: Path) -> None:
    pyproject, changelog = write_release_files(
        tmp_path,
        version="0.6.0",
        changelog=(
            "# Changelog\n\n## 0.6.0 - 2026-08-06\n\n"
            "## Unreleased\n"
        ),
    )

    issues = release_issues(pyproject, changelog)

    assert any("must precede" in issue for issue in issues)
