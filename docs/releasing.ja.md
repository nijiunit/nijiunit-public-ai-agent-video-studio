[English](releasing.md) | 日本語

# バージョン管理とリリース手順

この文書は、人とAIエージェントが同じ規則でこのリポジトリを運営するための手順です。

## バージョンの正本

正式なバージョン番号は、`pyproject.toml`の次の値だけです。

```toml
[project]
version = "0.6.0"
```

`VERSION`などの重複ファイルは作りません。`CHANGELOG.md`の最新リリース見出しは、この値と一致させます。`scripts/check_release_version.py`が不一致を検出します。

## 通常の変更

通常の機能追加や修正では、バージョン番号を変更しません。

1. 機能追加、不具合修正、セキュリティ変更など、利用者に影響する内容を`CHANGELOG.md`の`Unreleased`へ追記します。
2. 誤字修正、文章の整形、内部リファクタリング、テストだけの変更は、利用者への影響がなければ追記不要です。
3. 実装に応じたテストと公開安全検査を行います。

これにより、複数の変更をためてから一つのリリースとして公開できます。

## バージョン番号の決め方

Semantic Versioningの`MAJOR.MINOR.PATCH`を使います。

- PATCH: 後方互換のある不具合修正。例: `0.6.0`から`0.6.1`
- MINOR: 後方互換のある機能追加。例: `0.6.0`から`0.7.0`
- MAJOR: 互換性を壊す変更。例: `1.4.0`から`2.0.0`

`1.0.0`未満で互換性を壊す変更は、番号の影響が分かりにくいため、AIエージェントだけで決めず利用者と確認します。

## リリース準備

利用者からリリース準備を明示的に依頼されたときだけ、次を行います。

1. Git差分を確認し、公開対象外の秘密情報や素材がないことを確認します。
2. `Unreleased`の内容からPATCH、MINOR、MAJORを判断します。不明な場合は利用者へ確認します。
3. `pyproject.toml`の`project.version`を新しい番号へ変更します。
4. `CHANGELOG.md`の`Unreleased`内容を`## X.Y.Z - YYYY-MM-DD`へ移し、その上に空の`## Unreleased`を新しく残します。
5. 次の検査を行います。

   ```powershell
   .\.venv\Scripts\python.exe scripts\check_release_version.py
   .\.venv\Scripts\python.exe -m pytest
   .\.venv\Scripts\python.exe -m ruff check .
   .\.venv\Scripts\python.exe scripts\check_public_repo.py
   ```

6. Privateの状態でcommitとpushを行い、GitHub Actionsの成功とGitHub上の表示を確認します。
7. 利用者の明示的な確認後だけ、タグ、GitHub Release、公開設定の変更を行います。

macOSまたはLinuxでは`.\.venv\Scripts\python.exe`を`./.venv/bin/python`へ置き換えます。

## GitタグとGitHub Release

リリースタグはバージョンの先頭へ`v`を付けます。バージョン`0.6.0`ならタグは`v0.6.0`です。

```bash
git tag -a v0.6.0 -m "Release v0.6.0"
git push origin v0.6.0
```

この操作は外部状態を変更します。AIエージェントは、利用者が明示的に依頼または承認した場合だけ実行します。公開済みタグを別のcommitへ付け替えてはいけません。誤りが見つかった場合は、新しいPATCH版を準備します。

GitHub Releaseのタイトルも`v0.6.0`とし、本文には該当するCHANGELOGの内容を使います。生成動画など大きな成果物を追加する場合は、リポジトリ本体へ入れる前に容量と配布権利を再確認します。

## AIエージェントの完了条件

リリース準備の完了報告には、少なくとも次を含めます。

- 旧バージョンと新バージョン
- PATCH、MINOR、MAJORを選んだ理由
- CHANGELOGへ移した内容
- 実行した検査と結果
- commit、push、タグ、GitHub Release、Public化のうち実際に行った操作
- macOSなど未検証の環境や、権利確認など人が判断すべき残事項
