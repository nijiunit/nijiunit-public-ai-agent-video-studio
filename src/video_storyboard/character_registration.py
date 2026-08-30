from __future__ import annotations

import hashlib
import html
import os
import re
import shutil
import subprocess
import unicodedata
from pathlib import Path
from typing import Literal

import imageio_ffmpeg
from pydantic import BaseModel, Field

from .character_registry import (
    CharacterMotion,
    CharacterRecord,
    CharacterReference,
    CharacterRegistry,
    ReferenceRole,
    RegistryEntry,
    RegistryFile,
    normalize_character_name,
)
from .schema import Storyboard

VIDEO_EXTENSIONS = {".mp4", ".mov", ".m4v", ".webm"}
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}


class RegistrationReference(BaseModel):
    path: Path
    role: ReferenceRole = "identity"
    label: str = "利用者が確認した基準素材"
    triggers: list[str] = Field(default_factory=list)
    motion_name_ja: str = "参考動作"
    motion_prompt_en: str = "Use only the body mechanics of this motion reference."


class CharacterRegistrationSpec(BaseModel):
    id: str | None = None
    name_ja: str
    aliases: list[str] = Field(default_factory=list)
    concept_id: str = "user_original"
    kind: Literal["human", "animal", "robot"]
    description_ja: str
    identity_prompt_en: str
    immutable_traits: list[str] = Field(min_length=1)
    forbidden_traits: list[str] = Field(default_factory=list)
    references: list[RegistrationReference] = Field(min_length=1)
    source_notes: list[str] = Field(default_factory=list)
    source_type: Literal["original", "generated", "third_party", "unknown"]
    asset_license: str | None = None
    publishable: bool = False
    rights_confirmed: bool = False


def _safe_character_id(name: str) -> str:
    normalized = unicodedata.normalize("NFKD", name)
    ascii_name = normalized.encode("ascii", "ignore").decode("ascii").lower()
    slug = re.sub(r"[^a-z0-9]+", "_", ascii_name).strip("_")
    if slug:
        return slug[:48]
    digest = hashlib.sha256(name.encode("utf-8")).hexdigest()[:10]
    return f"character_{digest}"


def _load_or_create_index(registry_dir: Path) -> RegistryFile:
    index_path = registry_dir / "registry.json"
    if index_path.is_file():
        return RegistryFile.model_validate_json(index_path.read_text(encoding="utf-8"))
    return RegistryFile(characters=[])


def _write_index(registry_dir: Path, index: RegistryFile) -> None:
    registry_dir.mkdir(parents=True, exist_ok=True)
    destination = registry_dir / "registry.json"
    temporary = destination.with_suffix(".json.tmp")
    temporary.write_text(index.model_dump_json(indent=2) + "\n", encoding="utf-8")
    temporary.replace(destination)


def _matching_active_id(registry_dir: Path, name: str) -> str | None:
    registry = CharacterRegistry.load_optional(registry_dir)
    if not registry:
        return None
    records, unresolved = registry.resolve([name])
    return records[0].id if records and not unresolved else None


def _next_version(registry_dir: Path, character_id: str) -> str:
    versions = []
    directory = registry_dir / character_id
    if directory.is_dir():
        for path in directory.iterdir():
            match = re.fullmatch(r"v(\d{3})", path.name)
            if path.is_dir() and match:
                versions.append(int(match.group(1)))
    return f"v{max(versions, default=0) + 1:03d}"


def _extract_frame(source: Path, seconds: float, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    command = [
        imageio_ffmpeg.get_ffmpeg_exe(),
        "-hide_banner",
        "-loglevel",
        "error",
        "-ss",
        str(seconds),
        "-i",
        str(source),
        "-frames:v",
        "1",
        "-vf",
        "scale='min(1280,iw)':-2",
        "-y",
        str(destination),
    ]
    result = subprocess.run(command, capture_output=True, check=False)
    if result.returncode:
        raise RuntimeError(f"参考動画から確認画像を作れませんでした: {source.name}")


def _prepare_references(
    spec: CharacterRegistrationSpec,
    profile_dir: Path,
) -> tuple[list[CharacterReference], list[CharacterMotion]]:
    references: list[CharacterReference] = []
    motions: list[CharacterMotion] = []
    for index, item in enumerate(spec.references, start=1):
        source = item.path.expanduser().resolve()
        if not source.is_file():
            raise FileNotFoundError(f"キャラクター参考素材がありません: {source}")
        suffix = source.suffix.lower()
        if suffix in IMAGE_EXTENSIONS:
            destination = profile_dir / "references" / f"reference_{index:02d}{suffix}"
            destination.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, destination)
            references.append(
                CharacterReference(
                    path=destination.relative_to(profile_dir).as_posix(),
                    role=item.role,
                    label=item.label,
                    triggers=item.triggers,
                    priority=100 if item.role in {"identity", "full_body"} else 70,
                )
            )
            continue
        if suffix not in VIDEO_EXTENSIONS:
            raise ValueError(f"未対応のキャラクター素材です: {source.name}")

        motion_source = profile_dir / "motions" / f"reference_{index:02d}{suffix}"
        motion_source.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, motion_source)
        frame_paths: list[str] = []
        for frame_index, seconds in enumerate((0.25, 1.5, 2.75), start=1):
            frame = (
                profile_dir
                / "references"
                / f"reference_{index:02d}_frame_{frame_index}.jpg"
            )
            _extract_frame(source, seconds, frame)
            relative = frame.relative_to(profile_dir).as_posix()
            frame_paths.append(relative)
            references.append(
                CharacterReference(
                    path=relative,
                    role="identity" if frame_index == 1 else "motion_keyframe",
                    label=f"{item.label} {frame_index}/3",
                    triggers=item.triggers,
                    priority=100 if frame_index == 1 else 75 - frame_index,
                )
            )
        if item.triggers:
            motions.append(
                CharacterMotion(
                    id=f"reference_motion_{index:02d}",
                    name_ja=item.motion_name_ja,
                    clip_path=motion_source.relative_to(profile_dir).as_posix(),
                    triggers=item.triggers,
                    prompt_en=item.motion_prompt_en,
                    keyframes=frame_paths,
                )
            )
    return references, motions


def _review_html(
    record: CharacterRecord,
    profile_dir: Path,
    destination: Path,
    language: str,
) -> Path:
    labels = {
        "ja": {
            "title": f"「{record.name_ja}」として覚える内容の確認",
            "pending": "まだ登録していません。写真と説明を確認した後に登録します。",
            "description": "このキャラクターについて",
            "fixed": "動画でも同じにするところ",
            "forbidden": "動画で変えない・追加しないこと",
            "action": f"上の写真が「{record.name_ja}」本人で、説明にも問題がなければ、その旨を普通の言葉でAIエージェントへ伝えてください。違う場合は、どこが違うか教えてください。",
        },
        "en": {
            "title": "Character review",
            "pending": "Registration is not final yet",
            "description": "Description",
            "fixed": "Traits kept across videos",
            "forbidden": "Traits never added",
            "action": "Review the images and traits. If they are correct, tell the AI agent that you approve this character. Otherwise, describe the change in your own words.",
        },
    }[language]
    images = []
    for reference in record.references:
        if reference.role not in {"identity", "full_body", "motion_keyframe"}:
            continue
        source = profile_dir / reference.path
        relative = Path(os.path.relpath(source, destination.parent)).as_posix()
        images.append(
            f'<figure><img src="{html.escape(relative)}" alt="{html.escape(reference.label)}">'
            f'<figcaption>{html.escape(reference.label)}</figcaption></figure>'
        )
    fixed = "".join(f"<li>{html.escape(value)}</li>" for value in record.immutable_traits)
    forbidden = "".join(
        f"<li>{html.escape(value)}</li>" for value in record.forbidden_traits
    ) or "<li>—</li>"
    document = f"""<!doctype html>
<html lang="{language}"><meta charset="utf-8"><title>{html.escape(labels['title'])}</title>
<style>body{{font-family:system-ui,sans-serif;background:#f5f8ff;color:#18304f;margin:0}}main{{max-width:1050px;margin:32px auto;background:white;padding:34px;border-radius:22px}}h1{{font-size:36px}}.pending{{background:#fff2b8;border:3px solid #e5b500;padding:18px;border-radius:14px;font-weight:700}}.images{{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:18px}}figure{{margin:0}}img{{width:100%;max-height:380px;object-fit:contain;background:#eef2f7;border-radius:12px}}section{{margin-top:26px}}li{{margin:8px 0}}.action{{background:#e7f8f5;border-left:7px solid #009c9b;padding:20px;font-size:20px}}</style>
<main><p class="pending">{html.escape(labels['pending'])}</p><h1>{html.escape(labels['title'])}</h1>
<div class="images">{''.join(images)}</div>
<section><h2>{html.escape(labels['description'])}</h2><p>{html.escape(record.description_ja)}</p></section>
<section><h2>{html.escape(labels['fixed'])}</h2><ul>{fixed}</ul></section>
<section><h2>{html.escape(labels['forbidden'])}</h2><ul>{forbidden}</ul></section>
<p class="action">{html.escape(labels['action'])}</p></main></html>"""
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(document, encoding="utf-8")
    return destination


def register_character(spec_path: Path, registry_dir: Path) -> tuple[Path, Path, Path]:
    spec = CharacterRegistrationSpec.model_validate_json(
        spec_path.resolve().read_text(encoding="utf-8")
    )
    if not spec.rights_confirmed:
        raise RuntimeError(
            "参考素材の利用権が未確認です。本人が利用できる素材か確認してから登録してください。"
        )
    registry_dir = registry_dir.resolve()
    index = _load_or_create_index(registry_dir)
    character_id = (
        spec.id
        or _matching_active_id(registry_dir, spec.name_ja)
        or _safe_character_id(spec.name_ja)
    )
    if any(entry.id == character_id for entry in index.pending):
        raise RuntimeError(
            f"確認待ちの版があります: {character_id}。先に承認または修正してください。"
        )
    version = _next_version(registry_dir, character_id)
    profile_dir = registry_dir / character_id / version
    references, motions = _prepare_references(spec, profile_dir)
    record = CharacterRecord(
        id=character_id,
        version=version,
        name_ja=spec.name_ja,
        aliases=spec.aliases,
        concept_id=spec.concept_id,
        kind=spec.kind,
        description_ja=spec.description_ja,
        identity_prompt_en=spec.identity_prompt_en,
        immutable_traits=spec.immutable_traits,
        forbidden_traits=spec.forbidden_traits,
        references=references,
        motions=motions,
        source_notes=spec.source_notes,
        source_type=spec.source_type,
        asset_license=spec.asset_license,
        publishable=spec.publishable,
        review_status="pending",
    )
    profile_path = profile_dir / "profile.json"
    profile_path.write_text(record.model_dump_json(indent=2) + "\n", encoding="utf-8")
    entry = RegistryEntry(
        id=character_id,
        active_version=version,
        profile=profile_path.relative_to(registry_dir).as_posix(),
    )
    index.pending.append(entry)
    _write_index(registry_dir, index)
    ja = _review_html(record, profile_dir, profile_dir / "review" / "character_review.ja.html", "ja")
    en = _review_html(record, profile_dir, profile_dir / "review" / "character_review.en.html", "en")
    return profile_path, ja, en


def approve_character(registry_dir: Path, character_id: str, version: str) -> Path:
    registry_dir = registry_dir.resolve()
    index = _load_or_create_index(registry_dir)
    entry = next(
        (
            value
            for value in index.pending
            if value.id == character_id and value.active_version == version
        ),
        None,
    )
    if entry is None:
        raise RuntimeError(f"確認待ちのキャラクター版がありません: {character_id}/{version}")
    profile_path = registry_dir / entry.profile
    record = CharacterRecord.model_validate_json(profile_path.read_text(encoding="utf-8"))
    record.review_status = "approved"
    profile_path.write_text(record.model_dump_json(indent=2) + "\n", encoding="utf-8")
    index.characters = [value for value in index.characters if value.id != character_id]
    index.characters.append(entry)
    index.pending = [
        value
        for value in index.pending
        if not (value.id == character_id and value.active_version == version)
    ]
    _write_index(registry_dir, index)
    CharacterRegistry.load(registry_dir).write_lock_file()
    return profile_path


def character_status(storyboard: Storyboard, registry_dir: Path) -> dict[str, object]:
    requested = list(
        dict.fromkeys(
            name.strip()
            for shot in storyboard.shots
            for name in shot.characters
            if name.strip()
        )
    )
    registry = CharacterRegistry.load_optional(registry_dir)
    resolved_records, unresolved = (
        registry.resolve(requested) if registry else ([], requested)
    )
    index = _load_or_create_index(registry_dir)
    pending = []
    for entry in index.pending:
        profile = registry_dir / entry.profile
        if profile.is_file():
            record = CharacterRecord.model_validate_json(profile.read_text(encoding="utf-8"))
            pending.append(
                {"id": record.id, "version": record.version, "name": record.name_ja}
            )
    pending_names = {normalize_character_name(item["name"]) for item in pending}
    return {
        "requested": requested,
        "approved": [
            {"id": record.id, "version": record.version, "name": record.name_ja}
            for record in resolved_records
        ],
        "pending": pending,
        "unresolved": [
            name
            for name in unresolved
            if normalize_character_name(name) not in pending_names
        ],
    }
