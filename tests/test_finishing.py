from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.build_cinematic_soundtrack import pulse, smoothstep, speech_duck
from scripts.generate_storyboard_tts import load_voice_overrides
from scripts.rebuild_clean_soundtrack import ambience_filter


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


def test_space_to_nature_ambience_changes_by_location() -> None:
    space = ambience_filter(1, 2, "space-to-nature")
    sky = ambience_filter(1, 6, "space-to-nature")
    ground = ambience_filter(1, 9, "space-to-nature")

    assert "lowpass=f=380" in space
    assert "lowpass=f=1800" in sky
    assert "lowpass=f=2300" in ground


def test_cinematic_envelopes_are_continuous_and_duck_dialogue() -> None:
    assert smoothstep(0.0, 1.0, -1.0) == 0.0
    assert smoothstep(0.0, 1.0, 2.0) == 1.0
    assert 0.49 < smoothstep(0.0, 1.0, 0.5) < 0.51

    assert pulse(5.0, 6.0, 0.2, 1.0, 0.3) == 0.0
    assert pulse(6.5, 6.0, 0.2, 1.0, 0.3) == 1.0
    assert speech_duck(4.0) == 1.0
    assert speech_duck(7.0) < 0.6
    assert speech_duck(28.0) < 0.6
    assert speech_duck(26.0) == 1.0
