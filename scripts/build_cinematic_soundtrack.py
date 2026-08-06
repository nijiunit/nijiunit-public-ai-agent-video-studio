from __future__ import annotations

import argparse
import json
import math
import random
import shutil
import struct
import subprocess
import wave
from datetime import UTC, datetime
from pathlib import Path

from imageio_ffmpeg import get_ffmpeg_exe

FFMPEG = get_ffmpeg_exe()
SAMPLE_RATE = 48_000
DURATION_SECONDS = 30.0
TARGET_LUFS = -16.0
TARGET_TRUE_PEAK_DB = -1.5
TARGET_LRA = 24.0


def clamp(value: float, minimum: float, maximum: float) -> float:
    return min(maximum, max(minimum, value))


def smoothstep(edge0: float, edge1: float, value: float) -> float:
    if edge0 == edge1:
        return float(value >= edge1)
    position = clamp((value - edge0) / (edge1 - edge0), 0.0, 1.0)
    return position * position * (3.0 - 2.0 * position)


def pulse(time: float, start: float, attack: float, hold: float, release: float) -> float:
    if time < start or time >= start + attack + hold + release:
        return 0.0
    if time < start + attack:
        return smoothstep(start, start + attack, time)
    if time < start + attack + hold:
        return 1.0
    return 1.0 - smoothstep(
        start + attack + hold,
        start + attack + hold + release,
        time,
    )


def speech_duck(time: float) -> float:
    first = pulse(time, 5.95, 0.22, 2.50, 0.32)
    second = pulse(time, 27.40, 0.22, 1.85, 0.35)
    return 1.0 - 0.42 * max(first, second)


def write_ambience(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    rng = random.Random(260806)
    slow_left = 0.0
    slow_right = 0.0
    fast_left = 0.0
    fast_right = 0.0
    previous_left = 0.0
    previous_right = 0.0

    with wave.open(str(path), "wb") as output:
        output.setnchannels(2)
        output.setsampwidth(2)
        output.setframerate(SAMPLE_RATE)
        block = bytearray()

        for index in range(int(DURATION_SECONDS * SAMPLE_RATE)):
            time = index / SAMPLE_RATE
            random_left = rng.uniform(-1.0, 1.0)
            random_right = rng.uniform(-1.0, 1.0)
            slow_left += 0.0011 * (random_left - slow_left)
            slow_right += 0.0011 * (random_right - slow_right)
            fast_left += 0.055 * (random_left - fast_left)
            fast_right += 0.055 * (random_right - fast_right)
            high_left = random_left - previous_left
            high_right = random_right - previous_right
            previous_left = random_left
            previous_right = random_right

            # A warm, continuous film bed: audible from frame one, but restrained.
            pad = (
                0.036 * math.sin(math.tau * 55.0 * time)
                + 0.024 * math.sin(math.tau * 82.5 * time + 0.7)
                + 0.0135 * math.sin(math.tau * 110.0 * time + 1.4)
            )
            pad *= 0.88 + 0.12 * math.sin(math.tau * 0.07 * time)
            mechanism = 0.009 * math.sin(math.tau * 143.0 * time)
            mechanism *= 1.0 - 0.65 * smoothstep(12.0, 16.0, time)
            space_air = 0.012 * (slow_left + slow_right)

            # Wind starts before the dive, then becomes fast and bright.
            wind_amount = 0.020 + 0.150 * smoothstep(8.5, 18.5, time)
            wind_amount *= 1.0 - 0.80 * smoothstep(24.0, 28.0, time)
            wind_left = wind_amount * (0.70 * fast_left + 0.30 * high_left)
            wind_right = wind_amount * (0.70 * fast_right + 0.30 * high_right)

            # The waterfall is heard in the distance, rushes past at 21-24 s,
            # then remains softly in the final landscape.
            waterfall = 0.032 * smoothstep(14.3, 18.0, time)
            waterfall += 0.260 * pulse(time, 19.0, 2.2, 1.25, 2.1)
            waterfall += 0.020 * smoothstep(25.0, 27.0, time)
            waterfall_noise_left = 0.64 * random_left + 1.65 * fast_left
            waterfall_noise_right = 0.64 * random_right + 1.65 * fast_right
            pass_position = smoothstep(20.5, 23.8, time)
            waterfall_left = waterfall * (1.12 - 0.46 * pass_position)
            waterfall_right = waterfall * (0.66 + 0.46 * pass_position)

            # River and grass give the low flight and landing a physical place.
            river_amount = 0.015 * smoothstep(17.0, 20.0, time)
            river_amount += 0.012 * smoothstep(25.0, 27.0, time)
            grass_amount = 0.030 * pulse(time, 23.5, 0.7, 2.3, 1.1)
            grass_left = grass_amount * high_left
            grass_right = grass_amount * high_right

            # Lux has a quiet harmonic identity plus two short light gestures.
            lux_hum = 0.006 * math.sin(math.tau * 329.63 * time)
            lux_hum += 0.004 * math.sin(math.tau * 494.0 * time + 0.3)
            chime_envelope = pulse(time, 5.80, 0.02, 0.03, 0.70)
            chime_envelope += 0.72 * pulse(time, 29.15, 0.02, 0.03, 0.65)
            chime = chime_envelope * (
                0.032 * math.sin(math.tau * 659.25 * time)
                + 0.020 * math.sin(math.tau * 987.77 * time)
            )

            # A soft two-part landing impact at the beginning of the last shot.
            landing = pulse(time, 27.32, 0.015, 0.02, 0.32)
            landing_tone = landing * (
                0.075 * math.sin(math.tau * 74.0 * time)
                + 0.026 * math.sin(math.tau * 148.0 * time)
            )

            duck = speech_duck(time)
            common = (pad + mechanism + space_air + lux_hum + chime) * duck
            left = common + wind_left + waterfall_left * waterfall_noise_left
            right = common + wind_right + waterfall_right * waterfall_noise_right
            left += river_amount * fast_left + grass_left + landing_tone
            right += river_amount * fast_right + grass_right + landing_tone

            left = math.tanh(left * 1.12) * 0.82
            right = math.tanh(right * 1.12) * 0.82
            block.extend(
                struct.pack(
                    "<hh",
                    int(clamp(left, -1.0, 1.0) * 32767),
                    int(clamp(right, -1.0, 1.0) * 32767),
                )
            )
            if len(block) >= 16_384:
                output.writeframesraw(block)
                block.clear()
        if block:
            output.writeframesraw(block)


def run_ffmpeg(arguments: list[str], *, capture: bool = False) -> str:
    result = subprocess.run(
        [FFMPEG, "-hide_banner", "-y", *arguments],
        text=True,
        encoding="utf-8",
        errors="replace",
        capture_output=True,
        check=False,
    )
    if result.returncode:
        raise RuntimeError("\n".join(result.stderr.splitlines()[-80:]))
    if capture:
        return result.stderr
    return ""


def loudness_analysis(audio: Path) -> dict[str, str]:
    stderr = run_ffmpeg(
        [
            "-i",
            str(audio),
            "-af",
            (
                f"loudnorm=I={TARGET_LUFS}:TP={TARGET_TRUE_PEAK_DB}:"
                f"LRA={TARGET_LRA}:print_format=json"
            ),
            "-f",
            "null",
            "NUL",
        ],
        capture=True,
    )
    start = stderr.rfind("{")
    end = stderr.rfind("}")
    if start < 0 or end < start:
        raise RuntimeError("FFmpeg did not return loudness analysis JSON")
    return json.loads(stderr[start : end + 1])


def mix_dialogue(
    ambience: Path,
    lux_tts: Path,
    mio_tts: Path,
    output: Path,
) -> dict[str, str]:
    pre_normalized = output.with_name(f"{output.stem}_pre_normalized.wav")
    run_ffmpeg(
        [
            "-i",
            str(ambience),
            "-i",
            str(lux_tts),
            "-i",
            str(mio_tts),
            "-filter_complex",
            (
                "[0:a]volume=1.0[bed];"
                "[1:a]highpass=f=75,lowpass=f=11000,"
                "acompressor=threshold=-22dB:ratio=2.7:attack=7:release=110:makeup=3,"
                "volume=1.16,adelay=6160:all=1,apad,atrim=duration=30,"
                "pan=stereo|c0=c0|c1=c0[lux];"
                "[2:a]highpass=f=75,lowpass=f=11000,"
                "acompressor=threshold=-22dB:ratio=2.7:attack=7:release=110:makeup=3,"
                "volume=1.16,adelay=27620:all=1,apad,atrim=duration=30,"
                "pan=stereo|c0=c0|c1=c0[mio];"
                "[bed][lux][mio]amix=inputs=3:duration=first:normalize=0,"
                "acompressor=threshold=-15dB:ratio=1.7:attack=15:release=180:makeup=1.5,"
                "alimiter=limit=0.95,atrim=duration=30[out]"
            ),
            "-map",
            "[out]",
            "-ar",
            str(SAMPLE_RATE),
            "-ac",
            "2",
            "-c:a",
            "pcm_s16le",
            str(pre_normalized),
        ]
    )
    measured = loudness_analysis(pre_normalized)
    normalizer = (
        f"loudnorm=I={TARGET_LUFS}:TP={TARGET_TRUE_PEAK_DB}:LRA={TARGET_LRA}:"
        f"measured_I={measured['input_i']}:"
        f"measured_LRA={measured['input_lra']}:"
        f"measured_TP={measured['input_tp']}:"
        f"measured_thresh={measured['input_thresh']}:"
        f"offset={measured['target_offset']}:linear=true:print_format=summary"
    )
    run_ffmpeg(
        [
            "-i",
            str(pre_normalized),
            "-af",
            normalizer,
            "-ar",
            str(SAMPLE_RATE),
            "-ac",
            "2",
            "-c:a",
            "pcm_s16le",
            str(output),
        ]
    )
    return measured


def mux(video: Path, soundtrack: Path, output: Path) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    run_ffmpeg(
        [
            "-i",
            str(video),
            "-i",
            str(soundtrack),
            "-map",
            "0:v:0",
            "-map",
            "1:a:0",
            "-t",
            "30",
            "-c:v",
            "copy",
            "-c:a",
            "aac",
            "-b:a",
            "256k",
            "-ar",
            str(SAMPLE_RATE),
            "-ac",
            "2",
            "-movflags",
            "+faststart",
            str(output),
        ]
    )


def volume_stats(audio: Path, start: float, duration: float) -> dict[str, float | None]:
    stderr = run_ffmpeg(
        [
            "-ss",
            str(start),
            "-t",
            str(duration),
            "-i",
            str(audio),
            "-af",
            "volumedetect",
            "-f",
            "null",
            "NUL",
        ],
        capture=True,
    )
    values: dict[str, float | None] = {"mean_volume_db": None, "max_volume_db": None}
    for line in stderr.splitlines():
        for source, target in (
            ("mean_volume:", "mean_volume_db"),
            ("max_volume:", "max_volume_db"),
        ):
            if source in line:
                values[target] = float(line.split(source, 1)[1].split("dB", 1)[0].strip())
    return values


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Build the deterministic 30-second Rainbow Waterfall cinematic mix."
    )
    parser.add_argument("--run-dir", required=True, type=Path)
    parser.add_argument("--input-video", required=True, type=Path)
    parser.add_argument("--output-video", required=True, type=Path)
    args = parser.parse_args()

    run_dir = args.run_dir.resolve()
    input_video = args.input_video.resolve()
    output_video = args.output_video.resolve()
    lux_tts = run_dir / "audio" / "tts" / "shot_003.wav"
    mio_tts = run_dir / "audio" / "tts" / "shot_010.wav"
    for required in (input_video, lux_tts, mio_tts):
        if not required.is_file():
            raise FileNotFoundError(required)

    audio_dir = run_dir / "audio"
    ambience = audio_dir / "cinematic_ambience.wav"
    soundtrack = audio_dir / "cinematic_mix.wav"
    write_ambience(ambience)
    loudness_first_pass = mix_dialogue(ambience, lux_tts, mio_tts, soundtrack)

    backup = run_dir / "rejected" / "before_cinematic_soundtrack" / input_video.name
    backup.parent.mkdir(parents=True, exist_ok=True)
    if not backup.exists():
        shutil.copy2(input_video, backup)
    mux(input_video, soundtrack, output_video)

    sections = []
    for name, start, duration in (
        ("space_opening", 0.0, 6.0),
        ("lux_dialogue", 6.0, 3.0),
        ("descent", 15.0, 6.0),
        ("waterfall_pass", 21.0, 3.0),
        ("low_flight", 24.0, 3.0),
        ("landing_and_mio_dialogue", 27.0, 3.0),
    ):
        sections.append(
            {
                "name": name,
                "start_seconds": start,
                "duration_seconds": duration,
                **volume_stats(soundtrack, start, duration),
            }
        )

    try:
        output_reference = output_video.relative_to(run_dir).as_posix()
    except ValueError:
        output_reference = output_video.name

    report = {
        "created_at": datetime.now(UTC).isoformat(),
        "duration_seconds": DURATION_SECONDS,
        "sample_rate_hz": SAMPLE_RATE,
        "channels": 2,
        "target_integrated_lufs": TARGET_LUFS,
        "target_true_peak_db": TARGET_TRUE_PEAK_DB,
        "target_loudness_range_lu": TARGET_LRA,
        "loudness_first_pass": loudness_first_pass,
        "loudness_final_pass": loudness_analysis(soundtrack),
        "dialogue_timing": {
            "lux_start_seconds": 6.16,
            "mio_start_seconds": 27.62,
        },
        "design": [
            "continuous cinematic pad and character resonance from frame one",
            "wind rises through atmospheric entry and cloud dive",
            "river and waterfall approach grows from 15 seconds",
            "waterfall peaks and pans left-to-right from 21 to 24 seconds",
            "grass-level airflow and landing impact lead into the final line",
        ],
        "video_api_audio_used": False,
        "third_party_music_or_sfx_used": False,
        "sections": sections,
        "output_video": output_reference,
    }
    report_path = audio_dir / "cinematic_mix_report.json"
    report_path.write_text(
        json.dumps(report, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )
    print(report_path)
    print(output_video)


if __name__ == "__main__":
    main()
