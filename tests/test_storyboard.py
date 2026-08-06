from pathlib import Path

from video_storyboard.schema import Storyboard

ROOT = Path(__file__).resolve().parents[1]


def test_public_storyboard_is_ten_three_second_shots() -> None:
    storyboard = Storyboard.model_validate_json(
        (ROOT / "examples" / "space-friends" / "storyboard.json").read_text(
            encoding="utf-8"
        )
    )
    assert len(storyboard.shots) == 10
    assert storyboard.total_duration_seconds == 30
    storyboard_image_shots = {
        shot.shot_number
        for shot in storyboard.shots
        if shot.continuity_start_mode == "storyboard_image"
    }
    assert storyboard_image_shots == {1, 4, 6, 8, 9}
