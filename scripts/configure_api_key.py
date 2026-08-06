from __future__ import annotations

import argparse
import getpass
import os
import re
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ENV_PATH = ROOT / ".env"
EXAMPLE_ENV_PATH = ROOT / ".env.example"
KEY_NAME = "GEMINI_API_KEY"
SAFE_KEY_PATTERN = re.compile(r"[A-Za-z0-9_-]{20,512}")


def read_configured_key(env_path: Path, environ: dict[str, str] | None = None) -> bool:
    environment = os.environ if environ is None else environ
    if environment.get(KEY_NAME, "").strip():
        return True
    if not env_path.is_file():
        return False
    for raw_line in env_path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        name, value = line.split("=", 1)
        if name.strip() == KEY_NAME and value.strip().strip('"').strip("'"):
            return True
    return False


def validate_api_key(value: str) -> str | None:
    if not value:
        return "APIキーが入力されていません。"
    if not SAFE_KEY_PATTERN.fullmatch(value):
        return "APIキーの形式を確認してください（空白を含めず、そのまま貼り付けます）。"
    return None


def update_env_text(current: str, key: str) -> str:
    newline = "\r\n" if "\r\n" in current else "\n"
    source_lines = current.splitlines()
    output_lines: list[str] = []
    replaced = False
    for line in source_lines:
        if line.lstrip().startswith(f"{KEY_NAME}="):
            if not replaced:
                output_lines.append(f"{KEY_NAME}={key}")
                replaced = True
            continue
        output_lines.append(line)
    if not replaced:
        if output_lines and output_lines[-1]:
            output_lines.append("")
        output_lines.append(f"{KEY_NAME}={key}")
    return newline.join(output_lines) + newline


def write_api_key(env_path: Path, key: str) -> None:
    if env_path.is_file():
        current = env_path.read_text(encoding="utf-8")
    elif (
        env_path.resolve() == DEFAULT_ENV_PATH.resolve() and EXAMPLE_ENV_PATH.is_file()
    ):
        current = EXAMPLE_ENV_PATH.read_text(encoding="utf-8")
    else:
        current = ""
    updated = update_env_text(current, key)
    env_path.parent.mkdir(parents=True, exist_ok=True)
    temp_name = ""
    try:
        with tempfile.NamedTemporaryFile(
            mode="w",
            encoding="utf-8",
            newline="",
            dir=env_path.parent,
            prefix=".env.",
            suffix=".tmp",
            delete=False,
        ) as temporary:
            temporary.write(updated)
            temp_name = temporary.name
        os.replace(temp_name, env_path)
        try:
            env_path.chmod(0o600)
        except OSError:
            pass
    finally:
        if temp_name:
            Path(temp_name).unlink(missing_ok=True)


def print_instructions(configured: bool) -> None:
    print("\nGemini APIキーの安全な保存")
    if configured:
        print("- APIキーはすでに設定されています（値は表示しません）。")
        print("- 変更する場合だけ、このツールを --replace 付きで実行してください。")
        return
    print("- Google AI Studioで取得済みのキーを、この端末だけで保存します。")
    print("- キーをチャット、画面共有、コマンド引数へ貼らないでください。")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Store a Gemini API key in .env without echoing it."
    )
    parser.add_argument(
        "--instructions-only",
        action="store_true",
        help="show the safe onboarding instructions without prompting",
    )
    parser.add_argument(
        "--replace",
        action="store_true",
        help="replace an already configured key",
    )
    args = parser.parse_args()

    configured = read_configured_key(DEFAULT_ENV_PATH)
    print_instructions(configured)
    if args.instructions_only:
        return 0
    if configured and not args.replace:
        return 0

    if not sys.stdin.isatty():
        print(
            "安全な非表示入力を開始できません。対話可能なローカル端末で、"
            "このコマンドを直接実行してください。"
        )
        return 2

    try:
        key = getpass.getpass(
            "\nAPIキーを貼り付けてEnter（入力内容は画面に表示されません）: "
        ).strip()
    except (EOFError, KeyboardInterrupt):
        print("\n設定を中止しました。APIキーは保存されていません。")
        return 2

    error = validate_api_key(key)
    if error:
        print(f"設定できませんでした: {error}")
        return 2

    write_api_key(DEFAULT_ENV_PATH, key)
    print("APIキーをローカルの.envへ安全に保存しました（値は表示しません）。")
    print(
        "続けて scripts/doctor.py --require-api-key --verify-api-key-online "
        "を実行してください。"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
