English | [日本語](releasing.ja.md)

# Versioning and release procedure

This document keeps repository maintenance consistent between human maintainers and AI agents.

## Single version source

The official version is only the following value in `pyproject.toml`:

```toml
[project]
version = "0.6.0"
```

Do not create a duplicate `VERSION` file. The latest released heading in `CHANGELOG.md` must match this value. `scripts/check_release_version.py` detects a mismatch.

## Ordinary changes

Do not change the version number during ordinary implementation work.

1. Record user-visible features, fixes, and security changes under `Unreleased` in `CHANGELOG.md`.
2. Typographical corrections, formatting, internal refactoring, and test-only changes do not need an entry unless they affect users.
3. Run the tests and public-safety checks appropriate to the change.

This allows several changes to be collected into one release.

## Choosing a version number

Use Semantic Versioning in `MAJOR.MINOR.PATCH` form.

- PATCH: a backward-compatible fix, such as `0.6.0` to `0.6.1`
- MINOR: a backward-compatible feature, such as `0.6.0` to `0.7.0`
- MAJOR: an incompatible change, such as `1.4.0` to `2.0.0`

For an incompatible change before `1.0.0`, the version impact can be ambiguous. An AI agent must confirm the chosen number with the user.

## Preparing a release

Perform these steps only when the user explicitly requests release preparation.

1. Review Git changes and confirm that no secret or non-public asset is included.
2. Use the `Unreleased` entries to determine PATCH, MINOR, or MAJOR. Ask the user if the choice is unclear.
3. Update `project.version` in `pyproject.toml`.
4. Move the `Unreleased` entries into `## X.Y.Z - YYYY-MM-DD`, leaving a new empty `## Unreleased` section above it.
5. Run:

   ```powershell
   .\.venv\Scripts\python.exe scripts\check_release_version.py
   .\.venv\Scripts\python.exe -m pytest
   .\.venv\Scripts\python.exe -m ruff check .
   .\.venv\Scripts\python.exe scripts\check_public_repo.py
   ```

6. Commit and push while the repository is private, then verify GitHub Actions and the rendered GitHub pages.
7. Create a tag, GitHub Release, or visibility change only after explicit user confirmation.

On macOS or Linux, replace `.\.venv\Scripts\python.exe` with `./.venv/bin/python`.

## Git tags and GitHub Releases

Prefix the version with `v`. Version `0.6.0` uses tag `v0.6.0`.

```bash
git tag -a v0.6.0 -m "Release v0.6.0"
git push origin v0.6.0
```

These commands change external state. An AI agent runs them only after an explicit user request or approval. Never move a published tag to a different commit. Correct an error with a new PATCH release.

Use `v0.6.0` as the corresponding GitHub Release title and base the release notes on the matching CHANGELOG entry. Before adding large generated media, review repository size and distribution rights again.

## AI-agent completion report

A release-preparation report must include:

- old and new versions
- why PATCH, MINOR, or MAJOR was chosen
- the entries moved from `Unreleased`
- checks executed and their results
- which of commit, push, tag, GitHub Release, and public visibility were actually performed
- untested environments, such as macOS, and human decisions still required, such as publication rights
