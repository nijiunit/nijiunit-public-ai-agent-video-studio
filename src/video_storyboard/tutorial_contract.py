from __future__ import annotations

import re
from datetime import datetime
from typing import Literal
from urllib.parse import parse_qs, urlparse

from pydantic import BaseModel, ConfigDict, Field, model_validator

YOUTUBE_VIDEO_ID_PATTERN = re.compile(r"^[0-9A-Za-z_-]{11}$")
YOUTUBE_CHANNEL_ID_PATTERN = re.compile(r"^UC[0-9A-Za-z_-]{22}$")
IDENTIFIER_PATTERN = re.compile(r"^[0-9A-Za-z][0-9A-Za-z._-]{0,99}$")
TIMESTAMP_PATTERN = re.compile(r"^(?:\d{1,3}:)?[0-5]\d:[0-5]\d$")


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


def parse_youtube_video_id(url: str) -> str:
    """Return a video ID from a supported public YouTube URL.

    Only HTTPS YouTube watch, Shorts, live, embed, and youtu.be links are
    accepted.  The canonical URL is rebuilt locally so tracking parameters or
    another origin can never become part of a downstream API request.
    """

    parsed = urlparse(url.strip())
    if parsed.scheme.lower() != "https":
        raise ValueError("YouTube URLはhttpsで指定してください")
    if parsed.username or parsed.password or parsed.fragment:
        raise ValueError("YouTube URLに認証情報やフラグメントは指定できません")

    host = (parsed.hostname or "").lower()
    path_parts = [part for part in parsed.path.split("/") if part]
    video_id: str | None = None

    if host == "youtu.be":
        if len(path_parts) == 1:
            video_id = path_parts[0]
    elif host in {"youtube.com", "www.youtube.com", "m.youtube.com"}:
        if parsed.path == "/watch":
            values = parse_qs(parsed.query).get("v", [])
            if len(values) == 1:
                video_id = values[0]
        elif len(path_parts) == 2 and path_parts[0] in {
            "shorts",
            "live",
            "embed",
        }:
            video_id = path_parts[1]
    else:
        raise ValueError("YouTube以外のURLは教材として使用できません")

    if not video_id or not YOUTUBE_VIDEO_ID_PATTERN.fullmatch(video_id):
        raise ValueError("YouTube動画IDを安全に取得できません")
    return video_id


def canonical_youtube_url(video_id: str) -> str:
    if not YOUTUBE_VIDEO_ID_PATTERN.fullmatch(video_id):
        raise ValueError("YouTube動画IDの形式が正しくありません")
    return f"https://www.youtube.com/watch?v={video_id}"


class OfficialChannel(StrictModel):
    channel_id: str
    channel_url: str = Field(min_length=1, max_length=2_000)
    title: str = Field(min_length=1, max_length=200)

    @model_validator(mode="after")
    def validate_channel(self) -> "OfficialChannel":
        if not YOUTUBE_CHANNEL_ID_PATTERN.fullmatch(self.channel_id):
            raise ValueError("official channel_id must be a YouTube channel ID")
        expected = f"https://www.youtube.com/channel/{self.channel_id}"
        if self.channel_url != expected:
            raise ValueError(f"official channel_url must be {expected}")
        return self


class TutorialStep(StrictModel):
    id: str = Field(min_length=1, max_length=100)
    title: str = Field(min_length=1, max_length=500)
    instruction: str = Field(min_length=1, max_length=5_000)
    expected_result: str = Field(min_length=1, max_length=2_000)
    source_timestamp: str | None = None

    @model_validator(mode="after")
    def validate_step(self) -> "TutorialStep":
        if not IDENTIFIER_PATTERN.fullmatch(self.id):
            raise ValueError("tutorial step ID contains unsupported characters")
        if self.source_timestamp and not TIMESTAMP_PATTERN.fullmatch(
            self.source_timestamp
        ):
            raise ValueError("source_timestamp must use HH:MM:SS or MM:SS")
        return self


class OfficialMessage(StrictModel):
    id: str = Field(min_length=1, max_length=100)
    type: Literal[
        "subscription_request",
        "subscriber_milestone_thanks",
        "activity_update",
        "product_announcement",
    ]
    text: str = Field(min_length=1, max_length=2_000)
    published_at: datetime
    valid_until: datetime | None = None
    source_timestamp: str | None = None
    delivery: Literal["after_tutorial"] = "after_tutorial"
    repeat_policy: Literal["once_per_session"] = "once_per_session"
    subscriber_count: int | None = Field(default=None, ge=1)

    @model_validator(mode="after")
    def validate_message(self) -> "OfficialMessage":
        if not IDENTIFIER_PATTERN.fullmatch(self.id):
            raise ValueError("official message ID contains unsupported characters")
        if self.published_at.tzinfo is None:
            raise ValueError("official message published_at requires a time zone")
        if self.valid_until:
            if self.valid_until.tzinfo is None:
                raise ValueError("official message valid_until requires a time zone")
            if self.valid_until <= self.published_at:
                raise ValueError("official message valid_until must be later than published_at")
        if self.source_timestamp and not TIMESTAMP_PATTERN.fullmatch(
            self.source_timestamp
        ):
            raise ValueError("source_timestamp must use HH:MM:SS or MM:SS")
        if self.type == "subscriber_milestone_thanks":
            if self.subscriber_count is None:
                raise ValueError("milestone thanks requires subscriber_count")
        elif self.subscriber_count is not None:
            raise ValueError("subscriber_count is only valid for milestone thanks")
        return self


class CommentObservation(StrictModel):
    comment_id: str = Field(min_length=1, max_length=200)
    published_at: datetime
    text: str = Field(min_length=1, max_length=2_000)
    selected_reason: str = Field(min_length=1, max_length=500)

    @model_validator(mode="after")
    def validate_comment(self) -> "CommentObservation":
        if self.published_at.tzinfo is None:
            raise ValueError("comment published_at requires a time zone")
        return self


class TutorialEntry(StrictModel):
    tutorial_id: str = Field(min_length=1, max_length=100)
    tutorial_version: str = Field(min_length=1, max_length=64)
    video_id: str
    youtube_url: str = Field(min_length=1, max_length=2_000)
    channel_id: str
    title: str = Field(min_length=1, max_length=500)
    published_at: datetime
    status: Literal["active", "retired"] = "active"
    goal: str = Field(min_length=1, max_length=2_000)
    prerequisites: list[str] = Field(default_factory=list, max_length=50)
    required_inputs: list[str] = Field(default_factory=list, max_length=50)
    rights_notes: list[str] = Field(default_factory=list, max_length=50)
    compatible_profile_ids: list[str] = Field(min_length=1, max_length=20)
    steps: list[TutorialStep] = Field(min_length=1, max_length=100)
    official_messages: list[OfficialMessage] = Field(
        default_factory=list,
        max_length=50,
    )
    comments_observed_at: datetime | None = None
    comment_observations: list[CommentObservation] = Field(
        default_factory=list,
        max_length=50,
    )

    @model_validator(mode="after")
    def validate_entry(self) -> "TutorialEntry":
        if not IDENTIFIER_PATTERN.fullmatch(self.tutorial_id):
            raise ValueError("tutorial_id contains unsupported characters")
        if not IDENTIFIER_PATTERN.fullmatch(self.tutorial_version):
            raise ValueError("tutorial_version contains unsupported characters")
        if not YOUTUBE_VIDEO_ID_PATTERN.fullmatch(self.video_id):
            raise ValueError("video_id must be an 11-character YouTube ID")
        if not YOUTUBE_CHANNEL_ID_PATTERN.fullmatch(self.channel_id):
            raise ValueError("channel_id must be a YouTube channel ID")
        if self.youtube_url != canonical_youtube_url(self.video_id):
            raise ValueError("youtube_url must be the canonical URL for video_id")
        if self.published_at.tzinfo is None:
            raise ValueError("tutorial published_at requires a time zone")
        if len(set(self.compatible_profile_ids)) != len(self.compatible_profile_ids):
            raise ValueError("compatible_profile_ids must be unique")

        step_ids = [step.id for step in self.steps]
        if len(set(step_ids)) != len(step_ids):
            raise ValueError("tutorial step IDs must be unique")
        message_ids = [message.id for message in self.official_messages]
        if len(set(message_ids)) != len(message_ids):
            raise ValueError("official message IDs must be unique")
        comment_ids = [comment.comment_id for comment in self.comment_observations]
        if len(set(comment_ids)) != len(comment_ids):
            raise ValueError("comment IDs must be unique")

        if self.comment_observations and self.comments_observed_at is None:
            raise ValueError("comment observations require comments_observed_at")
        if self.comments_observed_at and self.comments_observed_at.tzinfo is None:
            raise ValueError("comments_observed_at requires a time zone")
        return self


class TutorialCatalog(StrictModel):
    schema_version: Literal["1.0"] = "1.0"
    knowledge_version: str = Field(min_length=1, max_length=64)
    language: Literal["ja", "en"]
    official_channel: OfficialChannel
    tutorials: list[TutorialEntry] = Field(default_factory=list, max_length=500)

    @model_validator(mode="after")
    def validate_catalog(self) -> "TutorialCatalog":
        if not IDENTIFIER_PATTERN.fullmatch(self.knowledge_version):
            raise ValueError("knowledge_version contains unsupported characters")
        tutorial_ids = [tutorial.tutorial_id for tutorial in self.tutorials]
        video_ids = [tutorial.video_id for tutorial in self.tutorials]
        if len(set(tutorial_ids)) != len(tutorial_ids):
            raise ValueError("tutorial IDs must be unique")
        if len(set(video_ids)) != len(video_ids):
            raise ValueError("YouTube video IDs must be unique")
        for tutorial in self.tutorials:
            if tutorial.channel_id != self.official_channel.channel_id:
                raise ValueError("tutorial channel_id does not match official channel")
        return self

    def active_tutorial_for_video(self, video_id: str) -> TutorialEntry:
        matches = [
            tutorial
            for tutorial in self.tutorials
            if tutorial.video_id == video_id and tutorial.status == "active"
        ]
        if not matches:
            raise ValueError(
                "この動画はnijiunit公式の利用可能な動画教材として登録されていません"
            )
        return matches[0]


def validate_tutorial_catalog_pair(
    japanese: TutorialCatalog,
    english: TutorialCatalog,
    knowledge_version: str,
) -> None:
    for language, catalog in (("ja", japanese), ("en", english)):
        if catalog.language != language:
            raise RuntimeError(f"tutorial_catalog_{language}の言語が一致しません")
        if catalog.knowledge_version != knowledge_version:
            raise RuntimeError(
                f"tutorial_catalog_{language}の知識バージョンが一致しません"
            )
    if japanese.official_channel != english.official_channel:
        raise RuntimeError("日英の公式YouTubeチャンネル情報が一致しません")

    def contract(catalog: TutorialCatalog) -> dict[str, object]:
        return {
            tutorial.tutorial_id: {
                "tutorial_version": tutorial.tutorial_version,
                "video_id": tutorial.video_id,
                "youtube_url": tutorial.youtube_url,
                "channel_id": tutorial.channel_id,
                "published_at": tutorial.published_at,
                "status": tutorial.status,
                "compatible_profile_ids": tutorial.compatible_profile_ids,
                "steps": [
                    (step.id, step.source_timestamp) for step in tutorial.steps
                ],
                "messages": [
                    (
                        message.id,
                        message.type,
                        message.published_at,
                        message.valid_until,
                        message.source_timestamp,
                        message.delivery,
                        message.repeat_policy,
                        message.subscriber_count,
                    )
                    for message in tutorial.official_messages
                ],
                "comments_observed_at": tutorial.comments_observed_at,
                "comment_ids": [
                    (comment.comment_id, comment.published_at)
                    for comment in tutorial.comment_observations
                ],
            }
            for tutorial in catalog.tutorials
        }

    if contract(japanese) != contract(english):
        raise RuntimeError("日英の動画教材ID、手順、公式メッセージ契約が一致しません")
