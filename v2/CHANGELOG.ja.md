# 変更履歴

[English](CHANGELOG.md)

正典は[英語版](CHANGELOG.md)です。GitHub Releaseの本文は英語版の各版の節から作られます。

TensorFoldで配信する2.x系です。`v2.*` のタグはこのファイルの節を公開します。1.x系の履歴は[v1/CHANGELOG.ja.md](../v1/CHANGELOG.ja.md)にあります。

## 2.1.4 — 2026-10-06

### Engine

- imageは [Bizuayeu/TensorFold](https://github.com/Bizuayeu/TensorFold) のbranch `release/2.1.4` の `a265436de869bd596b20a915758de0cc829fb5a0`（[`TENSORFOLD_REF`](docker/Dockerfile)）からTensorFoldを作ります。2.1.1のエンジンに、TensorFoldのpull request #421（m-naoki-m）を上流のmergeより先に取り込みました。`_take_over` は、残す保持promptを決めてから写すようになりました。長い会話の後に新しい会話が来ても、他の保持promptを写しては捨てることがなくなります（issue #420の測定ではrankあたり約15 GiB）。pull requestの試験は2.1.1のエンジンで6本中3本が落ち、このエンジンでは通ります。上流の試験2本の作り物のsnapshotには、本物が持つ `drafter_rows` の欄を足しました。

### Documentation

- [運用](docs/operations.ja.md#起動の結果)：新しいimageや別のエンジンが重みを読んだ直後に、起動が窓を断るときと、その対処（ページキャッシュ）。

### Accepted

2026-10-06に参照機の対で、TP=2・画像入力を有効にして、リリース候補のimage（linux/arm64 `sha256:257c69ba7c8586bd8ce5f158e9cf87af6365a78e2b7baa00338d1ac0c0d4a717`、3台で同じ）で測りました：

- decode検査は2.1.1のtoken idと文字列を出し、画像の検査はすべて合格しました。
- issue #420の筋書き：11 turnで247,330 tokenまで伸ばした会話の後に、頭を共有しない会話を送りました。新しい会話の間も `MemAvailable` はrank 0で11〜12 GiB、rank 1で12〜15 GiBのままで、最初の要求は1.4秒で答えました。
- 200,000×20の画像（vLLM #59126のもの）と114,000×28の画像は400（decodeした画素数の上限）で断られ、エンジンは配信を続けました。
- エンジン自身の試験：briefの一式は1,263 passed、小さなモデルのビットの照合は2.1.1と同じです。

## 2.1.3 — 2026-10-06

### Added

- decode検査と `score-nll` は、走らせる側で `TENSORFOLD_API_KEY` が設定されていればサーバーのAPI keyを送り（`Authorization: Bearer`）、無ければ何も送りません。rank 0のrankのファイルの `TENSORFOLD_API_KEY` の行でkeyを付けて起動したエンジンは、keyの無い要求をすべて拒みます（`/metrics` も）。loopbackの外でkey付きで配信する方法は[安全](README.ja.md#はじめ方)の注意に書き、rank 0の例のファイルにその行をコメントで入れました。

### Documentation

- [検証](docs/validation.ja.md#prefillとdecodeの速さ)は2.1.2の記述を直しました。長いpromptは、同じクロック・温度のまま約7.5%離れた2つの速さのどちらかで走り、3回続けると2つの起動では落ちず、1つでは落ちました。熱では説明できず、原因は分かっていません。起動後の最初の長いpromptは遅い、という記述は取り下げます（ある起動では速かった）。[決定](docs/decisions.ja.md)にTP=2の `split` と `gather` の比較を足しました：2つの速さのどちらでも `split` が約5%速く、tokenは同じです。
- [手順書](SETUP.ja.md#3-image)：imageのtagは、imageに写るファイルを最後に変えた版の名前で、文書やホスト側の道具だけの版ではそのままです。
- [CONTRIBUTING](../CONTRIBUTING.ja.md)：CUDAか固定のvLLMのimageが要る1.x系のテストは、GPUのホストでだけ走ります。

### Accepted

2026-10-06に参照機の対で、TP=2、2.1.1のimage（変わらず）、rank 0のrankのファイルにkeyを置いて：keyなしの `/health` は200、`/v1/models` と `/metrics` はkeyなしと違うkeyで401、正しいkeyで200。keyを渡したdecode検査は2.1.1のtoken idと文字列を出し、keyなしでは401で止まりました。rank 0のserveと記憶の見張りのlog、検査のlogにkeyは出ていません。

## 2.1.2 — 2026-10-05

### Documentation

- [検証](docs/validation.ja.md#prefillとdecodeの速さ)は、続けて流すとprefillが遅くなるのでホストを冷ます、とは書かなくなりました。2.1.1では、38,960 tokenのprefillを冷まさずに3回続けても、TP=2・TP=3とも速さは落ちず、クロックとCPUの周波数は変わらず、熱の待ちにも達しませんでした。引いていたTP=3の1,670から1,540 tok/sへの低下（2.0.0の受け入れの頃の観測）は再び出ませんでした。起動後の最初の長いpromptは遅いので、測る前に1本流すことも書きました。

image・スクリプト・配信の既定は変わらないので、2.1.1のimageと受け入れがそのまま有効です。

## 2.1.1 — 2026-10-05

### Engine

- imageは [Bizuayeu/TensorFold](https://github.com/Bizuayeu/TensorFold) のbranch `release/2.1.1` の `1a3fb1789830f4c336179eae21129f21c5abae0f`（[`TENSORFOLD_REF`](docker/Dockerfile)）からTensorFoldを作ります。2.1.0のエンジンに下の直しを足したものです。

### Fixed

- 複数の画像を持つ要求では、画像のtowerを1回だけ呼んでまとめてencodeしていました。そのため、ある画像の特徴量が同じ呼び出しの他の画像によって変わりました（実物のtowerで、448×448の画像を896×672の画像と並べると、どちらの順でも448×448の側のビットが変わりました）。今は1枚ごとにtowerを呼ぶので、要求に他の何が入っていても画像の特徴量は同じです。

### Accepted

2026-10-05に参照機で、TP=2・画像入力を有効にして、リリース候補のimage（linux/arm64 `sha256:54cf0e5bc7fe56a218a91f704443285caa11f68f5389fa618ef577d7b9fcad67`、3台で同じ）で測りました（[測定値](README.ja.md#リリースでの測定値)）：

- decode検査は2.1.0のtoken id・文字列のhash・受理長を出しました。
- 画像の検査はすべて合格でした。同じ大きさの2枚の画像は、1枚ずつ聞いても2枚まとめて聞いても同じ数を読みました。
- 38,960 tokenのprefillを冷まさずに3回続けて、1,327.0・1,326.8・1,322.8 tok/sでした。その間、GPUのクロックは2,184 MHzのままでclock event reasonは無く、CPUの全コアは最大の周波数のままで、最も熱いACPIのzoneは56 °Cから88.5 °Cまで上がり、熱の待ちには達しませんでした。

## 2.1.0 — 2026-10-05

### Engine

- imageは [Bizuayeu/TensorFold](https://github.com/Bizuayeu/TensorFold) のbranch `release/2.1.0` の `9a1c7cc9fd231c65ebf5bffaed421937303e0796`（[`TENSORFOLD_REF`](docker/Dockerfile)）からTensorFoldを作ります。2.0.0の追加を上流のv0.6.5へ衝突なしで載せ直し、次を足しました：
  - **画像入力**。上流のpull request #194（rank 0でencodeし、特徴量を他のrankへ送る）を3 rankへ広げ、1枚の画像をcheckpointの上限8,000の視覚tokenまでにし、rank 0の作業域をtowerの実測から決めます（[採否](docs/decisions.ja.md#他で名前を挙げていないエンジンのcommit)）。
  - latentの経路が持つ `kv_b` の2つ目の写し（`latent.AbsorbW`・`AbsorbQ4`）を、重みのバイト数と起動時の見積もりに数えます。これまで漏れていました。
- 上流のv0.6.5でAPI key（`--api-key`・`--api-key-file`・`TENSORFOLD_API_KEY`）が入りました。この系列は設定しません（[はじめ方](README.ja.md#はじめ方)）。

### Serving defaults

- **画像入力を有効にし、rankのファイルで切り替えます**：例のファイルのとおり全rankで `VISION=1` なら `serve.sh` が `--vision` を渡し、`VISION=0` で無効になります。窓は変わりません。TP=2ではrank 0が1.05 GiBのtowerを持ち、他の会話の保持promptは既定の3 GiBのうち2.4 GiBになります（TP=3は3 GiBのまま）。
- **TP=2はNCCLを4 channelにし、rankのファイルにIBのtransportを書きます**（TP=3と同じ）。NCCLが自分で開く64本と比べ、decodeは+0.8〜1.0%、起動時の余地は約1.5 GiB増、prefillは0.4%以内でした。各rankの性能コアへの固定と、draftの深さの固定は測って採りませんでした（[採否](docs/decisions.ja.md)）。

### Fixed

- decode検査はstreamingのdeltaの欄を1つしか取っていませんでした。draftの1 roundの塊が推論を終えて本文を始めると推論の末尾を捨て（「200.」が「200」になる）、token idは同じでも文字列のhashがdraftの深さで動きました。今は両方を取ります。countとcodeは文字列の基準のhashが新しくなりました（[検証](docs/validation.ja.md#decode検査)）。token idは2.0.0のままです。

### Accepted

2026-10-05に参照機で、リリース候補のimage（linux/arm64 `sha256:d4d2014ca311841a5ff65c09d97a33abdf2c7db00ba4386dc7ecf7fd689cbb69`、3台で同じ）で測りました（[測定値](README.ja.md#リリースでの測定値)）：

- decode検査はTP=2とTP=3で、画像入力の無効・有効とも、2.0.0のtoken idと受理長を出しました。
- 画像入力を無効にしたTP=2のNLLの採点セットは2.0.0と全精度で同じで、38,960 tokenのprefillは1,221.5（1回目）・1,331.1・1,329.9 tok/sでした。
- 画像入力は両TPで、1枚、prompt 7,966 tokenの4:3の画像、2枚の順番、単色、toolの結果の画像、文字の質問、toolの往復に正しく答え、動画は400で拒みました。

2.0.0の他の結果はそのまま有効です。promptとdecodeの経路は同じtokenを出します。コマンドのtagは `glm53-tf:2.1.0` です。

## 2.0.10 — 2026-10-05

### Documentation

- [採否](docs/decisions.ja.md)は、2.x系がまだ取り上げていない1.x系の施策にLPAを加えました。1.x系の後段Prefill近似は長いprefillの結果を設計上変え、2.x系の基準のhashとNLLは厳密なprefillのものです。
- [QSFPネットワーク](../docs/qsfp-network.ja.md#8-3台をリングにつなぐ)は、dummy interfaceの `glmhost` が例の名前であることを書きます。参照機のリングでは `tp3host0` で、この系列のTP=3のrankのファイルが `NCCL_SOCKET_IFNAME` に書く名前です。

image・台本・配信の既定値は変わらないので、2.0.7のimageと受け入れはそのまま有効です。

## 2.0.9 — 2026-10-05

### Tests

- tool引数ゲートの大きすぎる本文のテストは、0.3秒待つ代わりに、ゲートの処理のスレッドが全部終わるのを待ってから、上流に何も届いていないことを確かめます。0.5秒遅れて送る不具合を戻すと、このテストは落ちます。

### Changed

- CIは検査の道具を、1.x系のlockではなくcheckoutのルートの `requirements/dev.lock.txt`（Ruff。全系で一つの版）から入れます（[CONTRIBUTING](../CONTRIBUTING.ja.md)）。

image・台本・配信の既定値は変わらないので、2.0.7のimageと受け入れはそのまま有効です。

## 2.0.8 — 2026-10-05

### Documentation

- 1.x系との比較は、1.x系が冷却gateと熱の見張りで熱を扱うと書いていました。1.x系はエンジンの中で待たず、測定では要求の合間に冷却gateでホストを休ませました。1.x系で熱の見張りを使った記録はありません。
- clusterのファイルの `CHECKOUT` は各機上のこのリポジトリのルートで、1.x系の `--checkout` はその `v1/` を指します。設定の表にそう書きました。

### Tests

- `--wait` で一時停止中のdownloadを扱うテストは、確かめることを全部まとめた1本です。別の `test_transfer_state.py` は同じことを繰り返していました。

image・台本・配信の既定値は変わらないので、2.0.7のimageと受け入れはそのまま有効です（リポジトリの `.dockerignore` から、それ以上何も通していなかった行を外しました。build contextは同じです）。

## 2.0.7 — 2026-10-05

### Changed

- imageを作り直して受け入れ直しました。Dockerfileは、tag `26.07-py3` の代わりにdigestでNVIDIAのbaseを固定します（`nvcr.io/nvidia/pytorch@sha256:2140e699…`、2.0.0を受け入れたもの）。imageの中で変わったのは `THIRD_PARTY_NOTICES.md`（ライセンス整理の新しい置き場と、このimageもこのファイルを持つこと）と `serve.sh` のコメントの直しです。base・package・エンジンは層ごとに2.0.0と同じです。2026-10-05に作り直したimageを参照機で同値として受け入れました。TP=2とTP=3で[decode検査](docs/validation.ja.md#decode検査)が基準のhash・token id・受理長を出し、NLLの採点セットは2.0.0と全精度で一致しました。他の結果は2.0.0のものがそのまま当てはまります。コマンドのtagは `glm53-tf:2.0.7` です。
- ホストのツールを `v2/host/` からcheckoutのルートの[`host/`](../host/README.ja.md)へ移し、全系共通の[ホストの準備](../docs/hosts.ja.md)とfabricの文書と並べました。`python3 host/cool-gate`、`python3 host/thermal-watch`、`host/` から `sudo sh install.sh` です。
- clusterのファイルは、Gitが無視する `state/cluster.env` に置きます。手順はcheckoutのルートの `my-cluster.env` に置かせていて、そこはGitが無視しません。

### Added

- [運用](docs/operations.ja.md)：起動の終わり方、他のrankが待つ中で一つのrankが止まる場合、socketに落ちたNCCL、containerの作り直し、新しいimageへの移行、電源が落ちたホスト、1.x系へのホストの引き渡し。
- [採否](docs/decisions.ja.md)：2.x系が採ったもの・採らなかったもの（日付、測った効果、再び開く条件）、変更履歴が名指さないリリースbranchのcommit、2.x系でまだ評価していない1.x系の施策。
- [ベンチマークの方法](docs/benchmarks.ja.md)：リリースの測定値と検証の基準値の取り方。

### Documentation

- [手順書](SETUP.ja.md)の§6と§9に、`cluster.sh` の起動の終わり方（READY、全rankのlogの末尾つきのFAILED、15分でTIMEOUT）、logの場所、停止がrankごとに最大60秒待つことを書きました。READMEは `TF_GLM_CACHE_GIB` とNLLの検査が使うendpointを挙げ、prefillの行はTP=2の3本が1回の冷却の後に続けて流したものと書きます。

### Tests

- 文書が引く `serve.sh` の値、台本の既定値、ゲートのport、`TENSORFOLD_REF`、固定したbaseとrevisionを両言語で検査します。clusterのファイルは `state/` の下に置くこと、どの台本も構文が通ることも検査します。1.x系からの写しで落ちていた検査2つ（score-nllが送る本文、decode検査のtokenの記録をdecode-divergenceが読むこと）を戻しました。

## 2.0.6 — 2026-10-04

### Added

- 公開監査はこの系列も検査します：必須のファイル、変更履歴の両言語に節がある版、Apache-2.0のライセンス、`config/model.lock.json` のモデルのrevisionの固定。

### Documentation

- リリースの測定値は、未公開のcommitを名指しする代わりに、走らせたエンジンの版（リリース、その1つ前の表示の行だけが違う版、熱の待ちを入れる前の版）を書きます。熱の待ちが無いと[熱の見張り](../host/README.ja.md#長い運転の間)が94 °Cでエンジンを止めたことも、記録のとおり書きます。機が熱くなるとprefillが遅くなることは[検証](docs/validation.ja.md)に一度だけ書きます。比較の1.xの列は、1.x系のベンチマークの出所を名乗ります。

image・台本・配信の既定値は変わらないので、2.0.0のimageと受け入れはそのまま有効です。

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
