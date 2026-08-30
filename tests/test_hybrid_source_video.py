import json
from pathlib import Path
from types import SimpleNamespace

import pytest

from video_storyboard import video
from video_storyboard.assets import AssetRecord
from video_storyboard.knowledge import MediaContract
from video_storyboard.schema import CharacterProfile, Shot, Storyboard


def make_shot(
    number: int,
    *,
    production_mode: str = "generated_video",
    duration: float = 3,
    source_start: float | None = None,
    source_end: float | None = None,
) -> Shot:
    return Shot(
        shot_number=number,
        duration_seconds=duration,
        production_mode=production_mode,
        source_asset="source.mov" if production_mode == "source_video" else None,
        source_start_seconds=source_start,
        source_end_seconds=source_end,
        title=f"shot {number}",
        story_purpose="test",
        scene_description="test scene",
        characters=[],
        action="test action",
        emotion="calm",
        camera="locked",
        lighting="soft",
        sound="none",
        continuity="same scene",
        continuity_start_mode=(
            "previous_final_frame" if number > 1 else "storyboard_image"
        ),
        reference_assets=["source.mov"],
        main_image_prompt="test",
        video_prompt="test",
        frame_descriptions=["frame"] * 9,
    )


def make_storyboard(shots: list[Shot]) -> Storyboard:
    return Storyboard(
        title="hybrid",
        logline="source then generated",
        audience="test",
        visual_style="real",
        story_summary="test",
        character_bible=[CharacterProfile(name="none", description="none")],
        shots=shots,
    )


def test_source_video_allows_an_exact_partial_cut_before_generation() -> None:
    storyboard = make_storyboard(
        [
            make_shot(
                1,
                production_mode="source_video",
                source_start=0,
                source_end=3,
            ),
            make_shot(
                2,
                production_mode="source_video",
                duration=1.3,
                source_start=3,
                source_end=4.3,
            ),
            make_shot(3),
        ]
    )

    assert storyboard.shots[1].start_seconds == 3
    assert storyboard.shots[1].end_seconds == pytest.approx(4.3)
    assert storyboard.shots[2].start_seconds == pytest.approx(4.3)
    assert storyboard.total_duration_seconds == pytest.approx(7.3)
    assert storyboard.shots[1].frame_offset_seconds(8) == pytest.approx(
        1.3 * 8 / 9
    )


def test_generated_video_cannot_be_shorter_than_three_seconds() -> None:
    with pytest.raises(ValueError, match="exactly 3 seconds"):
        make_shot(1, duration=1.3)


def test_source_video_is_copied_without_calling_the_generation_service(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    shot = make_shot(
        1,
        production_mode="source_video",
        duration=1.3,
        source_start=15,
        source_end=16.3,
    )
    storyboard = make_storyboard([shot])
    source = tmp_path / "source.mov"
    source.write_bytes(b"source")
    assets = [
        AssetRecord(
            original_name="source.mov",
            original_path="source.mov",
            kind="video",
            role="video_reference",
            notes="test",
            api_path=str(source),
        )
    ]
    service_calls: list[int] = []

    class FakeService:
        model = "fake"

        def __init__(self, profile, model=None) -> None:
            pass

        def create_clip(self, *_args) -> None:
            service_calls.append(1)

    def fake_source_clip(_shot, _source, destination, _media):
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(b"clip")
        return destination

    monkeypatch.setattr(video, "VideoService", FakeService)
    monkeypatch.setattr(video, "render_source_clip", fake_source_clip)
    monkeypatch.setattr(video, "extract_nine_frames", lambda *_args, **_kwargs: [])
    monkeypatch.setattr(
        video,
        "inspect_video",
        lambda path: {
            "path": path.name,
            "duration_seconds": 1.3,
            "width": 1280,
            "height": 720,
            "fps": 24,
            "has_audio": True,
            "bytes": 4,
        },
    )
    profile = SimpleNamespace(
        media=MediaContract(width=1280, height=720),
        video=SimpleNamespace(maximum_character_reference_images=0),
    )

    completed = video.render_video_shots(
        storyboard,
        tmp_path,
        profile,
        assets=assets,
        character_registry_dir=None,
    )

    assert service_calls == []
    assert completed == [tmp_path / "video" / "clips" / "shot_001.mp4"]
    metadata = json.loads(
        (tmp_path / "video" / "metadata" / "shot_001.json").read_text(
            encoding="utf-8"
        )
    )
    assert metadata["production_mode"] == "source_video"
    assert metadata["source_end_seconds"] == 16.3


def test_concatenation_uses_the_real_hybrid_duration(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    storyboard = make_storyboard(
        [
            make_shot(
                1,
                production_mode="source_video",
                duration=1.3,
                source_start=0,
                source_end=1.3,
            ),
            make_shot(2),
        ]
    )
    clips = tmp_path / "video" / "clips"
    clips.mkdir(parents=True)
    (clips / "shot_001.mp4").write_bytes(b"one")
    (clips / "shot_002.mp4").write_bytes(b"two")
    captured: list[str] = []
    monkeypatch.setattr(video, "_run_ffmpeg", lambda args: captured.extend(args))

    video.concatenate_clips(
        storyboard,
        tmp_path,
        tmp_path / "final" / "video.mp4",
        MediaContract(width=1280, height=720),
    )

    assert captured[captured.index("-t") + 1] == "4.3"
    assert "trim=end_frame=103" in captured[captured.index("-vf") + 1]
