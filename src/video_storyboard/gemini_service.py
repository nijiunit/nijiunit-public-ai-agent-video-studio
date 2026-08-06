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
from .schema import ApiStoryboard, Storyboard
from .settings import IMAGE_MODEL, STORY_MODEL, require_api_key

STORY_SYSTEM_INSTRUCTION = """
あなたは、短編映画、コメディ、実写パロディの絵コンテを設計するシニア監督です。
入力ストーリーの出来事を勝手に削除せず、素材にない重要設定を勝手に追加しません。
映像は3秒単位に分割し、各ショットの中で一つの明確な動作だけを扱います。
登場人物・場所・小道具の連続性を最優先します。
参照画像はキャラクターや物体の外見だけに使い、画像内の文字、ロゴ、UIは再現しません。
転倒や失敗は明るいスラップスティックとして描き、流血、負傷、残酷表現を避けます。
"""


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
    raise AssertionError("unreachable")


class GeminiService:
    def __init__(
        self,
        story_model: str | None = None,
        image_model: str | None = None,
    ) -> None:
        self.client = genai.Client(api_key=require_api_key())
        self.story_model = story_model or STORY_MODEL
        self.image_model = image_model or IMAGE_MODEL

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
        prompt = f"""
次のストーリーと参照素材から、完成尺30〜42秒を目安に、
3秒単位の映像絵コンテを作ってください。ショット数は10〜14です。
映像比率は16:9です。

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
- 全編を映画的で高品質な実写映像として設計する。
- ニキは参照画像の顔立ちを保った、小柄で愛嬌のある実写のナマケモノ。
- ブライトさんは参照アニメ画像の黒髪、眉、顔立ち、赤い襟の濃紺の士官服を
  保ちながら、自然な実写の成人男性として翻案する。
- ガンダムは参照画像の白・青・赤の配色、頭部、胸部、盾、巨大な人型兵器の
  シルエットを維持する。機体表面に文字やロゴを描かない。
- ニキがガンダムを格好よく操縦できることと、ブライトさんが嫉妬して
  自分も操縦したがることを、表情と動作で明確に見せる。
- 原文のブライトさんの3つのセリフを省略せず、dialogueへ正確に割り当てる。
- セリフを言うショットのvideo_promptには、話者名と日本語の発話内容を含める。
- 最後はブライトさんが操縦するガンダムが飛び上がった直後に制御を失い、
  頭から柔らかい地面へ落ちる。明るいコメディ表現で、負傷や流血は描かない。
- 1ショットは必ず3秒。
- continuity_start_modeは通常storyboard_imageとする。同じ構図・同じ人物配置を
  切れ目なく継続するカットだけprevious_final_frameとし、構図変更、時間経過、
  場所移動、登場人物の増減があるカットでは絶対に使用しない。
- 各ショットに0.333秒刻みの9コマ説明を正確に9件作る。
- main_image_promptとvideo_promptは英語で、参照素材の維持条件を具体的に書く。
- dialogueとnarrationは日本語で記載する。
- 画像・映像内に文字、字幕、題字、ロゴ、スマホUI、透かしを入れない。
"""
        contents: list[Any] = []
        opened_images: list[Image.Image] = []
        uploaded_files: list[Any] = []
        try:
            for item in assets:
                if item.kind == "video":
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
                            f"動画素材の処理に失敗しました: {item.original_name}"
                        )
                    uploaded_files.append(uploaded)
                    contents.extend(
                        [
                            uploaded,
                            f"直前の動画は {item.original_name}: {item.notes}",
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
            response = _retry(
                lambda: self.client.models.generate_content(
                    model=self.story_model,
                    contents=contents,
                    config={
                        "system_instruction": STORY_SYSTEM_INSTRUCTION,
                        "response_mime_type": "application/json",
                        "response_schema": ApiStoryboard,
                        "temperature": 0.4,
                        "max_output_tokens": 32768,
                    },
                )
            )
            if isinstance(response.parsed, ApiStoryboard):
                storyboard = response.parsed.to_storyboard()
            else:
                storyboard = ApiStoryboard.model_validate_json(
                    response.text
                ).to_storyboard()
            allowed_assets = {item.original_name for item in assets}
            for shot in storyboard.shots:
                shot.reference_assets = [
                    name for name in shot.reference_assets if name in allowed_assets
                ]
            return storyboard
        finally:
            for image in opened_images:
                image.close()
            for uploaded in uploaded_files:
                try:
                    self.client.files.delete(name=uploaded.name)
                except Exception:
                    pass

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
                reference_limit=4,
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
        comedy_rule = ""
        combined_action = f"{shot.title} {shot.action} {shot.scene_description}"
        if any(word in combined_action for word in {"落ち", "墜落", "転倒"}):
            comedy_rule = (
                "- Treat the fall as harmless slapstick comedy. The cockpit and "
                "pilot remain protected. No injury, blood, fire, explosion, or gore."
            )
        prompt = f"""
Use case: original cinematic live-action production
Asset type: main storyboard keyframe for a 3-second cinematic shot
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
- Convert illustrated references into convincing high-budget live-action
  photography; keep already-photorealistic references photorealistic.
- Preserve the identity and original component design of the supplied
  references. Do not import faces, uniforms, armor parts, color blocking,
  insignia, weapons, or silhouettes from unrelated famous franchises.
- Mechanical subjects must look like coherent full-scale practical machines
  with believable metal, joints, hydraulics, weight, and scale.
- Animal characters must remain natural photorealistic animals matching their
  supplied facial markings, fur, proportions, and friendly comic presence.
- Never reproduce the title, lettering, labels, logos, watermarks, captions,
  interface elements, or text visible in any reference image.
{comedy_rule}
- Preserve continuity with the previous and next shots.
- One cinematic live-action still, landscape 16:9, no split screen, no collage,
  no text.
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
            config_kwargs: dict[str, Any] = {
                "response_modalities": ["TEXT", "IMAGE"],
            }
            fields = getattr(types.GenerateContentConfig, "model_fields", {})
            if "response_format" in fields:
                config_kwargs["response_format"] = {
                    "image": {"aspect_ratio": "16:9", "image_size": "1K"}
                }
            elif "image_config" in fields:
                config_kwargs["image_config"] = {
                    "aspect_ratio": "16:9",
                    "image_size": "1K",
                }
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

    @staticmethod
    def _select_references(
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
        return selected[:4]
