# 検証（2.x）

[English](validation.md) · [2.x系の概要](../README.ja.md) · [セットアップ手順書](../SETUP.ja.md)

2.x系の起動を何で受け入れるかを、回す順に基準値と一緒に並べます。基準値は2026-10-02と10-03に参照機で、エンジンの開発版で測りました。2.0.0は2026-10-04にこれらと比べて受け入れました（[リリースでの測定値](../README.ja.md#リリースでの測定値)）。違う結果は日常の利用の前に説明すべき所見で、基準を置き換える値ではありません。

道具はrank 0でcheckoutの `v2/` から、その仮想環境で（[手順書 §2](../SETUP.ja.md#2-checkoutとcheckpoint)）、loopbackのエンジン（`http://127.0.0.1:8095`、rankのファイルで変えなければモデル `glm-tf`）に当てます。長い要求の間はホストを冷まし（[GPUクロックの上限](../../docs/hosts.ja.md#gpuクロックの上限)）、メモリの見張りを動かしたままにします。

## decode検査

約2,048 tokenの固定prompt（`PROMPT_TOKENS`。正確な数は各行の`prompt_tokens`）の後にgreedyで512 token、タスクごとに3回。1.x系と同じです（[切替の後のdecode検査](../../v1/docs/launch-safety.ja.md#切替の後のdecode検査)）。

```sh
for k in count prose code; do
  BASE=http://127.0.0.1:8095 MODEL=glm-tf PROMPT_KIND=$k SAMPLES=3 \
  TOKENS_OUT=../records/<run>/tokens-$k.json python -m glm53_tf decode-check
done
```

各サンプルの前に `TF_GLM_CACHE_ENTRIES`（既定8、エンジンの既定と同じ）本の短い別の要求を送るので、どのサンプルもpromptを最初からprefillします（各行の `cached` が0）。サーバーを別の値で起動した場合は同じ値を渡します。summaryには速さ、MTPの受理長（各応答の `tensorfold` ブロックから1＋accepted／rounds）、`distinct_completions` が出ます。`TOKENS_OUT` には各サンプルの文章とtoken idが残り、hashの違う2回の起動は `python -m glm53_tf decode-divergence A.json B.json` で最初に分かれたtokenを比べます。

**合格の条件**：各タスクが起動の中で一つのcompletion（`distinct_completions` が1）で、その `completion_sha256` がそのTPの基準と同じこと。

| タスク | TP=2 `completion_sha256` | TP=3 `completion_sha256` | TP=3 `token_ids_sha256` |
|---|---|---|---|
| count | `93951874af05c708` | `be0f5d346e96452b` | `3e398a9c0dfc5cd9` |
| prose | `e33450686f6b5624` | `8901c751b210f13c` | `0a3bb372ba424ae0` |
| code | `389d8fb9e3972b66` | `ac0a26c61c97838c` | `91f20cec01a74182` |

TP=2のhashは開発版の7つの版と1本・2本のrailで、TP=3のhashは10回の起動、1本・2本のrail、3通りのprefillの交換で変わりませんでした。TP=2とTP=3は設計上互いに違います（rank間の和の分け方が違う）。基準の速さ：TP=2 41.16／26.82／34.87 tok/s、TP=3 52.90／38.29／48.66。TP=3の受理長3.549／2.222／3.234。

## draftした応答とserialの一致

同じpromptをdraftありとなし（要求の本文に `"draft": false` で1 roundに1 token）で流し、同じ文章になること。prose・code・countのpromptで256 token、TP=2とTP=3の両方で確かめました。文章は全体で比べます。draftありのstreamでは1つのdeltaに `reasoning_content` と `content` の両方が乗ることがあり、deltaごとに片方しか読まないと、無い違いが出ます。

## teacher-forced NLL

[`config/nll_set.json`](../config/nll_set.json) のNLL採点セット（1.x系のもののbyte単位の写し）：4領域（日本語・英語・コード・数学）に各4本、領域ごとに5,851〜6,830 token。tokenizerはcheckpoint自身のものを使います。

```sh
python -m glm53_tf score-nll --url http://127.0.0.1:8095 \
  --tokenizer ~/.cache/huggingface/hub/models--nvidia--GLM-5.3-Flash-NVFP4/snapshots/423acf37583782c51c142d145aef733d72943d93/tokenizer.json \
  --out ../records/<run>/nll.json
```

実行する環境に `tokenizers` packageが要ります（Hugging Faceのlockには入っていません）。各本文を2回採点し、全要求が答え、各本文の2回が一致すれば（参照機ではargmaxの一致1.0、動き0）passです。

| 領域（位置数） | TP=2 | TP=3 | 1.x TP=2配布既定（1.26.0） |
|---|---|---|---|
| 日本語（6,826） | 2.5474 | 2.5313 | 2.5412 |
| 英語（6,678） | 2.9257 | 2.9001 | 2.9079 |
| コード（5,941） | 1.3184 | 1.3101 | 1.3145 |
| 数学（5,847） | 0.6250 | 0.6237 | 0.6285 |

**合格の条件**：passで、各領域がそのTPの基準と同じこと。TP=3の値はprefillの交換が違う2回の起動で同一だったので、値が違えばビットが違います。

## prefillとdecodeの速さ

38,960 tokenのpromptを、先頭に毎回新しいnonceを入れて3回（中央値）、続いて短い固定promptの後に512 token。基準：TP=2はprefill 1,217.2 tok/s、decode 35.61 tok/s（2本のrail、`split` の交換より前）。TP=3は `split` で2回の起動のprefill 1,673.1と1,667.9 tok/s、decode 53.03と52.93 tok/s。1本のrailではTP=3のprefillが13%遅く、decodeは変わりませんでした。各promptの前にホストを冷まします。TP=3で3回続けると1,670から1,540 tok/sまで下がりました。測定の台本はこのリポジトリに入っていません。台本が何をするかは[ベンチマークの方法](benchmarks.ja.md)にあります。

## 長い入力

199,652 tokenの台帳の行の真ん中に合言葉一つ、499,622 tokenと1,036,859 tokenに合言葉三つ（先頭・中央・末尾）。TP=3の基準：199,652で145.6秒・正答、499,622で454.1秒・3/3、1,036,859で3/3・最初のtokenまで1,364秒（`split` の交換とindexerの改善より前の版。200Kと500Kの実測に当てた見積もりでは、今の版は約1,112秒）。この間の最も熱いホストは89.6〜90.1 ℃で、測定が回を止める94 ℃には届きませんでした。1Mのpromptは、TP=2の窓には入りません。

## tool引数ゲート越しのtool

1.x系の呼び方（69シナリオ、seed 42、temperature 0、parallel 1、effort low、`clear_thinking`、出力4,096 token、timeout 600秒）のtool-eval-benchを[ゲート](../SETUP.ja.md#7-tool引数ゲート任意)越しに：

```sh
tool-eval-bench run --model glm-tf --base-url http://127.0.0.1:8896 --format openai \
  --seed 42 --temperature 0 --parallel 1 --timeout 600 \
  --backend-kwargs '{"max_tokens": 4096, "chat_template_kwargs": {"reasoning_effort": "low", "clear_thinking": true}}'
```

基準：TP=2とTP=3とも91/100、Safety Gate通過（TC-43はゲート越しで通る）。構造化出力のTC-64〜69は全部通り、これにはimageのxgrammarが要ります。TP=2の失敗はTC-21とTC-61、TP=3はTC-61だけ。各1回なので、1〜2点は1回の試行で動く範囲です。

## 応答を止める

リリースのエンジンは、clientが切断したときやstop文字列が出たときに、全rankで1 round以内にdecodeを止めます（上流のpull request #301）。それより前は、1系列のdecodeがtokenの上限まで続いていました。TP=2とTP=3の両方で、次を満たせば合格です：大きな `max_tokens` のstreamの要求をclientが数秒で切るとdecodeが止まる（`/health` の `rounds` が増えなくなり、decodeを続けるrankが無い）、応答が届く `stop` 文字列を指定した要求がそこで終わり `finish_reason` が `stop`、そのどちらの直後に送った短い要求もすぐに始まる。

## メモリと温度

メモリの見張りのlog（`~/glm53-tf/logs/hostwatch-<label>.log`）に、実行中の各ホストの最低の `MemAvailable` が残ります。基準はTP=3の1Mの要求の最中でrank 0・1が29〜31 GiB、rank 2が35 GiB、TP=2はextensionを先にbuildしてrank 0で約9 GiBです。

熱の待ちは、全rankが `[tensorfold] heat:` の行を出します（待ちの始まりと終わりに1行ずつ、続く間は1分に1行、全rankで同じ）。応答の `tensorfold` ブロックに `heat_wait_s` が載ります。長いpromptが、熱の見張りがエンジンを止める94 ℃にどのホストも達せずに終われば合格です。
