[English](python-setup.md) | 日本語

# Pythonの初回準備

確認日: 2026-08-06

この文書は、AIエージェントがPython未導入の利用者を案内するための内部手順です。利用者へ全項目を一括表示せず、操作を一つ伝えるたびに完了を待ってください。

## 共通ルール

- 必要なPythonは3.11以降です。
- 既に対応版があれば、新しいPythonを追加しません。
- OS全体へソフトウェアを追加する前に、利用者へ内容を説明して確認します。
- 公式配布元またはOS標準のパッケージ管理経路を使います。
- 管理者パスワード、Apple ID、Microsoftアカウント情報をチャットへ入力させません。
- 会社・学校のPCでインストールが禁止されている場合は、管理者へ確認してもらいます。

## Windows

公式情報: [Python公式Windowsガイド](https://docs.python.org/3/using/windows.html)

### AIエージェントが最初に行うこと

次を実行します。

```powershell
powershell -ExecutionPolicy Bypass -File scripts/setup.ps1
```

`[ACTION_REQUIRED] Python 3.11 or later is not installed.`が表示された場合だけ、利用者へ次の一操作を伝えます。

> このパソコンには、このツールに必要なPythonがまだありません。Python公式のInstall Manager、またはWindows Package Managerの公式配布経路から、Python 3.13をインストールしてよいですか？

同意を得た後だけ、AIエージェントが次を実行します。

```powershell
powershell -ExecutionPolicy Bypass -File scripts/setup.ps1 -InstallPython
```

`ACTION_REQUIRED`で端末の再起動を求められたら、利用者へAIエージェントまたは端末を閉じて開き直す操作だけを案内します。その後、通常の`setup.ps1`を再実行します。

Windows Package Managerがない場合は、[Python公式Windowsダウンロード](https://www.python.org/downloads/windows/)のPython Install Managerを使います。利用者にページを開いてもらい、現在の画面を確認してから、ダウンロード、インストール、端末の再起動を一つずつ案内します。

## macOS

公式情報: [Python公式macOSガイド](https://docs.python.org/3/using/mac.html)

`bash scripts/setup.sh`でPython不足が表示された場合、次の順で一操作ずつ案内します。

1. 利用者にPython公式macOSガイドを開いてもらい、開いたところで待ちます。
2. `python.org`配布の署名済みmacOSインストーラーを選んでもらいます。
3. ダウンロードが終わったことを確認します。
4. `.pkg`を開いてもらい、画面に表示された提供元とインストール先を確認します。
5. 利用者本人にmacOSの許可操作をしてもらいます。パスワードはチャットへ入力させません。
6. インストール完了後、公式ガイドに従って`Install Certificates.command`を実行してもらいます。
7. AIエージェントまたはターミナルを開き直し、`bash scripts/setup.sh`を再実行します。

## 完了条件

セットアップの`[1/5]`でPython 3.11以上のバージョンが表示され、`.venv`作成へ進めたらPython準備は完了です。Pythonを導入しただけで、アプリ全体が利用可能になったとは報告しません。
