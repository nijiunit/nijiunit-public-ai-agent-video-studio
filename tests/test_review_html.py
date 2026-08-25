from pathlib import Path
from xml.etree import ElementTree
from zipfile import ZipFile

import pytest
from openpyxl import load_workbook
from PIL import Image

from scripts.build_html_review_from_workbook import extract_main_images
from video_storyboard.review_html import create_review_html
from video_storyboard.schema import CharacterProfile, Shot, Storyboard
from video_storyboard.workbook import create_workbook


def make_storyboard(aspect_ratio: str = "16:9") -> Storyboard:
    return Storyboard(
        title="虹の旅",
        logline="ロボットと光の友達が虹の台地へ向かう。",
        audience="家族",
        visual_style="映画的",
        aspect_ratio=aspect_ratio,
        story_summary="旅",
        character_bible=[CharacterProfile(name="ミオ", description="ロボット")],
        shots=[
            Shot(
                shot_number=1,
                title="出発",
                story_purpose="旅の始まり",
                scene_description="宇宙を並んで飛ぶ",
                characters=["ミオ", "ルクス"],
                action="前へ飛ぶ",
                emotion="期待",
                camera="追従",
                lighting="星明かり",
                dialogue="行こうよ",
                narration="",
                sound="静かな宇宙音",
                continuity="同じ姿",
                reference_assets=[],
                main_image_prompt="robot and light",
                video_prompt="fly forward",
                frame_descriptions=[f"変化 {number}" for number in range(1, 10)],
            )
        ],
    )


def prepare_images(run_dir: Path) -> None:
    image_dir = run_dir / "images"
    image_dir.mkdir(parents=True)
    Image.new("RGB", (320, 180), "navy").save(image_dir / "shot_001.png")


def test_storyboard_review_html_is_bilingual_offline_and_accessible(
    tmp_path: Path,
) -> None:
    storyboard = make_storyboard()
    prepare_images(tmp_path)

    japanese = create_review_html(
        storyboard,
        tmp_path,
        tmp_path / "review" / "storyboard_review.ja.html",
        language="ja",
    )
    english = create_review_html(
        storyboard,
        tmp_path,
        tmp_path / "review" / "storyboard_review.en.html",
        language="en",
    )

    ja_text = japanese.read_text(encoding="utf-8")
    en_text = english.read_text(encoding="utf-8")
    assert "上から1ショットずつ確認" in ja_text
    assert "修正してほしいこと" in ja_text
    assert "Nothing on this page is uploaded" in en_text
    assert "aria-live=\"polite\"" in ja_text
    assert "http://" not in ja_text and "https://" not in ja_text
    assert (
        japanese.parent / "storyboard_review_assets" / "shot_001_main.jpg"
    ).is_file()


def test_video_review_html_embeds_nine_real_frame_files(tmp_path: Path) -> None:
    storyboard = make_storyboard()
    prepare_images(tmp_path)
    frame_dir = tmp_path / "frames" / "shot_001"
    frame_dir.mkdir(parents=True)
    for number in range(1, 10):
        Image.new("RGB", (320, 180), (number * 10, 20, 30)).save(
            frame_dir / f"frame_{number:02d}.jpg"
        )

    output = create_review_html(
        storyboard,
        tmp_path,
        tmp_path / "final" / "video_review.ja.html",
        language="ja",
        video_frames=True,
    )

    text = output.read_text(encoding="utf-8")
    assert "生成動画から取り出した9コマ" in text
    assert text.count("<figure>") == 9


def test_legacy_workbook_can_be_converted_without_generation_api(
    tmp_path: Path,
) -> None:
    storyboard = make_storyboard()
    prepare_images(tmp_path)
    workbook = tmp_path / "storyboard_v001.xlsx"
    create_workbook(storyboard, tmp_path, [], workbook)

    extracted_dir = tmp_path / "legacy" / "images"
    count = extract_main_images(workbook, extracted_dir)

    assert count == 1
    assert (extracted_dir / "shot_001.png").is_file()


@pytest.mark.parametrize("aspect_ratio", ["9:16", "16:9"])
def test_excel_and_html_keep_the_selected_aspect_ratio(
    tmp_path: Path,
    aspect_ratio: str,
) -> None:
    storyboard = make_storyboard(aspect_ratio)
    prepare_images(tmp_path)
    workbook_path = tmp_path / f"storyboard_{aspect_ratio.replace(':', '-')}.xlsx"
    create_workbook(storyboard, tmp_path, [], workbook_path)
    html_path = create_review_html(
        storyboard,
        tmp_path,
        tmp_path
        / "review"
        / f"storyboard_{aspect_ratio.replace(':', '-')}.ja.html",
        language="ja",
    )

    workbook = load_workbook(workbook_path)
    assert workbook["00_全体"]["D3"].value == aspect_ratio
    with ZipFile(workbook_path) as archive:
        drawing = ElementTree.fromstring(
            archive.read("xl/drawings/drawing1.xml")
        )
    extent = drawing.find(
        ".//{http://schemas.openxmlformats.org/drawingml/2006/spreadsheetDrawing}ext"
    )
    assert extent is not None
    image_width = int(extent.attrib["cx"])
    image_height = int(extent.attrib["cy"])
    if aspect_ratio == "9:16":
        assert image_height > image_width
    else:
        assert image_width > image_height
    assert f"aspect-ratio: {aspect_ratio.replace(':', '/')}" in html_path.read_text(
        encoding="utf-8"
    )
