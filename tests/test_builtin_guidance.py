from pathlib import Path

import pytest

from video_storyboard.knowledge import load_builtin_guidance


def test_bundled_guidance_is_hash_verified() -> None:
    bundle = load_builtin_guidance()

    assert bundle.manifest.knowledge_version == "0.6.0-local.7"
    assert bundle.profile.profile_id == "standard-social-video"
    assert bundle.guide_path("ja").read_text(encoding="utf-8").strip()
    assert bundle.guide_path("en").read_text(encoding="utf-8").strip()


def test_bundled_guidance_rejects_tampered_resource(tmp_path: Path) -> None:
    source = Path("config/runtime-guidance")
    for item in source.iterdir():
        (tmp_path / item.name).write_bytes(item.read_bytes())
    (tmp_path / "agent_guide_ja.md").write_text("tampered", encoding="utf-8")

    with pytest.raises(RuntimeError, match="制作基本設定を検証できません"):
        load_builtin_guidance(tmp_path)
