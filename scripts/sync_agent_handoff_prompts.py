from __future__ import annotations

import argparse
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MANIFEST_PATH = ROOT / "config" / "agent-handoff" / "manifest.json"


def load_manifest(path: Path = MANIFEST_PATH) -> dict[str, object]:
    return json.loads(path.read_text(encoding="utf-8"))


def render_route(config: dict[str, object], root: Path = ROOT) -> str:
    guide_path = root / str(config["guide"])
    text = guide_path.read_text(encoding="utf-8").strip()
    handoff_path = config.get("handoff")
    if handoff_path:
        if text.count("{{HANDOFF_PROMPT}}") != 1:
            raise ValueError(f"{guide_path} must contain one handoff marker")
        handoff = (root / str(handoff_path)).read_text(encoding="utf-8").strip()
        text = text.replace("{{HANDOFF_PROMPT}}", handoff)
    elif "{{HANDOFF_PROMPT}}" in text:
        raise ValueError(f"{guide_path} has an unresolved handoff marker")

    for forbidden in config.get("forbidden", []):
        if str(forbidden) in text:
            raise ValueError(f"{guide_path} contains another route: {forbidden}")
    return text + "\n"


def rendered_prompts(
    root: Path = ROOT, *, include_unverified: bool = False
) -> dict[tuple[str, str], str]:
    manifest = load_manifest(root / "config" / "agent-handoff" / "manifest.json")
    routes = manifest["routes"]
    assert isinstance(routes, dict)
    result: dict[tuple[str, str], str] = {}
    for language, language_routes in routes.items():
        assert isinstance(language_routes, dict)
        for route, config in language_routes.items():
            assert isinstance(config, dict)
            status = str(config.get("status", "unverified"))
            if status not in {"verified", "unverified"}:
                raise ValueError(f"Invalid handoff status for {language}/{route}: {status}")
            if status != "verified" and not include_unverified:
                continue
            result[(str(language), str(route))] = render_route(config, root)
    return result


def sync(manual_root: Path, *, check: bool = False) -> list[Path]:
    changed: list[Path] = []
    for (language, route), text in rendered_prompts().items():
        destination = (
            manual_root
            / "public"
            / "ai-agent-video-manual"
            / language
            / "handoff"
            / "prompts"
            / f"{route}.txt"
        )
        current = destination.read_text(encoding="utf-8") if destination.exists() else None
        if current == text:
            continue
        changed.append(destination)
        if not check:
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_text(text, encoding="utf-8", newline="\n")
    return changed


def main() -> int:
    parser = argparse.ArgumentParser(description="Sync isolated AI handoff prompts.")
    parser.add_argument("--manual-root", type=Path, required=True)
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    changed = sync(args.manual_root.resolve(), check=args.check)
    if args.check and changed:
        for path in changed:
            print(path)
        return 1
    for path in changed:
        print(path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
