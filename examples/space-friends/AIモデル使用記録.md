# AIモデル使用記録 — 星のむこうの虹

- 作品名: 星のむこうの虹
- 制作版: public demo v002
- 制作日: 2026-08-06
- 最終尺: 30.00秒（10ショット×3秒）
- 映像: 1280×720、24fps、16:9、H.264
- 音声: AAC、48kHz、ステレオ、完成ミックス約-16.00 LUFS
- 最終MP4: `demo.mp4`
- SHA-256: `2f980282adccf5e70f4f207577cdb57cd1d46974a612af53c9a324ab8a6b1f24`

## 工程別のAI・ローカル処理

| 工程 | 提供元・モデル | 用途 | 主な入力 | 出力・採用範囲 | 再生成・人の判断 |
|---|---|---|---|---|---|
| 企画・脚本・コンテ改訂 | OpenAI Codex（セッションの正確な基盤モデルIDはUIから非公開） | 既存の10ショットを、雲の急降下、川の追走、滝横断、草原低空飛行、着地へ再構成 | 利用者の「滝へ近づく」「虹をすり抜ける」「映画の一場面」「風と滝の音」という要望、v001コンテ | `storyboard.json`、音響時間軸、検査条件 | S006〜S010を15秒の連続した見せ場へ改訂。首の逆向きと無音の口元を明示的な禁止事項に追加 |
| キャラクター外見 | 公開デモ用の承認済み生成素材 | ミオとルクスの同一性固定 | v002 identity画像、外見台帳、禁止事項 | v002正式identity画像 | 完全架空。実在人物、既存キャラクター、非公開作品を不使用 |
| キャラクターデザイン動画 | Google `gemini-omni-flash-preview` | 映画的降下と草原低空飛行を専用動作として追加 | ミオの正式identity、正面全身開始画、頭・首・胴体の同軸条件、サービスシーム固定条件 | `cinematic_descent`、`low_altitude_flight`の新規3秒MP4と各3キーフレーム | 2本とも3.00秒、1280×720、24fps、9コマで検査し`approved`。既存5動作も再検証 |
| 見せ場の開始画像 | OpenAI Codex内蔵imagegen（正確なモデルIDはUIから非公開） | 急降下、滝横断、草原低空飛行の映画的な構図を固定 | ミオとルクスの正式identity、v001の台地地理、川・滝・山・虹の固定条件 | `assets/shot_006_start_v002.png`、`shot_008_start_v002.png`、`shot_009_start_v002.png` | ミオの首方向、ルクスの三枚翼、同一の川・滝・山・虹を目視確認し、3枚を1280×720へ統一 |
| 3秒動画 | Google `gemini-omni-flash-preview` | S003、S006〜S010の再生成 | 開始画像または直前最終フレーム、identity、発動動作3キーフレーム、禁止事項 | 新規18秒分を採用 | 6ショット54コマを拡大確認。全10ショット90コマでも、首の逆向き、増殖、余分な翼、地形変形を確認 |
| 既存合格ショット | Google `gemini-omni-flash-preview` | S001、S002、S004、S005 | v001で生成・検査済みの宇宙飛行と地球接近 | 合格済み12秒分を継承 | 映像内容を変える必要がないため再API生成せず、v002でも再度36コマを確認 |
| TTS | Google `gemini-3.1-flash-tts-preview` | ルクスとミオの専用日本語音声 | `storyboard.json`の正確な台詞とショット別話者設定 | S003 `Kore` 2.436秒、S010 `Achird` 1.674秒 | v001の検証済みWAVを継承。動画生成APIの音声は不使用 |
| 映画的音響 | ローカルPython、FFmpeg | 宇宙の連続パッド、機械音、発光音、上昇する風、川、滝、飛沫、草、着地音を30秒の一本の時間軸で合成 | seed固定ノイズ、sine波、承認済みTTS、ショット時刻 | `scripts/build_cinematic_soundtrack.py`、48kHzステレオ | 第三者音源・生成AI音源なし。滝は21〜24秒で最大化し左から右へ移動。台詞中は背景を約42%下げる |
| 音量仕上げ | FFmpeg `loudnorm`、`acompressor` | 環境音の遠近と台詞の明瞭さを保ったまま全体音量を調整 | 合成前WAV | 完成ミックス約-16.00 LUFS、解析true peak -3.90dBFS | 冒頭0〜6秒は平均-30.5dB前後、滝横断は平均-18.4dB。無音区間なしを波形と区間別音量で確認 |
| 音声確認 | faster-whisper `small`（ローカル） | 背景音を含む完成ミックスの文字起こし | `cinematic_mix.wav` | 「ねえ、あの青い星へ行こうよ」「綺麗な星だね」 | 両台詞を認識。句読点、長音の表記差を除き台本と一致 |
| 字幕・連結 | FFmpeg / libass / libx264 | 正確な日本語字幕、10本の3秒クリップ連結、完成音声の明示的mux | 検証済み動画、字幕、完成ミックス | `demo.mp4` | 動画モデルに文字を描かせず、S003とS010へローカル描画。動画API由来の音声を完成版へ引き継がない |
| 映像確認 | ローカルFFmpeg、Pillow、OpenAI Codexの視覚確認 | 全90コマ、字幕、首・口元・翼数、最終MP4仕様を検査 | デザイン動画、本編クリップ、完成版 | `docs/character-motion-contact-sheet.jpg`、`docs/story-video-contact-sheet.jpg` | 最終版30.00秒、1280×720、24fps、音声あり、字幕ありを確認 |
| 音楽 | 未使用 | — | — | — | 第三者音楽なし |

## v002で生成した開始画像

| ショット | 保存先 | imagegenへの主な指示 |
|---|---|---|
| S006 | `assets/shot_006_start_v002.png` | 雲の切れ間から川へ向かう斜め急降下。ミオの頭・黒い首・胴体を同方向にし、ルクスは三枚翼。既存の山、蛇行する川、右の滝、虹を固定 |
| S008 | `assets/shot_008_start_v002.png` | 巨大な滝のすぐ横を二人が並走。水滴とミストを前景に置き、ルクスの金色光が自然な虹へ屈折。固体の虹トンネルにはしない |
| S009 | `assets/shot_009_start_v002.png` | 草原の1〜2m上を低空飛行。手前の草を大きくして強い視差を作り、遠景に同じ川、滝、山、虹を残す |

生成時の原寸画像はCodexの生成画像保存領域にも残し、公開用には上記3ファイルへ1280×720で複写しました。

## ショット別動画モデル

| ショット | モデル | v002での扱い | 開始方式 | 発動した台帳動作 |
|---|---|---|---|---|
| S001 | `gemini-omni-flash-preview` | v001合格版を継承 | 正式開始画像 | ミオ`zero_gravity_flight`、ルクス`friend_flight` |
| S002 | `gemini-omni-flash-preview` | v001合格版を継承 | S001最終フレーム | ミオ`zero_gravity_flight`、ルクス`friend_flight` |
| S003 | `gemini-omni-flash-preview` | v002で再生成 | S002最終フレーム | ミオ`zero_gravity_flight`、ルクス`friend_flight`＋`invitation_pulse`。ミオのサービスシームを固定 |
| S004 | `gemini-omni-flash-preview` | v001合格版を継承 | 正式開始画像 | ミオ`zero_gravity_flight`、ルクス`friend_flight` |
| S005 | `gemini-omni-flash-preview` | v001合格版を継承 | S004最終フレーム | ミオ`zero_gravity_flight`、ルクス`friend_flight` |
| S006 | `gemini-omni-flash-preview` | v002で再生成 | v002正式開始画像 | ミオ`cinematic_descent`、ルクス`friend_flight` |
| S007 | `gemini-omni-flash-preview` | v002で再生成 | S006最終フレーム | ミオ`cinematic_descent`、ルクス`friend_flight` |
| S008 | `gemini-omni-flash-preview` | v002で再生成 | v002正式開始画像 | ミオ`cinematic_descent`、ルクス`friend_flight` |
| S009 | `gemini-omni-flash-preview` | v002で再生成 | v002正式開始画像 | ミオ`low_altitude_flight`、ルクス`friend_flight` |
| S010 | `gemini-omni-flash-preview` | v002で再生成 | S009最終フレーム | ミオ`soft_landing`、ルクス通常存在 |

## 音響時間軸

| 時刻 | 主な音 | 目的 |
|---|---|---|
| 0〜6秒 | 映画的パッド、ミオの機械音、ルクスの共鳴 | 静かな宇宙を無音にしない |
| 6〜9秒 | ルクスの台詞、短い発光音 | 発話者を光の変化と音で一致させる |
| 9〜15秒 | 期待感のある低音、徐々に増える風 | 地球接近から急降下へつなぐ |
| 15〜21秒 | 高空の風、川、近づく滝 | 高度と速度の変化を音で伝える |
| 21〜24秒 | 滝の低音・水音・飛沫、左から右への通過 | 映像最大の見せ場を作る |
| 24〜27秒 | 草を切る風、川、遠ざかる滝 | 地上すれすれの速度と減速を伝える |
| 27〜30秒 | 着地音、弱い風と水音、ミオの台詞、ルクスの余韻音 | 静けさとの対比で結末を聞かせる |

## 公開・権利確認

- 完全架空のミオとルクス、および公開サンプル専用に生成した宇宙・地球・自然風景だけを使用。
- 実在人物、家族、ペット、既存キャラクター、顧客素材、過去作品、第三者音楽・効果音を不使用。
- コードはMIT。公開デモ素材は`ASSET_LICENSES.md`記載のCC BY 4.0。
- APIキー、個人パス、provider operation ID、動画生成APIの元音声を不掲載。
- v001の記録は`history/v001/AIモデル使用記録.md`に保存。
