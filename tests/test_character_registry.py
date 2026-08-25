from __future__ import annotations

import json
from pathlib import Path

import pytest

from video_storyboard.character_registry import (
    CharacterRegistry,
    require_resolved_character_names,
)


def _write_test_registry(root: Path) -> Path:
    registry_dir = root / "characters"
    entries = []
    definitions = (
        (
            "test_robot",
            "テストロボ",
            ["Test Robot"],
            "cinematic_descent",
            ["cinematic-descent"],
        ),
        (
            "test_light",
            "テストライト",
            ["Test Light"],
            "invitation_pulse",
            ["invitation pulse"],
        ),
    )
    for character_id, name_ja, aliases, motion_id, triggers in definitions:
        profile_dir = registry_dir / character_id / "v001"
        references = profile_dir / "references"
        motions = profile_dir / "motions"
        references.mkdir(parents=True)
        motions.mkdir(parents=True)
        (references / "identity.png").write_bytes(b"test identity")
        (motions / "design.mp4").write_bytes(b"test design motion")
        (motions / f"{motion_id}.mp4").write_bytes(b"test action motion")
        profile = {
            "schema_version": "1.0",
            "id": character_id,
            "version": "v001",
            "name_ja": name_ja,
            "aliases": aliases,
            "concept_id": "unit_test",
            "kind": "robot",
            "description_ja": "単体テスト専用の架空キャラクター",
            "identity_prompt_en": "A fictional unit-test character.",
            "immutable_traits": ["fictional"],
            "references": [
                {
                    "path": "references/identity.png",
                    "role": "identity",
                    "label": "test identity",
                }
            ],
            "design_video": {
                "id": "design_presence",
                "name_ja": "通常存在",
                "clip_path": "motions/design.mp4",
                "prompt_en": "Preserve neutral identity.",
            },
            "motions": [
                {
                    "id": motion_id,
                    "name_ja": motion_id,
                    "clip_path": f"motions/{motion_id}.mp4",
                    "triggers": triggers,
                    "prompt_en": f"Perform {motion_id}.",
                }
            ],
            "source_type": "generated",
            "asset_license": "CC0-1.0",
            "publishable": True,
        }
        profile_path = profile_dir / "profile.json"
        profile_path.write_text(
            json.dumps(profile, ensure_ascii=False),
            encoding="utf-8",
        )
        entries.append(
            {
                "id": character_id,
                "active_version": "v001",
                "profile": profile_path.relative_to(registry_dir).as_posix(),
            }
        )
    (registry_dir / "registry.json").write_text(
        json.dumps(
            {
                "schema_version": "1.0",
                "concepts": [
                    {
                        "id": "unit_test",
                        "name_ja": "単体テスト",
                        "description_ja": "作品に依存しないテストデータ",
                    }
                ],
                "characters": entries,
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    return registry_dir


def test_registry_is_valid_without_a_bundled_sample(tmp_path: Path) -> None:
    registry = CharacterRegistry.load(_write_test_registry(tmp_path))

    assert registry.validate() == []
    assert {record.id for record in registry.records} == {
        "test_robot",
        "test_light",
    }
    assert all(record.publishable for record in registry.records)
    assert all(record.asset_license for record in registry.records)


def test_alias_and_motion_selection_use_synthetic_fixtures(tmp_path: Path) -> None:
    registry = CharacterRegistry.load(_write_test_registry(tmp_path))
    records, unresolved = registry.resolve(["Test Robot", "テストライト"])

    assert unresolved == []
    motions = registry.select_motions(
        records,
        "cinematic-descentしながらinvitation pulseを見せる",
    )
    selected = {(motion.character_id, motion.motion_id) for motion in motions}
    assert ("test_robot", "design_presence") in selected
    assert ("test_robot", "cinematic_descent") in selected
    assert ("test_light", "design_presence") in selected
    assert ("test_light", "invitation_pulse") in selected
    assert all(motion.clip_path.is_file() for motion in motions)


def test_named_character_requires_a_registry_before_generation() -> None:
    with pytest.raises(RuntimeError, match="キャラクター台帳"):
        require_resolved_character_names(None, ["新しい主人公"])


def test_unknown_character_stops_before_generation(tmp_path: Path) -> None:
    registry = CharacterRegistry.load(_write_test_registry(tmp_path))

    with pytest.raises(RuntimeError, match="生成を停止"):
        require_resolved_character_names(registry, ["未登録の主人公"])
