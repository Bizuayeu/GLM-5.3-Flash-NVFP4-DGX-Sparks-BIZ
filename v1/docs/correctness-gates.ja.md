# 出力の正しさの関門

[English](correctness-gates.md)

配信した出力の二つの検査です。属する範囲は[検証範囲](validation.ja.md#フルモデルの範囲)にあります。

## prefix cacheの正しさの関門

2026-10-02、参照機で1.25.0のimageを使い、TP=2の両profileで [`server prefix-gate`](server-configuration.ja.md#コマンド) を2つの長さで流しました。配布既定は両方とも合格です。coldもwarmも6問中6問正答で、warmの要求はどれも14,014 tokenのpromptのうち9,216 token、98,982 tokenのうち92,160 tokenをcacheから戻しました。公開した任意設定は両方の長さで判定不能（`cold_incorrect`）でした。coldもwarmも6問中5問正答で、外れはどちらの段でも同じ課題、同じ誤答です。外れた課題を、そのとき任意設定を配信していた対（1.24.0のcheckout、image `99e6cf7a…`、要求の本文は同じ）へ新しいsaltで1本だけ送り直す（要求1本、cached 0 token）と、同じ誤ったコードが返りました。cacheの不具合ではないので、配信のprefix cachingはonのままです。

**長いcontextでの1つずれた読み取り。公開した任意設定だけで測った所見です。** 誤答はどれも、問われた記録の直前の記録のコードでした。98,982 tokenのログでRecord 03008を問うとRecord 03007のコード `LPDHS` を、14,013 tokenのログでRecord 00374を問うとRecord 00373の `GYCUK` を答えました。同じ課題で問うたもう一方の記録は、どちらも正答です。配布既定は同じログと課題で、両方の長さとも6問すべてに正答しました。原因は切り分けていません。任意設定はW4A16のattention射影と `lm_head` のほか、profileの他の設定（2系列、6 GiBのKV、pageの重複排除）でも配布既定と違います。attentionの再量子化が最も疑わしいというのは仮説にとどまります。1.29.0（2026-10-04）では、任意設定で何もcacheされていない要求を1本ずつ送っても同じ2つの誤答が返り、3つ目の課題（Record 01524の行の引用に、Record 01523の行で答えた）は、cacheを読む要求でも読まない要求でも、promptのprefillの区切られ方しだいで外れたり当たったりしました（[1.29.0での測定](benchmarks.ja.md#1290での測定)）。

関門は6本の要求を1つのsaltで並列に送るため、coldの段でもcacheを使わずにprefixを計算するのは最初に届いた1本だけで、残りはそれが書いたものを読むことがあります。cacheを使わない計算の証拠は、上の1本ずつの送り直しです。

## マルチバイト出力

gate射影とup射影のglobal scaleが食い違うModelOpt NVFP4 checkpointでは、多バイト文字が化けると報告されています（[vLLM #54150](https://github.com/vllm-project/vllm/issues/54150)）。固定したNVIDIAのcheckpointは該当しません。フルモデルのどのログにも `w1_weight_scale_2 must match` の警告は出ておらず、4層fixtureのlayer 3ではexpert 288個すべてでgateとupのscaleが一致しています。同じモデルの別のlauncherは、化けの原因を別に読んでいます。tonyd2wildのcheckpoint guard（commit `abb38bb`、2026-09-24、コードは採用しない）は、attentionを量子化したModelOptのbuildを化ける側として拒否します。BIZ AXLはattention射影を量子化している（W4A16、ModelOptではなく本リポジトリでのrepack）ので、そのguardが拒否する形に当たります。

rank 0 の `server mojibake` で監視します。日本語と韓国語で400文字以上の回答を、temperature 0またはsampled（`--temperature`、`--top-p`）で3回ずつ求め、回答とreasoningの両方でU+FFFD・孤立サロゲート・改行とタブ以外の制御文字を数えます。短い回答、別の言語の回答、空の回答、形の壊れた応答、失敗した要求は判定不能とし、合格にはしません。回答の全文は `records/<stamp>-mojibake-r0/result.json` に残ります。該当文字はどの実行でも見つかっていません。

| 日付 | profile | sampling | 回答 |
|---|---|---|---|
| 2026-09-17 | 配布既定、TP=2（1.3.1） | temperature 0 | 6本：852〜1,024文字、対象言語の文字が93〜95%、すべて `stop` で終了。reasoningはそのprofileのlow effortで空だったため、reasoningの文字列は検査できていない |
| 2026-09-21、09-25 | 公開した任意設定、TP=2（09-25は2系列profile） | temperature 0 | 各6本。09-25は日本語1,154文字・韓国語1,309文字、対象言語の文字が93〜94%、すべて `stop` で終了 |
| 2026-09-29、10-01 | 配布既定、次に公開した任意設定、TP=3 | temperature 0 | 各6本 |
| 2026-10-02 | 両profile、TP=2（1.25.0） | temperature 1.0、top_p 0.95、seed 42〜47 | 各6本 |

temperature 0の回答では、上の二つの読みのどちらが正しいかは決まりません。sampledの回答でも化けは見つかりませんでした。
