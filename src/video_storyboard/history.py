from __future__ import annotations

import hashlib
import json
import re
import shutil
import unicodedata
from datetime import UTC, datetime
from pathlib import Path


def _state_path(run_dir: Path) -> Path:
    return run_dir.resolve() / "completion_state.json"


def mark_completion_review_pending(run_dir: Path, review_artifact: Path) -> Path:
    destination = _state_path(run_dir)
    destination.write_text(
        json.dumps(
            {
                "status": "awaiting_user_review",
                "review_artifact": str(review_artifact.resolve()),
                "updated_at": datetime.now(UTC).isoformat(),
                "message_ja": (
                    "完成動画を確認してください。問題なければ、その意味が分かる普通の言葉で"
                    "伝えてください。確認後、制作一式をhistoryへ移します。移動後も修正できます。"
                ),
                "message_en": (
                    "Review the finished video. If it is satisfactory, say so in your "
                    "own words. The production will then move to history and can still "
                    "be revised later."
                ),
            },
            ensure_ascii=False,
            indent=2,
        )
        + "\n",
        encoding="utf-8",
    )
    return destination


def _normalized_confirmation(value: str) -> str:
    normalized = unicodedata.normalize("NFKC", value).casefold()
    return re.sub(r"[\s。、，,.!！?？「」『』\"'`]+", "", normalized)


def is_completion_confirmation(value: str) -> bool:
    normalized = _normalized_confirmation(value)
    negative = (
        "修正",
        "直して",
        "やり直",
        "まだ",
        "だめ",
        "ダメ",
        "違う",
        "問題がある",
        "問題があります",
        "問題有り",
        "notok",
        "notgood",
        "revise",
        "change",
        "fix",
    )
    if any(token.casefold() in normalized for token in negative):
        return False
    positive = (
        "この内容で完成",
        "これで完成",
        "完成です",
        "これでいい",
        "これでよい",
        "問題ない",
        "問題がない",
        "問題ありません",
        "問題がありません",
        "大丈夫",
        "承認",
        "ok",
        "okay",
        "looks good",
        "approved",
        "complete",
        "finished",
    )
    return any(token.replace(" ", "").casefold() in normalized for token in positive)


def _safe_title(value: str) -> str:
    cleaned = re.sub(r'[<>:"/\\|?*\x00-\x1f]+', "_", value).strip(" ._")
    return cleaned[:80] or "untitled"


def _next_history_directory(history_root: Path, title: str) -> Path:
    history_root.mkdir(parents=True, exist_ok=True)
    numbers = []
    for path in history_root.iterdir():
        match = re.match(r"^(\d{3})_", path.name)
        if path.is_dir() and match:
            numbers.append(int(match.group(1)))
    number = max(numbers, default=0) + 1
    return history_root / f"{number:03d}_{_safe_title(title)}"


def _hash_tree(root: Path) -> dict[str, str]:
    hashes = {}
    for path in sorted(root.rglob("*")):
        if not path.is_file() or path.name == "manifest.sha256.json":
            continue
        hashes[path.relative_to(root).as_posix()] = hashlib.sha256(
            path.read_bytes()
        ).hexdigest()
    return hashes


def archive_production(
    run_dir: Path,
    input_dir: Path,
    history_root: Path,
    confirmation: str,
    title: str | None = None,
) -> Path:
    run_dir = run_dir.resolve()
    input_dir = input_dir.resolve()
    history_root = history_root.resolve()
    if not is_completion_confirmation(confirmation):
        raise RuntimeError(
            "完成の確認として受け取れませんでした。完成でよい場合は、"
            "「これでいい」「問題ない」など、ご自身の言葉で伝えてください。"
        )
    final_videos = list((run_dir / "final").glob("*.mp4"))
    review_workbooks = list((run_dir / "final").glob("storyboard_*_video*.xlsx"))
    if not final_videos:
        raise RuntimeError("完成動画がないためhistoryへ移せません。")
    if not review_workbooks:
        raise RuntimeError("完成動画の確認用Excelがないためhistoryへ移せません。")
    state_path = _state_path(run_dir)
    if not state_path.is_file():
        raise RuntimeError("完成確認の待機記録がありません。先に動画確認資料を作ってください。")
    state = json.loads(state_path.read_text(encoding="utf-8"))
    if state.get("status") != "awaiting_user_review":
        raise RuntimeError("この制作は完成確認待ちの状態ではありません。")

    storyboard = json.loads((run_dir / "storyboard.json").read_text(encoding="utf-8"))
    archive = _next_history_directory(history_root, title or storyboard["title"])
    archive.mkdir(parents=True, exist_ok=False)
    try:
        if input_dir.is_dir():
            shutil.copytree(
                input_dir,
                archive / "input",
                ignore=shutil.ignore_patterns(".env", ".env.*", "__pycache__"),
            )
        state["status"] = "approved_for_history"
        state["confirmation"] = confirmation
        state["updated_at"] = datetime.now(UTC).isoformat()
        state_path.write_text(
            json.dumps(state, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        moved_run = Path(shutil.move(str(run_dir), str(archive / "run")))
        record = {
            "schema_version": "1.0",
            "archived_at": datetime.now(UTC).isoformat(),
            "title": title or storyboard["title"],
            "original_run_directory": str(run_dir),
            "editable_run_directory": str(moved_run.resolve()),
            "completion_confirmation": confirmation,
        }
        (archive / "archive_record.json").write_text(
            json.dumps(record, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        (archive / "manifest.sha256.json").write_text(
            json.dumps(_hash_tree(archive), ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
    except Exception:
        if archive.is_dir() and not any(archive.iterdir()):
            archive.rmdir()
        raise
    return archive


def completion_status(output_root: Path, history_root: Path) -> dict[str, object]:
    pending = []
    if output_root.is_dir():
        for state_path in sorted(output_root.rglob("completion_state.json")):
            state = json.loads(state_path.read_text(encoding="utf-8"))
            if state.get("status") == "awaiting_user_review":
                pending.append(
                    {
                        "run_dir": str(state_path.parent.resolve()),
                        "review_artifact": state.get("review_artifact"),
                        "message_ja": state.get("message_ja"),
                    }
                )
    archives = []
    if history_root.is_dir():
        archives = [str(path.resolve()) for path in sorted(history_root.glob("[0-9][0-9][0-9]_*")) if path.is_dir()]
    return {"awaiting_user_review": pending, "history": archives}
