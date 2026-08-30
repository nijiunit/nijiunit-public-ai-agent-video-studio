from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

from openpyxl import load_workbook
from PIL import Image

from video_storyboard import pipeline
from video_storyboard.schema import CharacterProfile, Shot, Storyboard
from video_storyboard.workbook import create_workbook


def _storyboard(description: str = "before") -> Storyboard:
    return Storyboard(
        title="test",
        logline="test",
        audience="test",
        visual_style="test",
        story_summary="test",
        character_bible=[CharacterProfile(name="none", description="none")],
        shots=[
            Shot(
                shot_number=1,
                title="shot",
                story_purpose="test",
                scene_description=description,
                characters=[],
                action="test",
                emotion="calm",
                camera="wide",
                lighting="soft",
                sound="none",
                continuity="same",
                reference_assets=[],
                main_image_prompt=description,
                video_prompt=description,
                frame_descriptions=[description] * 9,
            )
        ],
    )


def test_apply_corrections_revises_json_and_preserves_old_image(
    tmp_path: Path, monkeypatch
) -> None:
    run_dir = tmp_path / "v001"
    image_dir = run_dir / "images"
    image_dir.mkdir(parents=True)
    storyboard = _storyboard()
    (run_dir / "storyboard.json").write_text(
        storyboard.model_dump_json(indent=2), encoding="utf-8"
    )
    (run_dir / "manifest.json").write_text(
        json.dumps({"assets": []}), encoding="utf-8"
    )
    Image.new("RGB", (32, 18), "navy").save(image_dir / "shot_001.png")
    workbook_path = run_dir / "review" / "storyboard_v001.xlsx"
    create_workbook(storyboard, run_dir, [], workbook_path)
    workbook = load_workbook(workbook_path)
    sheet = workbook[workbook.sheetnames[1]]
    sheet["C4"] = "修正必要"
    sheet["H4"] = "小規模"
    sheet["C5"] = "背景を明るくする"
    workbook.save(workbook_path)

    guidance = SimpleNamespace(
        profile=SimpleNamespace(media=SimpleNamespace(aspect_ratio="16:9"))
    )
    monkeypatch.setattr(pipeline, "load_run_guidance", lambda _path: guidance)

    class FakeService:
        def __init__(self, **_kwargs):
            pass

        def revise_storyboard(self, *_args, **_kwargs):
            return _storyboard("after")

    monkeypatch.setattr(pipeline, "GeminiService", FakeService)

    result = pipeline.apply_corrections_command(
        run_dir, character_registry_dir=None
    )

    revised = Storyboard.model_validate_json(
        (run_dir / "storyboard.json").read_text(encoding="utf-8")
    )
    assert revised.shots[0].scene_description == "after"
    assert (run_dir / "storyboard_r001.json").is_file()
    assert (run_dir / "storyboard_r002.json").is_file()
    assert not (image_dir / "shot_001.png").exists()
    assert (
        run_dir / "rejected" / "before_storyboard_r002" / "shot_001.png"
    ).is_file()
    assert "再生成が必要な画像" in result
