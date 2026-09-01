from __future__ import annotations

import json
import threading
from http.client import HTTPConnection
from pathlib import Path

import pytest

from scripts.doctor import CERTIFICATE_FAILURE_DETAIL, Check
from scripts.open_setup import SetupState, create_server

TEST_KEY = "test_GeminiKey_1234567890abcdef"
REPLACEMENT_KEY = "test_GeminiKey_fedcba0987654321"
AUTHORIZATION_KEY = "AQ.synthetic.authorization_key_0123456789-test$"


@pytest.fixture
def setup_server(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    # A developer machine may already have a real key in its environment. Keep
    # this test server isolated so failures can never print or compare it.
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    verified_keys: list[str] = []

    def verifier(api_key: str) -> list[Check]:
        verified_keys.append(api_key)
        return [
            Check("Gemini authentication", "PASS", "accepted"),
            Check("configured Gemini models", "PASS", "available"),
        ]

    token = "test-csrf-token"
    server, _state = create_server(
        env_path=tmp_path / ".env",
        token=token,
        verifier=verifier,
    )
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    try:
        yield server, tmp_path / ".env", token, verified_keys
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def request(server, method: str, path: str, *, token: str = "", payload=None):
    host, port = server.server_address
    connection = HTTPConnection(host, port, timeout=3)
    headers = {}
    body = None
    if payload is not None:
        body = json.dumps(payload)
        headers = {
            "Content-Type": "application/json",
            "Origin": f"http://{host}:{port}",
            "X-NijiUnit-Token": token,
        }
    connection.request(method, path, body=body, headers=headers)
    response = connection.getresponse()
    response_body = response.read()
    response_headers = dict(response.getheaders())
    connection.close()
    return response.status, response_headers, response_body


def test_page_is_loopback_only_and_has_security_headers(setup_server):
    server, _env_path, _token, _verified_keys = setup_server
    assert server.server_address[0] == "127.0.0.1"

    status, headers, body = request(server, "GET", "/")
    html = body.decode("utf-8")

    assert status == 200
    assert headers["Cache-Control"] == "no-store, max-age=0"
    assert headers["X-Frame-Options"] == "DENY"
    assert "default-src 'none'" in headers["Content-Security-Policy"]
    assert "img-src 'self' data:" in headers[
        "Content-Security-Policy"
    ]
    assert "manual.nijiunit.com" not in headers["Content-Security-Policy"]
    assert "おめでとうございます" in html
    assert "Congratulations" in html
    assert "NijiUnitのインストール完了" in html
    assert "Google Gemini API" in html
    assert "この画面では、動画生成に必要なGoogleの初回設定を行います" in html
    assert "nijiunit-logo-side-name.png" in html
    assert "nijiunit-guide-friends-hero.png" in html
    assert "https://manual.nijiunit.com" not in html
    assert "Googleアカウントをお持ちですか？" in html
    assert "Google AI StudioでAPIキーを取得します" in html
    assert "Google AI StudioでAPIキーを取得する必要があります" in html
    assert "Google AI Studioを別ウィンドウで開く" in html
    assert "下の青いボタン「Google AI Studioを別ウィンドウで開く」" in html
    assert "①②③の手順でAPIキーをコピーし" in html
    assert "下の黄色い部分にAPIキーを貼り付け" in html
    assert "最後に、青いボタン「このPCに保存して、接続を確認する」" in html
    assert "コピーしたAPIキーを、この画面に貼り付けてください" in html
    assert 'class="info-card paste-card"' in html
    assert "return-note" not in html
    assert "stageCopy" not in html
    assert "stagePaste" not in html
    assert "fake-tab" not in html
    open_stage_start = html.index('id="stageOpen"')
    existing_stage_start = html.index('id="stageExisting"')
    assert open_stage_start < html.index('id="openStudio"') < existing_stage_start
    assert open_stage_start < html.index('id="apiKey"') < existing_stage_start
    assert "availableWidth * 0.64" in html
    assert "availableHeight * 0.78" in html
    assert "googleWindow.resizeTo(popupWidth, popupHeight)" in html
    assert "googleWindow.moveTo(popupLeft, popupTop)" in html
    assert 'showStage("Copy")' not in html
    assert 'showStage("Paste")' not in html
    assert "ご自身のプロジェクト（表示例）" in html
    assert "Your project (example)" in html
    assert "NijiUnit Video Production" not in html
    assert "••••••••2j20" not in html
    assert html.count('class="table-marker"') == 3
    assert "同じ行の請求階層を確認" in html
    assert "同じ行のコピーの印を押す" in html
    assert html.count('class="copy-icon"') == 1
    assert "このPCに保存して、接続を確認する" in html
    assert "APIキーは保存しました。接続できない原因を確認します" in html
    assert "APIキーを作り直す必要はありません" in html
    assert 'result.code === "certificate_verification_failed"' in html
    assert 'replaceAfterFailure").hidden = certificateFailure' in html
    assert "APIキーをこのPCに保存" in html
    assert ".env" not in html
    assert "Google Gemini APIへ接続" in html
    assert "NijiUnitに必要なモデルを確認" in html
    assert "おめでとうございます。<br>設定は完了です" in html
    assert "この設定画面を閉じてAIエージェントへ戻る" in html
    assert "window.open(\"https://aistudio.google.com/app/apikey\"" in html
    assert "window.close()" in html
    assert 'returnForAccount").addEventListener("click", function () { finish("needs_help")' in html
    assert 'finish("account_help")' not in html
    assert "アカウント作成からAIエージェントに相談します" in html
    assert "password or verification code into chat" in html
    assert "ChatGPTへ戻る" not in html
    assert "callout" not in html
    assert "__TOKEN__" not in html
    assert "localStorage" not in html
    assert "sessionStorage" not in html
    assert 'id="saveConnect" type="button" disabled' in html
    assert 'addEventListener("input", updateSaveConnectState)' in html
    assert html.count('addEventListener("change", updateSaveConnectState)') == 2
    assert "hasKey && projectConfirmed && replacementConfirmed" in html

    for asset_path in (
        "/assets/niji-background.png",
        "/assets/nijiunit-logo-side-name.png",
        "/assets/nijiunit-guide-friends-hero.png",
    ):
        asset_status, asset_headers, asset_body = request(server, "GET", asset_path)
        assert asset_status == 200
        assert asset_headers["Content-Type"] == "image/png"
        assert asset_headers["Cache-Control"] == "no-store, max-age=0"
        assert asset_body.startswith(b"\x89PNG\r\n\x1a\n")


def test_key_is_stored_but_never_returned(setup_server):
    server, env_path, token, _verified_keys = setup_server
    status, _headers, body = request(
        server,
        "POST",
        "/api/key",
        token=token,
        payload={"api_key": TEST_KEY, "replace": False},
    )

    assert status == 200
    assert TEST_KEY in env_path.read_text(encoding="utf-8")
    assert TEST_KEY.encode() not in body
    assert json.loads(body) == {"ok": True, "configured": True}

    status, _headers, status_body = request(server, "GET", "/api/status")
    assert status == 200
    assert TEST_KEY.encode() not in status_body
    assert json.loads(status_body)["configured"] is True


def test_google_authorization_key_is_stored_without_being_returned(setup_server):
    server, env_path, token, verified_keys = setup_server
    status, _headers, body = request(
        server,
        "POST",
        "/api/key",
        token=token,
        payload={"api_key": AUTHORIZATION_KEY, "replace": False},
    )

    assert status == 200
    assert AUTHORIZATION_KEY in env_path.read_text(encoding="utf-8")
    assert AUTHORIZATION_KEY.encode() not in body

    verify_status, _headers, verify_body = request(
        server,
        "POST",
        "/api/verify",
        token=token,
        payload={},
    )
    assert verify_status == 200
    assert verified_keys == [AUTHORIZATION_KEY]
    assert AUTHORIZATION_KEY.encode() not in verify_body


def test_existing_key_requires_explicit_replacement(setup_server):
    server, env_path, token, _verified_keys = setup_server
    env_path.write_text(f"GEMINI_API_KEY={TEST_KEY}\n", encoding="utf-8")

    status, _headers, body = request(
        server,
        "POST",
        "/api/key",
        token=token,
        payload={"api_key": REPLACEMENT_KEY, "replace": False},
    )
    assert status == 409
    assert json.loads(body)["code"] == "replace_required"
    assert TEST_KEY in env_path.read_text(encoding="utf-8")
    assert REPLACEMENT_KEY not in env_path.read_text(encoding="utf-8")

    status, _headers, body = request(
        server,
        "POST",
        "/api/key",
        token=token,
        payload={"api_key": REPLACEMENT_KEY, "replace": True},
    )
    assert status == 200
    assert REPLACEMENT_KEY in env_path.read_text(encoding="utf-8")
    assert TEST_KEY not in env_path.read_text(encoding="utf-8")
    assert REPLACEMENT_KEY.encode() not in body


def test_post_requires_session_token_and_same_origin(setup_server):
    server, env_path, token, _verified_keys = setup_server
    status, _headers, body = request(
        server,
        "POST",
        "/api/key",
        token="wrong-token",
        payload={"api_key": TEST_KEY, "replace": False},
    )
    assert status == 403
    assert json.loads(body)["code"] == "forbidden"
    assert not env_path.exists()

    host, port = server.server_address
    connection = HTTPConnection(host, port, timeout=3)
    connection.request(
        "POST",
        "/api/key",
        body=json.dumps({"api_key": TEST_KEY, "replace": False}),
        headers={
            "Content-Type": "application/json",
            "Origin": "https://example.invalid",
            "X-NijiUnit-Token": token,
        },
    )
    response = connection.getresponse()
    response.read()
    connection.close()
    assert response.status == 403
    assert not env_path.exists()


def test_verification_uses_saved_key_without_returning_it(setup_server):
    server, env_path, token, verified_keys = setup_server
    env_path.write_text(f"GEMINI_API_KEY={TEST_KEY}\n", encoding="utf-8")

    status, _headers, body = request(
        server,
        "POST",
        "/api/verify",
        token=token,
        payload={},
    )
    response = json.loads(body)

    assert status == 200
    assert response["ok"] is True
    assert response["verification"] == "ready"
    assert verified_keys == [TEST_KEY]
    assert TEST_KEY.encode() not in body
    assert response["checks"] == [
        {"name": "Gemini authentication", "status": "PASS"},
        {"name": "configured Gemini models", "status": "PASS"},
    ]
    assert response["code"] == "ready"


def test_certificate_failure_is_reported_without_exposing_the_key(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("GEMINI_API_KEY", raising=False)
    env_path = tmp_path / ".env"
    env_path.write_text(f"GEMINI_API_KEY={TEST_KEY}\n", encoding="utf-8")
    state = SetupState(
        env_path=env_path,
        token="test-token",
        language="ja",
        verifier=lambda _api_key: [
            Check("Gemini authentication", "FAIL", CERTIFICATE_FAILURE_DETAIL)
        ],
    )

    status, response = state.verify()

    assert status == 200
    assert response["ok"] is False
    assert response["code"] == "certificate_verification_failed"
    assert response["verification"] == "failed"
    assert TEST_KEY not in json.dumps(response)
