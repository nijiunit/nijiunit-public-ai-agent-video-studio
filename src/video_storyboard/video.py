from __future__ import annotations

import base64
import hashlib
import json
import mimetypes
import re
import subprocess
import time
from pathlib import Path
from typing import Any

from google import genai
from google.genai import types
from imageio_ffmpeg import get_ffmpeg_exe

from .character_registry import (
    CharacterLock,
    CharacterRegistry,
    require_resolved_character_names,
)
from .knowledge import MediaContract, ProductionProfile
from .schema import Shot, Storyboard
from .settings import (
    CHARACTER_REGISTRY_DIR,
    model_override,
    require_api_key,
)


def _video_prompt(
    shot: Shot,
    profile: ProductionProfile,
    character_lock: CharacterLock | None = None,
) -> str:
    if shot.dialogue:
        audio_instruction = (
            " The speaking character says exactly this line, following the "
            f"language instruction '{profile.audio.tts_language_instruction}': "
            f'"{shot.dialogue}". No subtitles or on-screen text.'
        )
    else:
        audio_instruction = (
            " No spoken dialogue. Use only sound appropriate to the shot and "
            "sound effects, with no vocals."
        )

    identity_instruction = ""
    if character_lock and character_lock.prompt:
        identity_instruction = (
            f"\n{character_lock.prompt}\n"
            "Use the supplied character-registry images only as identity, body, "
            "costume, and active-pose references. They are not extra opening frames "
            "and their backgrounds must not appear. "
        )

    remote_requirements = " ".join(profile.video.requirements)

    return (
        "<FIRST_FRAME> Use the supplied image as the exact opening frame and animate "
        "it conservatively. In a single continuous unbroken shot with no scene cuts: "
        f"{shot.video_prompt}{identity_instruction} "
        f"Current nijiunit production requirements: {remote_requirements} "
        "Do not add text, captions, logos, interface elements, blood, injury, or gore."
        f"{audio_instruction} Duration exactly "
        f"{profile.media.shot_duration_seconds} seconds. Output format stays "
        f"{profile.media.aspect_ratio} at "
        f"{profile.media.width}x{profile.media.height}."
    )


def _video_response_format(profile: ProductionProfile) -> dict[str, str]:
    return {
        "type": "video",
        "delivery": "inline",
        "aspect_ratio": profile.media.aspect_ratio,
        "duration": f"{profile.media.shot_duration_seconds}s",
    }


def _identity_metadata(character_lock: CharacterLock | None) -> dict[str, Any]:
    if not character_lock:
        return {
            "enabled": False,
            "characters": [],
            "references": [],
            "unresolved_characters": [],
        }
    return {
        "enabled": bool(character_lock.records),
        "characters": [
            {
                "id": record.id,
                "name_ja": record.name_ja,
                "version": record.version,
            }
            for record in character_lock.records
        ],
        "references": [
            {
                "character_id": selected.character_id,
                "role": selected.role,
                "label": selected.label,
                "filename": selected.path.name,
                "sha256": hashlib.sha256(selected.path.read_bytes()).hexdigest(),
            }
            for selected in character_lock.references
        ],
        "motions": [
            {
                "character_id": selected.character_id,
                "motion_id": selected.motion_id,
                "motion_name": selected.motion_name,
                "clip_filename": selected.clip_path.name,
                "clip_sha256": hashlib.sha256(
                    selected.clip_path.read_bytes()
                ).hexdigest(),
                "keyframes": [path.name for path in selected.keyframe_paths],
                "direct_video_input": False,
                "guidance_mode": selected.guidance_mode,
            }
            for selected in character_lock.motions
        ],
        "unresolved_characters": list(character_lock.unresolved_names),
    }


def _stable_veo_seed(shot: Shot, character_lock: CharacterLock | None) -> int:
    identity = ",".join(
        f"{record.id}:{record.version}"
        for record in character_lock.records
    ) if character_lock else "unlocked"
    digest = hashlib.sha256(
        f"{shot.shot_number}|{shot.title}|{identity}".encode("utf-8")
    ).digest()
    return int.from_bytes(digest[:4], "big") & 0x7FFFFFFF


def _omni_inputs(
    image_path: Path,
    prompt: str,
    character_lock: CharacterLock | None,
    profile: ProductionProfile,
) -> list[dict[str, str]]:
    first_mime = mimetypes.guess_type(image_path.name)[0] or "image/png"
    inputs: list[dict[str, str]] = [
        {
            "type": "image",
            "data": base64.b64encode(image_path.read_bytes()).decode("ascii"),
            "mime_type": first_mime,
        }
    ]
    declarations = ["[# Sources <FIRST_FRAME>@Image1]"]
    reference_roles: list[str] = []
    for index, selected in enumerate(
        character_lock.references if character_lock else (),
        start=2,
    ):
        mime_type = mimetypes.guess_type(selected.path.name)[0] or "image/png"
        inputs.append(
            {
                "type": "image",
                "data": base64.b64encode(selected.path.read_bytes()).decode("ascii"),
                "mime_type": mime_type,
            }
        )
        declarations.append(
            f"[# References <IMAGE_REF_{index - 2}>@Image{index}]"
        )
        reference_roles.append(
            f"IMAGE_REF_{index - 2} is {selected.character_name}'s "
            f"{selected.role} reference ({selected.label})."
        )
    role_instruction = (
        "Use Image1 as the exact starting frame. Use every IMAGE_REF only as an "
        "authoritative character identity, body, pose, or motion-keyframe "
        "reference, never as a literal scene or additional frame. Always-on design "
        "presence keyframes preserve temporal identity and natural movement scale "
        "only; do not copy their exact gesture. Action motion keyframes control body "
        "mechanics and timing only when the prompt explicitly activates that action. "
        "The requested shot action and setting remain authoritative."
        if len(inputs) > 1
        else "Use Image1 as the exact starting frame."
    )
    remote_reference_instructions = " ".join(
        profile.video.reference_instructions
    )
    inputs.append(
        {
            "type": "text",
            "text": " ".join(declarations)
            + "\n"
            + prompt
            + "\n"
            + " ".join(reference_roles)
            + "\n"
            + role_instruction
            + "\n"
            + remote_reference_instructions,
        }
    )
    return inputs


class VideoService:
    def __init__(
        self,
        profile: ProductionProfile,
        model: str | None = None,
    ) -> None:
        self.client = genai.Client(api_key=require_api_key())
        self.profile = profile
        self.model = model or model_override("video") or profile.models.video

    def create_clip(
        self,
        shot: Shot,
        image_path: Path,
        destination: Path,
        metadata_path: Path | None = None,
        character_lock: CharacterLock | None = None,
    ) -> Path:
        if self.profile.video.api_family == "veo":
            for attempt in range(1, 4):
                try:
                    return self._create_veo_clip(
                        shot,
                        image_path,
                        destination,
                        metadata_path,
                        character_lock,
                    )
                except Exception:
                    if attempt == 3:
                        raise
                    time.sleep(5 * attempt)
        prompt = _video_prompt(shot, self.profile, character_lock)
        has_identity_references = bool(
            character_lock and character_lock.references
        )
        interaction = self.client.interactions.create(
            model=self.model,
            input=_omni_inputs(image_path, prompt, character_lock, self.profile),
            response_format=_video_response_format(self.profile),
            generation_config={
                "video_config": {
                    "task": (
                        "reference_to_video"
                        if has_identity_references
                        else "image_to_video"
                    )
                }
            },
            background=False,
            store=False,
        )
        output = interaction.output_video
        if output is None or not output.data:
            raise RuntimeError(
                f"S{shot.shot_number:03d}: Gemini returned no inline video data."
            )
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(base64.b64decode(output.data))
        if metadata_path:
            metadata_path.parent.mkdir(parents=True, exist_ok=True)
            metadata_path.write_text(
                json.dumps(
                    {
                        "shot_number": shot.shot_number,
                        "model": self.model,
                        "interaction_id": interaction.id,
                        "status": str(interaction.status),
                        "requested_duration": (
                            f"{self.profile.media.shot_duration_seconds}s"
                        ),
                        "aspect_ratio": self.profile.media.aspect_ratio,
                        "identity_reference_mode": (
                            "first_frame_plus_character_registry_images"
                            if has_identity_references
                            else "first_frame_only"
                        ),
                        "character_lock": _identity_metadata(character_lock),
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
        return destination

    def _create_veo_clip(
        self,
        shot: Shot,
        image_path: Path,
        destination: Path,
        metadata_path: Path | None = None,
        character_lock: CharacterLock | None = None,
    ) -> Path:
        mime_type = mimetypes.guess_type(image_path.name)[0] or "image/png"
        selected_references = list(
            character_lock.references[
                : self.profile.video.maximum_character_reference_images
            ]
            if character_lock
            else ()
        )
        attached_references = (
            selected_references
            if self.profile.video.supports_asset_reference_images
            else []
        )
        source_duration = (
            self.profile.video.provider_duration_seconds_with_references
            if attached_references
            else self.profile.video.provider_duration_seconds
        )
        config_kwargs: dict[str, Any] = {
            "number_of_videos": 1,
            "duration_seconds": source_duration,
            "aspect_ratio": self.profile.media.aspect_ratio,
            "resolution": self.profile.video.provider_resolution,
        }
        if self.profile.video.supports_negative_prompt:
            config_kwargs["negative_prompt"] = ", ".join(
                self.profile.video.negative_prompt_terms
            )
        if attached_references:
            config_kwargs["reference_images"] = [
                types.VideoGenerationReferenceImage(
                    image=types.Image(
                        image_bytes=selected.path.read_bytes(),
                        mime_type=(
                            mimetypes.guess_type(selected.path.name)[0]
                            or "image/png"
                        ),
                    ),
                    reference_type=types.VideoGenerationReferenceType.ASSET,
                )
                for selected in attached_references
            ]

        operation = self.client.models.generate_videos(
            model=self.model,
            prompt=_video_prompt(shot, self.profile, character_lock),
            image=types.Image(
                image_bytes=image_path.read_bytes(),
                mime_type=mime_type,
            ),
            config=types.GenerateVideosConfig(**config_kwargs),
        )
        while not operation.done:
            time.sleep(10)
            operation = self.client.operations.get(operation)
        if operation.error:
            raise RuntimeError(
                f"S{shot.shot_number:03d}: Veo failed: {operation.error}"
            )
        response = operation.response
        generated = response.generated_videos if response else None
        if not generated or not generated[0].video:
            raise RuntimeError(
                f"S{shot.shot_number:03d}: Veo returned no video."
            )
        video_bytes = self.client.files.download(file=generated[0].video)
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(video_bytes)
        if metadata_path:
            metadata_path.parent.mkdir(parents=True, exist_ok=True)
            metadata_path.write_text(
                json.dumps(
                    {
                        "shot_number": shot.shot_number,
                        "model": self.model,
                        "operation_name": operation.name,
                        "status": "completed",
                        "requested_source_duration": f"{source_duration}s",
                        "normalized_duration": (
                            f"{self.profile.media.shot_duration_seconds}s"
                        ),
                        "aspect_ratio": self.profile.media.aspect_ratio,
                        "seed": None,
                        "seed_note": (
                            "Gemini Developer API does not accept Veo seed; "
                            "the deterministic seed is intentionally omitted."
                        ),
                        "identity_reference_mode": (
                            "veo_asset_reference_images"
                            if attached_references
                            else "first_frame_only_model_limitation"
                            if selected_references
                            else "first_frame_only"
                        ),
                        "character_lock": _identity_metadata(character_lock),
                    },
                    ensure_ascii=False,
                    indent=2,
                ),
                encoding="utf-8",
            )
        return destination


def _run_ffmpeg(arguments: list[str]) -> subprocess.CompletedProcess[str]:
    command = [get_ffmpeg_exe(), "-hide_banner", "-y", *arguments]
    result = subprocess.run(
        command,
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        check=False,
    )
    if result.returncode:
        raise RuntimeError(
            "ffmpeg failed:\n" + "\n".join(result.stderr.splitlines()[-30:])
        )
    return result


def inspect_video(path: Path) -> dict[str, Any]:
    result = subprocess.run(
        [get_ffmpeg_exe(), "-hide_banner", "-i", str(path)],
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        check=False,
    )
    text = result.stderr
    duration_match = re.search(
        r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)",
        text,
    )
    video_match = re.search(
        r"Video:.*?(\d{2,5})x(\d{2,5}).*?(\d+(?:\.\d+)?)\s*fps",
        text,
    )
    rate_match = re.search(r"Video:.*?(\d+(?:\.\d+)?)\s*tbr", text)
    duration = None
    if duration_match:
        duration = (
            int(duration_match.group(1)) * 3600
            + int(duration_match.group(2)) * 60
            + float(duration_match.group(3))
        )
    return {
        "path": path.name,
        "duration_seconds": duration,
        "width": int(video_match.group(1)) if video_match else None,
        "height": int(video_match.group(2)) if video_match else None,
        "fps": (
            float(rate_match.group(1))
            if rate_match
            else float(video_match.group(3))
            if video_match
            else None
        ),
        "has_audio": "Audio:" in text,
        "bytes": path.stat().st_size,
    }


def standardize_clip(
    source: Path,
    destination: Path,
    media: MediaContract,
) -> Path:
    metadata = inspect_video(source)
    destination.parent.mkdir(parents=True, exist_ok=True)
    frame_count = media.shot_duration_seconds * media.frames_per_second
    video_filter = (
        f"scale={media.width}:{media.height}:force_original_aspect_ratio=decrease,"
        f"pad={media.width}:{media.height}:(ow-iw)/2:(oh-ih)/2,"
        f"tpad=stop_mode=clone:stop_duration={media.shot_duration_seconds},"
        f"fps={media.frames_per_second},trim=end_frame={frame_count},"
        f"setpts=N/({media.frames_per_second}*TB),format=yuv420p"
    )
    if metadata["has_audio"]:
        arguments = [
            "-i",
            str(source),
            "-map",
            "0:v:0",
            "-map",
            "0:a:0",
            "-vf",
            video_filter,
            "-af",
            "apad,atrim=duration="
            f"{media.shot_duration_seconds},"
            "asetpts=PTS-STARTPTS,aresample=48000",
        ]
    else:
        arguments = [
            "-i",
            str(source),
            "-f",
            "lavfi",
            "-i",
            "anullsrc=channel_layout=stereo:sample_rate=48000",
            "-map",
            "0:v:0",
            "-map",
            "1:a:0",
            "-vf",
            video_filter,
            "-af",
            f"atrim=duration={media.shot_duration_seconds},asetpts=PTS-STARTPTS",
        ]
    arguments.extend(
        [
            "-t",
            str(media.shot_duration_seconds),
            "-c:v",
            "libx264",
            "-preset",
            "medium",
            "-crf",
            "18",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-movflags",
            "+faststart",
            str(destination),
        ]
    )
    _run_ffmpeg(arguments)
    return destination


def extract_nine_frames(
    clip: Path,
    destination_dir: Path,
    media: MediaContract,
) -> list[Path]:
    destination_dir.mkdir(parents=True, exist_ok=True)
    pattern = destination_dir / "frame_%02d.jpg"
    _run_ffmpeg(
        [
            "-i",
            str(clip),
            "-vf",
            f"fps={media.review_frames_per_second},"
            f"scale={media.width // 2}:{media.height // 2}",
            "-frames:v",
            str(media.review_frame_count),
            "-q:v",
            "2",
            str(pattern),
        ]
    )
    frames = sorted(destination_dir.glob("frame_*.jpg"))
    if len(frames) != media.review_frame_count:
        raise RuntimeError(
            f"Expected {media.review_frame_count} frames from {clip.name}, "
            f"but extracted {len(frames)}."
        )
    return frames


def extract_final_frame(
    clip: Path,
    destination: Path,
    media: MediaContract,
) -> Path:
    destination.parent.mkdir(parents=True, exist_ok=True)
    _run_ffmpeg(
        [
            "-sseof",
            "-0.05",
            "-i",
            str(clip),
            "-frames:v",
            "1",
            "-vf",
            f"scale={media.width}:{media.height}",
            str(destination),
        ]
    )
    if not destination.is_file():
        raise RuntimeError(f"Could not extract final frame from {clip}")
    return destination


def render_video_shots(
    storyboard: Storyboard,
    run_dir: Path,
    profile: ProductionProfile,
    model: str | None = None,
    limit: int | None = None,
    character_registry_dir: Path | None = CHARACTER_REGISTRY_DIR,
) -> list[Path]:
    registry = CharacterRegistry.load_optional(character_registry_dir)
    if registry:
        issues = registry.validate()
        if issues:
            raise RuntimeError("Invalid character registry:\n" + "\n".join(issues))
    require_resolved_character_names(
        registry,
        [name for shot in storyboard.shots for name in shot.characters],
    )
    service = VideoService(profile=profile, model=model)
    locks_by_shot: dict[int, CharacterLock] = {}
    if registry:
        reference_limit = profile.video.maximum_character_reference_images
        lock_manifest: list[dict[str, Any]] = []
        for shot in storyboard.shots:
            shot_text = " ".join(
                [
                    shot.title,
                    shot.scene_description,
                    shot.action,
                    shot.emotion,
                    shot.continuity,
                    shot.video_prompt,
                ]
            )
            lock = registry.build_lock(
                shot.characters,
                shot_text,
                reference_limit=reference_limit,
            )
            locks_by_shot[shot.shot_number] = lock
            lock_manifest.append(
                {
                    "shot_number": shot.shot_number,
                    "requested_characters": list(lock.requested_names),
                    "resolved_characters": [
                        {
                            "id": record.id,
                            "name_ja": record.name_ja,
                            "version": record.version,
                        }
                        for record in lock.records
                    ],
                    "unresolved_characters": list(lock.unresolved_names),
                    "references": [
                        {
                            "character_id": selected.character_id,
                            "role": selected.role,
                            "path": str(
                                selected.path.relative_to(registry.root)
                            ).replace("\\", "/"),
                        }
                        for selected in lock.references
                    ],
                    "motions": [
                        {
                            "character_id": selected.character_id,
                            "motion_id": selected.motion_id,
                            "clip": str(
                                selected.clip_path.relative_to(registry.root)
                            ).replace("\\", "/"),
                            "keyframes": [
                                str(path.relative_to(registry.root)).replace(
                                    "\\", "/"
                                )
                                for path in selected.keyframe_paths
                            ],
                            "direct_video_input": False,
                            "guidance_mode": selected.guidance_mode,
                        }
                        for selected in lock.motions
                    ],
                    "identity_prompt": lock.prompt,
                }
            )
        (run_dir / "character_locks.json").write_text(
            json.dumps(
                {
                    "schema_version": "1.0",
                    "video_model": service.model,
                    "registry_lock": registry.lock_data(),
                    "shots": lock_manifest,
                },
                ensure_ascii=False,
                indent=2,
            )
            + "\n",
            encoding="utf-8",
        )
        registry.write_lock_file()
    generated = 0
    completed: list[Path] = []
    for shot in storyboard.shots:
        image_path = run_dir / "images" / f"shot_{shot.shot_number:03d}.png"
        raw_path = run_dir / "video" / "raw" / f"shot_{shot.shot_number:03d}.mp4"
        clip_path = run_dir / "video" / "clips" / f"shot_{shot.shot_number:03d}.mp4"
        metadata_path = (
            run_dir / "video" / "metadata" / f"shot_{shot.shot_number:03d}.json"
        )
        if clip_path.exists():
            print(f"[skip] S{shot.shot_number:03d}: video already exists")
            completed.append(clip_path)
            continue
        if limit is not None and generated >= limit:
            break
        starting_frame_path = image_path
        if shot.continuity_start_mode == "previous_final_frame":
            if shot.shot_number <= 1:
                raise ValueError(
                    "S001 cannot use continuity_start_mode=previous_final_frame"
                )
            previous_clip = (
                run_dir
                / "video"
                / "clips"
                / f"shot_{shot.shot_number - 1:03d}.mp4"
            )
            if not previous_clip.is_file():
                raise FileNotFoundError(
                    f"Missing previous clip for continuity: {previous_clip}"
                )
            starting_frame_path = extract_final_frame(
                previous_clip,
                run_dir
                / "video"
                / "continuity"
                / f"shot_{shot.shot_number:03d}_first_frame.png",
                profile.media,
            )
            print(
                f"[continuity] S{shot.shot_number:03d}: "
                f"starting from S{shot.shot_number - 1:03d} final frame"
            )
        elif not image_path.exists():
            raise FileNotFoundError(f"Missing main image: {image_path}")
        character_lock = locks_by_shot.get(shot.shot_number)
        if character_lock and character_lock.records:
            locked = ", ".join(
                f"{record.name_ja}/{record.version}"
                for record in character_lock.records
            )
            print(f"[identity-lock] S{shot.shot_number:03d}: {locked}")
        print(
            f"[video] S{shot.shot_number:03d}: generating "
            f"{profile.media.shot_duration_seconds}-second clip"
        )
        service.create_clip(
            shot,
            starting_frame_path,
            raw_path,
            metadata_path,
            character_lock,
        )
        standardize_clip(raw_path, clip_path, profile.media)
        extract_nine_frames(
            clip_path,
            run_dir / "frames" / f"shot_{shot.shot_number:03d}",
            profile.media,
        )
        metadata = inspect_video(clip_path)
        metadata_path.write_text(
            json.dumps(
                {
                    **json.loads(metadata_path.read_text(encoding="utf-8")),
                    "continuity_start_mode": shot.continuity_start_mode,
                    "starting_frame": starting_frame_path.relative_to(
                        run_dir
                    ).as_posix(),
                    "normalized_output": metadata,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        print(
            f"[done] S{shot.shot_number:03d}: "
            f"{metadata['duration_seconds']:.2f}s, "
            f"{metadata['width']}x{metadata['height']}, "
            f"{metadata['fps']}fps"
        )
        completed.append(clip_path)
        generated += 1
    return completed


def concatenate_clips(
    storyboard: Storyboard,
    run_dir: Path,
    destination: Path,
    media: MediaContract,
) -> Path:
    clips = [
        run_dir / "video" / "clips" / f"shot_{shot.shot_number:03d}.mp4"
        for shot in storyboard.shots
    ]
    missing = [path for path in clips if not path.exists()]
    if missing:
        raise FileNotFoundError(
            "Missing generated clips: " + ", ".join(path.name for path in missing)
        )
    list_path = run_dir / "video" / "concat.txt"
    list_path.parent.mkdir(parents=True, exist_ok=True)
    list_path.write_text(
        "".join(
            f"file '{path.resolve().as_posix().replace(chr(39), chr(39) * 2)}'\n"
            for path in clips
        ),
        encoding="utf-8",
    )
    destination.parent.mkdir(parents=True, exist_ok=True)
    total_frames = len(clips) * media.shot_duration_seconds * media.frames_per_second
    total_duration = len(clips) * media.shot_duration_seconds
    _run_ffmpeg(
        [
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(list_path),
            "-vf",
            f"scale={media.width}:{media.height}:"
            "force_original_aspect_ratio=decrease,"
            f"pad={media.width}:{media.height}:(ow-iw)/2:(oh-ih)/2,"
            f"fps={media.frames_per_second},trim=end_frame={total_frames},"
            f"setpts=N/({media.frames_per_second}*TB),format=yuv420p",
            "-af",
            f"atrim=duration={total_duration},"
            "asetpts=PTS-STARTPTS,aresample=48000",
            "-t",
            str(total_duration),
            "-c:v",
            "libx264",
            "-preset",
            "medium",
            "-crf",
            "18",
            "-c:a",
            "aac",
            "-b:a",
            "192k",
            "-movflags",
            "+faststart",
            str(destination),
        ]
    )
    return destination
