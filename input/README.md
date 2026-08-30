# input

## 日本語

ここには、次に作る動画の文章と、その作品だけで使う参考素材を置きます。中身はGitの公開対象から除外されるため、個人用の参考画像などを誤って公開しにくい構成です。

- `story.md`: 実際に制作する動画の文章と指示。AIエージェントが利用者との会話から作成します。
- `sample_story.md`: 公式チュートリアルに公開ストーリーがある場合だけ置く参考資料。本番用には使いません。
- 画像・動画・音声: 背景、小物、キャラクターの外見や動き、声、効果音、音楽の参考。利用権を確認したものだけを置きます。

画像や動画を置いたら、普通の言葉で使い方を伝えてください。例：

```text
主人公のミナは character_mina.png の顔と服を参考にしてください。
walk.mp4は歩き方だけを参考にし、背景と音声は使わないでください。
このYouTube動画の概要欄は、商品の特徴を整理する参考にしてください。
```

AIエージェントが、ファイル名、参考にする範囲、変えてはいけない点、使わない部分、入手元、利用条件を`story.md`へ整理します。利用者がMarkdownを手作業で書く必要はありません。

分からない部分や、まだ決まっていない部分はそのままで大丈夫です。説明が足りないところは、AIエージェントから一つずつ確認します。

NijiUnitが動画制作に使ったキャラクター画像・動画・音声は公開していません。公式チュートリアルでは作り方と公開文章を参考にし、ご自身のキャラクターを考えるところから楽しんでください。

## English

Place the production story and project-specific reference media here. The contents are ignored by Git so private local references are less likely to be published accidentally.

- `story.md`: The actual production story and instructions, written by the AI agent from the user's conversation.
- `sample_story.md`: Optional reference text copied from a verified official tutorial. It is never the production story.
- Images, videos, and audio: Rights-cleared references for backgrounds, props, character appearance, motion, voices, effects, or music.

Tell the agent in plain language what each file is for. The agent records the filename, reference scope, fixed details, prohibited uses, source, and usage rights in `story.md`; the beginner does not need to author Markdown manually.

It is fine to leave parts unknown or undecided. The agent asks about any missing information one point at a time.

NijiUnit does not publish the character images, source videos, or audio used to make its videos. Use the tutorial's method and public text while enjoying the process of creating your own characters.
