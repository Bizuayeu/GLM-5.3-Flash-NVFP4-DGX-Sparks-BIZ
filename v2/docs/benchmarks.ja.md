# ベンチマークの方法（2.x）

[English](benchmarks.md) · [2.x系の概要](../README.ja.md) · [検証](validation.ja.md) · [決定](decisions.ja.md)

2.x系の値をどう取ったか：[リリースでの測定値](../README.ja.md#リリースでの測定値)の値と、[検証](validation.ja.md)の基準値です。値はその二つの頁にあり、この頁はその条件と手順を書きます。速さと長い入力の値を取った台本はこのリポジトリに入っていません。値を再現したり疑ったりできるよう、台本が何をするかをここに書きます。

## ホストと条件

- **ホスト。** 参照機のMSI EdgeXpert（GB10）。TP=2は直結の対、TP=3はリングの3台で、GPUには他に何も載せていません（1.x系は停止）。
- **GPUクロック**は[ホストのツール](../../host/README.ja.md)の起動時のunitで2,200 MHzを上限にしました（[GPUクロックの上限](../../docs/hosts.ja.md#gpuクロックの上限)）。負荷の下の記録は2,171〜2,197 MHzでした。
- **エンジン。** リリースのimageと、エンジンのcommitで1つ前と2つ前のimage。[どのエンジンで測ったか](../README.ja.md#リリースでの測定値)が各行のcommitを示します：decode検査はTP=2が `b44c2f1`、TP=3が `2d4fa9b`、TP=3のprefillと1M tokenのpromptは `2d4fa9b`、他の行は `304109c` です。
- **見張り。** メモリの見張りを全ホストで、熱の見張りをrank 0のホストで動かしました。
- **クライアント。** 要求はすべてrank 0からloopbackのエンジンへ一つずつ、検査が別に言わない限りtemperature 0、推論のeffortはlowです。リリースの時点では、同じcheckoutの1.x系の道具を使いました：decode検査、NLLの採点（`tokenizers` が入っているcontainerの中で実行）、port 8897のtool引数ゲートです。2.0.5で `glm53_tf` に同じ引数の写しができ、[検証](validation.ja.md)のコマンドはそれです。

## 長い要求の合間の冷却

測定のまとまり（decode検査、NLL、prefillとdecodeのbench、長い入力）の前ごとに、全ホストで同時に冷却gateを回しました。ホストのACPIの最高温度が帯以下になるか、上限の時間がたつまで待ちます。[`host/cool-gate`](../../host/README.ja.md#長い運転の間)と同じ規則です：

| ホスト | 帯 | 上限 |
|---|---|---|
| rank 0のホスト | 55.8 °C | 936 s |
| rank 1のホスト | 53.2 °C | 936 s |
| rank 2のホスト（TP=3） | 60 °C | 600 s |

最初の二つの帯は1.x系の測定のときにそのホストで較正した値です。rank 2のホストには較正が無く、`cool-gate` の既定値を使いました。冷却が要るのは、ホストが熱くなるほどprefillが遅くなるからで、そのときクロックは変わりません（[熱](../README.ja.md#リリースでの測定値)）。

リリースの値を取った `2d4fa9b` と `b44c2f1` の回では、熱の待ちを92 °C／88 °Cで入れていました（待ちを切った対照を除く）。`304109c` は熱の待ちより前です。

## decode検査

[検証](validation.ja.md#decode検査)のとおりです：各タスク（count、prose、code）を3回、約2,048 tokenの固定promptの後にgreedyで512 token。各回の前に追い出しの要求を送り、どの回もprompt全体をprefillします（`cached` 0）。道具は速さ、MTPの受理長、異なるcompletionごとのhashを出します。

## prefillとdecodeの速さ

時間を測る前に、約3,000 tokenのprefillでpromptのkernelのcompileを済ませました。

**prefill。** 一つのuser message：`nonce <新しいUUID>` の1行、固定の3,200行（`measurement line <i> of the fixed prefill prompt.`）、`Reply ok.`。chat templateを含めて38,960 tokenです。`max_tokens` 1、temperature 0、effort low、`clear_thinking`。速さは、promptのtoken数をクライアントでの要求の経過時間で割ったものです。エンジンには保持promptを消すendpointが無いので、先頭の新しいnonceで保持promptが一致しないようにしました。どの応答も `cached` は0でした。値は3回の中央値です：

- TP=2（`304109c`）：冷却gateを1回通した後に3つのpromptを続けて。互いの差は0.1%以内でした。
- TP=3（`2d4fa9b`）：冷却gateの後に1つのpromptを、熱の待ちを入れて3回、続いて対照として待ちを切って3回。gateを挟まずに3つ続けると、1回ごとに遅くなりました（[熱](../README.ja.md#リリースでの測定値)）。

**短いpromptの後のdecode。** `Count upward from one, one number per line.` をstreamで、`ignore_eos` で512 token、temperature 0、effort low。速さは、最初の後のcompletionのtoken数を、最初にstreamで届いたtokenの後の時間で割ったもので、3回の中央値です。promptは毎回同じなので、受理長が回の間で比べられます。

## 長い入力

長いpromptはどれも番号付きの行の台帳で（`Ledger <i>: the river barge delivered sacks of barley to the northern granary at dusk.`）、system messageは `You are a careful archivist. Read the ledger.`、temperature 0、effort lowです。保持promptから再開できないよう、各promptの前に関係の無い短い要求を送り、応答の `cached` は0でした。各promptの前にホストを冷ましました。

- **199,652 tokenに合言葉一つ。** 8,806行の真ん中に合言葉。行数は1.x系が記録したもので、本文は1.x系のものと同じです。streamなし、最大512 token。応答に合言葉があれば正答です。最初のtokenまでの時間は、rank 0の `[tensorfold] done` の行の `ttft` です。リリースでは両TPとも `304109c` で取りました。
- **499,622 tokenと1,036,859 tokenに合言葉三つ**（先頭から20分の1、真ん中、末尾から20分の1）。行数はエンジンの `/tokenize` で目標の長さに合わせます。streamで最大256 token、最初にstreamで届いたtokenまでをクライアントが測ります。応答が三つとも挙げれば正答です。リリースの1,036,859 tokenの値はTP=3の `2d4fa9b` で熱の待ちを入れたもので、待ちの合計は応答の `tensorfold` ブロックの `heat_wait_s` が示します。

検証の199,652と499,622 tokenの開発版の基準値は、エンジンのprofile（`TF_GLM_PROFILE=1`）を入れて取りました。profileはprefillのうち長さで伸びない部分に約11%を足しました。

## teacher-forced NLL

NLL採点セットと採点は[検証](validation.ja.md#teacher-forced-nll)のとおりで、checkpoint自身のtokenizerを使い、各テキストを2回採点します。リリースでは `304109c` で取り、結果は開発版の値と全精度で同じです。

## draftとserialの一致と停止

- **draftした応答とserialの一致**：prose、code、countingのpromptで256 token、`"draft": false` の有りと無しを、テキスト全体で比べます（[検証](validation.ja.md#draftした応答とserialの一致)）。streamのdeltaごとに一つの項目しか読まない比較は、TP=2で偽の差を出しました。一つのdeltaが `reasoning_content` と `content` の両方を運ぶことがあるためです。
- **応答を止める**：1から1,000までの数を1行ずつ並べさせる要求（約4,000 token、1分を超えるdecode）。約5秒でクライアントが切ると、`/health` の `rounds` とcompletionのtoken数が切った後の10秒から30秒の間に増えず、直後の短い要求がすぐ始まること。stop文字列 `"\n300\n"` では、`finish_reason` が `stop`、テキストは299で終わり、直後の短い要求も同じく。上へ数えさせる以前の形はやめました。モデルが切断の前に自分で答え終え、何も示さなかったためです。リリースでは `304109c` で取りました。

## ゲート越しのtool

1.x系と同じ呼び方のtool-eval-benchをtool引数ゲート越しに（[検証](validation.ja.md#tool引数ゲート越しのtool)）、各TPで1回、`304109c` で回しました。69のシナリオは冷却なしで続けて約9.5分走り、TP=2の回ではrank 0のホストが93 °Cに達しました。

## メモリと温度

各ホストの `MemAvailable` の最低値はメモリの見張りのlog（2秒ごと）から、温度はホストの記録（2秒ごと、ACPIの最高温度）から、熱の待ちは `[tensorfold] heat:` の行と各応答の `heat_wait_s` から読みます（[検証](validation.ja.md#メモリと温度)）。
