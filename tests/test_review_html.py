from pathlib import Path

from PIL import Image

from scripts.build_html_review_from_workbook import extract_main_images
from video_storyboard.review_html import create_review_html
from video_storyboard.schema import CharacterProfile, Shot, Storyboard
from video_storyboard.workbook import create_workbook


def make_storyboard() -> Storyboard:
    return Storyboard(
        title="虹の旅",
        logline="ロボットと光の友達が虹の台地へ向かう。",
        audience="家族",
        visual_style="映画的",
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
