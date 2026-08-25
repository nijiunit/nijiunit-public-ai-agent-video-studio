from __future__ import annotations

from html import escape
from pathlib import Path

from PIL import Image

from .schema import Shot, Storyboard


def _timecode(seconds: int) -> str:
    return f"{seconds // 60:02d}:{seconds % 60:02d}"


def _text(value: str) -> str:
    return escape(value or "—").replace("\n", "<br>")


def _labels(language: str) -> dict[str, str]:
    if language == "en":
        return {
            "page_title": "Storyboard review",
            "video_title": "Video frame review",
            "official": (
                "The Excel workbook is the official production record. "
                "This local HTML page is an offline review option when a "
                "spreadsheet application is unavailable."
            ),
            "privacy": (
                "Nothing on this page is uploaded. Images, text, and review "
                "entries stay on this computer."
            ),
            "steps": (
                "Review one shot at a time. Mark OK or Needs correction. "
                "Then create a summary and paste it into the AI-agent chat."
            ),
            "progress": "reviewed",
            "purpose": "Story purpose",
            "scene": "Visible scene",
            "characters": "Characters",
            "action": "Action",
            "emotion": "Emotion",
            "camera": "Camera",
            "lighting": "Lighting",
            "dialogue": "Dialogue",
            "narration": "Narration",
            "sound": "Sound",
            "continuity": "Continuity",
            "frames": "Nine-frame plan",
            "real_frames": "Nine frames extracted from the generated video",
            "status": "Review result",
            "pending": "Not reviewed",
            "ok": "OK",
            "revise": "Needs correction",
            "instruction": "Correction request",
            "placeholder": "Example: In S003, move the character slightly left.",
            "summary": "Create a summary for the AI agent",
            "copy": (
                "Copy the text below and paste it into the AI-agent chat. "
                "If every shot is OK, say: Storyboard approved."
            ),
            "copy_button": "Create and copy summary",
            "copied": "The summary was copied.",
            "reset": "Reset review entries",
            "reset_confirm": "Clear all review entries saved in this browser?",
            "frame_alt": "review frame",
        }
    return {
        "page_title": "絵コンテ確認",
        "video_title": "生成動画9コマ確認",
        "official": (
            "正式な制作記録はExcelコンテです。このローカルHTMLは、Excelなどの"
            "表計算アプリがない場合でも同じ内容を確認するための画面です。"
        ),
        "privacy": (
            "この画面の内容は外部へ送信されません。画像・文章・確認結果は"
            "このパソコン内だけで扱われます。"
        ),
        "steps": (
            "上から1ショットずつ確認し、「OK」または「修正が必要」を選んでください。"
            "最後に確認結果を作り、AIエージェントとのチャットへ貼り付けます。"
        ),
        "progress": "確認済み",
        "purpose": "物語上の役割",
        "scene": "画面の説明",
        "characters": "登場キャラクター",
        "action": "3秒間の動き",
        "emotion": "表情・感情",
        "camera": "カメラ",
        "lighting": "光・色",
        "dialogue": "セリフ",
        "narration": "ナレーション",
        "sound": "音",
        "continuity": "前後との連続性",
        "frames": "9コマ計画",
        "real_frames": "生成動画から取り出した9コマ",
        "status": "確認結果",
        "pending": "まだ確認していない",
        "ok": "OK",
        "revise": "修正が必要",
        "instruction": "修正してほしいこと",
        "placeholder": "例：S003の人物を、もう少し左へ移動してください。",
        "summary": "AIエージェントへ伝える確認結果を作る",
        "copy": (
            "下の文章をAIエージェントとのチャットへ貼り付けてください。"
            "全部OKなら「絵コンテを承認します」と伝えてください。"
        ),
        "copy_button": "確認結果を作ってコピー",
        "copied": "確認結果をコピーしました。",
        "reset": "この画面の入力を消す",
        "reset_confirm": "このブラウザーに保存した確認結果をすべて消しますか？",
        "frame_alt": "確認用コマ",
    }


def _prepare_review_image(source: Path, destination: Path) -> None:
    destination.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(source) as image:
        converted = image.convert("RGB")
        converted.thumbnail((960, 540), Image.Resampling.LANCZOS)
        converted.save(
            destination,
            "JPEG",
            quality=86,
            optimize=True,
            progressive=True,
        )


def _review_asset_dir(destination: Path) -> Path:
    stem = destination.stem
    for suffix in (".ja", ".en"):
        if stem.endswith(suffix):
            stem = stem.removesuffix(suffix)
            break
    return destination.parent / f"{stem}_assets"


def _detail_fields(shot: Shot, labels: dict[str, str]) -> str:
    fields = (
        (labels["purpose"], shot.story_purpose),
        (labels["scene"], shot.scene_description),
        (labels["characters"], "、".join(shot.characters) or "—"),
        (labels["action"], shot.action),
        (labels["emotion"], shot.emotion),
        (labels["camera"], shot.camera),
        (labels["lighting"], shot.lighting),
        (labels["dialogue"], shot.dialogue or "—"),
        (labels["narration"], shot.narration or "—"),
        (labels["sound"], shot.sound),
        (labels["continuity"], shot.continuity),
    )
    return "".join(
        f"<dt>{escape(label)}</dt><dd>{_text(value)}</dd>"
        for label, value in fields
    )


def _planned_frames(shot: Shot) -> str:
    items = "".join(
        f"<li><b>{index / 3:.3f}s</b><span>{_text(description)}</span></li>"
        for index, description in enumerate(shot.frame_descriptions)
    )
    return f'<ol class="frames">{items}</ol>'


def _video_frames(
    shot: Shot,
    run_dir: Path,
    asset_dir: Path,
    labels: dict[str, str],
) -> str:
    figures: list[str] = []
    for frame_index, description in enumerate(shot.frame_descriptions, start=1):
        source = (
            run_dir
            / "frames"
            / f"shot_{shot.shot_number:03d}"
            / f"frame_{frame_index:02d}.jpg"
        )
        if not source.is_file():
            raise FileNotFoundError(f"Missing extracted video frame: {source}")
        destination = (
            asset_dir
            / f"shot_{shot.shot_number:03d}_frame_{frame_index:02d}.jpg"
        )
        _prepare_review_image(source, destination)
        relative = f"{asset_dir.name}/{destination.name}"
        time = (frame_index - 1) / 3
        alt = (
            f"S{shot.shot_number:03d} {labels['frame_alt']} "
            f"{frame_index} {time:.3f}s"
        )
        figures.append(
            "<figure>"
            f'<img src="{escape(relative)}" alt="{escape(alt)}">'
            f"<figcaption><b>{time:.3f}s</b><span>{_text(description)}</span>"
            "</figcaption></figure>"
        )
    return f'<div class="video-frames">{"".join(figures)}</div>'


def _shot_card(
    shot: Shot,
    main_image_relative: str,
    frame_markup: str,
    frame_heading: str,
    labels: dict[str, str],
) -> str:
    number = f"S{shot.shot_number:03d}"
    return f"""
    <article class="shot" id="{number}" data-shot="{number}">
      <header>
        <h2>{number}　{escape(shot.title)}</h2>
        <span>{_timecode(shot.start_seconds)}–{_timecode(shot.end_seconds)}</span>
      </header>
      <img class="main-image" src="{escape(main_image_relative)}"
           alt="{number} {escape(shot.title)}">
      <dl>{_detail_fields(shot, labels)}</dl>
      <h3>{escape(frame_heading)}</h3>
      {frame_markup}
      <section class="review-box">
        <label>{escape(labels['status'])}
          <select class="status">
            <option value="pending">{escape(labels['pending'])}</option>
            <option value="ok">{escape(labels['ok'])}</option>
            <option value="revise">{escape(labels['revise'])}</option>
          </select>
        </label>
        <label>{escape(labels['instruction'])}
          <textarea class="instruction"
                    placeholder="{escape(labels['placeholder'])}"></textarea>
        </label>
      </section>
    </article>
    """


def create_review_html(
    storyboard: Storyboard,
    run_dir: Path,
    destination: Path,
    *,
    language: str,
    video_frames: bool = False,
) -> Path:
    """Create an offline, large-text review page with no network dependency."""
    if language not in {"ja", "en"}:
        raise ValueError("language must be 'ja' or 'en'")
    labels = _labels(language)
    asset_dir = _review_asset_dir(destination)
    cards: list[str] = []
    for shot in storyboard.shots:
        source = run_dir / "images" / f"shot_{shot.shot_number:03d}.png"
        if not source.is_file():
            raise FileNotFoundError(f"Missing storyboard image: {source}")
        main_target = asset_dir / f"shot_{shot.shot_number:03d}_main.jpg"
        _prepare_review_image(source, main_target)
        main_relative = f"{asset_dir.name}/{main_target.name}"
        if video_frames:
            frame_markup = _video_frames(shot, run_dir, asset_dir, labels)
            frame_heading = labels["real_frames"]
        else:
            frame_markup = _planned_frames(shot)
            frame_heading = labels["frames"]
        cards.append(
            _shot_card(
                shot,
                main_relative,
                frame_markup,
                frame_heading,
                labels,
            )
        )

    page_title = labels["video_title"] if video_frames else labels["page_title"]
    css_aspect_ratio = storyboard.aspect_ratio.replace(":", "/")
    html = f"""<!doctype html>
<html lang="{language}">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{escape(storyboard.title)} — {escape(page_title)}</title>
<style>
:root {{ color-scheme: light; font-family: system-ui, -apple-system, "Segoe UI", sans-serif; font-size: 19px; }}
body {{ margin: 0; background: #edf2f7; color: #17202a; line-height: 1.6; }}
.hero {{ background: #173a5e; color: white; padding: 28px max(24px, calc((100% - 1180px)/2)); }}
.hero h1 {{ margin: 0 0 14px; font-size: clamp(1.7rem, 4vw, 2.5rem); }}
.notice {{ background: #fff4cc; color: #3b2f00; border-left: 8px solid #f2b705; padding: 16px; margin-top: 14px; }}
.privacy {{ background: #dff4e5; color: #123d20; border-left: 8px solid #26964d; padding: 16px; margin-top: 12px; }}
.progress {{ position: sticky; top: 0; z-index: 10; background: #0f263d; color: white; padding: 12px 24px; font-weight: 700; }}
main {{ max-width: 1180px; margin: 28px auto; padding: 0 20px 60px; }}
.shot {{ background: white; border-radius: 14px; margin: 0 0 30px; padding: 22px; box-shadow: 0 4px 18px #18324a22; }}
.shot header {{ display: flex; justify-content: space-between; gap: 20px; align-items: baseline; border-bottom: 3px solid #2c6e9f; margin-bottom: 18px; }}
.shot h2 {{ margin: 0 0 10px; font-size: 1.45rem; }}
.main-image {{ display: block; width: min(100%, 960px); aspect-ratio: {css_aspect_ratio}; object-fit: contain; background: #101820; margin: 0 auto 22px; border-radius: 8px; }}
dl {{ display: grid; grid-template-columns: minmax(9rem, 15rem) 1fr; gap: 0; border: 1px solid #c8d4df; }}
dt, dd {{ margin: 0; padding: 11px 13px; border-bottom: 1px solid #dce4eb; }}
dt {{ background: #e8f2f8; font-weight: 700; }}
.frames {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 10px; padding: 0; list-style: none; }}
.frames li {{ border: 1px solid #bac8d4; border-radius: 8px; padding: 10px; background: #f7fafc; }}
.frames b, .frames span {{ display: block; }}
.video-frames {{ display: grid; grid-template-columns: repeat(3, 1fr); gap: 12px; }}
.video-frames figure {{ margin: 0; padding: 8px; border: 1px solid #bac8d4; border-radius: 8px; background: #f7fafc; }}
.video-frames img {{ width: 100%; aspect-ratio: {css_aspect_ratio}; object-fit: contain; background: #101820; }}
.video-frames b, .video-frames span {{ display: block; }}
.review-box {{ margin-top: 20px; padding: 18px; background: #fff7cf; border: 3px solid #e6b800; border-radius: 10px; }}
.review-box label {{ display: block; font-weight: 700; margin-bottom: 14px; }}
select, textarea, button {{ font: inherit; }}
select {{ display: block; min-width: 14rem; padding: 8px; margin-top: 7px; }}
textarea {{ display: block; box-sizing: border-box; width: 100%; min-height: 95px; padding: 10px; margin-top: 7px; }}
.finish {{ background: white; border-radius: 14px; padding: 22px; }}
button {{ padding: 12px 18px; border: 0; border-radius: 8px; background: #1769aa; color: white; font-weight: 700; cursor: pointer; margin: 8px 8px 8px 0; }}
button.secondary {{ background: #687581; }}
#summary {{ width: 100%; min-height: 180px; box-sizing: border-box; margin-top: 12px; }}
#copy-result {{ min-height: 1.6em; font-weight: 700; color: #17602d; }}
@media (max-width: 760px) {{ dl {{ grid-template-columns: 1fr; }} .frames, .video-frames {{ grid-template-columns: 1fr; }} .shot header {{ display: block; }} }}
</style>
</head>
<body>
<section class="hero">
  <h1>{escape(storyboard.title)} — {escape(page_title)}</h1>
  <p>{_text(storyboard.logline)}</p>
  <div class="notice"><b>{escape(labels['official'])}</b><br>{escape(labels['steps'])}</div>
  <div class="privacy">{escape(labels['privacy'])}</div>
</section>
<div class="progress"><span id="progress">0 / {len(storyboard.shots)}</span> {escape(labels['progress'])}</div>
<main>
{''.join(cards)}
<section class="finish">
  <h2>{escape(labels['summary'])}</h2>
  <p>{escape(labels['copy'])}</p>
  <button id="make-summary">{escape(labels['copy_button'])}</button>
  <button class="secondary" id="reset">{escape(labels['reset'])}</button>
  <p id="copy-result" role="status" aria-live="polite"></p>
  <textarea id="summary" readonly aria-label="{escape(labels['summary'])}"></textarea>
</section>
</main>
<script>
const key = 'nijiunit-review-' + location.pathname;
const shots = [...document.querySelectorAll('.shot')];
function load() {{
  let saved = {{}};
  try {{ saved = JSON.parse(localStorage.getItem(key) || '{{}}'); }} catch (_) {{ saved = {{}}; }}
  shots.forEach(card => {{
    const item = saved[card.dataset.shot] || {{}};
    card.querySelector('.status').value = item.status || 'pending';
    card.querySelector('.instruction').value = item.instruction || '';
  }});
  updateProgress();
}}
function save() {{
  const data = {{}};
  shots.forEach(card => data[card.dataset.shot] = {{
    status: card.querySelector('.status').value,
    instruction: card.querySelector('.instruction').value
  }});
  localStorage.setItem(key, JSON.stringify(data));
  updateProgress();
}}
function updateProgress() {{
  const done = shots.filter(card => card.querySelector('.status').value !== 'pending').length;
  document.getElementById('progress').textContent = `${{done}} / ${{shots.length}}`;
}}
shots.forEach(card => card.querySelectorAll('select,textarea').forEach(input => input.addEventListener('input', save)));
document.getElementById('make-summary').addEventListener('click', async () => {{
  const lines = ['{escape(storyboard.title)}'];
  shots.forEach(card => {{
    const status = card.querySelector('.status');
    const label = status.options[status.selectedIndex].text;
    const instruction = card.querySelector('.instruction').value.trim();
    lines.push(`${{card.dataset.shot}}: ${{label}}${{instruction ? ' — ' + instruction : ''}}`);
  }});
  const output = document.getElementById('summary');
  output.value = lines.join('\n');
  output.focus();
  output.select();
  try {{
    await navigator.clipboard.writeText(output.value);
  }} catch (_) {{ document.execCommand('copy'); }}
  document.getElementById('copy-result').textContent = '{escape(labels['copied'])}';
}});
document.getElementById('reset').addEventListener('click', () => {{
  if (window.confirm('{escape(labels['reset_confirm'])}')) {{
    localStorage.removeItem(key);
    load();
  }}
}});
load();
</script>
</body>
</html>
"""
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(html, encoding="utf-8")
    return destination
