# NVFP4 BIZ 2.x（TensorFold）

[English](README.md) · [リポジトリの索引](../README.ja.md) · [セットアップ手順書](SETUP.ja.md) · [検証](docs/validation.ja.md) · [変更履歴](CHANGELOG.ja.md)

**NVFP4 BIZ** は、NVIDIAの固定したGLM-5.3-Flash NVFP4 checkpointを、再学習も再量子化もせず配布のまま、DGX Sparkまたは互換のGB10機で配信します。名前はこの意図を表し、エンジンには依存しません。2.x系はvLLMに代えて[TensorFold](https://github.com/ashhart/TensorFold)（Apache-2.0）で、2台のTP=2または3台のTP=3で配信します。2.0.0が最初のリリースです。[1.x系](../v1/README.ja.md)も並んで続きます。

**BIZ**は保守者の印で、リポジトリの意図を示す語です。意味することと意味しないことは[リポジトリのREADME](../README.ja.md#biz)にあります。

## 要約

- **何であるか。** 固定したcheckpointを、固定したTensorFoldのcommitで一つのOpenAI互換endpointとして配信するための、build手順・起動の台本・受け入れ検査です。2台なら直結のConnectX-7リンクでTP=2、3台ならswitchなしのリングでTP=3です。公開している測定値はMSI EdgeXpert（MS-C931）で取りました。
- **状態。** 2.0.0は2026-10-04に参照機で、[検証](docs/validation.ja.md)の基準値に対して両TPで受け入れました（[リリースでの測定値](#リリースでの測定値)）。主張の範囲はそこまでです。他の機体は同じ検査を回して確かめます。
- **反復性はエンジンの契約。** draftした応答はserialと同じ、再開したpromptは最初からと同じ、promptのchunkの切り方で結果が変わらない。これはエンジンの契約で、1.x系はvLLMの上でスイッチを入れて反復性を得ています（[1.x系との違い](#1x系との違い)）。
- **精度。** routed expertとdense MLPはW4A16、他はBF16、KVはFP8です。NVIDIAのmodel cardは別のレシピ・別の機材でcheckpointを測っており、その精度表はこの配信を表しません。この配信を表す数字は[検証](docs/validation.ja.md)にあります。
- **ライセンス。** コードとエンジンはApache-2.0、重みはMITで運用者がダウンロードします。配信の経路に非商用の条件はありません（[ライセンスの早見表](../README.ja.md#ライセンスの早見表)）。
- **未検証。** 同時に2系列以上、画像入力、公開したAXLの重み、ハーネス連携（ZCode・Claude Code）、他のrank数と機材、アプリケーション全体の品質と本番の信頼性（[制限](#制限)）。

## 何であるか

- **重み**：`nvidia/GLM-5.3-Flash-NVFP4` のrevision `423acf37583782c51c142d145aef733d72943d93`。1.x系と同じで、[Z.aiのGLM-5.3-Flash](https://huggingface.co/zai-org/GLM-5.3-Flash)から作られています。routed expertとdense MLPはcheckpointのNVFP4 blockからW4A16で、attention・shared expert・headはBF16のまま計算します。例外はエンジンの中の一つだけです：MTP層のrouted expertはcheckpointではBF16で、draft専用にNVFP4へ量子化します。draftしたtokenは全部本体のモデルが検証するので、応答は変わりません。
- **エンジン**：TensorFoldのBIZ版。[Bizuayeu/TensorFold](https://github.com/Bizuayeu/TensorFold) のbranch `release/2.0.0` として公開します。TensorFold v0.6.4に、GLMのNVFP4の読み込み、FP8 latent KV、TP=3の分割、ビットを変えないprefillの改善、上流のpull request #301（止めた要求が全rankで1 round以内に終わる）、prompt chunkの合間に熱で待つprefillを足したものです。imageはその一つのcommitに固定します（[`TENSORFOLD_REF`](docker/Dockerfile)）。
- **image**：[`docker/Dockerfile`](docker/Dockerfile)。NVIDIAのPyTorch container 26.07に、測定した版のpackage（transformers 5.18.0、構造化出力のxgrammar 0.2.8、Hugging Face hubのclient）とエンジンを入れます。
- **起動**：[`scripts/`](scripts/) のshellの台本と、rankごとの環境ファイル一つ（[`examples/`](examples/) に参照機のファイル）。順番は[SETUP.ja.md](SETUP.ja.md)にあります。

## 必要な環境

- **機体**：DGX Sparkまたは互換のGB10機を2台か3台（Linux ARM64、各128 GBの統合メモリ）。GPUで他の大きな仕事を動かさないこと。同じ機で1.x系のserverが動いていれば先に止めます。
- **fabric**：RoCE v2のConnectX-7リンク。2台は直結、3台はswitchなしのリング（[3台をリングにつなぐ](../v1/docs/qsfp-network.ja.md#8-3台をリングにつなぐ)）。各portの2本のrailを両方使います。
- **ホストカーネル**：1.x系と同じです。今のDGX OSの更新が入れる既定のカーネルは、複数ノードのRoCEを壊すことがあります（[ホストカーネルと複数ノードRoCE](../v1/docs/operations.ja.md#ホストカーネルと複数ノードroce)）。
- **GPUクロック**は全機で2,200 MHzを上限にし、温度を記録します（[GPUクロックの上限](../v1/docs/operations.ja.md#gpuクロックの上限)）。2.x系の数字は全部この上限の下で測りました。
- **Docker**：NVIDIAのGPU runtimeとRDMA deviceが要ります（`/dev/infiniband` が無い機では、NCCLがsocketに落ちるので `create_container.sh` が止まります）。
- **disk**：checkpointに1台あたり約205 GB（全機が丸ごと持ちます）と、image。
- **操作する機械**：全機へSSHでき、`cluster.sh` を動かす機械一台。ダウンロードと検査には `v1/` の1.x系のPythonの道具を使います。

## はじめ方

各段とその後に確かめることは[セットアップ手順書](SETUP.ja.md)にあります。以下はTP=2のときの骨組みです。全機で同じ、確認済みの `v2.*` のtagを使います。

```sh
# 一度だけ、ある1台の v1/ から。その後cacheを他の機へ写し、写しごとに検証する（SETUP §2）
python -m glm53_setup download --background
python -m glm53_setup verify-download --hf .venv/bin/hf --output ../records/checksum --wait

# 各機で、checkoutのルートから（SETUP §3〜§5）。1台でbuildして他は `docker load`、image IDを比べる
docker build -f v2/docker/Dockerfile -t glm53-tf:2.0.0 .
v2/scripts/create_container.sh glm53-tf:2.0.0
cp v2/examples/tp2-rank0.env ~/glm53-tf/rank.env      # もう1台は tp2-rank1。その後この機の値に直す
docker exec glm53-tf bash /opt/glm53-tf/build_ext.sh

# 操作する機械で（SETUP §6・§9）
cp v2/examples/cluster.tp2.env my-cluster.env           # HOSTS（rank順）と CHECKOUT
v2/scripts/cluster.sh my-cluster.env start first        # first はlogの名前。rank 0のserving行でREADY
v2/scripts/cluster.sh my-cluster.env stop
```

rank 0はloopbackで答えます：

```sh
curl -s http://127.0.0.1:8095/v1/chat/completions -H 'Content-Type: application/json' -d '{
  "model": "glm-tf",
  "messages": [{"role": "user", "content": "Write a Python fibonacci function."}]
}'
```

モデルは答える前に考えます。思考は `reasoning_content`、答えは `content` に返るので、`max_tokens` を指定しない要求は両方で32,768 tokenまで使えます。小さい上限では思考の途中で終わり、`content` が空になることがあります。起動したら、日常の運用の前に[検証](docs/validation.ja.md)の検査（まずdecode検査）で受け入れます。

**安全。** 2.0.xが土台にする上流のv0.6.4のエンジンには認証がありません（v0.6.5でAPI keyが入りました。[Next Action](#next-action)）。`serve.sh` はrank 0を `127.0.0.1` で待ち受けさせ、[tool引数ゲート](SETUP.ja.md#7-tool引数ゲート任意)もloopbackだけで待ち受けます。SSHのtunnel（`ssh -L 8095:127.0.0.1:8095 <rank 0>`）か、認証を足すproxyを通して使ってください。rankのファイルで `HOST=0.0.0.0` にすると、APIは認証なしで外に出ます。

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

## 設定

配信は三か所で決まります。二つのファイルは [`examples/`](examples/) から写して自分の値に直し、Gitには入れないでください。

| 場所 | 設定 | 既定 | 意味 |
|---|---|---|---|
| rankのファイル（`/work/rank.env`、`serve.sh` が読む） | `MASTER` | なし（必須） | リンク上のrank 0のaddress。全rankで同じ |
| | `NCCL_IB_HCA`・`NCCL_IB_GID_INDEX`・`NCCL_SOCKET_IFNAME` | 参照機の値 | リンクのRDMA device（両rail）、RoCE v2のGIDの番号、bootstrapのinterface。TP=3ではsubnet-aware routingと4 channelが加わります（[`tp3-rank0.env`](examples/tp3-rank0.env)） |
| | `NCCL_DEBUG`・`NCCL_DEBUG_SUBSYS` | `INFO`・`INIT,NET` | NCCLが起動時に各接続のtransportを一度だけ書き、[SETUP §6](SETUP.ja.md#6-起動)がそれを読みます |
| | `MODEL_NAME`・`HOST`・`PORT` | `glm-tf`・`127.0.0.1`・`8095` | rank 0のmodel idと待ち受け |
| | `CHECKPOINT` | `/hub` の下の固定snapshot | container内のcheckpointのdirectory |
| | `TF_GLM_HEAT_HIGH`・`TF_GLM_HEAT_LOW` | `92`・`88`（°C） | prefillの熱の待ち。全rankで同じ値、空にすると待たない |
| | `TF_GLM_CACHE_ENTRIES` | `8`（エンジンの既定） | 他の会話の保持promptの本数。別の値にしたらdecode検査にも同じ値を渡します（[decode検査](docs/validation.ja.md#decode検査)） |
| `serve.sh` の引数 | `TP RANK RANK_ENV` の後 | なし | 既定の後ろで `tensorfold serve` に渡るので、こちらが勝ちます（`--context 500000`） |
| clusterのファイル（`cluster.sh`） | `TP`・`HOSTS`・`CHECKOUT` | なし（必須） | TPの大きさ、rank順のSSH名、各機上のこのリポジトリ |
| | `SSH`・`CONTAINER`・`WORK` | `ssh -o ConnectTimeout=20`・`glm53-tf`・`$HOME/glm53-tf` | 機への入り方、container、`/work` に見せる機のdirectory |
| `create_container.sh` | `IMAGE [WORK_DIR]`・`CONTAINER`・`HF_HUB` | `~/glm53-tf`・`glm53-tf`・`~/.cache/huggingface/hub` | image、作業directory（rankのファイル・extension・log）、container名、`/hub` に読み取り専用で見せるHugging Faceのcache |

rankのファイルは `bash` が全変数をexportしながら読むので、他の `TF_GLM_*` や `NCCL_*` の設定もエンジンに届きます。この表に無い設定は2.0.0では測っていません。

## API

rank 0がエンジンのHTTP APIを出します。受け入れで使ったもの：

- **`/v1/chat/completions`**：streamとそれ以外、toolと構造化出力（tool-eval-benchのTC-64〜TC-69。imageにxgrammarが要ります）を、[tool引数ゲート](SETUP.ja.md#7-tool引数ゲート任意)越しに。
- **思考**：検査が送る形の `chat_template_kwargs.reasoning_effort` と `clear_thinking`。streamでは1つのdeltaに `reasoning_content` と `content` の両方が乗ることがあります（[制限](#制限)）。
- **`"draft": false`**：要求のbodyに入れると1 roundに1 tokenずつdecodeします。draftした応答が一致すべきserialの基準です。
- **応答の `tensorfold` block**：`accepted` と `rounds`（MTPの受理）、`cached`（保持promptから再開したprompt token数）、`heat_wait_s`。
- **`/health`**（decodeの `rounds` など）と **`/metrics`**。1.x系の道具はこれでエンジンを見分けます。
- **停止**：クライアントの切断やstop文字列で、全rankのdecodeが1 round以内に終わります。

エンジンは `/v1/completions`・`/v1/models`・`/v1/responses`・Anthropicの `/v1/messages`・`/tokenize` にも答えますが、2.0.0の受け入れでは確かめていません。

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
| tool引数ゲート越しのtool-eval-bench | 93/100、Safety Gate通過 | 91/100、Safety Gate通過 | TP=2 AXL 90/100 |
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

## リポジトリの構成

2.x系のファイルは `v2/` にあります。imageはライセンスのあるcheckoutのルートからbuildします。

```
v2/
  README.md         このページ（各 .md の隣に .ja.md）
  SETUP.md          セットアップ手順書
  CHANGELOG.md      2.x系のリリース。v2.* のtagがその節を公開する
  docker/           Dockerfile：image。エンジンは TENSORFOLD_REF で固定
  scripts/          create_container.sh  各機の配信用container
                    build_ext.sh         エンジンのCUDA extension（imageごとに一度）
                    serve.sh             1 rank、配信の既定つき
                    cluster.sh           操作する機械から全rankを起動・停止・状態確認
                    hostwatch.sh         メモリの見張り（MemAvailableが5 GiBを切るとエンジンを止める）
  examples/         参照機のrankのファイルとclusterのファイル（TP=2とTP=3）
  docs/             validation.md：受け入れの検査と基準値
  pyproject.toml    2.x系の版
```

ダウンロード・検証・tool引数ゲート・検査の道具は1.x系のもので、`v1/` から動かします。

## TensorFoldの他のレシピ

GLM-5.3-FlashをTensorFoldで配信する公開レシピです。各レシピのリンク、2026-10-04に確認したライセンス、この系列が取り込んだものは、この表が正典です。他のエンジンのレシピは[1.x系の表](../v1/README.ja.md#dgx-spark向けの他のglm-53-flashレシピ)にあります。それぞれの測定は別の重みと設定によるもので、上の数字とは比べられません。

| レシピ | ライセンス | この系列が取り込んだもの |
|---|---|---|
| [ashhart/TensorFold](https://github.com/ashhart/TensorFold) | Apache-2.0（0.5.0まではMIT） | エンジンそのもの。リリースのbranchは上流v0.6.4に自前のcommitを足したもので、それらは上流のissue #308・#309・#310・#339とpull request #333として返しています |
| [MiaAI-Lab/GLM-5.3-Flash-EXL3-2x-DGX-Sparks-TensorFold](https://github.com/MiaAI-Lab/GLM-5.3-Flash-EXL3-2x-DGX-Sparks-TensorFold) | Apache-2.0 | FP8 latent KVはそのpatch 0038に倣い、v0.6.x上で書き直して、エンジンの表示にクレジットしています（上流のissue #309）。TP=3の分け方はpatch 0066と同じ規則です（単位の境界で切り、余りを若いrankへ）。上流のpull request #301（止めた要求が全rankで終わる）はそのままリリースに入っています。自前のEXL3 checkpointをDFlash2のdraftで、同時に最大8要求、画像と動画の入力つきで配信しています |
| [jakejharris/jspark3 v2.0.1](https://github.com/jakejharris/jspark3/releases/tag/v2.0.1) | Apache-2.0（レシピ）、MIT（そのエンジン＝TensorFold 0.3.6.2のfork） | 何も取り込んでいません。自前のTensorFoldのforkで、4-bitのMLX形式の重みを3台に分けてTP=3で配信します。既定はDFlash2のdraftで、商用には `--drafter none` の経路を示しています。会話の状態をdiskに保存するcacheを持ち、RigMarkで測っています |

## 免責事項

- **BIZは意図であり、約束ではありません**（[リポジトリのREADME](../README.ja.md#biz)）。
- **受け入れは参照機のものです。** 他の機や別のimage IDでの起動は、そこで[検証](docs/validation.ja.md)を回して受け入れます。
- **上流が取り込むまで、エンジンはforkです。** 上のissueとpull requestは上流でまだopenで、その間はリリースのbranchが持ちます。

## Next Action

各項目は、きっかけと、そのときこの系列がすることです。

- 上流がpull request [#320](https://github.com/ashhart/TensorFold/pull/320)（呼び手が止めたらGLMの応答を両rankで止める。2026-10-04時点で0.6.6の審査中）か#301をmergeする → リリースのbranchの#301を上流の停止に置き換え、そのリリースに載せ直し、imageを受け入れ直して、2.x系のリリースで `TENSORFOLD_REF` を動かす。
- 上流がissue #308・#309・#310・#339やpull request #333の中身を取り込む（2026-10-04時点で0.6.6の一覧にはどれも無い）→ リリースのbranchをその上流のリリースに載せ直し、上流が持つようになったものを外し、imageを受け入れ直して、2.x系のリリースで `TENSORFOLD_REF` を動かす。
- 上流のv0.6.5に追従する → エンジンでAPI keyが使える（`--api-key`・`--api-key-file`・`TENSORFOLD_API_KEY`。`/health` は開いたまま、`/metrics` は `--metrics-open` でなければkeyが要る）。rankのファイルで設定し、[はじめ方](#はじめ方)の安全の注意を書き直す。
- 上流が0.6.6を出す（2026-10-04時点で試験中：要求に無い `<tool_call>` のmarkupが応答の本文に漏れる件の#285と#256、同じtokenを延々繰り返すのを止める `--loop-guard` の#210と#262（#204向け）、起動時に開けるファイル数を上げる#294）→ リリースのbranchと突き合わせて読み、2.x系のリリースで追う。
- 上流のpull request [#243](https://github.com/ashhart/TensorFold/pull/243)（2 rankで `--parallel N`）がmergeされる → 同時に2系列以上を扱う作業に入る。
- 画像入力：2.0.0の後の予定。まず上流のpull request [#194](https://github.com/ashhart/TensorFold/pull/194)（GLM-5.3-FlashのCUDAの2 rankでの画像入力）を読み、合えばそれを土台にし、合わなければこの系列のエンジンに配線する。リリースで受け入れるまで、エンジンは画像を拒みます。
- [1.x系のNext Action](../v1/README.ja.md#next-action)にある機体のCPU周波数の検査 → その結果はこの系列の数字にも当てはまる。
- 公開したAXLの重みを2.x系で使うこと：2.0.0の後まで保留。2.x系は固定した重みだけを配信します。
- 次のエンジンの変更 → Dockerfileでbase imageをdigestで固定する（`nvcr.io/nvidia/pytorch@sha256:2140e699…`、2.0.0を受け入れたもの）。どのみちimageを受け入れ直すときなので。

## ローカルデータと開発

Gitに入れないもの（自分の機の値を入れたrankとclusterのファイルを含む）、ライセンス、開発への参加は[リポジトリのREADME](../README.ja.md#ローカルデータと開発)にあります。2.x系の変更は[CHANGELOG.ja.md](CHANGELOG.ja.md)にあります。
