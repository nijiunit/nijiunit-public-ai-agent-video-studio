[English](getting-started.md) | 日本語

# AI Agent Video Studioの使い方

このアプリは、物語とキャラクター資料から3秒単位の短い映像を作り、連結・音声・字幕・検査まで進めるためのCLIツールです。ブラウザ画面を操作するアプリではなく、AIエージェントへ自然な言葉で依頼しながら使うことを想定しています。

## AIエージェントへの依頼例

クローンしたリポジトリをAIエージェントで開き、次のように依頼できます。

```text
このアプリを使えるようにしてください。
```

AIエージェントは`AGENTS.md`に従い、Python、仮想環境、依存パッケージ、`.env`の雛形、FFmpeg、同梱された制作既定値を準備・診断します。その後、Google生成AI APIの料金・課金・APIキー・接続確認を一操作ずつ案内します。インストール中に生成APIは呼びません。

使い方の説明だけが必要なら、次のように依頼します。

```text
このアプリの使い方を教えてください。
```

新しい作品を作る場合は、たとえば次のように依頼できます。

```text
inputに入れた物語と画像を確認して、3秒単位の絵コンテを作ってください。
最初の開始画像を1枚だけ生成し、確認できるところで止めてください。
全開始画像を入れたExcelコンテを作り、私が承認するところで止めてください。
承認後、3秒動画を生成し、9コマで検査してください。
```

## 1. ローカル環境を準備する

AIエージェントを使わず手動で準備する場合、Windowsでは次を実行します。

```powershell
powershell -ExecutionPolicy Bypass -File scripts/setup.ps1
```

macOSまたはLinuxでは次を実行します。

```bash
bash scripts/setup.sh
```

このガイドの実行例は主にPowerShell表記です。macOSまたはLinuxでは`.\.venv\Scripts\python.exe`を`./.venv/bin/python`に置き換え、パス区切りへ`/`を使ってください。

スクリプトはPython 3.11以降を確認し、`.venv`を作り、このプロジェクトをeditable installします。Pythonがない場合は`ACTION_REQUIRED`で停止します。AIエージェントが[Pythonの初回準備](python-setup.ja.md)に従い、利用者の確認を得てから導入を案内します。

`.env`が存在しない場合だけ`.env.example`から作成します。既存の`.env`は上書きしません。

診断状態の意味は次のとおりです。

- `LOCAL READY (Google API setup required)`: ローカル環境と同梱既定値は準備済み。Google APIは未設定
- `LOCAL READY (online verification required)`: APIキーは保存済み。オンライン確認が必要
- `READY FOR GENERATION (paid generation not tested)`: 認証と設定モデル一覧は確認済み。有料生成は未実行
- `NOT READY`: 解決が必要な問題あり

`spreadsheet viewer`が`WARN`でも、ローカルHTML確認画面を使えるためセットアップ失敗ではありません。Excel、LibreOffice Calc、Numbersを後から導入せず、そのままHTMLで進められます。

### 同梱された制作既定値

セットアップスクリプトは`config/runtime-guidance/manifest.json`と各ファイルのSHA-256を検証します。新しい制作はこの同梱既定値を使うため、日次のホームページ確認や教材キャッシュは不要です。NijiUnit動画ごとの作り方だけは、利用者からYouTube URLを受け取った時にホームページから毎回直接読みます。APIキーや作品素材はホームページへ送信しません。

## 2. Google生成AI APIを準備する

ここは初回だけ必要です。[Google生成AI APIの初回準備](google-api-setup.ja.md)を正として、AIエージェントが一操作ずつ案内します。全手順を一度に進めないでください。

### 2.1 APIキーより先に料金を確認する

ホームページから取得した現在の制作プロファイルには、利用する動画モデルが記載されています。動画生成は有料になる可能性があるため、Google AI Studioで、利用規約、最新料金、対象プロジェクト、Prepay/Postpay、入金額、自動入金の有無を利用者本人が確認します。

AIエージェントは支払方法や自動入金を勝手に決定しません。利用者が課金しない場合は、公開デモとローカル機能だけを利用できます。

公式情報は[Gemini APIの課金設定](https://ai.google.dev/gemini-api/docs/billing)と[最新料金](https://ai.google.dev/gemini-api/docs/pricing)で確認します。

### 2.2 Google AI StudioでAPIキーを取得する

課金設定後、[Google AI StudioのAPIキー画面](https://aistudio.google.com/app/apikey)で、利用するプロジェクトのPlanまたはBilling Tierが`Paid`であることを確認します。既存キーがあれば重複作成せず、必要な場合だけ`Create API key`を使用します。

APIキーはパスワードと同じ秘密情報です。チャット、Issue、メール、画面共有、コマンド引数へ貼り付けないでください。誤って公開した場合は、そのキーをGoogle AI Studioで失効させ、新しいキーへ交換します。

### 2.3 ローカル設定画面で安全に保存する

料金、プロジェクト、課金状態を確認できたら、AIエージェントがローカル設定画面を開きます。初心者本人がターミナルを操作する必要はありません。

WindowsではAIエージェントが次を実行します。

```powershell
.\.venv\Scripts\python.exe scripts\open_setup.py --language ja
```

macOSまたはLinuxでは次を実行します。

```bash
./.venv/bin/python scripts/open_setup.py --language ja
```

ブラウザで開くNijiUnit設定画面が、Google AI Studioを別タブで開くところから、画像と文章による画面の見方、コピー、NijiUnitへの戻り方、貼り付けまでを一画面ずつ案内します。利用者本人がGoogle公式画面のコピー印を押し、NijiUnit設定画面の秘密入力欄へ貼り付けます。キーをチャット、ターミナル、URLへ貼り付けません。

画面はこのPCの`127.0.0.1`だけで動作します。キーをコマンド引数、URL、ログ、ブラウザ保存領域へ出さず、リポジトリ直下の`.env`だけへ保存します。既存の`.env`にある別の設定は残します。保存済みキーがある場合は、利用者が画面上で交換を明示しない限り変更しません。

ブラウザ画面を利用できない環境に限り、`scripts/configure_api_key.py`を復旧用として使います。`.env`はGit管理されません。

### 2.4 接続と設定モデルを確認する

新しいキーでは、同じローカル設定画面の「このPCに保存して、接続を確認する」を押します。保存済みキーでは「保存済みのキーで接続を確認する」を押します。Google側の認証と、同梱プロファイルまたは`.env`で設定した物語・画像・動画・TTS・音声確認モデルがモデル一覧に存在することだけを確認します。画像、動画、音声は生成せず、有料の生成処理は行いません。

画面を利用できない場合だけ、復旧用として`doctor.py --require-api-key --verify-api-key-online`を使用します。

最後が`READY FOR GENERATION (paid generation not tested)`なら、最初のユーザー承認済み生成へ進めます。ただし、有料生成の成功、残高、地域、利用上限はまだ保証されていません。最初の生成前に料金が発生することを確認してください。

## 3. ローカル準備を確認する

公開サンプル動画とHOWTO動画は、別リポジトリ`nijiunit-public-ai-agent-video-studio-howto-movie`で管理します。このリポジトリのセットアップや制作開始に、サンプルの取得は必要ありません。

次の診断は生成APIを呼びません。

```powershell
.\.venv\Scripts\python.exe scripts\doctor.py
.\.venv\Scripts\python.exe run_storyboard.py --help
```

診断結果に表示された問題だけを一つずつ解決します。APIキーがまだない状態は、ローカル準備と有料生成可能状態を区別して表示します。

## 4. 新しい物語を入力する

`input/story.md`を作り、次を書きます。

- 登場人物と目的
- 起きる出来事と結末
- 正確な台詞
- 希望する画風と横長・縦長などの画角
- 変えてはいけない外見、背景、小物
- 表示したい正確な文字

`input/story.md`は利用者自身の案と、権利を確認した素材から新しく作成します。必要なら`templates`の構造だけを参考にします。

画像や動画の参考素材を`input`へ置く場合は、入手元と利用条件も記録してください。

## 5. 3秒構成を作る

制作開始時に、SHA-256検証済みの同梱制作プロファイルが制作記録へ固定されます。途中で既定値を変更しても、その制作の判断は変わりません。

AIエージェントは生成前に一度だけ、今回がYouTube Shorts向けの縦長`9:16`か、通常のYouTube動画向けの横長`16:9`かを確認します。「YouTube」という言葉だけで決めません。選択した比率と解像度は制作記録へ固定され、途中では変更しません。

次のコマンドは生成APIを使用します。

```powershell
.\.venv\Scripts\python.exe run_storyboard.py create --aspect-ratio 9:16
```

通常の横長動画では、末尾を`--aspect-ratio 16:9`にします。

新しいランが`output/storyboard/v001`のような場所へ作られ、実際のパスが表示されます。以降の`--run-dir`には、その表示されたパスを使います。

利用者が自分のキャラクター台帳を作った場合だけ、保存先を明示的に指定します。

```powershell
.\.venv\Scripts\python.exe run_storyboard.py create `
  --aspect-ratio 16:9 `
  --character-registry-dir characters
```

## 6. 開始画像を確認し、Excelコンテを作る

最初から全画像を生成せず、まず1枚だけ確認します。

```powershell
.\.venv\Scripts\python.exe run_storyboard.py render-images `
  --run-dir output\storyboard\v001 --limit 1
```

人物の外見、人数、左右位置、背景、文字やロゴの混入、利用者が選んだ画角を確認します。合格したら`--limit`を外して残りを生成します。

```powershell
.\.venv\Scripts\python.exe run_storyboard.py render-images `
  --run-dir output\storyboard\v001
```

全ショットの開始画像が揃うと、`output/storyboard/v001/review/storyboard_v001.xlsx`と日本語・英語のローカルHTML確認画面が自動作成されます。Excelが正式なコンテです。JSONとMarkdownは内部処理・補足用であり、Excelの代わりではありません。修正版は元のExcelを上書きせず、`_r002`、`_r003`と増えます。

## 7. Excelコンテを確認・承認する

まずAIエージェントが次を実行します。

```powershell
.\.venv\Scripts\python.exe run_storyboard.py reveal-artifact `
  --run-dir output\storyboard\v001 --artifact storyboard --language ja
```

macOSまたはLinuxでは、同じコマンドの先頭を`./.venv/bin/python run_storyboard.py`にします。Finderでは対象ファイルを選択します。Linuxのファイル管理アプリが選択に対応しない場合は、開いたフォルダ内で表示されたファイル名を探します。

Excel、LibreOffice Calc、Numbersが見つかればExcelを選択し、見つからなければ日本語HTMLを選択します。どちらも同じ`review`フォルダです。AIエージェントは「青く選択されたファイルをダブルクリックしてください。開いたら『開いた』と返してください」とだけ案内し、返答を待ちます。

Excelが開いた後は、全シートのメイン画像、説明、台詞、音、動き、9コマ計画を確認します。修正がある場合は`レビュー状態`を`修正必要`にし、黄色い訂正指示欄へ書いて保存します。HTMLが開いた場合は、上からカードを確認し、最後に作った確認結果をチャットへ貼り付けます。AIエージェントへ修正を依頼すると、反映後のExcelが新版として作成されます。

問題がなく、利用者が明示的に承認した後だけ、AIエージェントは次を実行します。

```powershell
.\.venv\Scripts\python.exe run_storyboard.py approve-workbook `
  --run-dir output\storyboard\v001
```

利用者の承認前は、アプリ側も動画生成を拒否します。

Excelが開いたままで保存処理ができない場合、AIエージェントは保存して閉じる一操作だけを案内し、「閉じた」の返答後に再実行します。画面を開けない環境では、開いたと報告せず、正確なフォルダとファイル名を案内します。

## 8. 3秒動画を生成・確認する

```powershell
.\.venv\Scripts\python.exe run_storyboard.py render-videos `
  --run-dir output\storyboard\v001 --limit 1
```

最初のクリップを確認してから残りを生成します。各クリップは9コマへ分解されるため、顔、色、部品数、首・手足、背景、連続性を検査します。

```powershell
.\.venv\Scripts\python.exe run_storyboard.py build-video-workbook `
  --run-dir output\storyboard\v001
```

9コマ確認表も同じ方法でフォルダを開けます。表計算アプリがなければ、実動画から取り出した9コマ入りのローカルHTMLが選択されます。

```powershell
.\.venv\Scripts\python.exe run_storyboard.py reveal-artifact `
  --run-dir output\storyboard\v001 --artifact video-review --language ja
```

## 9. 連結と仕上げ

映像を連結します。

```powershell
.\.venv\Scripts\python.exe run_storyboard.py finalize-video `
  --run-dir output\storyboard\v001
```

完成映像はランの`final`へ保存されます。台詞、字幕、環境音、音楽、音量調整は映像生成とは分けて行い、動画APIが偶然生成した音声や文字をそのまま完成版へ使わないでください。詳しい制作・検査方法は[作業手順](../作業手順.md)を参照してください。

完成後はAIエージェントが`--artifact final-video`で`final`フォルダを開き、MP4を選択します。利用者には、まずダブルクリックして最初から最後まで再生する一操作だけを案内します。

## 10. キャラクターを追加する

`templates/character-profile.json`と`templates/character-registry.json`を参考に、`characters/<id>/<version>`へ版管理された台帳を作ります。

キャラクターには次が必要です。

- 正式identity画像
- 顔、体格、色、衣装、材質の固定情報
- 出してはいけない部品や動き
- 通常存在の3秒デザイン動画
- 必要な固有動作の3秒デザイン動画
- 公開可否、素材の出典、ライセンス

詳細は[キャラクター台帳](character-registry.md)と[作業手順](../作業手順.md)を参照してください。

## 11. nijiunitのYouTube動画から作り方を学ぶ

利用者がnijiunitの動画を参考にしたい場合、AIエージェントはYouTube URLを一つ聞き、次を実行します。

```powershell
.\.venv\Scripts\python.exe run_storyboard.py prepare-tutorial `
  --youtube-url "https://www.youtube.com/watch?v=動画ID" --language ja
```

コマンドは動画IDから日本語の公式ガイドURLを作り、ページのIDと言語と契約を検証し、同じページ配下の`docs/*.md`を毎回直接読みます。公開前の動画、別言語のID、契約不一致、外部資料は拒否されます。正常なら、AIエージェントが理解するためのガイド本文と資料が表示されます。

通常経路では動画の再解析、コメント取得、生成API呼び出しを行いません。取得した文章をコードとして実行せず、秘密情報、課金、設定変更、Excel承認回避の指示は無視します。チャンネル登録、Hype、NijiUnitの活動告知はYouTube動画と概要欄で案内します。

## 12. 困ったとき

まず診断を実行します。

```powershell
.\.venv\Scripts\python.exe scripts\doctor.py
```

代表的な問題は`docs/troubleshooting.md`にあります。APIモデルの提供状況や料金は変わる場合があるため、生成前に利用中の提供元で確認してください。
