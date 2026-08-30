from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, PrivateAttr, model_validator


class Shot(BaseModel):
    shot_number: int = Field(ge=1, description="Sequential number starting at 1")
    duration_seconds: float = Field(
        default=3,
        gt=0,
        le=3,
        description=(
            "Generated shots are exactly three seconds. Source-video shots may "
            "use a shorter final segment so a requested cut point stays exact."
        ),
    )
    production_mode: Literal["generated_video", "source_video"] = Field(
        default="generated_video",
        description="Whether this shot is generated or copied from an input video.",
    )
    source_asset: str | None = Field(
        default=None,
        description="Exact input filename used by a source-video shot.",
    )
    source_start_seconds: float | None = Field(default=None, ge=0)
    source_end_seconds: float | None = Field(default=None, gt=0)
    source_audio: Literal["mute", "preserve"] = "mute"
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

    _timeline_start_seconds: float = PrivateAttr(default=0.0)

    @model_validator(mode="after")
    def validate_production_mode(self) -> "Shot":
        if self.production_mode == "generated_video":
            if abs(self.duration_seconds - 3.0) > 0.001:
                raise ValueError("generated_video shots must be exactly 3 seconds")
            if any(
                value is not None
                for value in (
                    self.source_asset,
                    self.source_start_seconds,
                    self.source_end_seconds,
                )
            ):
                raise ValueError(
                    "generated_video shots must not contain source-video ranges"
                )
            return self

        if not self.source_asset:
            raise ValueError("source_video shots require source_asset")
        if self.source_start_seconds is None or self.source_end_seconds is None:
            raise ValueError(
                "source_video shots require source_start_seconds and source_end_seconds"
            )
        source_duration = self.source_end_seconds - self.source_start_seconds
        if source_duration <= 0:
            raise ValueError("source video end must be later than its start")
        if abs(source_duration - self.duration_seconds) > 0.001:
            raise ValueError(
                "source-video duration must match source_end_seconds - "
                "source_start_seconds"
            )
        return self

    @property
    def start_seconds(self) -> float:
        return self._timeline_start_seconds

    @property
    def end_seconds(self) -> float:
        return self.start_seconds + self.duration_seconds

    def frame_offset_seconds(self, frame_index: int) -> float:
        return frame_index * self.duration_seconds / len(self.frame_descriptions)


class CharacterProfile(BaseModel):
    name: str
    description: str


class ApiShot(BaseModel):
    shot_number: int
    duration_seconds: float = 3
    production_mode: Literal["generated_video", "source_video"] = "generated_video"
    source_asset: str | None = None
    source_start_seconds: float | None = None
    source_end_seconds: float | None = None
    source_audio: Literal["mute", "preserve"] = "mute"
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
                    duration_seconds=source.duration_seconds,
                    production_mode=source.production_mode,
                    source_asset=source.source_asset,
                    source_start_seconds=source.source_start_seconds,
                    source_end_seconds=source.source_end_seconds,
                    source_audio=source.source_audio,
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
        timeline = 0.0
        for number, shot in enumerate(self.shots, start=1):
            shot.shot_number = number
            shot._timeline_start_seconds = timeline
            timeline += shot.duration_seconds
        return self

    @property
    def total_duration_seconds(self) -> float:
        return round(sum(shot.duration_seconds for shot in self.shots), 3)
