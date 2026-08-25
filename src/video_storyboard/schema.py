from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator


class Shot(BaseModel):
    shot_number: int = Field(ge=1, description="Sequential number starting at 1")
    duration_seconds: int = Field(
        default=3, ge=3, le=3, description="One three-second review-sheet unit"
    )
    title: str = Field(description="Short shot title")
    story_purpose: str = Field(description="Purpose within the story")
    scene_description: str = Field(description="Visible content of the frame")
    characters: list[str] = Field(description="Characters visible in the frame")
    action: str = Field(description="Single action during the shot")
    emotion: str = Field(description="Character emotion and expression")
    camera: str = Field(description="Framing, camera position, and movement")
    lighting: str = Field(description="Time, light, color, and atmosphere")
    dialogue: str = Field(default="", description="Exact dialogue or empty string")
    narration: str = Field(default="", description="Exact narration or empty string")
    sound: str = Field(description="Ambience, sound effects, and music plan")
    continuity: str = Field(description="Elements that must match adjacent shots")
    continuity_start_mode: Literal[
        "storyboard_image",
        "previous_final_frame",
    ] = Field(
        default="storyboard_image",
        description=(
            "Normally storyboard_image. Use previous_final_frame only when "
            "continuing the exact same visual setup."
        ),
    )
    reference_assets: list[str] = Field(description="Referenced filenames from input")
    main_image_prompt: str = Field(
        description="Detailed prompt for the main starting image"
    )
    video_prompt: str = Field(
        description="Detailed prompt for this three-second video"
    )
    frame_descriptions: list[str] = Field(
        min_length=9,
        max_length=9,
        description="Nine time-ordered descriptions of visible frame changes",
    )

    @property
    def start_seconds(self) -> int:
        return (self.shot_number - 1) * 3

    @property
    def end_seconds(self) -> int:
        return self.start_seconds + 3


class CharacterProfile(BaseModel):
    name: str
    description: str


class ApiShot(BaseModel):
    shot_number: int
    title: str
    purpose: str
    scene_action: str
    characters: list[str]
    visual_direction: str
    audio: str
    dialogue: str = ""
    narration: str = ""
    continuity: str
    continuity_start_mode: Literal[
        "storyboard_image",
        "previous_final_frame",
    ] = "storyboard_image"
    reference_assets: list[str]
    main_image_prompt: str
    video_prompt: str
    frame_descriptions: list[str]


class ApiStoryboard(BaseModel):
    title: str
    logline: str
    visual_style: str
    character_bible: list[str]
    shots: list[ApiShot]

    def to_storyboard(
        self,
        *,
        audience: str = "general audience",
        aspect_ratio: Literal["16:9", "9:16"] = "16:9",
    ) -> "Storyboard":
        converted_shots: list[Shot] = []
        for number, source in enumerate(self.shots, start=1):
            frames = list(source.frame_descriptions[:9])
            while len(frames) < 9:
                frames.append(frames[-1] if frames else source.scene_action)
            converted_shots.append(
                Shot(
                    shot_number=number,
                    title=source.title,
                    story_purpose=source.purpose,
                    scene_description=source.scene_action,
                    characters=source.characters,
                    action=source.scene_action,
                    emotion=source.visual_direction,
                    camera=source.visual_direction,
                    lighting=source.visual_direction,
                    dialogue=source.dialogue,
                    narration=source.narration,
                    sound=source.audio,
                    continuity=source.continuity,
                    continuity_start_mode=source.continuity_start_mode,
                    reference_assets=source.reference_assets,
                    main_image_prompt=source.main_image_prompt,
                    video_prompt=source.video_prompt,
                    frame_descriptions=frames,
                )
            )
        profiles: list[CharacterProfile] = []
        for text in self.character_bible:
            name, separator, description = text.partition(":")
            profiles.append(
                CharacterProfile(
                    name=name.strip() if separator else "Unlabeled",
                    description=description.strip() if separator else text,
                )
            )
        return Storyboard(
            title=self.title,
            logline=self.logline,
            audience=audience,
            visual_style=self.visual_style,
            aspect_ratio=aspect_ratio,
            story_summary=self.logline,
            character_bible=profiles,
            shots=converted_shots,
        )


class Storyboard(BaseModel):
    schema_version: str = "1.0"
    title: str
    logline: str
    audience: str
    visual_style: str
    aspect_ratio: Literal["16:9", "9:16"] = "16:9"
    story_summary: str
    character_bible: list[CharacterProfile]
    shots: list[Shot] = Field(
        min_length=1,
        max_length=60,
        description="Three-second shots, up to 60 shots",
    )

    @model_validator(mode="after")
    def normalize_shot_numbers(self) -> "Storyboard":
        for number, shot in enumerate(self.shots, start=1):
            shot.shot_number = number
        return self

    @property
    def total_duration_seconds(self) -> int:
        return len(self.shots) * 3
