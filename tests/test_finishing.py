from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.generate_storyboard_tts import load_voice_overrides
from scripts.rebuild_clean_soundtrack import ambience_filter
from video_storyboard.knowledge import MediaContract


def test_voice_config_supports_shot_specific_speakers(tmp_path: Path) -> None:
    path = tmp_path / "voices.json"
    path.write_text(
        json.dumps(
            {
                "shots": {
                    "3": {
                        "voice": "Kore",
                        "speaker": "ルクス",
                        "style": "bright",
                    }
                }
            },
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )

    overrides = load_voice_overrides(path)

    assert overrides["3"]["voice"] == "Kore"
    assert overrides["3"]["speaker"] == "ルクス"


def test_voice_config_rejects_non_object_shots(tmp_path: Path) -> None:
    path = tmp_path / "voices.json"
    path.write_text('{"shots": []}', encoding="utf-8")

    with pytest.raises(ValueError, match="shots"):
        load_voice_overrides(path)


def test_ambience_filter_uses_work_specific_settings() -> None:
    value = ambience_filter(
        1,
        2,
        MediaContract(
            shot_duration_seconds=3,
            aspect_ratio="16:9",
            width=1280,
            height=720,
            frames_per_second=24,
            review_frames_per_second=3,
        ),
        {"highpass_hz": 40, "lowpass_hz": 380, "volume": 0.016},
    )

    assert "highpass=f=40" in value
    assert "lowpass=f=380" in value
    assert "volume=0.016" in value
