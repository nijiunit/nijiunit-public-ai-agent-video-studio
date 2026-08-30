from __future__ import annotations

import os
import platform
import shutil
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Callable


@dataclass(frozen=True)
class SpreadsheetViewer:
    name: str
    kind: str
    executable: str


@dataclass(frozen=True)
class RevealResult:
    opened: bool
    selected_path: Path
    command: tuple[str, ...]
    detail: str
    selected: bool = False


DIRECT_VIEW_EXTENSIONS = {
    ".gif",
    ".htm",
    ".html",
    ".jpeg",
    ".jpg",
    ".m4v",
    ".mov",
    ".mp4",
    ".pdf",
    ".png",
    ".webm",
    ".webp",
}


def _revision_number(path: Path, base_stem: str) -> int | None:
    if path.stem == base_stem:
        return 1
    prefix = f"{base_stem}_r"
    if not path.stem.startswith(prefix):
        return None
    suffix = path.stem.removeprefix(prefix)
    return int(suffix) if len(suffix) == 3 and suffix.isdigit() else None


def _revision_candidates(directory: Path, base_stem: str) -> list[Path]:
    candidates: list[tuple[int, Path]] = []
    if directory.is_dir():
        for path in directory.glob(f"{base_stem}*.xlsx"):
            revision = _revision_number(path, base_stem)
            if revision is not None:
                candidates.append((revision, path))
    return [path for _, path in sorted(candidates, key=lambda item: item[0])]


def current_storyboard_workbook(run_dir: Path) -> Path:
    """Return the newest storyboard workbook, including legacy run layouts."""
    run_dir = run_dir.resolve()
    base_stem = f"storyboard_{run_dir.name}"
    modern = _revision_candidates(run_dir / "review", base_stem)
    if modern:
        return modern[-1]
    legacy = run_dir / f"{base_stem}.xlsx"
    if legacy.is_file():
        return legacy
    return run_dir / "review" / f"{base_stem}.xlsx"


def next_storyboard_workbook(run_dir: Path) -> Path:
    """Choose a new workbook filename without overwriting a reviewed version."""
    run_dir = run_dir.resolve()
    base_stem = f"storyboard_{run_dir.name}"
    review_dir = run_dir / "review"
    modern = _revision_candidates(review_dir, base_stem)
    legacy = run_dir / f"{base_stem}.xlsx"
    revisions = [
        revision
        for path in modern
        if (revision := _revision_number(path, base_stem)) is not None
    ]
    if legacy.is_file():
        revisions.append(1)
    if not revisions:
        return review_dir / f"{base_stem}.xlsx"
    return review_dir / f"{base_stem}_r{max(revisions) + 1:03d}.xlsx"


def review_html_path(workbook_path: Path, language: str) -> Path:
    if language not in {"ja", "en"}:
        raise ValueError("language must be 'ja' or 'en'")
    return workbook_path.with_name(
        f"{workbook_path.stem}_review.{language}.html"
    )


def spreadsheet_review_artifact(
    workbook_path: Path,
    language: str,
    spreadsheet_available: bool | None = None,
) -> Path:
    if spreadsheet_available is None:
        spreadsheet_available = bool(detect_spreadsheet_viewers())
    html = review_html_path(workbook_path, language)
    return workbook_path if spreadsheet_available or not html.is_file() else html


def _video_review_stem(run_dir: Path) -> str:
    return f"storyboard_{run_dir.name}_video"


def current_video_review_workbook(run_dir: Path) -> Path:
    run_dir = run_dir.resolve()
    base_stem = _video_review_stem(run_dir)
    candidates = _revision_candidates(run_dir / "final", base_stem)
    if candidates:
        return candidates[-1]
    return run_dir / "final" / f"{base_stem}.xlsx"


def next_video_review_workbook(run_dir: Path) -> Path:
    run_dir = run_dir.resolve()
    base_stem = _video_review_stem(run_dir)
    directory = run_dir / "final"
    candidates = _revision_candidates(directory, base_stem)
    if not candidates:
        return directory / f"{base_stem}.xlsx"
    revision = _revision_number(candidates[-1], base_stem) or 1
    return directory / f"{base_stem}_r{revision + 1:03d}.xlsx"


def current_final_video(run_dir: Path) -> Path:
    final_dir = run_dir.resolve() / "final"
    candidates = list(final_dir.glob("*.mp4")) if final_dir.is_dir() else []
    if not candidates:
        return final_dir / f"story_video_{run_dir.name}.mp4"
    return max(candidates, key=lambda path: (path.stat().st_mtime_ns, path.name))


def current_ai_record(run_dir: Path, language: str = "ja") -> Path:
    final_dir = run_dir.resolve() / "final"
    names = (
        ["AIモデル使用記録.md", "AI-model-usage-record.md"]
        if language == "ja"
        else ["AI-model-usage-record.md", "AIモデル使用記録.md"]
    )
    for name in names:
        candidate = final_dir / name
        if candidate.is_file():
            return candidate
    return final_dir / names[0]


def artifact_for_reveal(
    run_dir: Path,
    kind: str,
    *,
    language: str = "ja",
    spreadsheet_available: bool | None = None,
) -> Path:
    """Resolve a user-facing artifact, preferring HTML without a spreadsheet app."""
    run_dir = run_dir.resolve()
    if kind == "storyboard":
        workbook = current_storyboard_workbook(run_dir)
        return spreadsheet_review_artifact(
            workbook,
            language,
            spreadsheet_available,
        )
    if kind == "review-html":
        return review_html_path(current_storyboard_workbook(run_dir), language)
    if kind == "final-video":
        return current_final_video(run_dir)
    if kind == "video-review":
        workbook = current_video_review_workbook(run_dir)
        return spreadsheet_review_artifact(
            workbook,
            language,
            spreadsheet_available,
        )
    if kind == "ai-record":
        return current_ai_record(run_dir, language)
    raise ValueError(f"Unknown artifact kind: {kind}")


def _existing_file(path: str | Path | None) -> str | None:
    if not path:
        return None
    candidate = Path(path)
    return str(candidate) if candidate.is_file() else None


def _windows_app_path(executable_name: str) -> str | None:
    if platform.system() != "Windows":
        return None
    try:
        import winreg

        keys = (
            (winreg.HKEY_CURRENT_USER, rf"Software\Microsoft\Windows\CurrentVersion\App Paths\{executable_name}"),
            (winreg.HKEY_LOCAL_MACHINE, rf"Software\Microsoft\Windows\CurrentVersion\App Paths\{executable_name}"),
        )
        for hive, key_name in keys:
            try:
                with winreg.OpenKey(hive, key_name) as key:
                    value, _ = winreg.QueryValueEx(key, None)
                    existing = _existing_file(value)
                    if existing:
                        return existing
            except OSError:
                continue
    except (ImportError, OSError):
        return None
    return None


def detect_spreadsheet_viewers(
    system: str | None = None,
    environ: dict[str, str] | None = None,
    which: Callable[[str], str | None] = shutil.which,
) -> list[SpreadsheetViewer]:
    """Find locally installed spreadsheet applications without launching them."""
    current_system = system or platform.system()
    env = os.environ if environ is None else environ
    found: list[SpreadsheetViewer] = []
    seen: set[str] = set()

    def add(name: str, kind: str, executable: str | None) -> None:
        if not executable:
            return
        normalized = str(Path(executable)).casefold()
        if normalized in seen:
            return
        seen.add(normalized)
        found.append(SpreadsheetViewer(name, kind, executable))

    if current_system == "Windows":
        add("Microsoft Excel", "excel", _windows_app_path("excel.exe"))
        for variable in ("ProgramFiles", "ProgramFiles(x86)"):
            base = env.get(variable)
            if not base:
                continue
            add(
                "Microsoft Excel",
                "excel",
                _existing_file(Path(base) / "Microsoft Office" / "root" / "Office16" / "EXCEL.EXE"),
            )
            add(
                "LibreOffice Calc",
                "libreoffice",
                _existing_file(Path(base) / "LibreOffice" / "program" / "scalc.exe"),
            )
        add("LibreOffice Calc", "libreoffice", which("scalc.exe"))
        add("LibreOffice Calc", "libreoffice", which("soffice.exe"))
    elif current_system == "Darwin":
        add(
            "Microsoft Excel",
            "excel",
            _existing_file("/Applications/Microsoft Excel.app/Contents/MacOS/Microsoft Excel"),
        )
        add(
            "LibreOffice Calc",
            "libreoffice",
            _existing_file("/Applications/LibreOffice.app/Contents/MacOS/soffice"),
        )
        add(
            "Apple Numbers",
            "numbers",
            _existing_file("/Applications/Numbers.app/Contents/MacOS/Numbers"),
        )
    else:
        add("LibreOffice Calc", "libreoffice", which("libreoffice"))
        add("LibreOffice Calc", "libreoffice", which("soffice"))
        add(
            "ONLYOFFICE Desktop Editors",
            "onlyoffice",
            which("onlyoffice-desktopeditors"),
        )

    priority = {"excel": 0, "libreoffice": 1, "numbers": 2, "onlyoffice": 3}
    return sorted(found, key=lambda item: (priority.get(item.kind, 99), item.name))


def desktop_session_available(
    system: str | None = None,
    environ: dict[str, str] | None = None,
) -> bool:
    current_system = system or platform.system()
    env = os.environ if environ is None else environ
    if env.get("CI", "").lower() in {"1", "true", "yes"}:
        return False
    if env.get("SSH_CONNECTION") or env.get("SSH_TTY"):
        return False
    if current_system in {"Windows", "Darwin"}:
        return True
    return bool(env.get("DISPLAY") or env.get("WAYLAND_DISPLAY"))


def is_directly_viewable(target: Path) -> bool:
    """Return whether a beginner should see the artifact itself, not its folder."""
    return target.suffix.lower() in DIRECT_VIEW_EXTENSIONS


def open_in_default_app(
    target: Path,
    *,
    dry_run: bool = False,
    system: str | None = None,
    environ: dict[str, str] | None = None,
    startfile: Callable[[str], object] | None = None,
    popen: Callable[..., subprocess.Popen] = subprocess.Popen,
) -> RevealResult:
    """Open the exact review artifact so the visible screen matches the guidance."""
    resolved = target.resolve()
    if not resolved.is_file():
        raise FileNotFoundError(f"Artifact does not exist: {resolved}")

    current_system = system or platform.system()
    if current_system == "Windows":
        command = ("startfile", str(resolved))
        detail = "The artifact itself opened in its default Windows application"
    elif current_system == "Darwin":
        command = ("open", str(resolved))
        detail = "The artifact itself opened in its default macOS application"
    else:
        command = ("xdg-open", str(resolved))
        detail = "The artifact itself opened in the desktop's default application"

    if not desktop_session_available(current_system, environ):
        return RevealResult(
            False,
            resolved,
            command,
            "No desktop session is available. Describe the exact artifact without claiming it opened.",
        )
    if dry_run:
        return RevealResult(True, resolved, command, f"DRY RUN: {detail}")

    try:
        if current_system == "Windows":
            opener = startfile or getattr(os, "startfile", None)
            if opener is None:
                raise OSError("Windows default application launcher is unavailable")
            opener(str(resolved))
        else:
            popen(
                list(command),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
    except (FileNotFoundError, OSError) as error:
        return RevealResult(
            False,
            resolved,
            command,
            f"Could not open the artifact ({type(error).__name__})",
        )
    return RevealResult(True, resolved, command, detail)


def reveal_in_file_manager(
    target: Path,
    *,
    dry_run: bool = False,
    system: str | None = None,
    environ: dict[str, str] | None = None,
    popen: Callable[..., subprocess.Popen] = subprocess.Popen,
) -> RevealResult:
    """Open the containing folder and select the artifact when the OS supports it."""
    resolved = target.resolve()
    if not resolved.exists():
        raise FileNotFoundError(f"Artifact does not exist: {resolved}")

    current_system = system or platform.system()
    if current_system == "Windows":
        command = ("explorer.exe", f"/select,{resolved}")
        detail = "Windows Explorer opened with the file selected"
    elif current_system == "Darwin":
        command = ("open", "-R", str(resolved))
        detail = "Finder opened with the file revealed"
    else:
        command = ("xdg-open", str(resolved.parent))
        detail = "The containing folder opened; file selection depends on the file manager"

    if not desktop_session_available(current_system, environ):
        return RevealResult(
            False,
            resolved,
            command,
            "No desktop session is available. Show the folder path and guide one action at a time.",
        )
    if dry_run:
        return RevealResult(
            True,
            resolved,
            command,
            f"DRY RUN: {detail}",
            selected=current_system in {"Windows", "Darwin"},
        )

    try:
        popen(
            list(command),
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except (FileNotFoundError, OSError) as error:
        return RevealResult(
            False,
            resolved,
            command,
            f"Could not open the file manager ({type(error).__name__})",
        )
    return RevealResult(
        True,
        resolved,
        command,
        detail,
        selected=current_system in {"Windows", "Darwin"},
    )
