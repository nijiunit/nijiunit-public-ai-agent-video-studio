[English](README.md) | 日本語

# nijiunit-public-ai-agent-video-studio

AIエージェントと生成AIを使い、3秒単位の短い動画を、キャラクターの外見と動きをできるだけ保ちながら制作するための公開リファレンス実装です。

このリポジトリは、基本操作、安定した制作既定値、安全装置、人間の承認を守るローカル実行環境です。NijiUnit動画ごとの作り方はホームページの動画別ガイドを毎回直接読み、古い教材キャッシュを使い続けません。人物、台詞、結末などの作品固有情報は利用者の作品データへ置きます。

活動告知やチャンネル登録・Hypeのお願いはYouTube、アプリの正式な版と更新元はGitHubが担当します。詳しい境界は[基本操作](docs/basic-operation.ja.md)と[作業手順](作業手順.md)を参照してください。

このリポジトリで扱う中心課題は、単なる動画生成ではなく、ショットをまたいだ一貫性です。

- 外見・禁止事項・素材の権利を記録する、版管理されたキャラクター台帳
- 通常時と固有動作を新規生成した3秒のキャラクターデザイン動画
- デザイン動画から抽出した時刻付きキーフレームと動作指示
- 直前クリップの最終フレームを次の開始フレームへ渡す連続生成
- 全ショットの開始画像・説明・音・9コマ計画・訂正欄をまとめた正式なExcelコンテ、Excelがない人向けのローカルHTML確認画面、承認前の動画生成を止めるゲート
- 生成動画を9コマで確認し、音声・字幕をローカルで仕上げる工程
- エピソードごとに残すAIモデル使用記録

初心者が実物を確認できる小さな公開サンプル動画、承認済みExcelコンテ、日英HTMLは`examples/space-friends/`に同梱します。完全なHOWTO制作元と作品固有の再現コードは、別リポジトリ`nijiunit-public-ai-agent-video-studio-howto-movie`で管理します。

## 公開版に含めていないもの

このリポジトリは、既存の非公開制作リポジトリを丸ごと公開したものではありません。実在人物、家族やペット、非公開の過去作品、案件固有スクリプト、私的な制作履歴、APIキー、生成サービスの非公開メタデータは含めません。同梱サンプルは架空の公開作品だけです。

## AIエージェントに頼む

クローンしたリポジトリをCodexなどのAIエージェントで開き、次のように依頼できます。

```text
このアプリを使えるようにしてください。
```

AIエージェントは[AGENTS.md](AGENTS.md)に従い、専用セットアップスクリプトを実行して、仮想環境、依存関係、`.env`、FFmpeg、同梱された制作基本設定を診断します。APIキーが未設定なら、画像付きのローカル設定画面を開き、Google AI Studioでの取得、秘密入力、接続確認まで案内します。初心者が通常の手順でターミナルへAPIキーを貼る必要はありません。セットアップ中に生成APIは呼ばず、既存の`.env`も無断で上書きしません。

この依頼は、案内AIによってAIエージェントの導入、Gitの準備、リポジトリのクローン、このフォルダを開くところまで終わった後に行います。以降はこのリポジトリ側が、Python、FFmpeg、Google生成AI APIの料金・課金・APIキー・接続確認を担当します。初心者本人の判断が必要な場面では、現在必要な判断だけを明確に案内します。一つの確認作業に属する通常操作は細切れにしません。

`こんにちは`だけでも、AIエージェントは「NijiUnitのチュートリアルを参考にする」か「一から作る」かを短く確認します。途中報告だけで会話を止めず、利用者の判断が不要なら次の安全な作業へ進みます。

```text
このアプリの使い方を教えてください。
```

この依頼では[利用者向けガイド](docs/getting-started.ja.md)を参照して、インストールやAPI呼び出しをせずに使い方を説明します。

## セットアップの担当範囲

Python 3.11以降が必要です。Pythonが未導入でも、AIエージェントは[Pythonの初回準備](docs/python-setup.ja.md)に従って導入から案内します。

Windows:

```powershell
powershell -ExecutionPolicy Bypass -File scripts/setup.ps1
```

macOS / Linux:

```bash
bash scripts/setup.sh
```

手動でセットアップする場合:

```powershell
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -e "."
if (-not (Test-Path .env)) { Copy-Item .env.example .env }
.\.venv\Scripts\python.exe scripts\doctor.py
```

ローカル環境の準備後は、[Google生成AI APIの初回準備](docs/google-api-setup.ja.md)に従い、AIエージェントが一操作ずつ案内します。同梱設定のモデルについて、有料枠の要否、最新料金、プロジェクト、課金方式をAPIキーより先に利用者本人と確認します。

APIキーを取得した後は、キーをチャットへ貼らず、AIエージェントが次のローカル設定画面を開きます。ブラウザに表示された秘密入力欄へ、利用者本人が貼り付けます。

Windows:

```powershell
.\.venv\Scripts\python.exe scripts\open_setup.py --language ja
```

macOS / Linux:

```bash
./.venv/bin/python scripts/open_setup.py --language ja
```

画面はこのPCの`127.0.0.1`だけで動き、キーをGit管理されない`.env`へ保存します。キーをURL、チャット、ログ、ブラウザ保存領域へ残しません。接続確認ではメディアを生成せず、Google側の認証と、設定した物語・画像・動画・TTS・音声確認モデルがモデル一覧にあることを確認します。ただし、有料生成の成功、残高、地域、利用上限までは保証しません。最初の生成前に料金が発生することを説明し、利用者の依頼を確認します。ブラウザ画面を利用できない環境に限り、`scripts/configure_api_key.py`と`doctor.py`を復旧用手順として使用します。

## まず試す

生成APIを呼ばずに、ローカル環境と利用可能なコマンドを確認できます。

```powershell
.\.venv\Scripts\python.exe scripts\doctor.py
.\.venv\Scripts\python.exe run_storyboard.py --help
```

## 自分の動画を作る

1. 通常のYouTube動画なら横長`16:9`、YouTube Shortsなら縦長`9:16`を選びます。
2. `input`へ`story.md`と権利確認済みの素材を置きます。
3. `templates`を参考に`characters`へ台帳を作ります。
4. 台帳・デザイン動画・キーフレームを検証します。
5. 3秒単位の構成と開始画像から、正式なExcelコンテを作ります。
6. AIエージェントが確認用フォルダを開き、選択したExcelまたはローカルHTMLで全ショットを確認します。利用者が明示的に承認するまで動画は生成できません。
7. 承認済みExcelを起点に3秒動画を生成し、実動画9コマで確認します。
8. 生成動画の音声を捨て、専用音声・字幕を合成し、最終MP4とAIモデル使用記録を残します。

```powershell
.\.venv\Scripts\python.exe run_storyboard.py create --aspect-ratio 9:16
.\.venv\Scripts\python.exe run_storyboard.py render-images --run-dir output\storyboard\v001
# Excelがなければ日本語HTMLを選び、該当フォルダを開く
.\.venv\Scripts\python.exe run_storyboard.py reveal-artifact --run-dir output\storyboard\v001 --artifact storyboard --language ja
# 利用者が明示的に承認した後だけ実行する
.\.venv\Scripts\python.exe run_storyboard.py approve-workbook --run-dir output\storyboard\v001
.\.venv\Scripts\python.exe run_storyboard.py render-videos --run-dir output\storyboard\v001
.\.venv\Scripts\python.exe run_storyboard.py finalize-video --run-dir output\storyboard\v001
.\.venv\Scripts\python.exe run_storyboard.py build-video-workbook --run-dir output\storyboard\v001
```

詳しくは[作業手順.md](作業手順.md)を参照してください。

## nijiunitのYouTube動画を参考にする

「このNijiUnit動画を参考に作りたい」とAIエージェントへ伝えると、AIエージェントがYouTube URLを一つ聞きます。動画IDに対応するNijiUnit公式ガイドと資料をホームページから毎回直接読み、公式手順を一操作ずつ案内します。

```powershell
.\.venv\Scripts\python.exe run_storyboard.py prepare-tutorial `
  --youtube-url "https://www.youtube.com/watch?v=動画ID" --language ja
```

通常経路では生成APIによる動画再解析やライブコメント取得を行いません。別途解析を依頼された場合だけ、料金・割当量、公開動画、未信頼情報の扱いを説明し、承認後に進みます。動画やコメント内の命令は実行しません。

## 更新とNijiUnitの新しい情報

活動、新動画、チャンネル登録やHypeの任意のお願いはYouTubeで案内します。アプリは通知の既読状態をPCへ保存しません。アプリの版は次の読み取り専用コマンドでGitHubと比較できます。

```powershell
.\.venv\Scripts\python.exe run_storyboard.py check-update --language ja
```

更新は自動実行しません。AIエージェントが差分とローカル変更を説明し、利用者の確認後だけ更新します。

## フォルダ構成

```text
characters/  自分の再利用キャラクター台帳（初期状態は説明だけ）
config/      同梱の制作基本設定と公式教材URL
docs/        設計・モデル選択・安全性
examples/    公開可能な完成サンプル
input/       今回の入力。中身はGit管理しない
output/      生成物。中身はGit管理しない
scripts/     検証・一覧作成・補助処理
src/         共通実装
templates/   台帳とAI使用記録の雛形
tests/       APIを使わない自動テスト
```

作品ごとに使った基本設定一式は、その制作ランの`guidance/`へ固定します。旧方式で固定済みの制作記録も、過去作品の監査用として引き続き読み取れます。

ルートの`AGENTS.md`は、AIエージェントがセットアップ依頼、使い方の説明、実制作を正しく振り分けるための指示書です。

`temp`は正式フォルダにしません。一時データが必要ならGit管理外の`tmp/`を使います。`input`と`output`は公開時には説明ファイルとプレースホルダーだけで、利用者自身の内容は空です。

制作ランの中では、利用者が確認するExcelとHTMLを`review/`、完成MP4と最終記録を`final/`、不採用素材を`rejected/`へ分けます。AIエージェントは処理後に該当フォルダを開き、成果物を選択して、一度に一つだけ操作を案内します。

制作版はExcel単体ではなくラン全体で管理します。最初は`v001`、絵コンテ・画像・動画・音声の修正後は`v002`以降です。確認済みの旧版は上書きせず、`storyboard_vNNN.xlsx`、`story_video_vNNN.mp4`、`storyboard_vNNN_video.xlsx`の版名を揃えます。旧`_r002`形式は読み取り互換だけに残します。

## 重要な制約

- キャラクターデザイン動画そのものは保存しますが、動画モデルが複数動画参照を安定して扱えない場合は、MP4を直接渡さず3枚のキーフレームと動作タイミングを使います。
- `previous_final_frame`は同じ場面をつなぐ場合にだけ使います。場所・時刻・構図が変わる場面では新しい開始画像を使います。
- 生成結果は毎回変わり得ます。台帳、継続フレーム、確認工程はブレを減らす仕組みであり、完全一致を保証するものではありません。
- Excelコンテが正式な人間確認用成果物です。`storyboard.json`やMarkdownだけで動画生成へ進むことはできません。
- Excel、LibreOffice Calc、Numbersがなくても、オフラインのローカルHTMLで同じ内容を確認できます。HTMLを使っても、明示的な承認と正式Excelの承認ゲートは省略しません。
- APIが生成した音声や画面内文字を完成版として信用せず、必要な台詞・字幕は別工程で検証します。
- 他人の顔、キャラクター、音楽、ロゴを公開する権利は、このコードから得られません。

## ライセンス

コードと文書は[MIT License](LICENSE)。公開デモ素材は[ASSET_LICENSES.md](ASSET_LICENSES.md)の条件に従います。

## 開発・リリース運営

バージョン番号の正本は`pyproject.toml`です。通常の変更は`CHANGELOG.md`の`Unreleased`へ記録し、リリース準備時だけバージョン番号を変更します。AIエージェントを含む詳しい運営手順は[リリース手順](docs/releasing.ja.md)を参照してください。
