# 星のむこうの虹

完全架空の友達「ミオ」と「ルクス」が、宇宙から青い地球へ向かい、雲を割って急降下し、虹の滝と草原を抜けて緑の台地へ降りる30秒の公開デモです。

![虹の滝のすぐ横を飛ぶミオとルクス](assets/shot_008_start_v002.png)

- [完成デモ（30秒MP4）](demo.mp4)
- [承認済みExcelコンテ](storyboard_approved.xlsx)
- [Excelなしで開ける日本語コンテ](storyboard_approved_review.ja.html)
- [English offline storyboard](storyboard_approved_review.en.html)
- [生成処理用の10ショットJSON](storyboard.json)
- [AIモデル使用記録](AIモデル使用記録.md)
- [映画的音響の測定記録](docs/cinematic-mix-report.json)
- [本編90コマ確認表](docs/story-video-contact-sheet.jpg)
- [キャラクター動作21コマ確認表](docs/character-motion-contact-sheet.jpg)
- [場面固定情報](environment_bible.json)

## このサンプルで確認できること

- 同じ場面では、直前3秒クリップの最終フレームを次の開始フレームへ引き継ぐ
- 動画生成前に、全10ショットのメイン画像と演出情報をExcelで確認・承認する
- 宇宙、地球接近、雲上、地上の切替点では、それぞれ承認済みの開始画像へ戻す
- キャラクター台帳v002に、無重力飛行、映画的降下、低空飛行、着地、並走、誘いの発光を登録する
- 動作動画のMP4を保存し、生成時には時刻付き3キーフレームと動作指示を利用する
- 生成動画APIの音声を除去し、ショット別TTS、連続した映画的音響、正確な字幕を合成する
- 風が強くなる急降下、川の接近、左から右へ通過する滝、草の風圧、着地音を30秒の一本の音響時間軸として設計する
- 10ショット×9コマを目視し、ルクスが四枚翼になったS003初稿を不採用にする

## 初心者がコンテを開く

チャット内のリンクを押すだけでは、パソコン上のファイルが開かない場合があります。AIエージェントは次を実行してフォルダを開き、ExcelがあればExcel、なければ日本語のローカルHTMLを青く選択します。

```powershell
.\.venv\Scripts\python.exe scripts\reveal_artifact.py `
  --path examples\space-friends\storyboard_approved.xlsx --language ja
```

利用者は青く選択されたファイルをダブルクリックします。ローカルHTMLはインターネットへ画像や入力内容を送りません。

## 台帳だけを検証する

```powershell
.\.venv\Scripts\python.exe run_storyboard.py validate-characters `
  --registry-dir examples\space-friends\characters

.\.venv\Scripts\python.exe scripts\validate_character_design_videos.py `
  --registry-dir examples\space-friends\characters
```

## 再生成について

`storyboard_approved.xlsx`が人が確認した正式コンテ、`storyboard.json`が生成処理用データです。`assets/shot_001_start.png`、`shot_004_start.png`、`shot_006_start_v002.png`、`shot_008_start_v002.png`、`shot_009_start_v002.png`が、採用版の場面開始資料です。生成AIの出力は非決定的なので、同じ入力でも同一の映像になる保証はありません。APIを呼ぶ処理には料金や利用上限が発生する場合があります。

公開済みMP4には第三者の音楽・効果音を使っていません。音声は専用TTS、環境音・風・川・滝・草・着地音は`build_cinematic_soundtrack.py`による決定的なローカル合成です。完成音声は約-16 LUFS、48kHzステレオで、ローカルASRにより二つの台詞を再確認しています。
