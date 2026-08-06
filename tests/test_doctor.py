from __future__ import annotations

from pathlib import Path

from scripts.doctor import (
    Check,
    api_key_is_set,
    api_key_online_checks,
    configured_models,
    readiness,
    spreadsheet_viewer_check,
)


def test_api_key_check_never_needs_to_return_the_secret(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        "# local only\nGEMINI_API_KEY=test-secret-that-must-not-be-printed\n",
        encoding="utf-8",
    )

    assert api_key_is_set(env_file, environ={}) is True


def test_api_key_check_accepts_environment_without_env_file(tmp_path: Path) -> None:
    assert api_key_is_set(
        tmp_path / "missing.env",
        environ={"GEMINI_API_KEY": "configured"},
    )


def test_readiness_distinguishes_warning_from_failure() -> None:
    assert readiness([Check("GEMINI_API_KEY", "WARN", "missing")]) == (
        "LOCAL READY (Google API setup required)"
    )
    assert readiness([Check("Python", "PASS", "3.11")]) == (
        "LOCAL READY (online verification required)"
    )
    assert (
        readiness(
            [
                Check("Gemini authentication", "PASS", "accepted"),
                Check("configured Gemini models", "PASS", "present"),
            ],
            online_verification_requested=True,
        )
        == "READY FOR GENERATION (paid generation not tested)"
    )
    assert (
        readiness(
            [Check("Gemini authentication", "PASS", "accepted")],
            online_verification_requested=True,
        )
        == "NOT READY"
    )
    assert readiness([Check("FFmpeg", "FAIL", "missing")]) == "NOT READY"


def test_configured_models_reads_overrides_without_exposing_key(tmp_path: Path) -> None:
    env_file = tmp_path / ".env"
    env_file.write_text(
        "GEMINI_API_KEY=not-returned\nVIDEO_MODEL=custom-video-model\n",
        encoding="utf-8",
    )

    result = configured_models(env_file, environ={})

    assert result["video"] == "custom-video-model"
    assert "GEMINI_API_KEY" not in result


def test_online_api_key_checks_models_without_generating_media() -> None:
    required = {
        "story": "story-model",
        "image": "image-model",
        "video": "video-model",
        "tts": "tts-model",
    }

    class Models:
        @staticmethod
        def list(*, config):
            assert config == {"page_size": 100}
            return iter({"name": f"models/{name}"} for name in required.values())

    class Client:
        models = Models()

        def close(self) -> None:
            pass

    def factory(*, api_key: str) -> Client:
        assert api_key == "example_key_12345678901234567890"
        return Client()

    results = api_key_online_checks(
        "example_key_12345678901234567890",
        required,
        client_factory=factory,
    )

    assert [result.status for result in results] == ["PASS", "PASS"]
    assert "no media was generated" in results[0].detail


def test_online_api_key_checks_report_missing_models() -> None:
    class Models:
        @staticmethod
        def list(*, config):
            return iter([{"name": "models/story-model"}])

    class Client:
        models = Models()

        def close(self) -> None:
            pass

    results = api_key_online_checks(
        "example_key_12345678901234567890",
        {"story": "story-model", "video": "paid-video-model"},
        client_factory=lambda **kwargs: Client(),
    )

    assert results[0].status == "PASS"
    assert results[1].status == "FAIL"
    assert "video=paid-video-model" in results[1].detail


def test_online_api_key_failure_never_displays_secret() -> None:
    secret = "example_key_12345678901234567890"

    def factory(*, api_key: str):
        raise RuntimeError(f"provider error containing {api_key}")

    results = api_key_online_checks(
        secret,
        {"video": "paid-video-model"},
        client_factory=factory,
    )

    assert results[0].status == "FAIL"
    assert secret not in results[0].detail


def test_missing_spreadsheet_application_is_nonblocking(
    monkeypatch,
) -> None:
    from video_storyboard import artifacts

    monkeypatch.setattr(artifacts, "detect_spreadsheet_viewers", lambda: [])

    result = spreadsheet_viewer_check()

    assert result.status == "WARN"
    assert "HTML" in result.detail
    assert readiness([result]) == "LOCAL READY (online verification required)"
