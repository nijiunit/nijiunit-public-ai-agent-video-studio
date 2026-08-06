import json
from pathlib import Path

from video_storyboard import video
from video_storyboard.schema import CharacterProfile, Shot, Storyboard


def make_shot(number: int, mode: str) -> Shot:
    return Shot(
        shot_number=number,
        title=f"shot {number}",
        story_purpose="test",
        scene_description="test scene",
        characters=[],
        action="small motion",
        emotion="calm",
        camera="locked",
        lighting="soft",
        sound="none",
        continuity="same scene",
        continuity_start_mode=mode,
        reference_assets=[],
        main_image_prompt="test",
        video_prompt="test",
        frame_descriptions=["frame"] * 9,
    )


def test_previous_frame_mode_does_not_require_a_storyboard_image(
    tmp_path: Path, monkeypatch
) -> None:
    storyboard = Storyboard(
        title="test",
        logline="test",
        audience="test",
        visual_style="test",
        story_summary="test",
        character_bible=[CharacterProfile(name="test", description="test")],
        shots=[
            make_shot(1, "storyboard_image"),
            make_shot(2, "previous_final_frame"),
        ],
    )
    first_clip = tmp_path / "video" / "clips" / "shot_001.mp4"
    first_clip.parent.mkdir(parents=True)
    first_clip.write_bytes(b"existing")

    starts: list[Path] = []

    class FakeService:
        model = "fake-model"

        def __init__(self, model=None) -> None:
            pass

        def create_clip(self, shot, start, raw, metadata, character_lock) -> None:
            starts.append(start)
            raw.parent.mkdir(parents=True, exist_ok=True)
            raw.write_bytes(b"raw")
            metadata.parent.mkdir(parents=True, exist_ok=True)
            metadata.write_text("{}", encoding="utf-8")

    def fake_final_frame(_clip: Path, destination: Path) -> Path:
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(b"png")
        return destination

    def fake_standardize(_raw: Path, destination: Path) -> Path:
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(b"clip")
        return destination

    monkeypatch.setattr(video, "VideoService", FakeService)
    monkeypatch.setattr(video, "extract_final_frame", fake_final_frame)
    monkeypatch.setattr(video, "standardize_clip", fake_standardize)
    monkeypatch.setattr(video, "extract_nine_frames", lambda *_args: [])
    monkeypatch.setattr(
        video,
        "inspect_video",
        lambda path: {
            "path": path.name,
            "duration_seconds": 3.0,
            "width": 1280,
            "height": 720,
            "fps": 24.0,
        },
    )

    completed = video.render_video_shots(
        storyboard,
        tmp_path,
        character_registry_dir=None,
    )

    assert len(completed) == 2
    assert starts == [tmp_path / "video" / "continuity" / "shot_002_first_frame.png"]
    metadata = json.loads(
        (tmp_path / "video" / "metadata" / "shot_002.json").read_text(
            encoding="utf-8"
        )
    )
    assert metadata["starting_frame"] == "video/continuity/shot_002_first_frame.png"

