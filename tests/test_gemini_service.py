from types import SimpleNamespace

import pytest

from video_storyboard.gemini_service import (
    _image_generation_config,
    _story_generation_config,
)
from video_storyboard.knowledge import StoryInstructions


def story_instructions(*, temperature: float | None) -> StoryInstructions:
    return StoryInstructions.model_validate(
        {
            "system_instruction": "test guidance",
            "requirements": [],
            "target_duration_seconds_min": 3,
            "target_duration_seconds_max": 3,
            "shot_count_min": 1,
            "shot_count_max": 1,
            "audience": "test audience",
            "prompt_language_instruction": "use English",
            "output_language_instruction": "preserve source language",
            "temperature": temperature,
            "max_output_tokens": 1024,
        }
    )


def test_story_config_omits_unsupported_sampling_parameter() -> None:
    config = _story_generation_config(story_instructions(temperature=None))

    assert {"temperature", "top_p", "top_k"}.isdisjoint(config)


def test_story_config_keeps_explicit_sampling_parameter() -> None:
    config = _story_generation_config(story_instructions(temperature=0.4))

    assert config["temperature"] == 0.4


@pytest.mark.parametrize("aspect_ratio", ["9:16", "16:9"])
def test_image_config_uses_the_pinned_aspect_ratio(aspect_ratio: str) -> None:
    profile = SimpleNamespace(
        media=SimpleNamespace(aspect_ratio=aspect_ratio),
        image=SimpleNamespace(image_size="1K"),
    )

    config = _image_generation_config(profile)

    image_config = config.get("image_config") or config["response_format"]["image"]
    assert image_config == {
        "aspect_ratio": aspect_ratio,
        "image_size": "1K",
    }
