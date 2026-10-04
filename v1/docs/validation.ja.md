# 検証範囲と証拠

[English](validation.md)

1.xの証拠が示すことと示さないこと、候補と無改変対照の比べ方、未解決の事項、通常運用を受け入れた範囲を扱います。独立したページを持つ検査：

## 関連する検査

- [再現性](repeatability.ja.md)：fixtureでの再量子化検査、expert内のtoken順序、indexerのtop-kの同点、起動状態。
- [出力の正しさの関門](correctness-gates.ja.md)：prefix cacheの正しさの関門とマルチバイト出力。
- [部品検証](component-validation.ja.md#gpu-1台のfixtureを再現する)：GPU 1台のfixtureの再現、CPUと部品の検査、kpool tail ringの再現。

## 証拠であり、本番認定ではない

以下の観測は、GB10 GPU、vLLMのsource commit `385dce36bcee42309924a5ece951a96db3dce7f2`、NVIDIAのモデルrevision `423acf37583782c51c142d145aef733d72943d93` で取得しました。非公開の生runは配布せず、本書はそれをレビューした要約です。

| 試験 | 観測結果 | 限界 |
|---|---|---|
| 実packed FP8 cacheでの参照Attention | 候補幅63／64／65／2048／2051／2176を検査。padding・空行を処理し、意図的なtail除去も検出 | 部品の検査であり、モデル全体の正当性ではない |
| 4層checkpoint | 選択した3,591件のtensorをすべてバイト単位で検証。元の幅と288 expertsを保持 | 言語品質のベンチマークではない |
| Marlin W4A16、GPU 1台 | ロード、生成、A→B→Aの再実行、2要求batchのtoken比較、prefill強制の試験に合格 | 入力は限定的で、本番信頼性の主張ではない |
| Marlin、8,705 tokenの入力 | 実測した8,704 tokenのattention manager blockを跨いだ。prefill強制の次tokenは一致し、選択したlogprobの差は0.0031653 | すべての境界やcontext容量の上限を網羅しない |
| batch不変モード | SM120の疎MLAが拒否。Triton MLAは疎に未対応 | 固定した本スタックでは使えない |

確率の許容差は、参照logprobの大きさに対するBF16イプシロン2つ分という暫定の上限でした。厳密な再実行、tokenの一致、許容差による比較は、それぞれ別の検査です。層を切り詰めたモデルは、数値差を拡大することがあります。

パッケージ化したCLIと再構成したDocker buildもGB10で確認しました。実cacheの部品試験と、context 16,384でのMarlin 4層試験は、8,705 tokenの境界入力を含めて合格しました。両試験containerともOOMなしで正常終了しました。これが検証するのは新しいパッケージ・workerのimport経路であり、run間のビット一致やフルモデルTP=2ではありません。

Marlinは演算そのものを変えます。[linear kernel](https://github.com/vllm-project/vllm/blob/385dce36bcee42309924a5ece951a96db3dce7f2/vllm/model_executor/kernels/linear/nvfp4/marlin.py)はW4A16で、[MoEのselector](https://github.com/vllm-project/vllm/blob/385dce36bcee42309924a5ece951a96db3dce7f2/vllm/model_executor/layers/fused_moe/oracle/nvfp4.py)は汎用の `use_a16` フラグとは独立にMARLIN向けのW4A16を選びます。このフラグだけから精度を推定しないでください。

**NVIDIAのモデルカードはこの配信を記述しません。** [固定したモデルカード](https://huggingface.co/nvidia/GLM-5.3-Flash-NVFP4)は、そのcheckpointについてBF16対NVFP4の精度表を載せています。その数値はNVIDIA GB200上でvLLMとSGLangを通し、temperature 1.0でサンプリングし、カードの事後量子化recipe（`nvfp4_experts_dense_mlp-kv_fp8_cast`、W4A4の経路）で測ったもので、その機体のその経路を記述します。このスタックは同じ重みをGB10上のMarlin W4A16で、独自のprefill・decode・投機の経路で動かすので、カードの表はここでは再現も主張もしません。この配信を記述する数値は、[ベンチマーク](benchmarks.ja.md)の教師強制NLLの行と長い入力の確認、[FreedomBench](freedombench.ja.md)の結果、[ハーネス](harnesses.ja.md)の各ケースで、いずれも測ったimageとprofileを添えています。

vLLMは[既定での再現性を保証していません](https://github.com/vllm-project/vllm/blob/385dce36bcee42309924a5ece951a96db3dce7f2/docs/usage/reproducibility.md)。ただし、これは本リポジトリのアダプタが正しいことの証明にもなりません。上の検査は証拠であって証明ではありません。

## 候補と無改変対照の比較

差を判定する前に同じ無改変armを2本以上測り、全反復の値・中央値・範囲を残します。候補に再起動が必要なら対照も別起動を含めます。差が対照のばらつきの内側なら、同等の証明ではなく**この分解能では判定不能**です。少数反復では遅い側の尾が無いことも証明できません。

- 実行物を特定します。モデル／tokenizerのrevision、image ID、sourceと読み込まれたoverlay、実効設定、対象kernelのdispatchを確認し、意図した実装が動いた証拠のない比較は無効にします。起動の識別子、sampling／thinking、入出力長、同時数、warmup、APC履歴も結果と保存します。
- cold prefillとAPC hitを分けます。coldの入力長の梯子では各要求の早い位置に固有nonceを置き、短い入力が次の入力のprefixになるのを避け、tokenizerかusageで長さを測ります。共通system／tool部分はヒットし得るためcached-token数とサーバーログを照合し、証拠の欠落は不明のままにします。
- 同一出力を前提とする速度比較ではcompletion hashを比べます。異なるcompletionは別条件として扱い、性能・品質の結果や失敗を残し、同一出力での改善という主張へ混ぜません。
- 重み・量子化・投機の深さを変える場合は種類ごとに複数promptを使い、調整用と評価用の入力を分けます。種類ごとに3つ以上を仮の出発点とし、無改変armのprompt間のばらつきから数の根拠を決めます。tok/sと採択長、step/sの目安（decode tok/s÷採択長）を並べます。completionが変わると、演算自体の速さが変わらなくてもdraftの採択が変わるためです。step/sを比べるのは同じ深さのarmどうしに限ります。深いdraftは1 stepで検証する位置が多いためです。1.6.0のroute gと深さの掃引は種類ごとに1 promptで、1.7.0の掃引は調整用・評価用に分けた10入力です（[両方のcheckpointで深さ3](speculative-decoding.ja.md#両方のcheckpointで深さ32026-09-21)）。
- draft側の変更はcompletionを変えるものと見込みます。このstackではdraftした候補が検証のbatchに入り、targetのBF16 logitsの同点が別の側に倒れるため、同じ深さでもdraftを変えると（top-kの使い回し、関門、再量子化した `lm_head`）ほとんどの入力で文章が変わり、無改変のarmは自分の文章を反復しました。そうした変更は採択と教師強制NLLで判定し、文章の一致は要件ではなく余得として扱います。
- 同じ計測窓の送信／完了要求数・出力token数とサーバーcounter差分を照合します。背景要求の混入や説明できない不一致がある窓は制御比較から除き、値と理由を残します。counterのない既存記録は、隔離を確認できた範囲を明示します。Mia PR #139の独立TP2報告がこの区別の実例です。同報告のadaptive policy・graph範囲・scratchサイズ変更は合算で測られています。
- 採択率の分母を明示します。生成draft数・検証候補数・実採択draft数（bonusを除く）は異なります。検証prefixを短くすれば、固定深さでの予測能力が改善しなくても率が上がり得ます（Mia PR #235）。DFlash2の結果を標準MTPへ、greedyの結果をsamplingへ転用しません。

`server agreement --reference` が受け取る参照結果は1本で、対照2本には対応しません。`self_agreement` は起動内の反復を測ります。無改変→候補→無改変の比較では3本を保存し、既存の `agreement.compare_records` 関数で対照同士も確認してください。起動内の安定を起動間の安定と読み替えません。2本目の参照を受けるCLIオプションは設けていません。

## 評価と未解決の事項

[FreedomBench](freedombench.ja.md)（固定した英語の設問、確認済みの日本語訳、言い回しと証拠配置の追加試験）、[HLE](hle.ja.md)（100問の部分集合二つを両profileで。公開されているHLEの値とは比べられない）、[ハーネス受け入れ一覧](harnesses.ja.md)（ケース別の状態と受け入れた経路）がそれぞれ結果の正典です。後述の基礎APIスモークは一覧のAPI群に反映され、クライアントのケースを終わらせません。[NCCL診断](nccl-validation.ja.md)の範囲は2 rankと3 rankでのtransportと合成データの正当性で、フルモデルではありません。fixture、APIスモーク、collectiveの結果を、[SETUP手順6](../SETUP.ja.md#6-フルモデルの検証)の受け入れが宣言していない範囲の証拠に変えないでください。

未解決の事項と、それぞれの正典：

- FB-05のLPAの部分（近似を実際に通すA/B/A）は、LPAがoffの間は未実施（[FreedomBench](freedombench.ja.md)）。
- 長いcontextで、公開した任意設定は問われた記録の直前の記録で答えた。原因は切り分けていない（[prefix cacheの関門](correctness-gates.ja.md#prefix-cacheの正しさの関門)）。
- モデルのAPIではtool-eval-benchのSafety Gateを通らない。任意の[tool引数ゲート](harnesses.ja.md#tool引数ゲート)越しでは通る。
- 持続的な混在負荷とbatchingの組合せは未検証。TP=3ではキャンセル、ツール利用、障害からの復旧を実施していない（[SETUP手順6](../SETUP.ja.md#6-フルモデルの検証)）。
- MTPの深さ、decodeのGraphs、prefix caching、APC／LPAの併用には限定した証拠しかない（[投機的デコーディング](speculative-decoding.ja.md)、[施策台帳](optimization-catalog.ja.md)、[prefix caching](benchmarks.ja.md#全モデルのprefix-caching独立評価p19)、[P22の契約](apc-lpa-design.ja.md)）。

## フルモデルの範囲

**状態。** 2台のTP=2と3台のTP=3で、両profileが通常運用として**受け入れ済み**です。いずれも[起動設定](server-configuration.ja.md)の設定で、[同時実行の範囲](#同時実行の範囲)の内側です。その受け入れの日付と範囲、各項目の証拠の所在は[SETUP手順6](../SETUP.ja.md#6-フルモデルの検証)が記録で、本ページやREADMEが食い違ったら手順6が優先します。その範囲の外（他のハードウェア、手順6の範囲を超える同時数、動画入力、未対応の要求設定）は何も検収していません。同時実行の範囲に続く小節は、証拠をどう集めたかの記録です。他の検査は[関連する検査](#関連する検査)にあります。

### 同時実行の範囲

| 構成とprofile | 同時系列数 | 状態 |
|---|---|---|
| 2台のTP=2、配布既定 | 1（`max_num_seqs = 1`）。それを超える要求は順番待ちになり、これが宣言した挙動 | 受け入れ済み（[SETUP手順6](../SETUP.ja.md#6-フルモデルの検証)）。同時2系列以上は**2台では非対応**：rankあたり3 GiBのKVは256Kの1系列向けで、固定の重みでの同時実行には、2台で予算を増やすことではなくrankを増やすこと（下のTP=3）が要る |
| 2台のTP=2、公開した任意設定（[例のprofile](../examples/server.axl.example.toml)） | 2。rankあたり6 GiBのKVから。再パックした重みはrankあたり4.4 GiB軽い | 受け入れ済み（[SETUP手順6](../SETUP.ja.md#6-フルモデルの検証)）。証拠は下 |
| 3台のTP=3、両profile（[例のprofile](../examples/server.tp3.example.toml)） | `max_model_len`、`max_num_seqs`、rankあたりのKVで決まる。テンプレートは262,144 tokenの1系列を配信する（[容量](benchmarks.ja.md#1240での測定)） | 受け入れ済み（[SETUP手順6](../SETUP.ja.md#6-フルモデルの検証)。スイッチなしのQSFPリングでつないだGB10×3、NVIDIAの[3台リングの手引き](https://build.nvidia.com/spark/connect-three-sparks)）。測っていないもの：長い要求4本以上の同時、配布既定の262,144超 |

**同時2系列profileの証拠。** 2026-09-23の1起動で、約200Kの合言葉要求2本を同時に送って両方正答・preemptionなし、tool呼び出し2本の同時で両方が正しい呼び出し、画像1本と散文1本の同時で両方回答しました（[1.10.2での測定](benchmarks.ja.md#1102での測定)。時間・decode速度・メモリもそこにあります）。同日の3起動（数値状態は2・1・2）がそれぞれ切替後の定型——両rankの重みのdigestが初回起動と一致、decode検査、要求のtrace、3起動目はkernel hashも——を通り、[1.10.4](benchmarks.ja.md#1104での測定)のsparkDashとtool-evalは2起動目で走り、3回の切替はいずれも復旧なしで完了しました。項目は[SETUP手順6](../SETUP.ja.md#6-フルモデルの検証)にあります。未測定：境界262,144 tokenの要求2本の同時。キャンセルはハーネスのケース[H-06](harnesses.ja.md#受け入れ試験一覧と実施状態)で、新しい起動は配布既定と同じく仮定せず検査します。

**TP=3の証拠。** 2026-09-29と10-01に、3台での両profileの起動が、decode検査（起動内で課題ごとに1種類、配布既定の同じruntime cacheでの2回目の起動は1回目とbit単位で一致）、教師強制のNLL、約200Kの合言葉、[画像入力](vision.ja.md#3台のtp3)、[日本語・韓国語の検査](correctness-gates.ja.md#マルチバイト出力)を通りました。rankごとの重みのdigestは配布既定で取りました。TP=2に対する教師強制のNLLは、平均の差の固定幅ではなく、二つの記録を位置ごとに比べて受け入れます：argmax一致0.93以上、実際のtokenのlog確率の動きの平均が、数値状態だけが違う同じ重みのTP=2の起動同士の1.5倍以内。両profileとも満たしました。TP=3の起動のdecode検査のhashは、各ホストのruntime cacheと組のときだけ有効です（[起動の安全](launch-safety.ja.md#3ノード)）。数値は[1.24.0での測定](benchmarks.ja.md#1240での測定)。

**同時2系列での反復性。** 単独の要求はbit一致で反復します。他の要求とstepを共有した要求は違うcompletionになりえます。固定したbackendにはbatch-invariant modeが無く（[証拠の表](#証拠であり本番認定ではない)）、呼び出しを共有するものが要求の結果を変えるためです：NVFP4のMarlin MoEはK方向をexpert block数で分け、prefillと共有したstepはprefill用のkernelを通り、MTPの深さ3では相方がいるとdecodeのstepが8行になり、6行を超えるのでattentionが参照計算の代わりにFA2を通ります（[起動設定](server-configuration.ja.md#attentionとcacheとcheckpoint)）。attentionは主因ではありません：すべての呼び出しを参照計算に切り替えても2系列の差の多くは残り、容疑者の先頭は、MoEと、prefillと共有したstepのprefill用のkernelです（[servingでの到達性](benchmarks.ja.md#servingでの到達性2026-09-26)）。どちらの重みでも同じで、同じ順に送った組は反復します（[1.14.0での測定](benchmarks.ja.md#1140での測定)）。これは宣言した挙動であって、受け入れた欠陥ではありません。**どんな負荷でも反復するcompletionが要る場合は `max_num_seqs = 1` で配信します**。同時に送った要求は待ち行列に入り、それぞれ単独のcompletionになります。要求が重なるときに2系列で増える処理量は[1.14.0での測定](benchmarks.ja.md#1140での測定)にあります。

### 読み込み・API・ベンチマークの確認

reference imageは、2台のGB10ホストで45層の言語層すべてを、Marlin W4A16、eager実行、同時1系列、context 16,384、rankあたり1 GiBのKVでロードしました。直列TP=2の4層fixtureは、既存の状態検査をすべて通過しました。fixtureを同時2系列にした場合、greedy経路の1本がほぼ同値の箇所で分岐しました。この生の診断は失敗のままであり、課題水準の受け入れとは別です。

フルモデルは、served IDの基礎確認、英語・日本語の最終回答、OpenAIのSSE、無害な自動ツールの呼出し・引数・戻り、AnthropicのMessages／count_tokensのスモーク検査に合格しました。reasoning effortを低くしたチャットの受け入れ試験も、これらの最終回答・ツールの基準を満たしました。再実行では推論文が異なりました。これは診断として残すものであり、自由記述の逐語一致を要求するものではありません。未対応のthinking offを指定した要求ではparserと本文が混ざったため、受け入れ済みの構成ではありません。[ハーネスの設定](harnesses.ja.md)を参照してください。

[vLLM公式の合成ベンチマーク](benchmarks.ja.md)は、計画した計測要求をすべて完了しました。MTPはテンプレートに入る前に、k=1とk=3で同じベンチとAPIのケースに合格しました。別のメタデータviewは、元のcheckpointを保ったまま、そのBF16 MTP層を全体のNVFP4から除外します。深さ1〜5と3の選定は[投機的デコーディング](speculative-decoding.ja.md)にあります。これらの確認はどれも、単体ではアプリケーションの品質を示しません。宣言した範囲での通常運用は、[SETUP手順6](../SETUP.ja.md#6-フルモデルの検証)に記録した受け入れに拠ります。

1.25.0のimageには、samplerの語彙の範囲のガード（vLLM #50843）が入っています。有限のlogitsの行には何もしません。2026-10-02、このimageで両profileのdecodeの確認は1.24.0のcompletionとbit単位で同じになり、公開した任意設定の `server agreement` は基準の記録と完全に一致しました（argmaxの一致1.0、log確率の動きなし）。
