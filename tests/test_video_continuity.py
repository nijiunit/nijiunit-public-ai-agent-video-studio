import json
from pathlib import Path

import pytest

from video_storyboard import video
from video_storyboard.knowledge import ProductionProfile
from video_storyboard.schema import CharacterProfile, Shot, Storyboard


def make_profile() -> ProductionProfile:
    return ProductionProfile.model_validate(
        {
            "schema_version": "1.0",
            "knowledge_version": "test-v1",
            "profile_id": "test",
            "models": {
                "story": "story-model",
                "image": "image-model",
                "video": "video-model",
                "tts": "tts-model",
                "asr": "asr-model",
            },
            "media": {
                "shot_duration_seconds": 3,
                "aspect_ratio": "16:9",
                "width": 1280,
                "height": 720,
                "frames_per_second": 24,
                "review_frames_per_second": 3,
            },
            "story": {
                "system_instruction": "test",
                "requirements": [],
                "target_duration_seconds_min": 3,
                "target_duration_seconds_max": 180,
                "shot_count_min": 1,
                "shot_count_max": 60,
                "audience": "test",
                "prompt_language_instruction": "use English",
                "output_language_instruction": "preserve the source language",
                "temperature": 0.4,
                "max_output_tokens": 1024,
            },
            "image": {"requirements": [], "reference_limit": 4, "image_size": "1K"},
            "video": {
                "api_family": "interactions",
                "requirements": [],
                "reference_instructions": [],
                "negative_prompt_terms": [],
                "maximum_character_reference_images": 6,
                "supports_asset_reference_images": False,
                "supports_negative_prompt": False,
                "provider_duration_seconds": 3,
                "provider_duration_seconds_with_references": 3,
                "provider_resolution": "720p",
            },
            "audio": {
                "default_voice": "test",
                "default_speaker": "test",
                "default_style": "test",
                "tts_language_instruction": "preserve source language",
                "transcription_instruction": "transcribe exact speech only",
                "maximum_speech_seconds": 2.5,
                "maximum_tempo_factor": 1.15,
                "default_ambience": {
                    "highpass_hz": 55,
                    "lowpass_hz": 700,
                    "volume": 0.038,
                },
                "subtitle": {
                    "font_name": "Noto Sans",
                    "font_size": 40,
                    "primary_colour": "&H00FFFFFF",
                    "outline_colour": "&H00101720",
                    "back_colour": "&H88070B12",
                    "bold": True,
                    "border_style": 3,
                    "outline": 7,
                    "shadow": 0,
                    "alignment": 2,
                    "margin_horizontal": 70,
                    "margin_vertical": 48,
                    "start_seconds": 0.12,
                    "end_padding_seconds": 0.08,
                    "fade_in_milliseconds": 100,
                    "fade_out_milliseconds": 120,
                },
            },
        }
    )


@pytest.mark.parametrize(
    ("aspect_ratio", "width", "height"),
    [("9:16", 720, 1280), ("16:9", 1280, 720)],
)
def test_video_request_and_prompt_use_the_pinned_format(
    aspect_ratio: str,
    width: int,
    height: int,
) -> None:
    profile = make_profile().for_aspect_ratio(aspect_ratio)
    shot = make_shot(1, "storyboard_image")

    response_format = video._video_response_format(profile)
    prompt = video._video_prompt(shot, profile)

    assert response_format["aspect_ratio"] == aspect_ratio
    assert response_format["duration"] == "3s"
    assert f"{aspect_ratio} at {width}x{height}" in prompt


@pytest.mark.parametrize(
    ("aspect_ratio", "width", "height"),
    [("9:16", 720, 1280), ("16:9", 1280, 720)],
)
def test_video_normalization_uses_the_pinned_dimensions(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    aspect_ratio: str,
    width: int,
    height: int,
) -> None:
    profile = make_profile().for_aspect_ratio(aspect_ratio)
    captured: list[str] = []
    monkeypatch.setattr(video, "inspect_video", lambda _path: {"has_audio": False})
    monkeypatch.setattr(
        video,
        "_run_ffmpeg",
        lambda arguments: captured.extend(arguments),
    )

    video.standardize_clip(tmp_path / "source.mp4", tmp_path / "out.mp4", profile.media)

    video_filter = captured[captured.index("-vf") + 1]
    assert f"scale={width}:{height}" in video_filter
    assert f"pad={width}:{height}" in video_filter


@pytest.mark.parametrize(
    ("aspect_ratio", "width", "height"),
    [("9:16", 720, 1280), ("16:9", 1280, 720)],
)
def test_nine_frame_review_uses_the_pinned_dimensions(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    aspect_ratio: str,
    width: int,
    height: int,
) -> None:
    profile = make_profile().for_aspect_ratio(aspect_ratio)
    captured: list[str] = []

    def fake_ffmpeg(arguments: list[str]) -> None:
        captured.extend(arguments)
        for number in range(1, 10):
            (tmp_path / "frames" / f"frame_{number:02d}.jpg").write_bytes(b"frame")

    monkeypatch.setattr(video, "_run_ffmpeg", fake_ffmpeg)

    frames = video.extract_nine_frames(
        tmp_path / "clip.mp4",
        tmp_path / "frames",
        profile.media,
    )

    video_filter = captured[captured.index("-vf") + 1]
    assert len(frames) == 9
    assert f"scale={width // 2}:{height // 2}" in video_filter


@pytest.mark.parametrize(
    ("aspect_ratio", "width", "height"),
    [("9:16", 720, 1280), ("16:9", 1280, 720)],
)
def test_final_video_reapplies_the_pinned_dimensions(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    aspect_ratio: str,
    width: int,
    height: int,
) -> None:
    profile = make_profile().for_aspect_ratio(aspect_ratio)
    storyboard = Storyboard(
        title="test",
        logline="test",
        audience="test",
        visual_style="test",
        aspect_ratio=aspect_ratio,
        story_summary="test",
        character_bible=[CharacterProfile(name="test", description="test")],
        shots=[make_shot(1, "storyboard_image")],
    )
    clip = tmp_path / "video" / "clips" / "shot_001.mp4"
    clip.parent.mkdir(parents=True)
    clip.write_bytes(b"clip")
    captured: list[str] = []
    monkeypatch.setattr(
        video,
        "_run_ffmpeg",
        lambda arguments: captured.extend(arguments),
    )

    video.concatenate_clips(
        storyboard,
        tmp_path,
        tmp_path / "final" / "video.mp4",
        profile.media,
    )

    video_filter = captured[captured.index("-vf") + 1]
    assert f"scale={width}:{height}" in video_filter
    assert f"pad={width}:{height}" in video_filter


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

        def __init__(self, profile, model=None) -> None:
            pass

        def create_clip(self, shot, start, raw, metadata, character_lock) -> None:
            starts.append(start)
            raw.parent.mkdir(parents=True, exist_ok=True)
            raw.write_bytes(b"raw")
            metadata.parent.mkdir(parents=True, exist_ok=True)
            metadata.write_text("{}", encoding="utf-8")

    def fake_final_frame(_clip: Path, destination: Path, _media) -> Path:
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(b"png")
        return destination

    def fake_standardize(_raw: Path, destination: Path, _media) -> Path:
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
        profile=make_profile(),
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
