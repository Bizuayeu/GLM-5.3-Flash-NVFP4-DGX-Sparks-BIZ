# 変更履歴

[English](CHANGELOG.md)

正典は[英語版](CHANGELOG.md)です。GitHub Releaseの本文は英語版の各版の節から作られます。

TensorFoldで配信する2.x系です。`v2.*` のタグはこのファイルの節を公開します。1.x系の履歴は[v1/CHANGELOG.ja.md](../v1/CHANGELOG.ja.md)にあります。

## 2.0.5 — 2026-10-04

### Changed

- この系列は自分の道具を使います。1.x系の道具を `v1/` から動かす代わりに、`v2/` から [`glm53_tf`](README.ja.md#リポジトリの構成) を `python -m glm53_tf download | verify-download | tool-gate | decode-check | decode-divergence | score-nll` で動かします。中身は1.x系の写しで、引数も同じです。decode検査とtool引数ゲートの既定はこの系列のエンジン（`http://127.0.0.1:8095`、モデル `glm-tf`。ゲートは8896で待ち受け）です。モデルの固定は `config/model.lock.json`、NLL採点セットは `config/nll_set.json`（1.x系のものとバイト単位で同じ）、Hugging Faceのclientのlockは `requirements/huggingface.lock.txt` です。`scripts/serve.sh` のrevisionとセットのhashがずれないことはテストで守ります。新しいコマンドは[セットアップ手順書](SETUP.ja.md)と[検証](docs/validation.ja.md)にあります。image・台本・配信の既定値は変わらないので、2.0.0のimageと受け入れはそのまま有効です。

### Documentation

- [`host/`](../host/README.ja.md)に、参照機でsudoなしに確かめたこと（記録係、`cool-gate` の両方の結果、container内で起こしたprocessを止める `thermal-watch`）と、`thermal-watch` はcontainerのPID 1を止められないことを書きました。
- リポジトリのREADMEは、各系列が自己完結していることと、ルートの `tools/` はリポジトリの公開監査とリリースノートだけだと書きます。

## 2.0.4 — 2026-10-04

### Fixed

- `host/gb10-telemetry` とホストの道具のテストは、UTCを `datetime.UTC` と書きます。Python 3.11以降でruffが求める書き方で、2.0.3のCIはここで止まっていました。他は変わりません。

## 2.0.3 — 2026-10-04

### Added

- [`host/`](../host/README.ja.md)：この系列の測定に使い、保守者の記録の中にだけあったホストの熱の道具です。GPUクロックの上限のunit、温度の記録係とそのunit・据え付け台本、`cool-gate`（長い要求の間にホストが冷めるのを待つ）、`thermal-watch`（94 °C以上が2回続くとエンジンを止める）。据え付け台本はserviceの利用者を引数に取ります。`thermal-watch` はこの系列のエンジンでだけ確かめました。CPUテストは `tests/` にあり、CIが回します。

### Documentation

- 1.x系との比較は、1.x系の公開したTP=3のdecode検査 51.00／30.10／39.48 tok/s を引きます。49.59／28.32／38.33は、どのテンプレートも設定しないprefillの上限512で走らせた値でした。1.x系のtool引数ゲートの結果はTP=2のもので、長さの違う走行を比べる行は1.x系の長さを書き、NLLの行は採点セットを名乗ります。
- 両系列に共通することは[リポジトリのREADME](../README.ja.md)へ移しました。1.x系が持つ事実（クロックの上限、ホストごとのcheckpointの大きさ、ホストのカーネル、ダウンロード、decode検査、再現性スイッチ）は書き直さずに指します。[検証](docs/validation.ja.md)は基準値を持ち、decode検査のpromptを `decode_check.py` と同じに書きます。
- 例のclusterのファイルは、`CHECKOUT` にcloneの既定のディレクトリを書きます。

image・台本・配信の既定値は変わらないので、2.0.0のimageと受け入れはそのまま有効です。

## 2.0.2 — 2026-10-04

### Documentation

- [Next Action](README.ja.md#next-action)。2026-10-04の上流とレシピの確認から：
  - 上流は0.6.6に向けて、GLMの両rankの停止として、リリースのbranchが持つ#301ではなくpull request #320を審査しています。どちらかがmergeされたら#301を置き換えます。この系列のissue #308・#309・#310・#339とpull request #333は、上流の0.6.6の一覧にありません。
  - 上流のv0.6.5に追従すると、エンジンでAPI keyが使えるようになります。[はじめ方](README.ja.md#はじめ方)の安全の注意は、認証が無いのはv0.6.4のことだと書くようにしました。
  - 上流の0.6.6は、この系列に効く三つの修正（tool呼び出しのmarkupが本文に漏れる件、同じtokenを延々繰り返すのを止めるガード、開けるファイル数の上限）のために見守ります。
  - 画像入力は、自前で配線する前に上流のpull request #194（GLM-5.3-FlashのCUDAの2 rankでの画像入力）を読みます。
  - 1.x系のNext Actionにある機体のCPU周波数の検査は、この系列の数字にも当てはまります。

## 2.0.1 — 2026-10-04

### Documentation

- [README](README.ja.md)に、初めて読む人が要る節を足しました。既存の節は変えていません：受け入れの範囲を書いた要約、必要な環境、TP=2のはじめ方（`curl` の要求と、エンジンに認証が無いことの注意。rank 0とtool引数ゲートはloopbackだけで待ち受けます）、rank・cluster・containerのファイルの設定を一つにまとめた表、受け入れで使ったAPIと確かめていない経路、リポジトリの構成、ライセンスの早見表、免責事項、Next Action、ローカルデータ。英語版の見出しはtitle caseにしました。
- [TensorFoldの他のレシピ](README.ja.md#tensorfoldの他のレシピ)：GLM-5.3-FlashをTensorFoldで配信する公開レシピのリンクと、この系列が取り込んだものの正典になる表です。上流のTensorFold、MiaAI-LabのTensorFold版（patch 0038に倣ったFP8 latent KV、patch 0066と同じ規則のTP=3の分け方、上流のpull request #301）、jakejharris/jspark3 v2.0.1（何も取り込んでいません）。1.x系のレシピの表は、MiaAI-LabのTensorFold版についてここを指します（1.28.2）。

image・台本・配信の既定は変わっていないので、2.0.0のimageと受け入れはそのまま有効です。

## 2.0.0 — 2026-10-04

2.x系の最初のリリースです。1.x系と同じ固定のcheckpoint（`nvidia/GLM-5.3-Flash-NVFP4` の `423acf37583782c51c142d145aef733d72943d93`）を、vLLMに代えて[TensorFold](https://github.com/ashhart/TensorFold)で、2台のTP=2または3台のTP=3で配信します。1.x系は[`v1/`](../v1/README.ja.md)で続きます。

### Engine

- imageは[Bizuayeu/TensorFold](https://github.com/Bizuayeu/TensorFold)のbranch `release/2.0.0` の `b44c2f197863f889659874e9be4b8e318768a828` からTensorFoldをbuildします（[`TENSORFOLD_REF`](docker/Dockerfile)）。上流のv0.6.4に、CUDAのGLM-5.3-Flash向けの次のものを足した版です。
  - **NVIDIAのNVFP4 checkpointを保存されたまま読む**（W4A16）：routed expertとdense MLPはNVFP4のblockから、attention・shared expert・headはBF16です（上流issue #308）。
  - **FP8 latent KV**（`TF_GLM_KV=fp8`）：DSAのlatent cacheとindexerのpool keyをe4m3の行で持ちます（上流issue #309）。
  - **TP=3**（`--tp 3`）：2 rankにも3 rankにも使う1つのshard plan。3で割れない大きさは不揃いの取り分にし、語彙のgatherは幅の違うshardをまたぎます（上流issue #310）。
  - **ビットを変えないprompt処理の高速化。**
    - promptのBF16 matmulはKの切れ端をregisterで足します（上流pull request #333）。
    - prompt chunkのrank間の交換を、行の切れ端ごとに2本目のstreamで回します。
    - 交換は正確なreduce-scatterで、各rankは自分の行だけを貼り合わせます（`split`。rank同士で送り合えるときの既定）。
    - indexerは1 programで16行を採点し、選択が読むpoolの列だけを採点し、top 512のために長い行を5回でなく3回読みます。
  - **止めた要求が1 roundのうちに全rankで終わる**：クライアントの切断やstop文字列のときです（上流pull request #301）。
  - **長いprefillが熱で待つ。** prompt chunkの前ごとに各rankが最も熱いthermal zoneを共有し、`TF_GLM_HEAT_HIGH` を超えたら、全rankが `TF_GLM_HEAT_LOW` 以下になるまでそろって待ちます。待ちはchunkの走る時刻を動かすだけで、ビットは変えません。待つたびに `[tensorfold] heat:` の行を出し、応答に `heat_wait_s` を載せます（上流issue #339）。

### Serving defaults

[`scripts/serve.sh`](scripts/serve.sh) が全rankに同じ値を設定します（[配信の既定](README.ja.md#配信の既定)）。

- FP8 latent KVと、checkpointのMTP headによる下書き（`--drafter none`）。
- 窓はTP=2で300,000 token（他の会話の保持promptに既定の3 GiBを残す）、TP=3では収まる最大（参照機のリングで1,048,576 token＝モデルの上限）。
- 要求が上限を指定しないときの応答は最大32,768 token。
- prefillの熱の待ちは92 °Cで待ち、88 °Cで再開します。参照機の熱の見張りは94 °Cでエンジンを止めます。待ちが無いと、TP=3の1M tokenのpromptは6分半でそこに達しました。

### Image and launch

- [`docker/Dockerfile`](docker/Dockerfile)：NVIDIAのPyTorch container 26.07に、測ったときの版のtransformers 5.18.0、xgrammar 0.2.8、Hugging Face hubのクライアントと、固定したcommitのエンジンを入れます。checkoutのルートからbuildします（[手順書](SETUP.ja.md#3-image)）。
- [`scripts/`](scripts/)：
  - `create_container.sh` と `build_ext.sh`：各機のcontainerと、エンジンのCUDA extension。
  - `serve.sh`：1つのrank。
  - `cluster.sh`：1台から全rankを起動・停止します（他のrankが先、rank 0が最後）。
  - `hostwatch.sh`：メモリの見張り。エンジンはcontainerの中でrootで動くので、containerを通して止めます。
- [`examples/`](examples/)：参照機のTP=2とTP=3のrankファイル（2 rail、GID 3、RoCE v2、subnetを見た経路選択、TP=3は4 channel）。`NCCL_DEBUG=INFO` で、NCCLが起動時に各接続の経路をログに出します。

### Accepted

2026-10-04に参照機で測りました（[測定値](README.ja.md#リリースでの測定値)、[検証](docs/validation.ja.md)）。decode checkと1M tokenのpromptは、リリースのimage（`glm53-tf:2.0.0`、linux/arm64のimage `sha256:3d06b02953398603580edcecef22c06c3c8ed0d9e3d1568d66f1bd0d1ae21b44`。`docker images` が示すIDはbuildの来歴も含み、buildしたcheckoutごとに変わります）か、その1つ前（表示の行の変更だけが違う）のimageで回しました。他の項目は、熱の待ちを入れる前のbranch `304109c` のimageで回しました。熱の待ちはprompt chunkの走る時刻しか変えません。

- decode checkはTP=2・TP=3とも参照のhashを出しました。熱の待ちが起きている最中も同じです。
- 下書きありの応答は逐次の応答と一致しました。
- teacher-forcedのNLLは開発buildの値と全精度で同じでした。
- TP=3では、熱の待ちを入れたまま1,036,859 tokenの中の合言葉3つを見つけました：最初のtokenまで1,264.8 s（うち待ち170.1 s）、最も熱い読みは92.8 °Cでした。
- tool-argument gate越しのtool-eval-bench：TP=2で93/100、TP=3で91/100、どちらもSafety Gateを通過しました。
