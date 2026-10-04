# NVFP4 BIZ 2.x（TensorFold）

[English](README.md) · [リポジトリの索引](../README.ja.md) · [セットアップ手順書](SETUP.ja.md) · [検証](docs/validation.ja.md) · [変更履歴](CHANGELOG.ja.md)

**NVFP4 BIZ** は、NVIDIAの固定したGLM-5.3-Flash NVFP4 checkpointを、再学習も再量子化もせず配布のまま、DGX Sparkまたは互換のGB10機で配信します。名前はこの意図を表し、エンジンには依存しません。2.x系はvLLMに代えて[TensorFold](https://github.com/ashhart/TensorFold)（Apache-2.0）で、2台のTP=2または3台のTP=3で配信します。2.0.0が最初のリリースです。[1.x系](../v1/README.ja.md)も並んで続きます。

## 何であるか

- **重み**：`nvidia/GLM-5.3-Flash-NVFP4` のrevision `423acf37583782c51c142d145aef733d72943d93`。1.x系と同じです。routed expertとdense MLPはcheckpointのNVFP4 blockからW4A16で、attention・shared expert・headはBF16のまま計算します。例外はエンジンの中の一つだけです：MTP層のrouted expertはcheckpointではBF16で、draft専用にNVFP4へ量子化します。draftしたtokenは全部本体のモデルが検証するので、応答は変わりません。
- **エンジン**：TensorFoldのBIZ版。[Bizuayeu/TensorFold](https://github.com/Bizuayeu/TensorFold) のbranch `release/2.0.0` として公開します。TensorFold v0.6.4に、GLMのNVFP4の読み込み、FP8 latent KV、TP=3の分割、ビットを変えないprefillの改善、上流のpull request #301（止めた要求が全rankで1 round以内に終わる）、prompt chunkの合間に熱で待つprefillを足したものです。imageはその一つのcommitに固定します（[`TENSORFOLD_REF`](docker/Dockerfile)）。
- **image**：[`docker/Dockerfile`](docker/Dockerfile)。NVIDIAのPyTorch container 26.07に、測定した版のpackage（transformers 5.18.0、構造化出力のxgrammar 0.2.8、Hugging Face hubのclient）とエンジンを入れます。
- **起動**：[`scripts/`](scripts/) のshellの台本と、rankごとの環境ファイル一つ（[`examples/`](examples/) に参照機のファイル）。順番は[SETUP.ja.md](SETUP.ja.md)にあります。

## 配信の既定

[`scripts/serve.sh`](scripts/serve.sh) が持ち、全rankで同じです。

| 設定 | TP=2（2台） | TP=3（3台） |
|---|---|---|
| KV cache | latentとindexerのpool keyをFP8（`TF_GLM_KV=fp8`） | 同じ |
| draft | checkpointのMTP head（`--drafter none`：DFlash2は使わない） | 同じ |
| 窓（`--context`） | 300,000 token | 0＝収まる最大：参照機のリングで1,048,576（モデルの上限） |
| 要求が指定しないときの応答の上限 | 32,768 token（`--max-tokens`） | 同じ |
| NCCL | 各リンク2本のrail、rankごとのファイルから | 2本のrail・4 channel・subnet-aware routing |
| rank間のprefillの交換 | エンジンの既定 `split` | 同じ |
| 熱によるprefillの休止 | chunkの合間に全rankそろって、どれかのrankのACPIの最高温度が92 °Cを超えたら、全rankが88 °C以下になるまで待つ（`TF_GLM_HEAT_HIGH`／`TF_GLM_HEAT_LOW`） | 同じ |
| 他の会話の保持prompt | エンジンの既定：8本、3 GiB | 同じ |

**TP=2を300,000にする理由。** `--context 0` では対の窓が567,255 tokenになり、他の会話の保持promptに何も残りませんでした。長い履歴を送り直すチャットやエージェントでは保持が効きます。エンジン自身のメモリの見積もりでは、300,000 tokenは567,255に比べてrankあたり約3.3 GiBを空け、既定の3 GiBの保持promptが収まります。1.x系は262,144 tokenですが、それには合わせていません。別の窓にするには `serve.sh` に `--context` を渡します（最後のflagが効きます）。対が持てる最大は約567Kです。

## 1.x系との違い

| | 1.x（vLLM） | 2.x（TensorFold） |
|---|---|---|
| 出力の反復性 | vLLMの[再現性のスイッチ](../v1/docs/server-configuration.ja.md#再現性のスイッチ)（expert内のtoken順の固定、indexerのtop-kの同点の決め方、計測なしで選ぶInductorのconfig） | エンジンの契約：draftした応答はserialと同じ、再開したpromptは最初からと同じ、promptのchunkの切り方で結果が変わらない |
| KVと窓 | FP8、262,144 token（rankあたり3 GiB） | latentとindex keyをFP8、TP=2で300,000 token、TP=3で1,048,576 |
| 起動 | `glm53_setup` が一つのserver TOMLを読む。`server preflight`・`cluster switch`・warmupの段階 | ここの台本。preflightや切替は無い |
| 同時に処理する系列 | 1、公開した任意設定の2系列profileで2 | 1 |
| 画像入力 | 受ける | 受けない |
| 公開したAXLの重み | 任意で使える | 対応しない |
| tool呼び出し | モデルのAPI、任意でtool引数ゲート越し | 同じゲートを `v1/` から起動してエンジンの前に置く |
| 長いprefill中の熱 | エンジンの外：要求の合間の冷却gateと熱の見張り | エンジンがprompt chunkの合間に全rankそろって待つ（92 °Cで待ち、88 °Cで再開） |

## リリースでの測定値

2026-10-04に参照機（MSI EdgeXpert、GPUクロックの上限2,200 MHz）で取りました。エンジンは、リリースのbranchの `b44c2f1`、その1つ前（表示の行だけが違う）の `2d4fa9b`、または熱の待ちを入れる前の `304109c` です。熱の待ちはprompt chunkの走る時刻しか変えません。どの行がどれかは注に書きました。手順と基準値は[検証](docs/validation.ja.md)にあります。

| 測定 | TP=2 | TP=3 | 1.x |
|---|---|---|---|
| decode検査 count／prose／code（tok/s） | 41.04／26.73／34.85 | 52.47／37.99／48.47 | TP=2配布既定 32.59／21.12／28.21、TP=3 AXL 49.59／28.32／38.33 |
| 同じタスクのMTP受理長 | 3.821／2.098／3.180 | 3.549／2.222／3.234 | — |
| 38,960 tokenのprefill（tok/s、3回の中央値、各回の前に冷却） | 1,329.9 | 1,668.5（熱の待ちを切ると1,671.4） | TP=2配布既定 1,233.4 |
| 短い固定promptの後の512 tokenのdecode（tok/s） | 35.31 | 52.93 | TP=2配布既定 27.18 |
| 窓（token） | 300,000（`--context 0` なら567,255） | 1,048,576 | 262,144（TP=2） |
| 199,652 tokenの合言葉 | 正答、最初のtokenまで163.7 s | 正答、最初のtokenまで133.2 s | TP=3 AXL 150.5 s |
| 1,036,859 tokenの3か所の合言葉 | — | 3/3、最初のtokenまで1,264.8 s（うち熱の待ち170.1 s） | TP=3 AXL 1,058 s |
| teacher-forced NLL 日／英／コード／数学 | 2.5474／2.9257／1.3184／0.6250 | 2.5313／2.9001／1.3101／0.6237 | TP=2配布既定（1.26.0）2.5412／2.9079／1.3145／0.6285 |
| tool引数ゲート越しのtool-eval-bench | 93/100、Safety Gate通過 | 91/100、Safety Gate通過 | TP=3 AXL 90/100 |
| 応答の途中のクライアント切断やstop文字列 | 1 round以内に止まり、次の要求がすぐ始まる | 同じ | — |

- **反復性。** TP=2とTP=3の出力は、互いにも1.x系ともビット一致しません。rank間の和の分け方が違うためです。それぞれは自分自身と一致します。起動の中でも、起動をまたいでも、railが1本でも2本でも、熱の待ちが起きている最中でも、decode検査はタスクごとに一つのcompletionでした（[基準のhash](docs/validation.ja.md#decode検査)）。NLLは開発版の値と全精度で同じでした。
- **どのエンジンで測ったか。**
  - decode検査は、TP=2が `b44c2f1`、TP=3が `2d4fa9b` です。
  - TP=3のprefillと1M tokenのpromptは `2d4fa9b` です。
  - 他の行は `304109c` です。
- **熱。** 1M tokenのpromptの間、最も熱い機は92 °C前後にとどまり、数秒ずつ約80回待って、最高は92.8 °Cでした。待ちが無いと、同じpromptは6分半で94 °Cに達し、熱の見張りがエンジンを止めました。prefillは機が熱くなるほど遅くもなります。38,960 tokenを3回続けると、1,670から1,540 tok/sまで下がりました。待ちの閾値の手前で、クロックは変わっていません。長い要求の合間には機を冷やしてください。
- **tool-eval-bench**は、1.x系と同じ69シナリオと呼び方で回しました。両TPともTC-61だけ失敗しました。

## 制限

- **一度に1系列。** エンジンのCUDAの経路はGLMの要求を一本ずつdecodeし、他は順番を待ちます。
- **テキストとtool呼び出しだけ。** エンジンはCUDAのGLMで画像入力を拒みます（`GLM-5.3-Flash image input is currently MLX-only`）。
- **TP=3はDFlash2とEXL3を拒みます。** どちらも2 rankにしか分割できません。この系列はどちらも使いません：`serve.sh` は `--drafter none` を渡し、checkpointはNVFP4です。
- **streamの応答。** draftがあると1 roundが思考から本文へまたがることがあり、1つのdeltaに `reasoning_content` と `content` の両方が乗ります。deltaごとに片方しか読まないクライアントは文を落とします。streamでない応答は欠けません。
- **FP8 KVはBF16 KVに対して損失があります**（1.x系も同じ）。draftした応答はserialと同じままです。短い4本の文章では、二つのcacheのNLLの差は0.011以内でした（2026-10-02）。
- **ConnectX-7のリンクでつないだ2台か3台**で、1.x系と同じです。他のrank数、他の機材、同時の要求は測定の範囲外です。

## ライセンス

リポジトリのルートの[LICENSE](../LICENSE)（Apache-2.0）、[NOTICE](../NOTICE)、[第三者の表示](../THIRD_PARTY_NOTICES.md)。エンジン自身の表示は、image内のそのソース（`/opt/tensorfold`）と一緒にあります。
