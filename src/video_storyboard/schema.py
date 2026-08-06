from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field, model_validator


class Shot(BaseModel):
    shot_number: int = Field(ge=1, description="1から始まる連番")
    duration_seconds: int = Field(
        default=3, ge=3, le=3, description="必ず3秒。1シート分の長さ"
    )
    title: str = Field(description="短い日本語のショット名")
    story_purpose: str = Field(description="物語上の役割")
    scene_description: str = Field(description="画面に見える内容の日本語説明")
    characters: list[str] = Field(description="画面に登場するキャラクター名")
    action: str = Field(description="3秒間に起きる動き")
    emotion: str = Field(description="キャラクターの感情・表情")
    camera: str = Field(description="画角、カメラ位置、カメラ移動")
    lighting: str = Field(description="時刻、光、色、雰囲気")
    dialogue: str = Field(default="", description="セリフ。なければ空文字")
    narration: str = Field(default="", description="ナレーション。なければ空文字")
    sound: str = Field(description="環境音、効果音、音楽")
    continuity: str = Field(description="前後ショットと一致させる要素")
    continuity_start_mode: Literal[
        "storyboard_image",
        "previous_final_frame",
    ] = Field(
        default="storyboard_image",
        description=(
            "通常はstoryboard_image。同一構図を連続させる場合だけ、"
            "前カット最終フレームを開始画像にするprevious_final_frame"
        ),
    )
    reference_assets: list[str] = Field(description="参照するinput内のファイル名")
    main_image_prompt: str = Field(
        description="メイン画像を生成するための詳細な英語プロンプト"
    )
    video_prompt: str = Field(
        description="この3秒の動画生成用の詳細な英語プロンプト"
    )
    frame_descriptions: list[str] = Field(
        min_length=9,
        max_length=9,
        description="0.333秒刻みの9コマ。それぞれ画面に見える変化を日本語で説明",
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

    def to_storyboard(self) -> "Storyboard":
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
                    name=name.strip() if separator else "設定",
                    description=description.strip() if separator else text,
                )
            )
        return Storyboard(
            title=self.title,
            logline=self.logline,
            audience="家族・子どもを含む一般視聴者",
            visual_style=self.visual_style,
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
        description="3秒単位のショット。最長3分（60ショット）まで",
    )

    @model_validator(mode="after")
    def normalize_shot_numbers(self) -> "Storyboard":
        for number, shot in enumerate(self.shots, start=1):
            shot.shot_number = number
        return self

    @property
    def total_duration_seconds(self) -> int:
        return len(self.shots) * 3
