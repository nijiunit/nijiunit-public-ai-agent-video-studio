[English](getting-started.md) | 日本語

# AI Agent Video Studioの使い方

このアプリは、物語とキャラクター資料から3秒単位の短い映像を作り、連結・音声・字幕・検査まで進めるためのCLIツールです。ブラウザ画面を操作するアプリではなく、AIエージェントへ自然な言葉で依頼しながら使うことを想定しています。

## AIエージェントへの依頼例

クローンしたリポジトリをAIエージェントで開き、次のように依頼できます。

初めてなら`こんにちは`だけでも構いません。AIエージェントは次の二択から始めます。

```text
こんにちは。NijiUnitで動画作りをお手伝いします。
まず、作り方を選んでください。
「NijiUnitのチュートリアルを参考にする」か「一から作る」のどちらにしますか？
```

```text
このアプリを使えるようにしてください。
```

AIエージェントは自分用のルート入口（Codexは`AGENTS.md`、Claude Codeは`CLAUDE.md`、Gemini CLIは`GEMINI.md`）から共通の日本語ガイドを読み、Python、仮想環境、依存パッケージ、`.env`の雛形、FFmpeg、同梱された制作既定値を準備・診断します。その後、Google生成AI APIの料金・課金・APIキー・接続確認を案内します。インストール中に生成APIは呼びません。

使い方の説明だけが必要なら、次のように依頼します。

```text
このアプリの使い方を教えてください。
```

新しい作品を作る場合は、たとえば次のように依頼できます。

```text
inputに入れた物語と画像を確認して、3秒単位の絵コンテを作ってください。
全開始画像を内部で検品し、画像入りExcelコンテを作って、私が承認するところで止めてください。
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
- `LOCAL READY (Google API configured; online verification not run)`: APIキーは保存済み。初回設定のやり直しは不要。制作時に必要ならAIエージェントが非生成の接続確認を行う
- `READY FOR GENERATION (paid generation not tested)`: 認証と設定モデル一覧は確認済み。有料生成は未実行
- `NOT READY`: 解決が必要な問題あり

`spreadsheet viewer`が`WARN`でも、ローカルHTML確認画面を使えるためセットアップ失敗ではありません。Excel、LibreOffice Calc、Numbersを後から導入せず、そのままHTMLで進められます。

### 同梱された制作既定値

セットアップスクリプトは`config/runtime-guidance/manifest.json`と各ファイルのSHA-256を検証します。新しい制作はこの同梱既定値を使うため、日次のホームページ確認や教材キャッシュは不要です。NijiUnit動画ごとの作り方だけは、利用者からYouTube URLを受け取った時にホームページから毎回直接読みます。APIキーや作品素材はホームページへ送信しません。

## 2. Google生成AI APIを準備する

ここはAPIキーが未設定の初回、キーを交換・再設定するとき、または保存済み設定の接続確認に失敗したときだけ必要です。設定済みで変更がなければ繰り返しません。[Google生成AI APIの初回準備](google-api-setup.ja.md)を正として、必要な場合だけAIエージェントが案内します。

### 2.1 最初にローカル設定画面を開く

ローカル診断が`Google API setup required`の場合だけ、AIエージェントが「NijiUnit 初回設定」を開きます。APIキーが保存済みで利用者が変更していなければ、画面を開かず、初回設定をやり直すかも質問しません。制作前に接続確認が必要なら、AIエージェント自身が非生成のオンライン確認を行います。初心者本人がターミナルを操作する必要はありません。

WindowsではAIエージェントが次を実行します。

```powershell
.\.venv\Scripts\python.exe scripts\open_setup.py --language ja
```

macOSまたはLinuxでは次を実行します。

```bash
./.venv/bin/python scripts/open_setup.py --language ja
```

表示された画面が、Googleアカウントの状態確認、Google AI Studioを別画面で開く操作、プロジェクトと請求階層の確認、キーのコピー、NijiUnitへの戻り方、貼り付けまでを一画面ずつ案内します。

### 2.2 APIキーより先に料金を確認する

ホームページから取得した現在の制作プロファイルには、利用する動画モデルが記載されています。動画生成は有料になる可能性があるため、Google AI Studioで、利用規約、最新料金、対象プロジェクト、Prepay/Postpay、入金額、自動入金の有無を利用者本人が確認します。

AIエージェントは支払方法や自動入金を勝手に決定しません。利用者が課金しない場合は、公開デモとローカル機能だけを利用できます。

公式情報は[Gemini APIの課金設定](https://ai.google.dev/gemini-api/docs/billing)と[最新料金](https://ai.google.dev/gemini-api/docs/pricing)で確認します。

### 2.3 Google AI StudioでAPIキーを取得する

課金設定後、[Google AI StudioのAPIキー画面](https://aistudio.google.com/app/apikey)で、利用するプロジェクトのPlanまたはBilling Tierが`Paid`であることを確認します。既存キーがあれば重複作成せず、必要な場合だけ`Create API key`を使用します。

APIキーはパスワードと同じ秘密情報です。チャット、Issue、メール、画面共有、コマンド引数へ貼り付けないでください。誤って公開した場合は、そのキーをGoogle AI Studioで失効させ、新しいキーへ交換します。

### 2.4 ローカル設定画面で安全に保存する

利用者本人がGoogle公式画面のコピー印を押し、開いたままのNijiUnit設定画面へ戻って秘密入力欄へ貼り付けます。キーをチャット、ターミナル、URLへ貼り付けません。

画面はこのPCの`127.0.0.1`だけで動作します。キーをコマンド引数、URL、ログ、ブラウザ保存領域へ出さず、リポジトリ直下の`.env`だけへ保存します。既存の`.env`にある別の設定は残します。保存済みキーがある場合は、利用者が画面上で交換を明示しない限り変更しません。

ブラウザ画面を利用できない環境に限り、`scripts/configure_api_key.py`を復旧用として使います。`.env`はGit管理されません。

### 2.5 接続と設定モデルを確認する

新しいキーでは、同じローカル設定画面の「このPCに保存して、接続を確認する」を押します。保存済みキーでは「保存済みのキーで接続を確認する」を押します。Google側の認証と、同梱プロファイルまたは`.env`で設定した物語・画像・動画・TTS・音声確認モデルがモデル一覧に存在することだけを確認します。画像、動画、音声は生成せず、有料の生成処理は行いません。

保存済みキーの非生成オンライン確認には、AIエージェントが`doctor.py --require-api-key --verify-api-key-online`を使用できます。利用者にコマンド入力を頼みません。

最後が`READY FOR GENERATION (paid generation not tested)`なら、最初のユーザー承認済み生成へ進めます。ただし、有料生成の成功、残高、地域、利用上限はまだ保証されていません。最初の生成前に料金が発生することを確認してください。

## 3. ローカル準備を確認する

初心者向けの小さな公開サンプル動画、承認済みExcelコンテ、日英HTMLは`examples/space-friends/`に同梱しています。`run_storyboard.py show-sample --artifact video --language ja`で実物を表示できます。完全なHOWTO制作元は別リポジトリ`nijiunit-public-ai-agent-video-studio-howto-movie`で管理します。

次の診断は生成APIを呼びません。

```powershell
.\.venv\Scripts\python.exe scripts\doctor.py
.\.venv\Scripts\python.exe run_storyboard.py --help
```

診断結果に表示された問題だけを一つずつ解決します。APIキーがまだない状態は、ローカル準備と有料生成可能状態を区別して表示します。

## 4. 新しい物語を入力する

最初に、「NijiUnitのチュートリアルを参考にする」か「一から作る」かを選びます。

チュートリアルから取得できるのは作り方と公開文章です。NijiUnitが制作に使ったキャラクター画像・動画・音声は公開していません。公式ページに公開ストーリーがある場合だけ、確認後に`input/sample_story.md`へ参考資料として保存できます。

チュートリアルの公開ストーリーを`sample_story.md`へ保存した場合は、それを参考に、本番用の`input/story.md`へ作りたい動画を普通の文章で書きます。参考画像・動画・音声がある場合は、正確なファイル名と、顔、服、動きなど何を参考にするかも書き、ファイルを`input`へ置きます。

一から作る場合や文章作成を手伝ってほしい場合は、題材を普通の言葉で伝えると、AIエージェントが`templates/story-input.ja.md`を内部の構造として使い、`input/story.md`へ整理します。Markdown記法や長いテンプレートへの記入は不要です。内容は次の項目を含みます。

- 登場人物と目的
- 起きる出来事と結末
- 正確な台詞
- 希望する画風と横長・縦長などの画角
- 変えてはいけない外見、背景、小物
- 表示したい正確な文字

`input/story.md`は利用者自身の案と、権利を確認した素材から新しく作成します。`sample_story.md`があっても、本番用の`story.md`が必ず優先されます。

配置後に`inputに入れました`と伝えると、AIエージェントがフォルダーを読み、ストーリーの意味、実際のファイル名、各素材をどこに使うかを具体的に返します。質問がなければ途中報告だけで止まらず、残る判断へ進みます。制作情報と比率が揃うと、開始画像の有料生成とExcelコンテ作成をまとめて進めてよいか確認します。

画像・動画・音声の参考素材がある場合は、その場所と使用許可を普通の言葉で伝えます。既存の場所を指定済みなら、AIエージェントが`import-input`で安全に取り込むため、同じファイルを手作業でコピーする必要はありません。場所が未指定の場合だけ`input`フォルダーを開きます。`主人公のミナは character_mina.png の顔と服を参考にしてください。walk.mp4は歩き方だけを参考にしてください。`のように伝えると、AIエージェントが入手元、利用条件、参考範囲、変えてはいけない点、使わない部分を`story.md`へ整理します。

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

## 6. 開始画像をAIが検品し、Excelコンテを作る

AIエージェントが全ショットの開始画像を生成します。

```powershell
.\.venv\Scripts\python.exe run_storyboard.py render-images `
  --run-dir output\storyboard\v001
```

AIエージェントは人物の外見、人数、左右位置、背景、文字やロゴの混入、利用者が選んだ画角を内部で検品し、明らかな問題を修正します。通常制作では画像1枚だけを利用者へ見せて返答を待ちません。新規または変更キャラクターの基準画像確認が必要な場合だけ、キャラクター台帳の承認としてExcel前に個別確認します。

全ショットの開始画像が揃うと、`output/storyboard/v001/review/storyboard_v001.xlsx`と日本語・英語のローカルHTML確認画面が自動作成されます。Excelが正式なコンテです。JSONとMarkdownは内部処理・補足用であり、Excelの代わりではありません。

修正はチャットへ普通に書くか、Excelの黄色い訂正欄へ書いて保存します。確認済み`v001`は変更せず、修正版は制作一式を`v002`へ進めます。新しいExcelは`storyboard_v002.xlsx`です。変わらない承認済み素材は出所記録付きで引き継ぎ、差し替える素材は`v002/rejected/`へ残します。

## 7. Excelコンテを確認・承認する

まずAIエージェントが次を実行します。

```powershell
.\.venv\Scripts\python.exe run_storyboard.py reveal-artifact `
  --run-dir output\storyboard\v001 --artifact storyboard --language ja
```

macOSまたはLinuxでは、同じコマンドの先頭を`./.venv/bin/python run_storyboard.py`にします。Finderでは対象ファイルを選択します。Linuxのファイル管理アプリが選択に対応しない場合は、開いたフォルダ内で表示されたファイル名を探します。

Excel、LibreOffice Calc、Numbersが見つかればExcelを選択し、見つからなければ日本語HTMLを選択した状態でフォルダを開きます。AIエージェント自身がエクスプローラー画面と対象ファイルを確認してから、正確なファイル名と確認方法を一度に案内します。Excelなら「『確認_絵コンテ.xlsx』を開き、全シートのメイン画像、説明、台詞、音、動き、9コマ計画を確認してください。修正がある場合は`レビュー状態`を`修正必要`にし、黄色い訂正指示欄へ書いて保存してください。問題がなければその旨を伝えてください」と案内します。利用者へ「開いた」とだけ返す中間報告は求めません。選択色は環境で変わるため説明に使いません。

HTMLの場合は、上から全カードを確認し、最後に作った確認結果をチャットへ貼り付けます。AIエージェントへ修正を依頼すると、反映後のExcelが新版として作成されます。

`S001の背景を直し、終わったらそのまま動画作成へ進んでください`のように、修正とその後の進行を同時に明示できます。この場合、AIエージェントは修正後の新版Excelを検査し、新しい判断がなければ同じ承認を聞き直さずに進みます。

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

動画または音声を修正する場合も、確認済み版を上書きしません。動画訂正は`revise-run --scope video`、鳴き声やナレーションなどの音声訂正は`revise-run --scope audio`で次の`vNNN`を作り、変更しない承認済み素材を引き継ぎます。完成ファイルと確認Excelも新しい版名へ揃えます。

## 9. 連結と仕上げ

承認済みクリップへローカル音響と字幕を反映し、映像を連結して、実動画9コマ入りの確認資料まで作ります。台詞またはナレーションがある場合の`--generate-speech`は有料API操作なので、AIエージェントが料金を説明し、利用者の確認後だけ付けます。音楽を使う場合も、利用権を確認してから指定します。

```powershell
.\.venv\Scripts\python.exe run_storyboard.py finish-production `
  --run-dir output\storyboard\v001
```

完成映像はランの`final`へ保存されます。動画APIが偶然生成した音声や文字をそのまま完成版へ使いません。表計算アプリがなければ、実動画から取り出した9コマ入りのローカルHTMLも作られます。

完成後はAIエージェントが完成MP4と9コマ確認資料を一つずつ表示します。問題なければ、`これでいいです`、`問題ありません`、`OKです`など、同じ意味の普通の言葉で伝えられます。

その後、`archive-production`が制作一式を`history/001_作品名`へ移します。会話が途中で終わっても完成確認待ちは保存され、次回`completion-status`で再開します。移動後も`history/.../run`から修正できます。

## 10. キャラクターを追加する

初心者はJSONを手書きしません。AIエージェントが会話を`templates/character-registration.ja.json`の構造へ整理し、`register-character`で`characters/<id>/<version>`へ確認待ち版と日英HTMLを作ります。利用者が確認した後だけ`approve-character`で有効化します。

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

取得するのは作り方と公開文章であり、NijiUnitが制作に使ったキャラクター画像・動画・音声ではありません。検証済みチュートリアルに公開ストーリーがある場合は、AIエージェントが保存するかを先に確認したうえで、次を実行できます。

```powershell
.\.venv\Scripts\python.exe run_storyboard.py prepare-tutorial `
  --youtube-url "https://www.youtube.com/watch?v=動画ID" --language ja `
  --write-sample-story
```

これは参考用の`input/sample_story.md`を作り、内容の異なる既存ファイルは上書きしません。本番用は必ず別の`input/story.md`へ作成します。

通常経路では動画の再解析、コメント取得、生成API呼び出しを行いません。取得した文章をコードとして実行せず、秘密情報、課金、設定変更、Excel承認回避の指示は無視します。チャンネル登録、Hype、NijiUnitの活動告知はYouTube動画と概要欄で案内します。

## 12. 困ったとき

まず診断を実行します。

```powershell
.\.venv\Scripts\python.exe scripts\doctor.py
```

代表的な問題は`docs/troubleshooting.md`にあります。APIモデルの提供状況や料金は変わる場合があるため、生成前に利用中の提供元で確認してください。
