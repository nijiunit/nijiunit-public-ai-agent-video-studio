# AIモデル使用記録 — 星のむこうの虹

- 作品名: 星のむこうの虹
- 制作版: public demo v001
- 制作日: 2026-08-05
- 最終尺: 30.00秒（10ショット×3秒）
- 映像: 1280×720、24fps、16:9、H.264
- 音声: AAC、48kHz、ステレオ
- 最終MP4: `demo.mp4`
- SHA-256: `e1d1c4fcc72f48dec90675f553cc49ef2090acdd1e4013ebe40fe299002b936e`

## 工程別のAI・ローカル処理

| 工程 | 提供元・モデル | 用途 | 主な入力 | 出力・採用範囲 | 再生成・人の判断 |
|---|---|---|---|---|---|
| 企画・脚本 | OpenAI Codex（セッションの正確な基盤モデルIDはUIから非公開） | 30秒の物語、台詞、10ショット構成、場面固定情報 | 利用者が示したミオと光の友達、宇宙、地球、虹の台地という案 | `input/story.md`、`storyboard.json`、`environment_bible.json` | 4場面10ショットへ整理。台詞はS003とS010だけに限定 |
| キャラクター外見 | 承認済みの公開用生成素材 | ミオとルクスの同一性 | 公開可能な架空キャラクターの正式identity画像 | v002の正式identity画像 | 非公開作品、実在人物、既存キャラクターを参照していない |
| 飛行用全身開始画 | OpenAI Codex内蔵imagegen（正確なモデルIDはUIから非公開） | ミオの浮遊姿勢を固定 | ミオの公開identity画像と外見・禁止事項 | `assets/mio_hover_start.png` | 16:9、脚を下げた直立浮遊、翼・噴射なしを採用 |
| キャラクターデザイン動画 | Google `gemini-omni-flash-preview` | 無重力飛行、降下、着地、友達飛行、誘いの発光 | 公開identity画像、動作タイミング、禁止事項 | ミオ3本、ルクス2本の新規3秒動画と各3キーフレーム | ミオの目が青くなった降下・着地初稿を不採用。余分なリングや暗転が出たルクス発光初稿・第2稿を不採用。全7動作を検査 |
| 本編開始画像 | OpenAI Codex内蔵imagegen | 宇宙、地球接近、雲上、地上の開始構図 | ミオとルクスの公開identity、場面固定情報 | `assets/shot_001_start.png`、`shot_004_start.png`、`shot_006_start.png`、`shot_008_start.png` | 全4枚を1280×720へ統一し、人物数、三枚翼、地球数、川・滝・虹の位置を確認 |
| 3秒動画 | Google `gemini-omni-flash-preview` | S001〜S010 | 場面開始画像または直前最終フレーム、台帳identity、通常存在と発動動作のキーフレーム、禁止事項 | 全30秒の映像 | 全90コマを確認。ルクスが一時的に四枚翼になったS003初稿を不採用にし、光だけで誘う第2稿を採用 |
| TTS | Google `gemini-3.1-flash-tts-preview` | ルクスとミオの専用日本語音声 | `storyboard.json`の正確な台詞とショット別話者設定 | S003 `Kore` 2.436秒、S010 `Achird` 1.674秒 | 動画生成APIの音声は不使用 |
| 音声確認 | faster-whisper `small`（ローカル） | 専用TTSの文字起こし照合 | S003・S010のWAV | 「ねえ あの青い星へ行こうよ」「綺麗な星だね」 | 句読点・表記差を除き台本と一致 |
| 環境音・余韻音 | FFmpegのローカル合成 | 静かな宇宙、空の風、地上の自然音、S003・S010の短い余韻 | seed固定pink-noise、sine波、場面別フィルター | 全10ショットのクリーン音声 | 第三者音源なし、生成AIなし、`space-to-nature`プロファイル使用 |
| 音楽 | 未使用 | — | — | — | 第三者音楽なし |
| 字幕・連結 | FFmpeg / libass / libx264 | 正確な日本語字幕、3秒クリップ連結 | 検証済み動画、専用TTS、台詞 | `demo.mp4` | 動画モデルに文字を描かせず、S003とS010へローカル描画 |
| 映像確認 | ローカルFFmpeg、Pillow、OpenAI Codexの視覚確認 | 3秒仕様、全90コマ、字幕フレーム、最終MP4検査 | デザイン動画、本編クリップ、完成版 | `docs/character-motion-contact-sheet.jpg`、`docs/story-video-contact-sheet.jpg` | 最終版30.00秒、1280×720、24fps、音声ありを確認 |

## ショット別動画モデル

| ショット | モデル | 開始方式 | 発動した台帳動作 |
|---|---|---|---|
| S001 | `gemini-omni-flash-preview` | 正式開始画像 | ミオ`zero_gravity_flight`、ルクス`friend_flight`、両者通常存在 |
| S002 | `gemini-omni-flash-preview` | S001最終フレーム | ミオ`zero_gravity_flight`、ルクス`friend_flight`、両者通常存在 |
| S003 | `gemini-omni-flash-preview` | S002最終フレーム | ミオ`zero_gravity_flight`、ルクス`friend_flight`＋`invitation_pulse`、両者通常存在 |
| S004 | `gemini-omni-flash-preview` | 正式開始画像 | ミオ`zero_gravity_flight`、ルクス`friend_flight`、両者通常存在 |
| S005 | `gemini-omni-flash-preview` | S004最終フレーム | ミオ`zero_gravity_flight`、ルクス`friend_flight`、両者通常存在 |
| S006 | `gemini-omni-flash-preview` | 正式開始画像 | ミオ`legs_down_descent`、両者通常存在 |
| S007 | `gemini-omni-flash-preview` | S006最終フレーム | ミオ`legs_down_descent`、両者通常存在 |
| S008 | `gemini-omni-flash-preview` | 正式開始画像 | ミオ`soft_landing`、両者通常存在 |
| S009 | `gemini-omni-flash-preview` | S008最終フレーム | 両者通常存在 |
| S010 | `gemini-omni-flash-preview` | S009最終フレーム | 両者通常存在 |

## 公開・権利確認

- 完全架空のミオとルクス、および公開サンプル専用に生成した宇宙・地球・自然風景だけを使用。
- 実在人物、家族、ペット、既存キャラクター、顧客素材、過去作品、第三者音楽を不使用。
- コードはMIT。公開デモ素材は`ASSET_LICENSES.md`記載のCC BY 4.0。
- APIキー、個人パス、provider operation ID、動画生成APIの元音声を不掲載。
