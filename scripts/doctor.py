from __future__ import annotations

import argparse
import importlib.metadata
import importlib.util
import json
import os
import subprocess
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from video_storyboard.knowledge import (  # noqa: E402
    ensure_production_allowed,
    load_builtin_guidance,
)

MINIMUM_PYTHON = (3, 11)
PROJECT_DISTRIBUTION = "nijiunit-ai-agent-video-studio"
DEPENDENCIES = {
    "google.genai": "google-genai",
    "openpyxl": "openpyxl",
    "PIL": "Pillow",
    "pydantic": "pydantic",
    "dotenv": "python-dotenv",
    "imageio_ffmpeg": "imageio-ffmpeg",
}
MODEL_ROLES = ("story", "image", "video", "tts", "asr", "tutorial")


@dataclass(frozen=True)
class Check:
    name: str
    status: str
    detail: str


def read_api_key(env_path: Path, environ: dict[str, str] | None = None) -> str:
    environment = os.environ if environ is None else environ
    environment_value = environment.get("GEMINI_API_KEY", "").strip()
    if environment_value:
        return environment_value
    if not env_path.is_file():
        return ""
    for raw_line in env_path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, value = line.split("=", 1)
        if name.strip() != "GEMINI_API_KEY":
            continue
        return value.strip().strip('"').strip("'")
    return ""


def read_env_setting(
    env_path: Path,
    name: str,
    default: str,
    environ: dict[str, str] | None = None,
) -> str:
    environment = os.environ if environ is None else environ
    environment_value = environment.get(name, "").strip()
    if environment_value:
        return environment_value
    if env_path.is_file():
        for raw_line in env_path.read_text(
            encoding="utf-8", errors="replace"
        ).splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            setting_name, value = line.split("=", 1)
            if setting_name.strip() == name:
                return value.strip().strip('"').strip("'") or default
    return default


def configured_models(
    env_path: Path,
    defaults: dict[str, str] | None = None,
    environ: dict[str, str] | None = None,
) -> dict[str, str]:
    defaults = defaults or {}
    values = {
        role: read_env_setting(
            env_path,
            f"{role.upper()}_MODEL",
            defaults.get(role, ""),
            environ=environ,
        )
        for role in MODEL_ROLES
    }
    return {role: model for role, model in values.items() if model}


def api_key_is_set(env_path: Path, environ: dict[str, str] | None = None) -> bool:
    return bool(read_api_key(env_path, environ=environ))


def _model_identifier(model: object) -> str:
    name = (
        model.get("name", "") if isinstance(model, dict) else getattr(model, "name", "")
    )
    return str(name).removeprefix("models/")


def api_key_online_checks(
    api_key: str,
    required_models: dict[str, str],
    client_factory=None,
) -> list[Check]:
    if not api_key:
        return [Check("Gemini authentication", "FAIL", "API key is not configured")]
    client = None
    try:
        if client_factory is None:
            from google import genai

            client_factory = genai.Client
        client = client_factory(api_key=api_key)
        models = client.models.list(config={"page_size": 100})
        available = {_model_identifier(model) for model in models}
        missing = {
            role: model
            for role, model in required_models.items()
            if model not in available
        }
        checks = [
            Check(
                "Gemini authentication",
                "PASS",
                "provider accepted the key; no media was generated",
            )
        ]
        if missing:
            details = ", ".join(f"{role}={model}" for role, model in missing.items())
            checks.append(
                Check(
                    "configured Gemini models",
                    "FAIL",
                    f"not present in the model catalog: {details}",
                )
            )
        else:
            details = ", ".join(
                f"{role}={model}" for role, model in required_models.items()
            )
            checks.append(
                Check(
                    "configured Gemini models",
                    "PASS",
                    f"present in the model catalog: {details}",
                )
            )
        return checks
    except Exception as error:  # noqa: BLE001
        return [
            Check(
                "Gemini authentication",
                "FAIL",
                f"provider rejected or could not verify the key ({type(error).__name__}); "
                "the secret was not displayed",
            )
        ]
    finally:
        if client is not None:
            try:
                client.close()
            except Exception:  # noqa: BLE001
                pass


def dependency_check(module: str, distribution: str) -> Check:
    try:
        available = importlib.util.find_spec(module) is not None
    except (ImportError, ModuleNotFoundError, ValueError):
        available = False
    if not available:
        return Check(distribution, "FAIL", f"Python module {module} is missing")
    try:
        version = importlib.metadata.version(distribution)
    except importlib.metadata.PackageNotFoundError:
        version = "installed"
    return Check(distribution, "PASS", version)


def project_install_check() -> Check:
    try:
        version = importlib.metadata.version(PROJECT_DISTRIBUTION)
    except importlib.metadata.PackageNotFoundError:
        return Check(
            "project",
            "FAIL",
            "project is not installed; run scripts/setup.ps1 or scripts/setup.sh",
        )
    return Check("project", "PASS", f"editable package {version}")


def ffmpeg_check() -> Check:
    try:
        from imageio_ffmpeg import get_ffmpeg_exe

        executable = Path(get_ffmpeg_exe())
        if not executable.is_file():
            return Check("FFmpeg", "FAIL", "bundled executable is missing")
        result = subprocess.run(
            [str(executable), "-version"],
            text=True,
            encoding="utf-8",
            errors="replace",
            capture_output=True,
            check=False,
            timeout=10,
        )
        if result.returncode:
            return Check("FFmpeg", "FAIL", "executable did not start")
        first_line = result.stdout.splitlines()[0] if result.stdout else "available"
        return Check("FFmpeg", "PASS", first_line)
    except Exception as error:  # noqa: BLE001
        return Check("FFmpeg", "FAIL", f"{type(error).__name__}: {error}")


def spreadsheet_viewer_check() -> Check:
    try:
        from video_storyboard.artifacts import detect_spreadsheet_viewers

        viewers = detect_spreadsheet_viewers()
    except Exception as error:  # noqa: BLE001
        return Check(
            "spreadsheet viewer",
            "WARN",
            f"detection failed ({type(error).__name__}); local HTML review is available",
        )
    if not viewers:
        return Check(
            "spreadsheet viewer",
            "WARN",
            "Excel/LibreOffice/Numbers not found; local HTML review will be used",
        )
    names = ", ".join(dict.fromkeys(viewer.name for viewer in viewers))
    return Check("spreadsheet viewer", "PASS", names)


def collect_checks(
    require_api_key: bool = False,
    verify_api_key_online: bool = False,
) -> list[Check]:
    version = sys.version_info[:3]
    python_ok = version >= MINIMUM_PYTHON
    checks = [
        Check(
            "Python",
            "PASS" if python_ok else "FAIL",
            ".".join(str(part) for part in version),
        ),
        project_install_check(),
    ]
    checks.extend(
        dependency_check(module, distribution)
        for module, distribution in DEPENDENCIES.items()
    )
    checks.extend([ffmpeg_check(), spreadsheet_viewer_check()])

    guidance = None
    try:
        guidance = load_builtin_guidance()
        ensure_production_allowed(guidance, "ja")
        checks.append(
            Check(
                "bundled production defaults",
                "PASS",
                f"verified version {guidance.manifest.knowledge_version}",
            )
        )
    except Exception:
        checks.append(
            Check(
                "bundled production defaults",
                "FAIL",
                "not available; update or reinstall this repository",
            )
        )

    api_key = read_api_key(ROOT / ".env")
    key_set = bool(api_key)
    checks.append(
        Check(
            "GEMINI_API_KEY",
            "PASS" if key_set else ("FAIL" if require_api_key else "WARN"),
            (
                "configured"
                if key_set
                else "not configured; open the local page with scripts/open_setup.py"
            ),
        )
    )
    if verify_api_key_online and key_set and guidance:
        profile_models = guidance.profile.models.model_dump()
        checks.extend(
            api_key_online_checks(
                api_key,
                configured_models(ROOT / ".env", defaults=profile_models),
            )
        )
    output_dir = ROOT / "output"
    checks.append(
        Check(
            "output directory",
            "PASS"
            if output_dir.is_dir() and os.access(output_dir, os.W_OK)
            else "FAIL",
            "available" if output_dir.is_dir() else "missing",
        )
    )
    return checks


def readiness(checks: list[Check], online_verification_requested: bool = False) -> str:
    if any(item.status == "FAIL" for item in checks):
        return "NOT READY"
    api_key_missing = any(
        item.name == "GEMINI_API_KEY" and item.status == "WARN"
        for item in checks
    )
    if api_key_missing:
        return "LOCAL READY (Google API setup required)"
    if not online_verification_requested:
        return "LOCAL READY (Google API configured; online verification not run)"
    required_online_checks = {"Gemini authentication", "configured Gemini models"}
    passed_online_checks = {
        item.name
        for item in checks
        if item.name in required_online_checks and item.status == "PASS"
    }
    if passed_online_checks != required_online_checks:
        return "NOT READY"
    return "READY FOR GENERATION (paid generation not tested)"


def main() -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Diagnose the local AI Agent Video Studio installation. "
            "No API is called unless --verify-api-key-online is supplied."
        )
    )
    parser.add_argument(
        "--json", action="store_true", help="print machine-readable JSON"
    )
    parser.add_argument(
        "--require-api-key",
        action="store_true",
        help="treat a missing GEMINI_API_KEY as a failure",
    )
    parser.add_argument(
        "--verify-api-key-online",
        action="store_true",
        help="make one non-generation provider request to verify authentication",
    )
    args = parser.parse_args()
    checks = collect_checks(
        require_api_key=args.require_api_key or args.verify_api_key_online,
        verify_api_key_online=args.verify_api_key_online,
    )
    state = readiness(
        checks,
        online_verification_requested=args.verify_api_key_online,
    )

    if args.json:
        print(
            json.dumps(
                {"readiness": state, "checks": [asdict(item) for item in checks]},
                ensure_ascii=False,
                indent=2,
            )
        )
    else:
        print("AI Agent Video Studio doctor")
        for item in checks:
            print(f"[{item.status:4}] {item.name}: {item.detail}")
        print(f"\n{state}")
    return int(state == "NOT READY")


if __name__ == "__main__":
    raise SystemExit(main())
