from __future__ import annotations

import hashlib
import json
import unicodedata
from dataclasses import dataclass
from pathlib import Path
from typing import Literal

from pydantic import BaseModel, Field, model_validator

ReferenceRole = Literal[
    "identity",
    "full_body",
    "pose",
    "motion_keyframe",
    "anti_example",
]


def normalize_character_name(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).strip().casefold()
    if normalized.endswith("さん"):
        normalized = normalized[:-2]
    return "".join(character for character in normalized if not character.isspace())


class CharacterReference(BaseModel):
    path: str
    role: ReferenceRole = "identity"
    label: str
    priority: int = Field(default=50, ge=0, le=100)
    triggers: list[str] = Field(default_factory=list)
    use_for_generation: bool = True

    @model_validator(mode="after")
    def anti_examples_are_never_generation_inputs(self) -> "CharacterReference":
        if self.role == "anti_example":
            self.use_for_generation = False
        return self


class CharacterPose(BaseModel):
    id: str
    name_ja: str
    triggers: list[str]
    required: list[str]
    forbidden: list[str] = Field(default_factory=list)
    prompt_en: str


class CharacterMotion(BaseModel):
    id: str
    name_ja: str
    clip_path: str
    triggers: list[str] = Field(default_factory=list)
    default: bool = False
    prompt_en: str
    timing: list[str] = Field(default_factory=list)
    forbidden: list[str] = Field(default_factory=list)
    keyframes: list[str] = Field(default_factory=list, max_length=3)
    keyframe_times_seconds: list[float] = Field(
        default_factory=lambda: [0.25, 1.5, 2.75],
        max_length=3,
    )
    priority: int = Field(default=70, ge=0, le=100)
    use_for_generation: bool = True

    @model_validator(mode="after")
    def keyframes_and_times_match(self) -> "CharacterMotion":
        if self.keyframes and len(self.keyframes) != len(self.keyframe_times_seconds):
            raise ValueError("motion keyframes and keyframe_times_seconds must match")
        if any(value < 0 or value > 3 for value in self.keyframe_times_seconds):
            raise ValueError("motion keyframe times must be within the 3-second clip")
        return self


class CharacterRecord(BaseModel):
    schema_version: str = "1.0"
    id: str
    version: str
    name_ja: str
    aliases: list[str] = Field(default_factory=list)
    concept_id: str = "default"
    kind: Literal["human", "animal", "robot"]
    description_ja: str
    identity_prompt_en: str
    immutable_traits: list[str]
    forbidden_traits: list[str] = Field(default_factory=list)
    references: list[CharacterReference]
    poses: list[CharacterPose] = Field(default_factory=list)
    design_video: CharacterMotion | None = None
    motions: list[CharacterMotion] = Field(default_factory=list)
    source_notes: list[str] = Field(default_factory=list)
    source_type: Literal["original", "generated", "third_party", "unknown"] = (
        "unknown"
    )
    asset_license: str | None = None
    publishable: bool = False
    review_status: Literal["pending", "approved"] = "approved"

    @model_validator(mode="after")
    def publishable_assets_require_a_license(self) -> "CharacterRecord":
        if self.publishable and not self.asset_license:
            raise ValueError("publishable character assets require asset_license")
        return self


class RegistryEntry(BaseModel):
    id: str
    active_version: str
    profile: str


class RegistryConcept(BaseModel):
    id: str
    name_ja: str
    description_ja: str = ""


class RegistryFile(BaseModel):
    schema_version: str = "1.0"
    concepts: list[RegistryConcept] = Field(default_factory=list)
    characters: list[RegistryEntry]
    pending: list[RegistryEntry] = Field(default_factory=list)


@dataclass(frozen=True)
class SelectedCharacterReference:
    character_id: str
    character_name: str
    version: str
    role: ReferenceRole
    label: str
    path: Path
    priority: int


@dataclass(frozen=True)
class SelectedCharacterMotion:
    character_id: str
    character_name: str
    version: str
    motion_id: str
    motion_name: str
    clip_path: Path
    keyframe_paths: tuple[Path, ...]
    prompt_en: str
    timing: tuple[str, ...]
    forbidden: tuple[str, ...]
    guidance_mode: Literal["design_presence", "action"] = "action"


@dataclass(frozen=True)
class CharacterLock:
    requested_names: tuple[str, ...]
    records: tuple[CharacterRecord, ...]
    references: tuple[SelectedCharacterReference, ...]
    motions: tuple[SelectedCharacterMotion, ...]
    unresolved_names: tuple[str, ...]
    prompt: str


class CharacterRegistry:
    def __init__(
        self,
        root: Path,
        records: list[tuple[CharacterRecord, Path]],
        concepts: list[RegistryConcept] | None = None,
    ) -> None:
        self.root = root.resolve()
        self.concepts = tuple(concepts or [])
        self._records = {record.id: record for record, _ in records}
        self._profile_dirs = {
            record.id: profile_path.parent.resolve()
            for record, profile_path in records
        }
        self._aliases: dict[str, str] = {}
        for record, _ in records:
            for value in [record.id, record.name_ja, *record.aliases]:
                key = normalize_character_name(value)
                existing = self._aliases.get(key)
                if existing and existing != record.id:
                    raise ValueError(
                        f"Duplicate character alias {value!r}: {existing}, {record.id}"
                    )
                self._aliases[key] = record.id

    @classmethod
    def load(cls, root: Path) -> "CharacterRegistry":
        root = root.resolve()
        index_path = root / "registry.json"
        index = RegistryFile.model_validate_json(
            index_path.read_text(encoding="utf-8")
        )
        records: list[tuple[CharacterRecord, Path]] = []
        for entry in index.characters:
            profile_path = (root / entry.profile).resolve()
            if not profile_path.is_relative_to(root):
                raise ValueError(f"Profile is outside registry: {entry.profile}")
            record = CharacterRecord.model_validate_json(
                profile_path.read_text(encoding="utf-8")
            )
            if record.id != entry.id or record.version != entry.active_version:
                raise ValueError(
                    f"Registry entry mismatch: {entry.id}/{entry.active_version} "
                    f"!= {record.id}/{record.version}"
                )
            records.append((record, profile_path))
        return cls(root, records, index.concepts)

    @classmethod
    def load_optional(cls, root: Path | None) -> "CharacterRegistry | None":
        if root is None:
            return None
        index_path = root.resolve() / "registry.json"
        if not index_path.exists():
            return None
        return cls.load(root)

    @property
    def records(self) -> tuple[CharacterRecord, ...]:
        return tuple(self._records.values())

    def resolve(self, names: list[str]) -> tuple[list[CharacterRecord], list[str]]:
        resolved: list[CharacterRecord] = []
        unresolved: list[str] = []
        used: set[str] = set()
        for name in names:
            character_id = self._aliases.get(normalize_character_name(name))
            if character_id is None:
                unresolved.append(name)
                continue
            if character_id not in used:
                resolved.append(self._records[character_id])
                used.add(character_id)
        return resolved, unresolved

    def _reference_path(
        self,
        record: CharacterRecord,
        reference: CharacterReference,
    ) -> Path:
        path = (self._profile_dirs[record.id] / reference.path).resolve()
        if not path.is_relative_to(self.root):
            raise ValueError(
                f"Reference is outside registry: {record.id}: {reference.path}"
            )
        return path

    def _asset_path(self, record: CharacterRecord, relative_path: str) -> Path:
        path = (self._profile_dirs[record.id] / relative_path).resolve()
        if not path.is_relative_to(self.root):
            raise ValueError(
                f"Asset is outside registry: {record.id}: {relative_path}"
            )
        return path

    def asset_path(self, record: CharacterRecord, relative_path: str) -> Path:
        return self._asset_path(record, relative_path)

    @staticmethod
    def _matches_trigger(values: list[str], shot_text: str) -> bool:
        normalized_shot = unicodedata.normalize("NFKC", shot_text).casefold()
        return any(
            unicodedata.normalize("NFKC", value).casefold() in normalized_shot
            for value in values
        )

    def _active_poses(
        self,
        record: CharacterRecord,
        shot_text: str,
    ) -> list[CharacterPose]:
        return [
            pose
            for pose in record.poses
            if self._matches_trigger(pose.triggers, shot_text)
        ]

    def _active_motions(
        self,
        record: CharacterRecord,
        shot_text: str,
    ) -> list[CharacterMotion]:
        matched = [
            motion
            for motion in record.motions
            if motion.use_for_generation
            and motion.triggers
            and self._matches_trigger(motion.triggers, shot_text)
        ]
        if matched:
            return matched
        return [
            motion
            for motion in record.motions
            if motion.use_for_generation and motion.default
        ]

    def select_motions(
        self,
        records: list[CharacterRecord],
        shot_text: str,
    ) -> list[SelectedCharacterMotion]:
        selected: list[SelectedCharacterMotion] = []
        for record in records:
            values: list[tuple[CharacterMotion, Literal["design_presence", "action"]]] = []
            if record.design_video and record.design_video.use_for_generation:
                values.append((record.design_video, "design_presence"))
            values.extend(
                (motion, "action")
                for motion in self._active_motions(record, shot_text)
            )
            for motion, guidance_mode in values:
                selected.append(
                    SelectedCharacterMotion(
                        character_id=record.id,
                        character_name=record.name_ja,
                        version=record.version,
                        motion_id=motion.id,
                        motion_name=motion.name_ja,
                        clip_path=self._asset_path(record, motion.clip_path),
                        keyframe_paths=tuple(
                            self._asset_path(record, path)
                            for path in motion.keyframes
                        ),
                        prompt_en=motion.prompt_en,
                        timing=tuple(motion.timing),
                        forbidden=tuple(motion.forbidden),
                        guidance_mode=guidance_mode,
                    )
                )
        return selected

    def select_references(
        self,
        records: list[CharacterRecord],
        shot_text: str,
        limit: int = 6,
    ) -> list[SelectedCharacterReference]:
        candidates: dict[str, list[tuple[CharacterReference, Path]]] = {}
        active_motions = {
            record.id: self._active_motions(record, shot_text)
            for record in records
        }
        design_motion_paths: dict[str, list[Path]] = {
            record.id: [] for record in records
        }
        for record in records:
            active_pose_ids = {pose.id for pose in self._active_poses(record, shot_text)}
            values: list[tuple[CharacterReference, Path]] = []
            for reference in record.references:
                if not reference.use_for_generation or reference.role == "anti_example":
                    continue
                if reference.role in {"pose", "motion_keyframe"}:
                    triggered = self._matches_trigger(reference.triggers, shot_text)
                    triggered = triggered or any(
                        pose_id in reference.triggers for pose_id in active_pose_ids
                    )
                    if not triggered:
                        continue
                path = self._reference_path(record, reference)
                values.append((reference, path))
            for motion in active_motions[record.id]:
                for index, keyframe in enumerate(motion.keyframes):
                    values.append(
                        (
                            CharacterReference(
                                path=keyframe,
                                role="motion_keyframe",
                                label=(
                                    f"{motion.name_ja} motion keyframe "
                                    f"{index + 1}/{len(motion.keyframes)}"
                                ),
                                priority=max(0, motion.priority - index),
                            ),
                            self._asset_path(record, keyframe),
                        )
                    )
            if record.design_video and record.design_video.use_for_generation:
                motion = record.design_video
                for index, keyframe in enumerate(motion.keyframes):
                    path = self._asset_path(record, keyframe)
                    design_motion_paths[record.id].append(path)
                    values.append(
                        (
                            CharacterReference(
                                path=keyframe,
                                role="motion_keyframe",
                                label=(
                                    f"always-on design presence keyframe "
                                    f"{index + 1}/{len(motion.keyframes)}"
                                ),
                                priority=max(0, motion.priority - index),
                            ),
                            path,
                        )
                    )
            values.sort(key=lambda item: item[0].priority, reverse=True)
            candidates[record.id] = values

        selected: list[SelectedCharacterReference] = []
        selected_paths: set[Path] = set()

        def add(record: CharacterRecord, value: tuple[CharacterReference, Path]) -> None:
            reference, path = value
            if path in selected_paths or len(selected) >= limit:
                return
            selected.append(
                SelectedCharacterReference(
                    character_id=record.id,
                    character_name=record.name_ja,
                    version=record.version,
                    role=reference.role,
                    label=reference.label,
                    path=path,
                    priority=reference.priority,
                )
            )
            selected_paths.add(path)

        # First guarantee one authoritative identity image per on-screen character.
        for record in records:
            identity = next(
                (
                    value
                    for value in candidates[record.id]
                    if value[0].role in {"identity", "full_body"}
                ),
                None,
            )
            if identity:
                add(record, identity)

        # In a single-character shot, reserve the complementary face/full-body
        # identity angle before temporal samples. Multi-character shots keep one
        # identity slot per character so the reference budget remains balanced.
        if len(records) == 1:
            record = records[0]
            for value in candidates[record.id]:
                if value[0].role in {"identity", "full_body"}:
                    add(record, value)

        # Then add active poses.
        for record in records:
            for value in candidates[record.id]:
                if value[0].role == "pose":
                    add(record, value)

        # Always give every character one neutral temporal-identity sample before
        # action-specific motion frames consume the remaining reference budget.
        for record in records:
            first_design_path = next(
                iter(design_motion_paths[record.id]),
                None,
            )
            if first_design_path is None:
                continue
            design_value = next(
                (
                    value
                    for value in candidates[record.id]
                    if value[1] == first_design_path
                ),
                None,
            )
            if design_value:
                add(record, design_value)

        # Distribute motion samples round-robin so a multi-character shot gets at
        # least one timing/body-mechanics frame for each character before any one
        # character consumes the remaining reference budget.
        motion_values = {
            record.id: [
                value
                for value in candidates[record.id]
                if value[0].role == "motion_keyframe"
            ]
            for record in records
        }
        max_motion_frames = max(
            (len(values) for values in motion_values.values()),
            default=0,
        )
        for frame_index in range(max_motion_frames):
            for record in records:
                values = motion_values[record.id]
                if frame_index < len(values):
                    add(record, values[frame_index])

        # Finally add secondary identity and full-body angles.
        for record in records:
            for value in candidates[record.id]:
                if value[0].role in {"identity", "full_body"}:
                    add(record, value)
        return selected

    def build_lock(
        self,
        character_names: list[str],
        shot_text: str,
        reference_limit: int = 6,
    ) -> CharacterLock:
        records, unresolved = self.resolve(character_names)
        references = self.select_references(records, shot_text, reference_limit)
        motions = self.select_motions(records, shot_text)
        prompt_lines = [
            "CHARACTER REGISTRY LOCKS (authoritative and override conflicting shot text):"
        ]
        for record in records:
            prompt_lines.append(
                f"- {record.name_ja} [{record.id}/{record.version}]: "
                f"{record.identity_prompt_en}"
            )
            if record.immutable_traits:
                prompt_lines.append(
                    "  Must preserve: " + "; ".join(record.immutable_traits) + "."
                )
            if record.forbidden_traits:
                prompt_lines.append(
                    "  Never show: " + "; ".join(record.forbidden_traits) + "."
                )
            for pose in self._active_poses(record, shot_text):
                prompt_lines.append(
                    f"  Active pose {pose.id}: {pose.prompt_en}"
                )
                if pose.forbidden:
                    prompt_lines.append(
                        "  Pose exclusions: " + "; ".join(pose.forbidden) + "."
                    )
            if record.design_video and record.design_video.use_for_generation:
                design = record.design_video
                prompt_lines.append(
                    f"  Always-on design presence {design.id}: "
                    f"{design.prompt_en}"
                )
                prompt_lines.append(
                    "  Design-presence rule: use it only to preserve temporal "
                    "identity, resting posture, material response, breathing, and "
                    "natural movement scale. Never copy its exact demonstrated "
                    "gesture when the requested shot action differs."
                )
                if design.forbidden:
                    prompt_lines.append(
                        "  Design-presence exclusions: "
                        + "; ".join(design.forbidden)
                        + "."
                    )
            for motion in self._active_motions(record, shot_text):
                prompt_lines.append(
                    f"  Active motion {motion.id}: {motion.prompt_en}"
                )
                if motion.timing:
                    prompt_lines.append(
                        "  Motion timing: " + " | ".join(motion.timing) + "."
                    )
                if motion.forbidden:
                    prompt_lines.append(
                        "  Motion exclusions: " + "; ".join(motion.forbidden) + "."
                    )
        if not records:
            prompt_lines = []
        return CharacterLock(
            requested_names=tuple(character_names),
            records=tuple(records),
            references=tuple(references),
            motions=tuple(motions),
            unresolved_names=tuple(unresolved),
            prompt="\n".join(prompt_lines),
        )

    def validate(self) -> list[str]:
        issues: list[str] = []
        for record in self.records:
            if record.review_status != "approved":
                issues.append(f"Character is not approved: {record.id}/{record.version}")
            generation_references = 0
            for reference in record.references:
                try:
                    path = self._reference_path(record, reference)
                except ValueError as exc:
                    issues.append(str(exc))
                    continue
                if not path.is_file():
                    issues.append(f"Missing reference: {record.id}: {reference.path}")
                if reference.use_for_generation:
                    generation_references += 1
            if generation_references == 0:
                issues.append(f"No generation reference: {record.id}")
            for motion in record.motions:
                for label, relative_path in [
                    ("motion clip", motion.clip_path),
                    *[("motion keyframe", path) for path in motion.keyframes],
                ]:
                    try:
                        path = self._asset_path(record, relative_path)
                    except ValueError as exc:
                        issues.append(str(exc))
                        continue
                    if not path.is_file():
                        issues.append(
                            f"Missing {label}: {record.id}/{motion.id}: "
                            f"{relative_path}"
                        )
            if record.design_video:
                design = record.design_video
                for label, relative_path in [
                    ("design video", design.clip_path),
                    *[("design keyframe", path) for path in design.keyframes],
                ]:
                    try:
                        path = self._asset_path(record, relative_path)
                    except ValueError as exc:
                        issues.append(str(exc))
                        continue
                    if not path.is_file():
                        issues.append(
                            f"Missing {label}: {record.id}/{design.id}: "
                            f"{relative_path}"
                        )
        return issues

    def lock_data(self) -> dict[str, object]:
        characters: list[dict[str, object]] = []
        for record in self.records:
            references: list[dict[str, object]] = []
            for reference in record.references:
                path = self._reference_path(record, reference)
                if not path.is_file():
                    continue
                references.append(
                    {
                        "path": str(path.relative_to(self.root)).replace("\\", "/"),
                        "role": reference.role,
                        "use_for_generation": reference.use_for_generation,
                        "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                    }
                )
            characters.append(
                {
                    "id": record.id,
                    "name_ja": record.name_ja,
                    "version": record.version,
                    "concept_id": record.concept_id,
                    "references": references,
                    "design_video": (
                        {
                            "id": record.design_video.id,
                            "clip": {
                                "path": str(
                                    self._asset_path(
                                        record, record.design_video.clip_path
                                    ).relative_to(self.root)
                                ).replace("\\", "/"),
                                "sha256": hashlib.sha256(
                                    self._asset_path(
                                        record, record.design_video.clip_path
                                    ).read_bytes()
                                ).hexdigest(),
                            },
                            "keyframes": [
                                {
                                    "path": str(
                                        self._asset_path(record, keyframe)
                                        .relative_to(self.root)
                                    ).replace("\\", "/"),
                                    "sha256": hashlib.sha256(
                                        self._asset_path(record, keyframe)
                                        .read_bytes()
                                    ).hexdigest(),
                                }
                                for keyframe in record.design_video.keyframes
                                if self._asset_path(record, keyframe).is_file()
                            ],
                        }
                        if record.design_video
                        and self._asset_path(
                            record, record.design_video.clip_path
                        ).is_file()
                        else None
                    ),
                    "motions": [
                        {
                            "id": motion.id,
                            "clip": {
                                "path": str(
                                    self._asset_path(record, motion.clip_path)
                                    .relative_to(self.root)
                                ).replace("\\", "/"),
                                "sha256": hashlib.sha256(
                                    self._asset_path(record, motion.clip_path)
                                    .read_bytes()
                                ).hexdigest(),
                            },
                            "keyframes": [
                                {
                                    "path": str(
                                        self._asset_path(record, keyframe)
                                        .relative_to(self.root)
                                    ).replace("\\", "/"),
                                    "sha256": hashlib.sha256(
                                        self._asset_path(record, keyframe)
                                        .read_bytes()
                                    ).hexdigest(),
                                }
                                for keyframe in motion.keyframes
                                if self._asset_path(record, keyframe).is_file()
                            ],
                        }
                        for motion in record.motions
                        if self._asset_path(record, motion.clip_path).is_file()
                    ],
                }
            )
        return {"schema_version": "1.0", "characters": characters}

    def write_lock_file(self, destination: Path | None = None) -> Path:
        output = destination or self.root / "registry.lock.json"
        output.write_text(
            json.dumps(self.lock_data(), ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        return output


def require_resolved_character_names(
    registry: CharacterRegistry | None,
    character_names: list[str],
) -> None:
    """Stop paid image/video generation unless every named character is locked."""
    requested = list(
        dict.fromkeys(name.strip() for name in character_names if name.strip())
    )
    if not requested:
        return
    if registry is None:
        raise RuntimeError(
            "キャラクターが登場するため、生成前にキャラクター台帳が必要です。"
            "AIエージェントに、各キャラクターの基準画像と特徴を台帳へ登録するよう"
            "依頼してください。登録が終わるまで有料の画像・動画生成は開始しません。\n"
            "A character registry is required before paid image or video generation."
        )
    _, unresolved = registry.resolve(requested)
    if unresolved:
        raise RuntimeError(
            "次のキャラクターを台帳で確認できないため、生成を停止しました: "
            + ", ".join(unresolved)
            + "。AIエージェントに、同じキャラクターとして使う基準画像と特徴を"
            "台帳へ登録するよう依頼してください。\n"
            "Generation stopped before billing because character identity is unresolved."
        )
