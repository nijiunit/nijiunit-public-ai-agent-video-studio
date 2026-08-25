from __future__ import annotations

import hashlib
import json
import os
import re
import shutil
import tempfile
from dataclasses import dataclass
from datetime import datetime, timedelta
from pathlib import Path
from typing import Callable, Literal
from urllib.parse import urljoin, urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener

from pydantic import BaseModel, ConfigDict, Field, model_validator

from . import __version__
from .tutorial_contract import (
    TutorialCatalog,
    validate_tutorial_catalog_pair,
)

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_CONFIG_PATH = ROOT / "config" / "studio.json"
DEFAULT_STATE_DIR = ROOT / ".nijiunit" / "knowledge"
DEFAULT_BUILTIN_GUIDANCE_DIR = ROOT / "config" / "runtime-guidance"
REQUIRED_RESOURCES = {
    "agent_guide_ja",
    "agent_guide_en",
    "production_profile",
    "notices_ja",
    "notices_en",
}
OPTIONAL_PAIRED_RESOURCES = {
    "tutorial_catalog_ja",
    "tutorial_catalog_en",
}
SUPPORTED_RESOURCES = REQUIRED_RESOURCES | OPTIONAL_PAIRED_RESOURCES
VERSION_PATTERN = re.compile(r"^[0-9A-Za-z][0-9A-Za-z._-]{0,63}$")
SHA256_PATTERN = re.compile(r"^[0-9a-f]{64}$")


class StrictModel(BaseModel):
    model_config = ConfigDict(extra="forbid", str_strip_whitespace=True)


class StudioConfig(StrictModel):
    schema_version: Literal["1.0"] = "1.0"
    knowledge_manifest_url: str
    allowed_origins: list[str] = Field(min_length=1, max_length=20)
    check_interval_hours: int = Field(default=24, ge=1, le=168)
    request_timeout_seconds: int = Field(default=15, ge=1, le=60)
    maximum_resource_bytes: int = Field(
        default=1_048_576,
        ge=1_024,
        le=10_485_760,
    )


class Compatibility(StrictModel):
    minimum_studio_version: str
    maximum_studio_version_exclusive: str


class ResourceDescriptor(StrictModel):
    url: str = Field(min_length=1, max_length=2_000)
    sha256: str
    media_type: Literal["application/json", "text/markdown"]

    @model_validator(mode="after")
    def validate_sha256(self) -> "ResourceDescriptor":
        self.sha256 = self.sha256.lower()
        if not SHA256_PATTERN.fullmatch(self.sha256):
            raise ValueError("sha256 must contain exactly 64 hexadecimal characters")
        return self


class KnowledgeManifest(StrictModel):
    schema_version: Literal["1.0"] = "1.0"
    knowledge_version: str
    published_at: datetime
    valid_until: datetime | None = None
    compatibility: Compatibility
    resources: dict[str, ResourceDescriptor]

    @model_validator(mode="after")
    def validate_contract(self) -> "KnowledgeManifest":
        if not VERSION_PATTERN.fullmatch(self.knowledge_version):
            raise ValueError("knowledge_version contains unsupported characters")
        missing = sorted(REQUIRED_RESOURCES - set(self.resources))
        if missing:
            raise ValueError("manifest is missing resources: " + ", ".join(missing))
        unexpected = sorted(set(self.resources) - SUPPORTED_RESOURCES)
        if unexpected:
            raise ValueError(
                "this studio version does not support resources: "
                + ", ".join(unexpected)
            )
        tutorial_resources = set(self.resources) & OPTIONAL_PAIRED_RESOURCES
        if tutorial_resources and tutorial_resources != OPTIONAL_PAIRED_RESOURCES:
            missing_tutorials = sorted(
                OPTIONAL_PAIRED_RESOURCES - tutorial_resources
            )
            raise ValueError(
                "manifest must provide both tutorial catalogs: "
                + ", ".join(missing_tutorials)
            )
        expected_media_types = {
            "agent_guide_ja": "text/markdown",
            "agent_guide_en": "text/markdown",
            "production_profile": "application/json",
            "notices_ja": "application/json",
            "notices_en": "application/json",
            "tutorial_catalog_ja": "application/json",
            "tutorial_catalog_en": "application/json",
        }
        for resource_id, descriptor in self.resources.items():
            expected = expected_media_types[resource_id]
            if descriptor.media_type != expected:
                raise ValueError(
                    f"{resource_id} media_type must be {expected}"
                )
        if self.published_at.tzinfo is None:
            raise ValueError("published_at must include a time-zone offset")
        if self.valid_until and self.valid_until.tzinfo is None:
            raise ValueError("valid_until must include a time-zone offset")
        if self.valid_until and self.valid_until <= self.published_at:
            raise ValueError("valid_until must be later than published_at")
        return self


class ModelSelection(StrictModel):
    story: str = Field(min_length=1, max_length=200)
    image: str = Field(min_length=1, max_length=200)
    video: str = Field(min_length=1, max_length=200)
    tts: str = Field(min_length=1, max_length=200)
    asr: str = Field(min_length=1, max_length=200)
    tutorial: str | None = Field(default=None, min_length=1, max_length=200)


class StoryInstructions(StrictModel):
    system_instruction: str = Field(min_length=1, max_length=20_000)
    requirements: list[str] = Field(default_factory=list, max_length=100)
    target_duration_seconds_min: int = Field(ge=3, le=180)
    target_duration_seconds_max: int = Field(ge=3, le=180)
    shot_count_min: int = Field(ge=1, le=60)
    shot_count_max: int = Field(ge=1, le=60)
    audience: str = Field(min_length=1, max_length=500)
    prompt_language_instruction: str = Field(min_length=1, max_length=1_000)
    output_language_instruction: str = Field(min_length=1, max_length=1_000)
    # Newer provider models may reject legacy sampling parameters.  Keep this
    # optional so the website can explicitly omit it without inventing a local
    # replacement value.
    temperature: float | None = Field(default=None, ge=0, le=2)
    max_output_tokens: int = Field(default=32768, ge=1024, le=65536)

    @model_validator(mode="after")
    def validate_ranges(self) -> "StoryInstructions":
        if self.target_duration_seconds_min > self.target_duration_seconds_max:
            raise ValueError("minimum target duration exceeds maximum")
        if self.shot_count_min > self.shot_count_max:
            raise ValueError("minimum shot count exceeds maximum")
        return self


class ImageInstructions(StrictModel):
    requirements: list[str] = Field(default_factory=list, max_length=100)
    reference_limit: int = Field(default=4, ge=1, le=8)
    image_size: Literal["1K", "2K", "4K"] = "1K"


class VideoInstructions(StrictModel):
    api_family: Literal["interactions", "veo"]
    requirements: list[str] = Field(default_factory=list, max_length=100)
    reference_instructions: list[str] = Field(default_factory=list, max_length=100)
    negative_prompt_terms: list[str] = Field(default_factory=list, max_length=100)
    maximum_character_reference_images: int = Field(ge=0, le=6)
    supports_asset_reference_images: bool
    supports_negative_prompt: bool
    provider_duration_seconds: int = Field(ge=3, le=8)
    provider_duration_seconds_with_references: int = Field(ge=3, le=8)
    provider_resolution: str = Field(min_length=1, max_length=50)

    @model_validator(mode="after")
    def validate_adapter_contract(self) -> "VideoInstructions":
        if self.api_family == "interactions":
            if self.supports_asset_reference_images:
                raise ValueError(
                    "interactions uses inline identity images, not Veo asset references"
                )
            if self.supports_negative_prompt:
                raise ValueError("interactions does not use a separate negative prompt")
            if self.provider_duration_seconds != 3:
                raise ValueError(
                    "this studio version requires a three-second interactions request"
                )
        if (
            self.supports_asset_reference_images
            and self.maximum_character_reference_images == 0
        ):
            raise ValueError("asset references require a positive reference limit")
        if not self.supports_asset_reference_images and (
            self.provider_duration_seconds_with_references
            != self.provider_duration_seconds
        ):
            raise ValueError(
                "reference duration must equal normal duration when asset references are disabled"
            )
        return self


class AmbienceInstructions(StrictModel):
    highpass_hz: int = Field(ge=20, le=20_000)
    lowpass_hz: int = Field(ge=20, le=20_000)
    volume: float = Field(ge=0, le=1)

    @model_validator(mode="after")
    def validate_filters(self) -> "AmbienceInstructions":
        if self.highpass_hz >= self.lowpass_hz:
            raise ValueError("ambience highpass_hz must be lower than lowpass_hz")
        return self


class SubtitleInstructions(StrictModel):
    font_name: str = Field(min_length=1, max_length=200)
    font_size: int = Field(ge=8, le=200)
    primary_colour: str = Field(pattern=r"^&H[0-9A-Fa-f]{8}$")
    outline_colour: str = Field(pattern=r"^&H[0-9A-Fa-f]{8}$")
    back_colour: str = Field(pattern=r"^&H[0-9A-Fa-f]{8}$")
    bold: bool
    border_style: Literal[1, 3]
    outline: int = Field(ge=0, le=20)
    shadow: int = Field(ge=0, le=20)
    alignment: int = Field(ge=1, le=9)
    margin_horizontal: int = Field(ge=0, le=1000)
    margin_vertical: int = Field(ge=0, le=1000)
    start_seconds: float = Field(ge=0, lt=3)
    end_padding_seconds: float = Field(ge=0, lt=3)
    fade_in_milliseconds: int = Field(ge=0, le=2000)
    fade_out_milliseconds: int = Field(ge=0, le=2000)

    @model_validator(mode="after")
    def validate_font_name(self) -> "SubtitleInstructions":
        if any(character in self.font_name for character in ",\r\n"):
            raise ValueError("subtitle font_name must not contain commas or newlines")
        return self


class AudioInstructions(StrictModel):
    default_voice: str = Field(min_length=1, max_length=200)
    default_speaker: str = Field(min_length=1, max_length=500)
    default_style: str = Field(min_length=1, max_length=2_000)
    tts_language_instruction: str = Field(min_length=1, max_length=1_000)
    transcription_instruction: str = Field(min_length=1, max_length=2_000)
    maximum_speech_seconds: float = Field(gt=0, le=30)
    maximum_tempo_factor: float = Field(ge=1, le=2)
    default_ambience: AmbienceInstructions
    subtitle: SubtitleInstructions


class MediaContract(StrictModel):
    shot_duration_seconds: Literal[3] = 3
    aspect_ratio: Literal["16:9", "9:16"] = "16:9"
    width: int = Field(ge=360, le=4320)
    height: int = Field(ge=360, le=4320)
    frames_per_second: Literal[24] = 24
    review_frames_per_second: Literal[3] = 3

    @model_validator(mode="after")
    def validate_dimensions(self) -> "MediaContract":
        expected = 16 / 9 if self.aspect_ratio == "16:9" else 9 / 16
        if abs((self.width / self.height) - expected) > 0.01:
            raise ValueError("width and height do not match aspect_ratio")
        if self.width % 2 or self.height % 2:
            raise ValueError("width and height must be even for H.264 output")
        return self

    @property
    def review_frame_count(self) -> int:
        return self.shot_duration_seconds * self.review_frames_per_second


class ProductionProfile(StrictModel):
    schema_version: Literal["1.0"] = "1.0"
    knowledge_version: str
    profile_id: str = Field(min_length=1, max_length=200)
    models: ModelSelection
    media: MediaContract
    story: StoryInstructions
    image: ImageInstructions
    video: VideoInstructions
    audio: AudioInstructions

    @model_validator(mode="after")
    def validate_engine_contract(self) -> "ProductionProfile":
        if not VERSION_PATTERN.fullmatch(self.knowledge_version):
            raise ValueError("knowledge_version contains unsupported characters")
        if self.media.review_frame_count != 9:
            raise ValueError("this studio version requires exactly 9 review frames")
        shortest = self.story.shot_count_min * self.media.shot_duration_seconds
        longest = self.story.shot_count_max * self.media.shot_duration_seconds
        if (
            longest < self.story.target_duration_seconds_min
            or shortest > self.story.target_duration_seconds_max
        ):
            raise ValueError("story duration and shot-count ranges do not overlap")
        if self.audio.maximum_speech_seconds > self.media.shot_duration_seconds:
            raise ValueError("maximum speech duration exceeds the shot duration")
        subtitle = self.audio.subtitle
        if (
            subtitle.start_seconds + subtitle.end_padding_seconds
            >= self.media.shot_duration_seconds
        ):
            raise ValueError("subtitle display interval must be positive")
        return self

    def for_aspect_ratio(
        self,
        aspect_ratio: Literal["16:9", "9:16"] | None,
    ) -> "ProductionProfile":
        """Resolve one production orientation without changing remote files.

        The website profile defines the output resolution's long and short
        edges and its default orientation.  This engine supports both YouTube
        orientations by swapping those edges when the user selects the other
        ratio.  The resolved choice is pinned in the production lock.
        """
        if aspect_ratio is None or aspect_ratio == self.media.aspect_ratio:
            return self
        selected_media = self.media.model_copy(
            update={
                "aspect_ratio": aspect_ratio,
                "width": self.media.height,
                "height": self.media.width,
            }
        )
        selected_media = MediaContract.model_validate(selected_media.model_dump())
        return self.model_copy(update={"media": selected_media})


class Notice(StrictModel):
    id: str = Field(min_length=1, max_length=200)
    published_at: datetime
    severity: Literal["info", "important", "critical"]
    title: str = Field(min_length=1, max_length=500)
    message: str = Field(min_length=1, max_length=5_000)
    url: str | None = Field(default=None, max_length=2_000)
    valid_until: datetime | None = None

    @model_validator(mode="after")
    def validate_timestamp(self) -> "Notice":
        if self.published_at.tzinfo is None:
            raise ValueError("notice published_at must include a time-zone offset")
        if self.valid_until and self.valid_until.tzinfo is None:
            raise ValueError("notice valid_until must include a time-zone offset")
        if self.valid_until and self.valid_until <= self.published_at:
            raise ValueError("notice valid_until must be after published_at")
        return self


class NoticeFeed(StrictModel):
    schema_version: Literal["1.0"] = "1.0"
    knowledge_version: str
    notices: list[Notice] = Field(default_factory=list, max_length=100)

    @model_validator(mode="after")
    def validate_contract(self) -> "NoticeFeed":
        if not VERSION_PATTERN.fullmatch(self.knowledge_version):
            raise ValueError("knowledge_version contains unsupported characters")
        identifiers = [notice.id for notice in self.notices]
        if len(set(identifiers)) != len(identifiers):
            raise ValueError("notice IDs must be unique within a feed")
        return self


class NoticeReceipt(StrictModel):
    status: Literal["shown", "snoozed", "dismissed"]
    updated_at: datetime
    snoozed_until: datetime | None = None

    @model_validator(mode="after")
    def validate_contract(self) -> "NoticeReceipt":
        if self.updated_at.tzinfo is None:
            raise ValueError("notice receipt updated_at must include a time-zone offset")
        if self.snoozed_until and self.snoozed_until.tzinfo is None:
            raise ValueError("notice receipt snoozed_until must include a time-zone offset")
        if self.status == "snoozed" and self.snoozed_until is None:
            raise ValueError("snoozed notice receipt requires snoozed_until")
        if self.status != "snoozed" and self.snoozed_until is not None:
            raise ValueError("only a snoozed notice receipt may have snoozed_until")
        return self


class GuidanceState(StrictModel):
    schema_version: Literal["1.0"] = "1.0"
    manifest_url: str | None = None
    active_knowledge_version: str | None = None
    active_manifest_sha256: str | None = Field(default=None, pattern=r"^[0-9a-f]{64}$")
    last_attempt: datetime | None = None
    last_success: datetime | None = None
    last_error: str | None = None
    notice_receipts: dict[str, NoticeReceipt] = Field(default_factory=dict)

    @model_validator(mode="after")
    def validate_timestamps(self) -> "GuidanceState":
        for name in ("last_attempt", "last_success"):
            value = getattr(self, name)
            if value and value.tzinfo is None:
                raise ValueError(f"{name} must include a time-zone offset")
        for notice_id in self.notice_receipts:
            if not notice_id or len(notice_id) > 200:
                raise ValueError("notice receipt ID is invalid")
        return self


@dataclass(frozen=True)
class GuidanceBundle:
    manifest: KnowledgeManifest
    profile: ProductionProfile
    cache_dir: Path
    resource_paths: dict[str, Path]
    used_cached_copy: bool = False
    warning: str | None = None

    def for_aspect_ratio(
        self,
        aspect_ratio: Literal["16:9", "9:16"] | None,
    ) -> "GuidanceBundle":
        return GuidanceBundle(
            manifest=self.manifest,
            profile=self.profile.for_aspect_ratio(aspect_ratio),
            cache_dir=self.cache_dir,
            resource_paths=self.resource_paths,
            used_cached_copy=self.used_cached_copy,
            warning=self.warning,
        )

    def guide_path(self, language: str) -> Path:
        if language not in {"ja", "en"}:
            raise ValueError("language must be 'ja' or 'en'")
        return self.resource_paths[f"agent_guide_{language}"]

    def notices(self, language: str) -> NoticeFeed:
        if language not in {"ja", "en"}:
            raise ValueError("language must be 'ja' or 'en'")
        path = self.resource_paths[f"notices_{language}"]
        return NoticeFeed.model_validate_json(path.read_text(encoding="utf-8"))

    def tutorial_catalog(self, language: str) -> TutorialCatalog:
        if language not in {"ja", "en"}:
            raise ValueError("language must be 'ja' or 'en'")
        resource_id = f"tutorial_catalog_{language}"
        path = self.resource_paths.get(resource_id)
        if path is None:
            raise FileNotFoundError(
                "現在のホームページ指示には動画教材カタログがありません"
            )
        return TutorialCatalog.model_validate_json(path.read_text(encoding="utf-8"))


Fetcher = Callable[[str, int, int], bytes]


def load_studio_config(path: Path = DEFAULT_CONFIG_PATH) -> StudioConfig:
    raw = json.loads(path.read_text(encoding="utf-8"))
    override = os.getenv("NIJIUNIT_KNOWLEDGE_MANIFEST_URL", "").strip()
    if override:
        raw["knowledge_manifest_url"] = override
    return StudioConfig.model_validate(raw)


def _origin(url: str) -> str:
    parsed = urlparse(url)
    if not parsed.scheme or not parsed.hostname:
        raise ValueError(f"absolute URL required: {url}")
    host = parsed.hostname.lower()
    port = f":{parsed.port}" if parsed.port else ""
    return f"{parsed.scheme.lower()}://{host}{port}"


def _is_localhost(url: str) -> bool:
    return (urlparse(url).hostname or "").lower() in {
        "localhost",
        "127.0.0.1",
        "::1",
    }


def _allowed_origins(config: StudioConfig) -> set[str]:
    values = {_origin(value) for value in config.allowed_origins}
    manifest_origin = _origin(config.knowledge_manifest_url)
    if _is_localhost(config.knowledge_manifest_url) and os.getenv(
        "NIJIUNIT_KNOWLEDGE_ALLOW_HTTP_LOCALHOST", ""
    ) == "1":
        values.add(manifest_origin)
    return values


def _validate_remote_url(url: str, config: StudioConfig) -> None:
    parsed = urlparse(url)
    allow_local_http = (
        parsed.scheme.lower() == "http"
        and _is_localhost(url)
        and os.getenv("NIJIUNIT_KNOWLEDGE_ALLOW_HTTP_LOCALHOST", "") == "1"
    )
    if parsed.scheme.lower() != "https" and not allow_local_http:
        raise ValueError("knowledge URLs must use HTTPS; localhost requires explicit opt-in")
    if _origin(url) not in _allowed_origins(config):
        raise ValueError(f"knowledge URL origin is not allowed: {_origin(url)}")
    if parsed.username or parsed.password:
        raise ValueError("knowledge URLs must not contain credentials")


def _download(url: str, timeout_seconds: int, maximum_bytes: int) -> bytes:
    class NoRedirect(HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            return None

    request = Request(
        url,
        headers={
            "Accept": "application/json, text/markdown;q=0.9",
            "User-Agent": f"nijiunit-ai-agent-video-studio/{__version__}",
        },
    )
    opener = build_opener(NoRedirect())
    with opener.open(request, timeout=timeout_seconds) as response:
        data = response.read(maximum_bytes + 1)
    if len(data) > maximum_bytes:
        raise ValueError(f"remote knowledge resource exceeds {maximum_bytes} bytes")
    return data


def _version_tuple(value: str) -> tuple[int, int, int]:
    parts = value.split(".")
    if len(parts) != 3 or any(not part.isdigit() for part in parts):
        raise ValueError(f"semantic version required: {value}")
    return tuple(int(part) for part in parts)  # type: ignore[return-value]


def _validate_compatibility(manifest: KnowledgeManifest) -> None:
    current = _version_tuple(__version__)
    minimum = _version_tuple(manifest.compatibility.minimum_studio_version)
    maximum = _version_tuple(
        manifest.compatibility.maximum_studio_version_exclusive
    )
    if current < minimum or current >= maximum:
        raise RuntimeError(
            "ホームページの指示とこのツールの版に互換性がありません。"
            f" studio={__version__}, supported=>={minimum} and <{maximum}"
        )


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _atomic_write(path: Path, data: bytes) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_name(f".{path.name}.tmp")
    temporary.write_bytes(data)
    os.replace(temporary, path)


def _state_path(state_dir: Path) -> Path:
    return state_dir / "state.json"


def _load_state(state_dir: Path) -> GuidanceState:
    path = _state_path(state_dir)
    if not path.is_file():
        return GuidanceState()
    try:
        return GuidanceState.model_validate_json(path.read_text(encoding="utf-8"))
    except Exception as error:
        raise RuntimeError(f"ローカルの指示状態ファイルが壊れています: {path}") from error


def _save_state(state_dir: Path, state: GuidanceState) -> None:
    _atomic_write(
        _state_path(state_dir),
        (state.model_dump_json(indent=2) + "\n").encode("utf-8"),
    )


def _resource_path(cache_dir: Path, resource_id: str) -> Path:
    suffix = (
        ".json"
        if resource_id == "production_profile"
        or resource_id.startswith("notices_")
        or resource_id.startswith("tutorial_catalog_")
        else ".md"
    )
    return cache_dir / f"{resource_id}{suffix}"


def _manifest_is_expired(manifest: KnowledgeManifest, now: datetime) -> bool:
    return bool(manifest.valid_until and now > manifest.valid_until)


def _validate_notice_pair(
    japanese: NoticeFeed,
    english: NoticeFeed,
    knowledge_version: str,
) -> None:
    for language, feed in (("ja", japanese), ("en", english)):
        if feed.knowledge_version != knowledge_version:
            raise RuntimeError(
                f"notices_{language}の知識バージョンが一致しません"
            )
    japanese_contract = {
        notice.id: (notice.published_at, notice.severity, notice.valid_until)
        for notice in japanese.notices
    }
    english_contract = {
        notice.id: (notice.published_at, notice.severity, notice.valid_until)
        for notice in english.notices
    }
    if japanese_contract != english_contract:
        raise RuntimeError("日英のお知らせID、日時、重要度、有効期限が一致しません")


def pending_notices(
    feed: NoticeFeed,
    *,
    state_dir: Path = DEFAULT_STATE_DIR,
    now: datetime | None = None,
) -> list[Notice]:
    """Return notices the AI should tell the user now.

    Critical notices are always returned while present in the verified feed.
    Other notices are shown once, unless the user explicitly postpones them.
    """
    current_time = now or datetime.now().astimezone()
    state = _load_state(state_dir)
    result: list[Notice] = []
    for notice in feed.notices:
        if notice.valid_until and current_time > notice.valid_until:
            continue
        if notice.severity == "critical":
            result.append(notice)
            continue
        receipt = state.notice_receipts.get(notice.id)
        if receipt is None:
            result.append(notice)
        elif receipt.status == "snoozed" and receipt.snoozed_until and current_time >= receipt.snoozed_until:
            result.append(notice)
    return result


def record_notices_shown(
    notices: list[Notice],
    *,
    state_dir: Path = DEFAULT_STATE_DIR,
    now: datetime | None = None,
) -> None:
    current_time = now or datetime.now().astimezone()
    state = _load_state(state_dir)
    changed = False
    for notice in notices:
        if notice.severity == "critical":
            continue
        state.notice_receipts[notice.id] = NoticeReceipt(
            status="shown",
            updated_at=current_time,
        )
        changed = True
    if changed:
        _save_state(state_dir, state)


def set_notice_preference(
    notice: Notice,
    action: Literal["later", "dismiss"],
    *,
    state_dir: Path = DEFAULT_STATE_DIR,
    hours: int = 24,
    now: datetime | None = None,
) -> NoticeReceipt:
    if notice.severity == "critical":
        raise ValueError("重大なお知らせは後回し・非表示にできません")
    current_time = now or datetime.now().astimezone()
    if action == "later":
        if hours < 1 or hours > 24 * 30:
            raise ValueError("後で知らせる時間は1時間以上720時間以下で指定してください")
        receipt = NoticeReceipt(
            status="snoozed",
            updated_at=current_time,
            snoozed_until=current_time + timedelta(hours=hours),
        )
    else:
        receipt = NoticeReceipt(status="dismissed", updated_at=current_time)
    state = _load_state(state_dir)
    state.notice_receipts[notice.id] = receipt
    _save_state(state_dir, state)
    return receipt


def _validate_tutorial_catalogs(
    resource_bytes: dict[str, bytes],
    knowledge_version: str,
) -> None:
    present = OPTIONAL_PAIRED_RESOURCES & set(resource_bytes)
    if not present:
        return
    japanese = TutorialCatalog.model_validate_json(
        resource_bytes["tutorial_catalog_ja"]
    )
    english = TutorialCatalog.model_validate_json(
        resource_bytes["tutorial_catalog_en"]
    )
    validate_tutorial_catalog_pair(japanese, english, knowledge_version)


def ensure_production_allowed(
    bundle: GuidanceBundle,
    language: str = "ja",
) -> None:
    critical = [
        notice
        for notice in bundle.notices(language).notices
        if notice.severity == "critical"
    ]
    if critical:
        details = "\n".join(
            f"- {notice.title}: {notice.message}" for notice in critical
        )
        raise RuntimeError(
            "ホームページに制作停止が必要な重大なお知らせがあります。"
            "内容を確認し、解決済みの新しい指示版が出るまで生成処理を開始できません。\n"
            + details
        )


def _load_bundle_from_cache(
    state_dir: Path,
    version: str,
    *,
    used_cached_copy: bool = False,
    warning: str | None = None,
) -> GuidanceBundle:
    cache_dir = state_dir / "cache" / version
    return _load_bundle_from_directory(
        cache_dir,
        used_cached_copy=used_cached_copy,
        warning=warning,
    )


def _load_bundle_from_directory(
    cache_dir: Path,
    *,
    used_cached_copy: bool = False,
    warning: str | None = None,
) -> GuidanceBundle:
    manifest_path = cache_dir / "manifest.json"
    if not manifest_path.is_file():
        raise FileNotFoundError(f"検証済み指示キャッシュがありません: {manifest_path}")
    manifest = KnowledgeManifest.model_validate_json(
        manifest_path.read_text(encoding="utf-8")
    )
    _validate_compatibility(manifest)
    paths: dict[str, Path] = {}
    for resource_id, descriptor in manifest.resources.items():
        path = _resource_path(cache_dir, resource_id)
        if not path.is_file():
            raise FileNotFoundError(f"指示キャッシュの構成ファイルがありません: {path}")
        if _sha256(path.read_bytes()) != descriptor.sha256:
            raise RuntimeError(f"指示キャッシュのハッシュが一致しません: {path}")
        paths[resource_id] = path
    profile = ProductionProfile.model_validate_json(
        paths["production_profile"].read_text(encoding="utf-8")
    )
    if profile.knowledge_version != manifest.knowledge_version:
        raise RuntimeError("production_profileの知識バージョンが一致しません")
    japanese = NoticeFeed.model_validate_json(
        paths["notices_ja"].read_text(encoding="utf-8")
    )
    english = NoticeFeed.model_validate_json(
        paths["notices_en"].read_text(encoding="utf-8")
    )
    _validate_notice_pair(japanese, english, manifest.knowledge_version)
    _validate_tutorial_catalogs(
        {
            resource_id: path.read_bytes()
            for resource_id, path in paths.items()
            if resource_id in OPTIONAL_PAIRED_RESOURCES
        },
        manifest.knowledge_version,
    )
    return GuidanceBundle(
        manifest=manifest,
        profile=profile,
        cache_dir=cache_dir,
        resource_paths=paths,
        used_cached_copy=used_cached_copy,
        warning=warning,
    )


def load_builtin_guidance(
    guidance_dir: Path = DEFAULT_BUILTIN_GUIDANCE_DIR,
) -> GuidanceBundle:
    """Load the versioned production defaults shipped with this application.

    Current productions must not depend on a website cache.  The website owns
    video-specific lessons, while this package owns stable runtime defaults and
    safety gates.  Existing run snapshots and the former remote package reader
    remain supported so old productions stay auditable.
    """
    try:
        return _load_bundle_from_directory(guidance_dir.resolve())
    except Exception as error:
        raise RuntimeError(
            "同梱された制作基本設定を検証できません。リポジトリを更新または"
            f"再インストールしてください: {guidance_dir}"
        ) from error


def load_active_guidance(
    state_dir: Path = DEFAULT_STATE_DIR,
) -> GuidanceBundle:
    state = _load_state(state_dir)
    if not state.active_knowledge_version:
        raise FileNotFoundError("ホームページの指示をまだ取得していません")
    bundle = _load_bundle_from_cache(state_dir, state.active_knowledge_version)
    if _manifest_is_expired(bundle.manifest, datetime.now().astimezone()):
        raise RuntimeError("検証済みホームページ指示の有効期限が切れています")
    return bundle


def _cache_is_fresh(state: GuidanceState, config: StudioConfig, now: datetime) -> bool:
    if not state.active_knowledge_version or not state.last_success:
        return False
    last_success = state.last_success.astimezone(now.tzinfo)
    if now.date() != last_success.date():
        return False
    elapsed = now - last_success
    return elapsed.total_seconds() < config.check_interval_hours * 3600


def sync_guidance(
    *,
    config_path: Path = DEFAULT_CONFIG_PATH,
    state_dir: Path = DEFAULT_STATE_DIR,
    force: bool = False,
    fetcher: Fetcher = _download,
    now: datetime | None = None,
) -> GuidanceBundle:
    config = load_studio_config(config_path)
    _validate_remote_url(config.knowledge_manifest_url, config)
    current_time = now or datetime.now().astimezone()
    state = _load_state(state_dir)
    if not force and _cache_is_fresh(state, config, current_time):
        cached = _load_bundle_from_cache(
            state_dir,
            state.active_knowledge_version or "",
            used_cached_copy=True,
        )
        if not _manifest_is_expired(cached.manifest, current_time):
            return cached

    state.manifest_url = config.knowledge_manifest_url
    state.last_attempt = current_time
    try:
        manifest_bytes = fetcher(
            config.knowledge_manifest_url,
            config.request_timeout_seconds,
            config.maximum_resource_bytes,
        )
        manifest = KnowledgeManifest.model_validate_json(manifest_bytes)
        _validate_compatibility(manifest)
        if _manifest_is_expired(manifest, current_time):
            raise RuntimeError("ホームページから取得した指示の有効期限が切れています")
        manifest_digest = _sha256(manifest_bytes)
        if (
            not force
            and state.active_knowledge_version == manifest.knowledge_version
        ):
            if (
                state.active_manifest_sha256
                and state.active_manifest_sha256 != manifest_digest
            ):
                raise RuntimeError(
                    "同じknowledge_versionのmanifestが変更されています。"
                    "新しいバージョン番号で公開してください。"
                )
            try:
                cached = _load_bundle_from_cache(
                    state_dir,
                    manifest.knowledge_version,
                    used_cached_copy=True,
                )
            except (FileNotFoundError, RuntimeError, ValueError):
                pass
            else:
                if (cached.cache_dir / "manifest.json").read_bytes() != manifest_bytes:
                    raise RuntimeError(
                        "同じknowledge_versionのmanifestが変更されています。"
                        "新しいバージョン番号で公開してください。"
                    )
                state.active_manifest_sha256 = manifest_digest
                state.last_success = current_time
                state.last_error = None
                _save_state(state_dir, state)
                return cached
        resource_bytes: dict[str, bytes] = {}
        for resource_id, descriptor in manifest.resources.items():
            resource_url = urljoin(config.knowledge_manifest_url, descriptor.url)
            _validate_remote_url(resource_url, config)
            data = fetcher(
                resource_url,
                config.request_timeout_seconds,
                config.maximum_resource_bytes,
            )
            if _sha256(data) != descriptor.sha256:
                raise RuntimeError(
                    f"ホームページ指示のハッシュが一致しません: {resource_id}"
                )
            resource_bytes[resource_id] = data

        profile = ProductionProfile.model_validate_json(
            resource_bytes["production_profile"]
        )
        if profile.knowledge_version != manifest.knowledge_version:
            raise RuntimeError("production_profileの知識バージョンが一致しません")
        feeds = {
            language: NoticeFeed.model_validate_json(
                resource_bytes[f"notices_{language}"]
            )
            for language in ("ja", "en")
        }
        _validate_notice_pair(feeds["ja"], feeds["en"], manifest.knowledge_version)
        _validate_tutorial_catalogs(resource_bytes, manifest.knowledge_version)
        for feed in feeds.values():
            for notice in feed.notices:
                if notice.url:
                    _validate_remote_url(notice.url, config)

        final_dir = state_dir / "cache" / manifest.knowledge_version
        if final_dir.exists():
            existing = (final_dir / "manifest.json").read_bytes()
            if existing != manifest_bytes:
                if state.active_manifest_sha256 == manifest_digest:
                    _atomic_write(final_dir / "manifest.json", manifest_bytes)
                else:
                    raise RuntimeError(
                        "同じknowledge_versionの内容が変更されています。"
                        "新しいバージョン番号で公開してください。"
                    )
            for resource_id, data in resource_bytes.items():
                _atomic_write(_resource_path(final_dir, resource_id), data)
        else:
            final_dir.parent.mkdir(parents=True, exist_ok=True)
            with tempfile.TemporaryDirectory(
                prefix="guidance-",
                dir=final_dir.parent,
            ) as temporary_name:
                temporary = Path(temporary_name)
                (temporary / "manifest.json").write_bytes(manifest_bytes)
                for resource_id, data in resource_bytes.items():
                    _resource_path(temporary, resource_id).write_bytes(data)
                temporary.replace(final_dir)

        state.active_knowledge_version = manifest.knowledge_version
        state.active_manifest_sha256 = manifest_digest
        state.last_success = current_time
        state.last_error = None
        _save_state(state_dir, state)
        return _load_bundle_from_cache(state_dir, manifest.knowledge_version)
    except Exception as error:
        state.last_error = str(error)
        _save_state(state_dir, state)
        if state.active_knowledge_version:
            cached = _load_bundle_from_cache(
                state_dir,
                state.active_knowledge_version,
                used_cached_copy=True,
                warning=(
                    "ホームページの最新版を確認できなかったため、最後に検証できた"
                    f"指示を使用します: {error}"
                ),
            )
            if _manifest_is_expired(cached.manifest, current_time):
                raise RuntimeError(
                    "検証済み指示の有効期限が切れ、ホームページも確認できません。"
                ) from error
            return cached
        raise RuntimeError(
            "ホームページから制作指示を取得できません。初回取得が成功するまで"
            "動画制作は開始できません。"
        ) from error


def snapshot_guidance(bundle: GuidanceBundle, run_dir: Path) -> Path:
    destination = run_dir / "guidance"
    if destination.exists():
        lock = load_run_guidance(run_dir)
        if lock.manifest.knowledge_version != bundle.manifest.knowledge_version:
            raise RuntimeError(
                "この制作には別の知識バージョンが既に固定されています: "
                f"{lock.manifest.knowledge_version}"
            )
        if lock.profile.media != bundle.profile.media:
            raise RuntimeError(
                "この制作には別の映像比率が既に固定されています: "
                f"{lock.profile.media.aspect_ratio}"
            )
        return destination
    destination.mkdir(parents=True)
    shutil.copy2(bundle.cache_dir / "manifest.json", destination / "manifest.json")
    for resource_id, source in bundle.resource_paths.items():
        shutil.copy2(source, _resource_path(destination, resource_id))
    lock_data = {
        "schema_version": "1.0",
        "knowledge_version": bundle.manifest.knowledge_version,
        "studio_version": __version__,
        "manifest_sha256": _sha256(
            (bundle.cache_dir / "manifest.json").read_bytes()
        ),
        "selected_media": bundle.profile.media.model_dump(mode="json"),
        "resources": {
            resource_id: descriptor.sha256
            for resource_id, descriptor in bundle.manifest.resources.items()
        },
    }
    (destination / "guidance-lock.json").write_text(
        json.dumps(lock_data, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    return destination


def load_run_guidance(run_dir: Path) -> GuidanceBundle:
    guidance_dir = run_dir / "guidance"
    manifest_path = guidance_dir / "manifest.json"
    lock_path = guidance_dir / "guidance-lock.json"
    if not manifest_path.is_file() or not lock_path.is_file():
        raise FileNotFoundError(
            "この制作にはホームページ指示の確定記録がありません: "
            f"{guidance_dir}"
        )
    lock = json.loads(lock_path.read_text(encoding="utf-8"))
    if lock.get("schema_version") != "1.0":
        raise RuntimeError("guidance-lock.jsonのスキーマ版に対応していません")
    manifest = KnowledgeManifest.model_validate_json(
        manifest_path.read_text(encoding="utf-8")
    )
    if lock.get("manifest_sha256") != _sha256(manifest_path.read_bytes()):
        raise RuntimeError("制作記録のmanifestハッシュが一致しません")
    if lock.get("knowledge_version") != manifest.knowledge_version:
        raise RuntimeError("guidance-lock.jsonの知識バージョンが一致しません")
    paths: dict[str, Path] = {}
    for resource_id, descriptor in manifest.resources.items():
        path = _resource_path(guidance_dir, resource_id)
        if not path.is_file() or _sha256(path.read_bytes()) != descriptor.sha256:
            raise RuntimeError(f"制作記録の指示ファイルを検証できません: {path}")
        if lock.get("resources", {}).get(resource_id) != descriptor.sha256:
            raise RuntimeError(f"制作記録の指示ロックが一致しません: {resource_id}")
        paths[resource_id] = path
    profile = ProductionProfile.model_validate_json(
        paths["production_profile"].read_text(encoding="utf-8")
    )
    if profile.knowledge_version != manifest.knowledge_version:
        raise RuntimeError("production_profileの知識バージョンが一致しません")
    selected_media_data = lock.get("selected_media")
    if selected_media_data is not None:
        try:
            selected_media = MediaContract.model_validate(selected_media_data)
        except ValueError as error:
            raise RuntimeError(
                "制作記録の映像比率・解像度を検証できません"
            ) from error
        expected_profile = profile.for_aspect_ratio(selected_media.aspect_ratio)
        if selected_media != expected_profile.media:
            raise RuntimeError("制作記録の映像比率・解像度を検証できません")
        profile = expected_profile
    japanese = NoticeFeed.model_validate_json(
        paths["notices_ja"].read_text(encoding="utf-8")
    )
    english = NoticeFeed.model_validate_json(
        paths["notices_en"].read_text(encoding="utf-8")
    )
    _validate_notice_pair(japanese, english, manifest.knowledge_version)
    _validate_tutorial_catalogs(
        {
            resource_id: path.read_bytes()
            for resource_id, path in paths.items()
            if resource_id in OPTIONAL_PAIRED_RESOURCES
        },
        manifest.knowledge_version,
    )
    _validate_compatibility(manifest)
    return GuidanceBundle(manifest, profile, guidance_dir, paths)


def guidance_status(
    *,
    config_path: Path = DEFAULT_CONFIG_PATH,
    state_dir: Path = DEFAULT_STATE_DIR,
) -> dict[str, object]:
    config = load_studio_config(config_path)
    state = _load_state(state_dir)
    state_data = state.model_dump(mode="json")
    last_checked_manifest_url = state_data.pop("manifest_url")
    result: dict[str, object] = {
        "configured_manifest_url": config.knowledge_manifest_url,
        "last_checked_manifest_url": last_checked_manifest_url,
        "studio_version": __version__,
        **state_data,
        "cache_verified": False,
    }
    if state.active_knowledge_version:
        try:
            bundle = _load_bundle_from_cache(
                state_dir,
                state.active_knowledge_version,
            )
            result["cache_verified"] = True
            result["agent_guide_ja"] = str(bundle.guide_path("ja"))
            result["agent_guide_en"] = str(bundle.guide_path("en"))
            result["profile_id"] = bundle.profile.profile_id
            result["default_aspect_ratio"] = bundle.profile.media.aspect_ratio
            result["supported_aspect_ratios"] = ["9:16", "16:9"]
            result["tutorial_catalog_available"] = (
                "tutorial_catalog_ja" in bundle.resource_paths
                and "tutorial_catalog_en" in bundle.resource_paths
            )
            if result["tutorial_catalog_available"]:
                catalog = bundle.tutorial_catalog("ja")
                result["official_youtube_channel_id"] = (
                    catalog.official_channel.channel_id
                )
                result["active_tutorial_count"] = len(
                    [
                        tutorial
                        for tutorial in catalog.tutorials
                        if tutorial.status == "active"
                    ]
                )
            result["valid_until"] = bundle.manifest.valid_until.isoformat() if bundle.manifest.valid_until else None
            result["cache_expired"] = _manifest_is_expired(
                bundle.manifest,
                datetime.now().astimezone(),
            )
        except Exception as error:
            result["cache_error"] = str(error)
    return result
