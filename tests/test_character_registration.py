from __future__ import annotations

import json
from pathlib import Path

from PIL import Image

from video_storyboard.character_registration import (
    approve_character,
    character_status,
    register_character,
)
from video_storyboard.character_registry import CharacterRegistry
from video_storyboard.schema import CharacterProfile, Shot, Storyboard


def _storyboard(name: str) -> Storyboard:
    return Storyboard(
        title="test",
        logline="test",
        audience="test",
        visual_style="test",
        story_summary="test",
        character_bible=[CharacterProfile(name=name, description="test")],
        shots=[
            Shot(
                shot_number=1,
                title="test",
                story_purpose="test",
                scene_description="test",
                characters=[name],
                action="run",
                emotion="happy",
                camera="wide",
                lighting="day",
                sound="none",
                continuity="same",
                reference_assets=[],
                main_image_prompt="test",
                video_prompt="test",
                frame_descriptions=["frame"] * 9,
            )
        ],
    )


def test_character_is_pending_until_the_user_approves_it(tmp_path: Path) -> None:
    reference = tmp_path / "ritchan.png"
    Image.new("RGB", (32, 32), "pink").save(reference)
    spec = tmp_path / "spec.json"
    spec.write_text(
        json.dumps(
            {
                "name_ja": "リっちゃん",
                "kind": "human",
                "description_ja": "元気に走るオリジナルキャラクター",
                "identity_prompt_en": "An original energetic runner.",
                "immutable_traits": ["pink cap"],
                "references": [{"path": str(reference), "role": "identity"}],
                "source_type": "original",
                "rights_confirmed": True,
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    registry_dir = tmp_path / "characters"

    profile, ja, en = register_character(spec, registry_dir)

    assert profile.is_file()
    assert ja.is_file()
    assert en.is_file()
    assert CharacterRegistry.load_optional(registry_dir) is None or not CharacterRegistry.load(registry_dir).records
    pending = character_status(_storyboard("リっちゃん"), registry_dir)
    assert pending["pending"][0]["name"] == "リっちゃん"
    assert pending["unresolved"] == []

    character_id = profile.parents[1].name
    approve_character(registry_dir, character_id, "v001")

    registry = CharacterRegistry.load(registry_dir)
    records, unresolved = registry.resolve(["リっちゃん"])
    assert unresolved == []
    assert records[0].review_status == "approved"
    assert registry.validate() == []
