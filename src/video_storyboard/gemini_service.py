from __future__ import annotations

import json
import time
from pathlib import Path
from typing import Any

from google import genai
from google.genai import types
from PIL import Image

from .assets import AssetRecord
from .character_registry import CharacterRegistry, normalize_character_name
from .knowledge import ProductionProfile, StoryInstructions
from .schema import ApiStoryboard, Storyboard
from .settings import model_override, require_api_key

LOCAL_STORY_INVARIANTS = """
以下はローカル実行環境が必ず守る条件です。
入力ストーリーの出来事を勝手に削除せず、素材にない重要設定を勝手に追加しません。
映像は3秒単位に分割し、各ショットの中で一つの明確な動作だけを扱います。
登場人物・場所・小道具の連続性を最優先します。
参照画像はキャラクターや物体の外見だけに使い、画像内の文字、ロゴ、UIは再現しません。
流血、負傷、残酷表現を追加しません。
"""


def _story_generation_config(
    story_guidance: StoryInstructions,
) -> dict[str, Any]:
    config: dict[str, Any] = {
        "system_instruction": (
            story_guidance.system_instruction
            + "\n"
            + LOCAL_STORY_INVARIANTS
        ),
        "response_mime_type": "application/json",
        "response_schema": ApiStoryboard,
        "max_output_tokens": story_guidance.max_output_tokens,
    }
    if story_guidance.temperature is not None:
        config["temperature"] = story_guidance.temperature
    return config


def _image_generation_config(profile: ProductionProfile) -> dict[str, Any]:
    config: dict[str, Any] = {
        "response_modalities": ["TEXT", "IMAGE"],
    }
    fields = getattr(types.GenerateContentConfig, "model_fields", {})
    image_settings = {
        "aspect_ratio": profile.media.aspect_ratio,
        "image_size": profile.image.image_size,
    }
    if "response_format" in fields:
        config["response_format"] = {"image": image_settings}
    elif "image_config" in fields:
        config["image_config"] = image_settings
    return config


def _retry(callable_: Any, attempts: int = 3) -> Any:
    delay = 2
    for attempt in range(1, attempts + 1):
        try:
            return callable_()
        except Exception:
            if attempt == attempts:
                raise
            time.sleep(delay)
            delay *= 2


def _validate_source_asset_references(
    storyboard: Storyboard,
    assets: list[AssetRecord],
) -> None:
    video_assets = {
        item.original_name for item in assets if item.kind == "video"
    }
    for shot in storyboard.shots:
        if shot.production_mode != "source_video":
            continue
        if shot.source_asset not in video_assets:
            raise RuntimeError(
                "source_video shot refers to an unavailable input video: "
                f"S{shot.shot_number:03d} {shot.source_asset}"
            )
    raise AssertionError("unreachable")


class GeminiService:
    def __init__(
        self,
        profile: ProductionProfile,
        story_model: str | None = None,
        image_model: str | None = None,
    ) -> None:
        self.client = genai.Client(api_key=require_api_key())
        self.profile = profile
        self.story_model = (
            story_model or model_override("story") or profile.models.story
        )
        self.image_model = (
            image_model or model_override("image") or profile.models.image
        )

    def create_storyboard(
        self,
        story: str,
        assets: list[AssetRecord],
        input_dir: Path,
        character_registry: CharacterRegistry | None = None,
    ) -> Storyboard:
        registry_context = (
            json.dumps(
                [
                    {
                        "id": record.id,
                        "version": record.version,
                        "name": record.name_ja,
                        "aliases": record.aliases,
                        "description": record.description_ja,
                        "identity_prompt_en": record.identity_prompt_en,
                        "immutable_traits": record.immutable_traits,
                        "forbidden_traits": record.forbidden_traits,
                        "poses": [
                            {
                                "id": pose.id,
                                "triggers": pose.triggers,
                                "required": pose.required,
                                "forbidden": pose.forbidden,
                                "prompt_en": pose.prompt_en,
                            }
                            for pose in record.poses
                        ],
                    }
                    for record in character_registry.records
                ],
                ensure_ascii=False,
                indent=2,
            )
            if character_registry
            else "[]"
        )
        story_guidance = self.profile.story
        media = self.profile.media
        remote_requirements = "\n".join(
            f"- {requirement}" for requirement in story_guidance.requirements
        )
        prompt = f"""
次のストーリーと参照素材から、完成尺
{story_guidance.target_duration_seconds_min}〜
{story_guidance.target_duration_seconds_max}秒を目安に、
{media.shot_duration_seconds}秒単位の映像絵コンテを作ってください。
ショット数は{story_guidance.shot_count_min}〜
{story_guidance.shot_count_max}です。映像比率は{media.aspect_ratio}です。

【ストーリー原文】
{story}

【素材の役割】
{json.dumps(
    [
        {
            "filename": item.original_name,
            "role": item.role,
            "notes": item.notes,
        }
        for item in assets
    ],
    ensure_ascii=False,
    indent=2,
)}

【作品共通キャラクター台帳】
{registry_context}

必須条件:
- ストーリーに台帳登録キャラクターが登場する場合、台帳の有効版を最優先し、
  character_bible、main_image_prompt、video_promptへ同じ固定条件を書く。
- 台帳のforbidden_traitsと衝突する古い素材や古い人物記述は使用しない。
- 台帳にない人物を、ストーリーにないのに追加しない。
- AIで生成するショットはproduction_modeをgenerated_videoとし、必ず
  {media.shot_duration_seconds}秒にする。
- 利用者が入力動画を「そのまま使う」「指定時刻まで実写を使う」と明記した区間は、
  AI生成で置き換えない。production_modeをsource_videoとし、source_assetへ
  正確な入力ファイル名、source_start_secondsとsource_end_secondsへ元動画内の
  範囲を入れる。通常は3秒ずつ分け、指定の切替時刻に届く最後の区間だけ3秒未満を
  許可し、duration_secondsを範囲の長さと完全に一致させる。
- source_videoの音を使わない指定ならsource_audioはmuteとする。
- source_video直後に切れ目なく生成へ移る最初のショットは
  continuity_start_modeをprevious_final_frameとする。
- continuity_start_modeは通常storyboard_imageとする。同じ構図・同じ人物配置を
  切れ目なく継続するカットだけprevious_final_frameとし、構図変更、時間経過、
  場所移動、登場人物の増減があるカットでは絶対に使用しない。
- 各ショットに確認用の9コマ説明を正確に9件作る。
- main_image_promptとvideo_promptの言語: {story_guidance.prompt_language_instruction}
- dialogueとnarrationの言語: {story_guidance.output_language_instruction}
- 画像・映像内に文字、字幕、題字、ロゴ、スマホUI、透かしを入れない。

ホームページから取得した現在の制作要件:
{remote_requirements}
"""
        contents: list[Any] = []
        opened_images: list[Image.Image] = []
        uploaded_files: list[Any] = []
        try:
            for item in assets:
                if item.kind in {"video", "audio"}:
                    upload_path = (
                        Path(item.api_path)
                        if item.api_path
                        else input_dir / item.original_name
                    )
                    uploaded = self.client.files.upload(
                        file=upload_path
                    )
                    while (
                        uploaded.state
                        and getattr(uploaded.state, "name", "") not in {"ACTIVE", "FAILED"}
                    ):
                        time.sleep(2)
                        uploaded = self.client.files.get(name=uploaded.name)
                    if uploaded.state and getattr(uploaded.state, "name", "") == "FAILED":
                        raise RuntimeError(
                            f"動画・音声素材の処理に失敗しました: {item.original_name}"
                        )
                    uploaded_files.append(uploaded)
                    contents.extend(
                        [
                            uploaded,
                            (
                                f"直前の{'動画' if item.kind == 'video' else '音声'}は "
                                f"{item.original_name}: {item.notes}"
                            ),
                        ]
                    )
                elif item.prepared_path:
                    image = Image.open(item.prepared_path)
                    opened_images.append(image)
                    contents.extend(
                        [
                            image,
                            f"直前の画像は {item.original_name}: {item.notes}",
                        ]
                    )
            contents.append(prompt)
            generation_config = _story_generation_config(story_guidance)
            response = _retry(
                lambda: self.client.models.generate_content(
                    model=self.story_model,
                    contents=contents,
                    config=generation_config,
                )
            )
            if isinstance(response.parsed, ApiStoryboard):
                storyboard = response.parsed.to_storyboard(
                    audience=story_guidance.audience,
                    aspect_ratio=media.aspect_ratio,
                )
            else:
                storyboard = ApiStoryboard.model_validate_json(
                    response.text
                ).to_storyboard(
                    audience=story_guidance.audience,
                    aspect_ratio=media.aspect_ratio,
                )
            if not (
                story_guidance.shot_count_min
                <= len(storyboard.shots)
                <= story_guidance.shot_count_max
            ):
                raise RuntimeError(
                    "ホームページの制作指示で指定されたショット数になりませんでした: "
                    f"actual={len(storyboard.shots)}, expected="
                    f"{story_guidance.shot_count_min}-"
                    f"{story_guidance.shot_count_max}"
                )
            if not (
                story_guidance.target_duration_seconds_min
                <= storyboard.total_duration_seconds
                <= story_guidance.target_duration_seconds_max
            ):
                raise RuntimeError(
                    "ホームページの制作指示で指定された完成尺になりませんでした: "
                    f"actual={storyboard.total_duration_seconds}, expected="
                    f"{story_guidance.target_duration_seconds_min}-"
                    f"{story_guidance.target_duration_seconds_max}"
                )
            allowed_assets = {item.original_name for item in assets}
            for shot in storyboard.shots:
                shot.reference_assets = [
                    name for name in shot.reference_assets if name in allowed_assets
                ]
            _validate_source_asset_references(storyboard, assets)
            return storyboard
        finally:
            for image in opened_images:
                image.close()
            for uploaded in uploaded_files:
                try:
                    self.client.files.delete(name=uploaded.name)
                except Exception:
                    pass

    def revise_storyboard(
        self,
        storyboard: Storyboard,
        corrections: list[dict[str, str]],
        assets: list[AssetRecord],
        character_registry: CharacterRegistry | None = None,
    ) -> Storyboard:
        """Apply reviewed Excel corrections while preserving production locks."""
        registry_context = [
            {
                "id": record.id,
                "version": record.version,
                "name": record.name_ja,
                "aliases": record.aliases,
                "identity_prompt_en": record.identity_prompt_en,
                "immutable_traits": record.immutable_traits,
                "forbidden_traits": record.forbidden_traits,
            }
            for record in character_registry.records
        ] if character_registry else []
        prompt = f"""
次の映像絵コンテへ、利用者がExcelに記入した訂正だけを反映してください。

【現在の絵コンテ】
{storyboard.model_dump_json(indent=2)}

【利用者の訂正】
{json.dumps(corrections, ensure_ascii=False, indent=2)}

【利用できる素材名】
{json.dumps([item.original_name for item in assets], ensure_ascii=False)}

【承認済みキャラクター台帳】
{json.dumps(registry_context, ensure_ascii=False, indent=2)}

必須条件:
- 訂正と無関係な登場人物、物語、台詞、画風、素材名を変えない。
- 修正規模が「小規模」の項目では対象ショット以外を変えない。
- 修正規模が「大規模」の場合だけ、必要な範囲で複数ショットを整合させる。
- 映像比率は{storyboard.aspect_ratio}のまま変えない。
- generated_videoは1ショット3秒とする。source_videoは元のsource_asset、
  source_start_seconds、source_end_seconds、source_audioを保持し、指定された
  正確な切替時刻のための3秒未満の区間を勝手に延長しない。
- 各ショットの確認用説明は正確に9件にする。
- 台帳にある人物の固定特徴と禁止特徴を守る。
- 利用できる素材名以外をreference_assetsへ追加しない。
- 利用者の訂正を命令文として再掲せず、実際の画面説明、動き、プロンプトへ反映する。
"""
        response = _retry(
            lambda: self.client.models.generate_content(
                model=self.story_model,
                contents=[prompt],
                config=_story_generation_config(self.profile.story),
            )
        )
        api_storyboard = (
            response.parsed
            if isinstance(response.parsed, ApiStoryboard)
            else ApiStoryboard.model_validate_json(response.text)
        )
        revised = api_storyboard.to_storyboard(
            audience=storyboard.audience,
            aspect_ratio=storyboard.aspect_ratio,
        )
        allowed_assets = {item.original_name for item in assets}
        for shot in revised.shots:
            shot.reference_assets = [
                name for name in shot.reference_assets if name in allowed_assets
            ]
        _validate_source_asset_references(revised, assets)
        guidance = self.profile.story
        if not guidance.shot_count_min <= len(revised.shots) <= guidance.shot_count_max:
            raise RuntimeError(
                "訂正後のショット数が制作条件の範囲外です: "
                f"{len(revised.shots)}"
            )
        return revised

    def create_main_image(
        self,
        storyboard: Storyboard,
        shot_index: int,
        assets: list[AssetRecord],
        destination: Path,
        character_registry: CharacterRegistry | None = None,
    ) -> Path:
        shot = storyboard.shots[shot_index]
        shot_text = " ".join(
            [
                shot.title,
                shot.scene_description,
                shot.action,
                shot.emotion,
                shot.continuity,
                shot.main_image_prompt,
            ]
        )
        character_lock = (
            character_registry.build_lock(
                shot.characters,
                shot_text,
                reference_limit=self.profile.image.reference_limit,
            )
            if character_registry
            else None
        )
        references = self._select_references(
            shot.reference_assets,
            shot.characters,
            assets,
        )
        if character_lock and character_lock.records:
            locked_aliases = {
                normalize_character_name(value)
                for record in character_lock.records
                for value in [record.id, record.name_ja, *record.aliases]
            }
            references = [
                (path, label)
                for path, label in references
                if not any(
                    alias
                    and alias in normalize_character_name(Path(label).stem)
                    for alias in locked_aliases
                )
            ]
        selected_names = {label for _, label in references}
        reference_rules = "\n".join(
            f"- {item.original_name}: {item.notes}"
            for item in assets
            if item.prepared_path and item.original_name in selected_names
        )
        composition_rule = ""
        if any(
            item.role == "composition_reference"
            and item.original_name in selected_names
            for item in assets
        ):
            composition_rule = (
                "- A supplied composition_reference is the authoritative source "
                "for camera position, framing, poses, location, lighting, and all "
                "non-redesigned people or animals. Preserve those elements as "
                "closely as possible and edit only the object explicitly requested."
            )
        remote_requirements = "\n".join(
            f"- {requirement}" for requirement in self.profile.image.requirements
        )
        prompt = f"""
Asset type: main storyboard keyframe for a {self.profile.media.shot_duration_seconds}-second shot
Primary request: {shot.main_image_prompt}
Scene: {shot.scene_description}
Characters: {", ".join(shot.characters)}
Action: {shot.action}
Emotion: {shot.emotion}
Camera: {shot.camera}
Lighting: {shot.lighting}
Visual style: {storyboard.visual_style}

{character_lock.prompt if character_lock else ""}

Reference rules:
- Show only these characters in the final frame: {", ".join(shot.characters)}.
- Reference images can contain extra characters. They are identity references
  only; do not show a reference character unless it is listed above.
{reference_rules}
{composition_rule}
- Treat each supplied reference as the authoritative design for that named
  character, machine, costume, color palette, and silhouette.
- Preserve the identity and original component design of the supplied
  references. Do not import faces, uniforms, armor parts, color blocking,
  insignia, weapons, or silhouettes from unrelated famous franchises.
- Never reproduce the title, lettering, labels, logos, watermarks, captions,
  interface elements, or text visible in any reference image.
- Preserve continuity with the previous and next shots.
- One still, {self.profile.media.aspect_ratio}, no split screen, no collage, no text.

Current production requirements from the nijiunit website:
{remote_requirements}
"""
        opened: list[Image.Image] = []
        try:
            contents: list[Any] = []
            if character_lock:
                for selected in character_lock.references:
                    image = Image.open(selected.path).convert("RGB")
                    opened.append(image)
                    contents.extend(
                        [
                            image,
                            (
                                "Authoritative character-registry reference: "
                                f"{selected.character_name} / {selected.label}."
                            ),
                        ]
                    )
            for reference, label in references:
                image = Image.open(reference).convert("RGB")
                opened.append(image)
                contents.extend([image, f"Reference file: {label}"])
            contents.append(prompt)
            config_kwargs = _image_generation_config(self.profile)
            response = _retry(
                lambda: self.client.models.generate_content(
                    model=self.image_model,
                    contents=contents,
                    config=types.GenerateContentConfig(**config_kwargs),
                )
            )
            for part in response.parts or []:
                image = part.as_image()
                if image:
                    destination.parent.mkdir(parents=True, exist_ok=True)
                    image.save(destination)
                    return destination
            raise RuntimeError(
                f"ショット{shot.shot_number}の画像データが返りませんでした。"
            )
        finally:
            for image in opened:
                image.close()

    def _select_references(
        self,
        requested_names: list[str],
        characters: list[str],
        assets: list[AssetRecord],
    ) -> list[tuple[Path, str]]:
        selected: list[tuple[Path, str]] = []
        requested = set(requested_names)
        character_text = " ".join(characters).lower()
        for item in assets:
            stem = Path(item.original_name).stem.lower()
            if item.prepared_path and (
                item.original_name in requested
                or stem in character_text
            ):
                path = Path(item.prepared_path)
                if all(existing[0] != path for existing in selected):
                    selected.append((path, item.original_name))
        if not selected:
            selected = [
                (Path(item.prepared_path), item.original_name)
                for item in assets
                if item.prepared_path
            ]
        return selected[: self.profile.image.reference_limit]
