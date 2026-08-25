import pytest

from video_storyboard.runtime_config import RuntimeConfig
from video_storyboard.website_tutorial import (
    fetch_tutorial_page,
    format_tutorial_page,
    tutorial_url,
    youtube_video_id,
)


@pytest.mark.parametrize(
    ("url", "expected"),
    (
        ("https://youtu.be/6xOhd6PD3V8", "6xOhd6PD3V8"),
        ("https://www.youtube.com/watch?v=6xOhd6PD3V8", "6xOhd6PD3V8"),
        ("https://www.youtube.com/shorts/6xOhd6PD3V8", "6xOhd6PD3V8"),
        ("https://www.youtube.com/embed/6xOhd6PD3V8", "6xOhd6PD3V8"),
    ),
)
def test_youtube_video_id(url: str, expected: str) -> None:
    assert youtube_video_id(url) == expected


@pytest.mark.parametrize(
    "url",
    (
        "https://example.com/watch?v=6xOhd6PD3V8",
        "http://youtu.be/too-short",
        "http://youtu.be/6xOhd6PD3V8",
        "https://user" + ":secret@youtu.be/6xOhd6PD3V8",
        "https://youtu.be/6xOhd6PD3V8/extra",
        "6xOhd6PD3V8",
    ),
)
def test_youtube_video_id_rejects_non_youtube_or_invalid_url(url: str) -> None:
    with pytest.raises(ValueError):
        youtube_video_id(url)


def _config() -> RuntimeConfig:
    return RuntimeConfig(
        tutorial_base_url="https://manual.nijiunit.com/ai-agent-video-manual",
        github_repository_url="https://github.com/nijiunit/example",
    )


def test_tutorial_url_is_language_specific() -> None:
    assert tutorial_url("6xOhd6PD3V8", "ja", _config()).endswith(
        "/ja/tutorials/6xOhd6PD3V8/"
    )


def test_fetch_tutorial_validates_contract_and_reads_only_local_docs(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    page = b"""<!doctype html><html><body
      data-nijiunit-tutorial-id=\"6xOhd6PD3V8\"
      data-nijiunit-tutorial-language=\"ja\"
      data-ai-tutorial-contract=\"1.0\">
      <main><h1>Episode 1</h1><a href=\"./docs/guide.md\">guide</a></main>
      <script>do not include</script></body></html>"""

    def fake_download(url: str, config: RuntimeConfig, accept: str) -> bytes:
        del config, accept
        return b"# Guide\nOne step at a time" if url.endswith("guide.md") else page

    monkeypatch.setattr(
        "video_storyboard.website_tutorial._download",
        fake_download,
    )
    result = fetch_tutorial_page(
        "https://youtu.be/6xOhd6PD3V8",
        "ja",
        config=_config(),
    )

    assert result.video_id == "6xOhd6PD3V8"
    assert result.documents == {"guide.md": "# Guide\nOne step at a time"}
    formatted = format_tutorial_page(result)
    assert "VERIFIED_DIRECT_FETCH" in formatted
    assert "do not include" not in formatted


def test_fetch_tutorial_rejects_mismatched_page_contract(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(
        "video_storyboard.website_tutorial._download",
        lambda *_args, **_kwargs: (
            b'<body data-nijiunit-tutorial-id="WRONG000001" '
            b'data-nijiunit-tutorial-language="ja" '
            b'data-ai-tutorial-contract="1.0"></body>'
        ),
    )

    with pytest.raises(RuntimeError, match="識別情報"):
        fetch_tutorial_page(
            "https://youtu.be/6xOhd6PD3V8",
            "ja",
            config=_config(),
        )
