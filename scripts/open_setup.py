from __future__ import annotations

import argparse
import json
import os
import secrets
import sys
import threading
import webbrowser
from dataclasses import dataclass, field
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Callable
from urllib.parse import urlsplit

ROOT = Path(__file__).resolve().parents[1]
SRC = ROOT / "src"
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(SRC) not in sys.path:
    sys.path.insert(0, str(SRC))

from scripts.configure_api_key import (  # noqa: E402
    read_configured_key,
    validate_api_key,
    write_api_key,
)
from scripts.doctor import (  # noqa: E402
    Check,
    api_key_online_checks,
    configured_models,
    read_api_key,
)
from video_storyboard.knowledge import load_builtin_guidance  # noqa: E402

DEFAULT_ENV_PATH = ROOT / ".env"
DEFAULT_TEMPLATE_PATH = Path(__file__).with_name("setup_ui.html")
DEFAULT_ASSET_DIR = Path(__file__).with_name("setup_assets")
SETUP_ASSETS = {
    "/assets/niji-background.png": "niji-background.png",
    "/assets/nijiunit-guide-friends-hero.png": "nijiunit-guide-friends-hero.png",
    "/assets/nijiunit-logo-side-name.png": "nijiunit-logo-side-name.png",
}
MAX_REQUEST_BYTES = 8_192
Verifier = Callable[[str], list[Check]]


def verify_saved_key(api_key: str) -> list[Check]:
    guidance = load_builtin_guidance()
    profile_models = guidance.profile.models.model_dump()
    required_models = configured_models(
        DEFAULT_ENV_PATH,
        defaults=profile_models,
    )
    return api_key_online_checks(api_key, required_models)


@dataclass
class SetupState:
    env_path: Path
    token: str
    language: str
    verifier: Verifier = verify_saved_key
    verification_state: str = "not_checked"
    finish_reason: str = "cancelled"
    lock: threading.Lock = field(default_factory=threading.Lock)

    def key_source(self) -> str:
        if os.environ.get("GEMINI_API_KEY", "").strip():
            return "environment"
        if read_configured_key(self.env_path, environ={}):
            return "file"
        return "none"

    def public_status(self) -> dict[str, object]:
        source = self.key_source()
        return {
            "configured": source != "none",
            "source": source,
            "verification": self.verification_state,
        }

    def save_key(self, api_key: object, replace: object) -> tuple[int, dict[str, object]]:
        if not isinstance(api_key, str) or not isinstance(replace, bool):
            return HTTPStatus.BAD_REQUEST, {"ok": False, "code": "invalid_request"}

        key = api_key.strip()
        error = validate_api_key(key)
        if error:
            return HTTPStatus.BAD_REQUEST, {"ok": False, "code": "invalid_key"}

        with self.lock:
            source = self.key_source()
            if source == "environment":
                return HTTPStatus.CONFLICT, {
                    "ok": False,
                    "code": "managed_by_environment",
                }
            if source == "file" and not replace:
                return HTTPStatus.CONFLICT, {
                    "ok": False,
                    "code": "replace_required",
                }
            write_api_key(self.env_path, key)
            self.verification_state = "not_checked"

        return HTTPStatus.OK, {"ok": True, "configured": True}

    def verify(self) -> tuple[int, dict[str, object]]:
        api_key = read_api_key(self.env_path)
        if not api_key:
            return HTTPStatus.BAD_REQUEST, {"ok": False, "code": "key_missing"}

        checks = self.verifier(api_key)
        required = {"Gemini authentication", "configured Gemini models"}
        passed = {
            item.name
            for item in checks
            if item.name in required and item.status == "PASS"
        }
        ready = passed == required
        self.verification_state = "ready" if ready else "failed"
        return HTTPStatus.OK, {
            "ok": ready,
            "verification": self.verification_state,
            "checks": [
                {"name": item.name, "status": item.status}
                for item in checks
                if item.name in required
            ],
        }


def render_setup_html(template_path: Path, state: SetupState) -> tuple[str, str]:
    nonce = secrets.token_urlsafe(24)
    html = template_path.read_text(encoding="utf-8")
    replacements = {
        "__LANG__": state.language,
        "__TOKEN__": state.token,
        "__NONCE__": nonce,
    }
    for marker, value in replacements.items():
        html = html.replace(marker, value)
    return html, nonce


def handler_factory(state: SetupState, template_path: Path, asset_dir: Path):
    class SetupHandler(BaseHTTPRequestHandler):
        server_version = "NijiUnitSetup"
        sys_version = ""

        def log_message(self, format: str, *args: object) -> None:
            return

        def _security_headers(self, nonce: str | None = None) -> None:
            self.send_header("Cache-Control", "no-store, max-age=0")
            self.send_header("Pragma", "no-cache")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("X-Frame-Options", "DENY")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("Cross-Origin-Resource-Policy", "same-origin")
            self.send_header("Cross-Origin-Opener-Policy", "same-origin")
            if nonce:
                self.send_header(
                    "Content-Security-Policy",
                    "default-src 'none'; "
                    f"style-src 'nonce-{nonce}'; "
                    f"script-src 'nonce-{nonce}'; "
                    "img-src 'self' data:; "
                    "connect-src 'self'; "
                    "base-uri 'none'; form-action 'none'; frame-ancestors 'none'",
                )

        def _send_json(self, status: int, payload: dict[str, object]) -> None:
            body = json.dumps(payload, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self.send_header("Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self._security_headers()
            self.end_headers()
            self.wfile.write(body)

        def _send_html(self) -> None:
            html, nonce = render_setup_html(template_path, state)
            body = html.encode("utf-8")
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self._security_headers(nonce)
            self.end_headers()
            self.wfile.write(body)

        def _send_asset(self, filename: str) -> None:
            body = (asset_dir / filename).read_bytes()
            self.send_response(HTTPStatus.OK)
            self.send_header("Content-Type", "image/png")
            self.send_header("Content-Length", str(len(body)))
            self._security_headers()
            self.end_headers()
            self.wfile.write(body)

        def _authorized(self) -> bool:
            if not secrets.compare_digest(
                self.headers.get("X-NijiUnit-Token", ""), state.token
            ):
                return False
            origin = self.headers.get("Origin", "")
            if not origin:
                return True
            host, port = self.server.server_address
            return origin == f"http://{host}:{port}"

        def _discard_request_body(self) -> None:
            """Drain a small rejected request so Windows can return the 403 response."""
            try:
                content_length = int(self.headers.get("Content-Length", "0"))
            except ValueError:
                return
            if 0 < content_length <= MAX_REQUEST_BYTES:
                self.rfile.read(content_length)

        def _read_json(self) -> dict[str, object] | None:
            content_type = self.headers.get("Content-Type", "").split(";", 1)[0]
            if content_type.strip().lower() != "application/json":
                return None
            try:
                content_length = int(self.headers.get("Content-Length", "0"))
            except ValueError:
                return None
            if content_length <= 0 or content_length > MAX_REQUEST_BYTES:
                return None
            try:
                payload = json.loads(self.rfile.read(content_length))
            except (UnicodeDecodeError, json.JSONDecodeError):
                return None
            return payload if isinstance(payload, dict) else None

        def do_GET(self) -> None:  # noqa: N802
            path = urlsplit(self.path).path
            if path == "/":
                self._send_html()
                return
            if path in SETUP_ASSETS:
                self._send_asset(SETUP_ASSETS[path])
                return
            if path == "/api/status":
                self._send_json(HTTPStatus.OK, state.public_status())
                return
            self._send_json(HTTPStatus.NOT_FOUND, {"ok": False})

        def do_POST(self) -> None:  # noqa: N802
            if not self._authorized():
                self._discard_request_body()
                self._send_json(
                    HTTPStatus.FORBIDDEN,
                    {"ok": False, "code": "forbidden"},
                )
                return

            path = urlsplit(self.path).path
            payload = self._read_json()
            if payload is None:
                self._send_json(
                    HTTPStatus.BAD_REQUEST,
                    {"ok": False, "code": "invalid_request"},
                )
                return

            try:
                if path == "/api/key":
                    status, response = state.save_key(
                        payload.get("api_key"), payload.get("replace", False)
                    )
                elif path == "/api/verify":
                    status, response = state.verify()
                elif path == "/api/shutdown":
                    reason = payload.get("reason", "cancelled")
                    if reason not in {"ready", "needs_help", "cancelled"}:
                        status, response = HTTPStatus.BAD_REQUEST, {
                            "ok": False,
                            "code": "invalid_request",
                        }
                        self._send_json(status, response)
                        return
                    with state.lock:
                        state.finish_reason = str(reason)
                    status, response = HTTPStatus.OK, {"ok": True}
                    threading.Thread(
                        target=self.server.shutdown,
                        daemon=True,
                    ).start()
                else:
                    status, response = HTTPStatus.NOT_FOUND, {"ok": False}
            except Exception:  # noqa: BLE001
                status, response = HTTPStatus.INTERNAL_SERVER_ERROR, {
                    "ok": False,
                    "code": "internal_error",
                }
            self._send_json(status, response)

    return SetupHandler


def create_server(
    *,
    env_path: Path = DEFAULT_ENV_PATH,
    language: str = "ja",
    token: str | None = None,
    verifier: Verifier = verify_saved_key,
    template_path: Path = DEFAULT_TEMPLATE_PATH,
    asset_dir: Path = DEFAULT_ASSET_DIR,
    port: int = 0,
) -> tuple[ThreadingHTTPServer, SetupState]:
    state = SetupState(
        env_path=env_path,
        token=token or secrets.token_urlsafe(32),
        language=language,
        verifier=verifier,
    )
    server = ThreadingHTTPServer(
        ("127.0.0.1", port),
        handler_factory(state, template_path, asset_dir),
    )
    return server, state


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Open the local NijiUnit setup page without exposing API keys."
    )
    parser.add_argument("--language", choices=("ja", "en"), default="ja")
    parser.add_argument("--port", type=int, default=0)
    parser.add_argument("--no-browser", action="store_true")
    args = parser.parse_args()

    server, state = create_server(language=args.language, port=args.port)
    host, port = server.server_address
    url = f"http://{host}:{port}/"
    if args.language == "ja":
        print("NijiUnitの設定画面をこのPC内だけで開きます。")
        print("APIキーの値は、画面・URL・ログへ表示しません。")
    else:
        print("Opening the NijiUnit setup page only on this computer.")
        print("The API key is never displayed in the page URL or server log.")
    print(url)

    if not args.no_browser:
        webbrowser.open(url, new=2)
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()
    if args.language == "ja":
        if state.finish_reason == "ready":
            print("SETUP_RESULT=READY: 初回設定と接続確認が完了しました。")
        elif state.finish_reason == "needs_help":
            print("SETUP_RESULT=NEEDS_HELP: 設定画面で解決しない項目があります。")
        else:
            print("SETUP_RESULT=CANCELLED: 初回設定は完了していません。")
    else:
        if state.finish_reason == "ready":
            print("SETUP_RESULT=READY: Setup and connection verification completed.")
        elif state.finish_reason == "needs_help":
            print("SETUP_RESULT=NEEDS_HELP: The setup page needs agent assistance.")
        else:
            print("SETUP_RESULT=CANCELLED: First setup is not complete.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
