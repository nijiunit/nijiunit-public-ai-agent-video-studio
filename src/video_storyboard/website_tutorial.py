from __future__ import annotations

import html
import re
from dataclasses import dataclass
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import parse_qs, quote, unquote, urljoin, urlparse
from urllib.request import HTTPRedirectHandler, Request, build_opener

from . import __version__
from .runtime_config import RuntimeConfig, load_runtime_config

YOUTUBE_ID_PATTERN = re.compile(r"^[0-9A-Za-z_-]{11}$")


@dataclass(frozen=True)
class TutorialPage:
    video_id: str
    language: str
    url: str
    page_text: str
    documents: dict[str, str]


SAMPLE_STORY_NAME_MARKERS = (
    "ストーリー公開版",
    "sample-story",
    "sample_story",
    "public-story",
    "public_story",
)
SAMPLE_STORY_EXACT_STEMS = {"ストーリー", "story"}


class _TutorialHTMLParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.body_attributes: dict[str, str] = {}
        self.document_links: list[str] = []
        self.text_parts: list[str] = []
        self._ignored_depth = 0

    def handle_starttag(self, tag: str, attrs) -> None:
        attributes = {name: value or "" for name, value in attrs}
        if tag == "body":
            self.body_attributes = attributes
        if tag in {"script", "style", "noscript"}:
            self._ignored_depth += 1
        if tag == "a":
            href = attributes.get("href", "")
            if href.lower().endswith(".md") and "/docs/" in href.replace("\\", "/"):
                self.document_links.append(href)

    def handle_endtag(self, tag: str) -> None:
        if tag in {"script", "style", "noscript"} and self._ignored_depth:
            self._ignored_depth -= 1

    def handle_data(self, data: str) -> None:
        if self._ignored_depth:
            return
        value = " ".join(data.split())
        if value:
            self.text_parts.append(value)


def youtube_video_id(youtube_url: str) -> str:
    parsed = urlparse(youtube_url.strip())
    if (
        parsed.scheme.lower() != "https"
        or parsed.username
        or parsed.password
        or parsed.port not in {None, 443}
    ):
        raise ValueError("YouTube動画URLは認証情報を含まないHTTPS URLを指定してください")
    host = (parsed.hostname or "").lower()
    video_id = ""
    if host in {"youtu.be", "www.youtu.be"}:
        parts = [part for part in parsed.path.split("/") if part]
        if len(parts) == 1:
            video_id = parts[0]
    elif host in {"youtube.com", "www.youtube.com", "m.youtube.com"}:
        if parsed.path.rstrip("/") == "/watch":
            video_id = parse_qs(parsed.query).get("v", [""])[0]
        else:
            parts = [part for part in parsed.path.split("/") if part]
            if len(parts) == 2 and parts[0] in {"shorts", "embed", "live"}:
                video_id = parts[1]
    if not YOUTUBE_ID_PATTERN.fullmatch(video_id):
        raise ValueError("有効なYouTube動画URLから11文字の動画IDを取得できません")
    return video_id


def tutorial_url(video_id: str, language: str, config: RuntimeConfig) -> str:
    if language not in {"ja", "en"}:
        raise ValueError("language must be 'ja' or 'en'")
    if not YOUTUBE_ID_PATTERN.fullmatch(video_id):
        raise ValueError("YouTube動画IDが不正です")
    return f"{config.tutorial_base_url.rstrip('/')}/{language}/tutorials/{video_id}/"


def _is_loopback(url: str) -> bool:
    return (urlparse(url).hostname or "").lower() in {
        "127.0.0.1",
        "localhost",
        "::1",
    }


def _validate_official_url(url: str, config: RuntimeConfig) -> None:
    parsed = urlparse(url)
    base = urlparse(config.tutorial_base_url)
    if parsed.username or parsed.password:
        raise ValueError("教材URLに認証情報を含めることはできません")
    if parsed.scheme != "https" and not (
        parsed.scheme == "http" and _is_loopback(url)
    ):
        raise ValueError("教材はHTTPSのNijiUnit公式ページだけを利用できます")
    if (parsed.scheme, parsed.hostname, parsed.port) != (
        base.scheme,
        base.hostname,
        base.port,
    ):
        raise ValueError("教材URLが設定済みのNijiUnit公式サイトと一致しません")


def _download(url: str, config: RuntimeConfig, accept: str) -> bytes:
    class NoRedirect(HTTPRedirectHandler):
        def redirect_request(self, req, fp, code, msg, headers, newurl):
            return None

    _validate_official_url(url, config)
    request = Request(
        url,
        headers={
            "Accept": accept,
            "User-Agent": f"nijiunit-ai-agent-video-studio/{__version__}",
        },
    )
    with build_opener(NoRedirect()).open(
        request,
        timeout=config.request_timeout_seconds,
    ) as response:
        content_type = response.headers.get_content_type()
        data = response.read(config.maximum_page_bytes + 1)
    if len(data) > config.maximum_page_bytes:
        raise ValueError("NijiUnit教材ページが許容サイズを超えています")
    if content_type not in {"text/html", "text/markdown", "text/plain"}:
        raise ValueError(f"NijiUnit教材のContent-Typeが不正です: {content_type}")
    return data


def fetch_tutorial_page(
    youtube_url: str,
    language: str = "ja",
    *,
    config: RuntimeConfig | None = None,
) -> TutorialPage:
    runtime = config or load_runtime_config()
    video_id = youtube_video_id(youtube_url)
    page_url = tutorial_url(video_id, language, runtime)
    page_bytes = _download(page_url, runtime, "text/html")
    try:
        page_html = page_bytes.decode("utf-8")
    except UnicodeDecodeError as error:
        raise ValueError("NijiUnit教材ページはUTF-8ではありません") from error

    parser = _TutorialHTMLParser()
    parser.feed(page_html)
    expected_attributes = {
        "data-nijiunit-tutorial-id": video_id,
        "data-nijiunit-tutorial-language": language,
        "data-ai-tutorial-contract": "1.0",
    }
    for name, expected in expected_attributes.items():
        if parser.body_attributes.get(name) != expected:
            raise RuntimeError(
                f"NijiUnit公式教材の識別情報を検証できません: {name}"
            )

    page_origin = urlparse(page_url)
    expected_docs_prefix = f"{page_origin.path.rstrip('/')}/docs/"
    documents: dict[str, str] = {}
    for href in dict.fromkeys(parser.document_links):
        document_url = urljoin(page_url, quote(href, safe="/:?=&%"))
        parsed_document = urlparse(document_url)
        if (
            (parsed_document.scheme, parsed_document.hostname, parsed_document.port)
            != (page_origin.scheme, page_origin.hostname, page_origin.port)
            or not parsed_document.path.startswith(expected_docs_prefix)
        ):
            raise RuntimeError("教材ページに許可されていない資料URLがあります")
        data = _download(document_url, runtime, "text/markdown, text/plain;q=0.9")
        try:
            documents[parsed_document.path.rsplit("/", 1)[-1]] = data.decode("utf-8")
        except UnicodeDecodeError as error:
            raise ValueError("NijiUnit教材資料はUTF-8ではありません") from error
    if not documents:
        raise RuntimeError("NijiUnit公式教材にAIエージェント用資料がありません")

    return TutorialPage(
        video_id=video_id,
        language=language,
        url=page_url,
        page_text=html.unescape("\n".join(parser.text_parts)),
        documents=documents,
    )


def format_tutorial_page(page: TutorialPage) -> str:
    if page.language == "ja":
        lines = [
            "NIJIUNIT_OFFICIAL_TUTORIAL: VERIFIED_DIRECT_FETCH",
            f"YouTube動画ID: {page.video_id}",
            f"言語: {page.language}",
            f"参照URL: {page.url}",
            "保存方式: ローカルへキャッシュせず、今回の応答で直接取得",
            "取得内容: 公式ページと公開Markdown資料",
            "取得した画像・動画・音声素材: なし",
            "",
            "=== 公式ページ本文 ===",
            page.page_text,
        ]
        document_heading = "公式資料"
    else:
        lines = [
            "NIJIUNIT_OFFICIAL_TUTORIAL: VERIFIED_DIRECT_FETCH",
            f"YouTube video ID: {page.video_id}",
            f"Language: {page.language}",
            f"Source URL: {page.url}",
            "Storage: fetched directly for this response without a local cache",
            "Retrieved: official page and public Markdown documents",
            "Retrieved image, video, or audio source assets: none",
            "",
            "=== Official page ===",
            page.page_text,
        ]
        document_heading = "Official document"
    for name, content in page.documents.items():
        lines.extend(("", f"=== {document_heading}: {name} ===", content.rstrip()))
    return "\n".join(lines).rstrip()


def sample_story_document(page: TutorialPage) -> tuple[str, str] | None:
    """Return the official public story document, when the tutorial provides one."""
    for encoded_name, content in page.documents.items():
        decoded_name = unquote(encoded_name).casefold()
        decoded_stem = Path(decoded_name).stem
        if decoded_stem in SAMPLE_STORY_EXACT_STEMS or any(
            marker.casefold() in decoded_stem for marker in SAMPLE_STORY_NAME_MARKERS
        ):
            return decoded_name, content
    return None


def write_sample_story(page: TutorialPage, input_dir: Path) -> Path:
    """Write the verified public story as a local reference without overwriting."""
    document = sample_story_document(page)
    if document is None:
        if page.language == "ja":
            raise FileNotFoundError(
                "この公式チュートリアルには保存できる公開ストーリーがありません"
            )
        raise FileNotFoundError(
            "This official tutorial does not provide a public sample story"
        )

    source_name, content = document
    if page.language == "ja":
        header = f"""# 参考用サンプルストーリー

- 公式チュートリアル: {page.url}
- YouTube動画ID: `{page.video_id}`
- 元資料: `{source_name}`

このファイルは作り方を理解するための参考資料です。本番用の文章ではありません。
NijiUnitが制作に使ったキャラクター画像・動画・音声は公開されていません。元作品の人物や物語を複製せず、ご自身の題材とキャラクターで`story.md`を作成してください。

---

"""
    else:
        header = f"""# Sample story for reference

- Official tutorial: {page.url}
- YouTube video ID: `{page.video_id}`
- Source document: `{source_name}`

This file is reference material for understanding the production method; it is not the production story.
The character images, videos, and audio used by NijiUnit are not published. Do not copy the original characters or story; create `story.md` from your own subject and characters.

---

"""

    destination = input_dir / "sample_story.md"
    rendered = f"{header}{content.rstrip()}\n"
    if destination.exists():
        if destination.read_text(encoding="utf-8") == rendered:
            return destination
        if page.language == "ja":
            raise FileExistsError(
                "input/sample_story.mdは既にあり、内容が異なります。上書きしません"
            )
        raise FileExistsError(
            "input/sample_story.md already exists with different content; it was not overwritten"
        )
    input_dir.mkdir(parents=True, exist_ok=True)
    destination.write_text(rendered, encoding="utf-8")
    return destination
