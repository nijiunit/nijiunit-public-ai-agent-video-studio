# Contributing

Small, focused pull requests are welcome.

1. Create a branch.
2. Run `scripts/setup.ps1 -WithDev` on Windows or `scripts/setup.sh --dev` on
   macOS/Linux.
3. Run `pytest` and `ruff check .`.
4. Do not commit private stories, likeness references, API keys, generated
   provider operation IDs, or media without clear publication rights.
5. For sample media, update `ASSET_LICENSES.md` and the relevant character
   profile provenance fields.

API-backed tests must be opt-in. Ordinary CI must not spend credits or require a
secret.

## Versioning and releases

- Treat `project.version` in `pyproject.toml` as the single version source.
- Record user-visible changes under `Unreleased` in `CHANGELOG.md` first.
- Do not change the version in an ordinary pull request. Update the version and
  CHANGELOG together only in a release-preparation pull request, following
  Semantic Versioning.
- Run `python scripts/check_release_version.py` before release.
- Never move a published tag. Publish a correction as a new PATCH version.

See the [English release guide](docs/releasing.md) or
[日本語版](docs/releasing.ja.md).
