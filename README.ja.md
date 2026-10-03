# GLM-5.3-Flash-NVFP4-DGX-Sparks-BIZ

[English](README.md)

**NVFP4 BIZ** は、NVIDIAの固定したGLM-5.3-Flash NVFP4 checkpointを配布のまま、DGX Sparkまたは互換のGB10機で配信します。このリポジトリは配信の系列ごとにディレクトリを分けています。

| 系列 | エンジン | ディレクトリ | 変更履歴 |
|---|---|---|---|
| 1.x | vLLM | [v1/](v1/README.ja.md) | [v1/CHANGELOG.ja.md](v1/CHANGELOG.ja.md) |
| 2.x | TensorFold | [v2/](v2/README.ja.md)：TP=2とTP=3、FP8 KV、テキストとtool呼び出し。2.0.0に向けて準備中（[手順書](v2/SETUP.ja.md)） | [v2/CHANGELOG.ja.md](v2/CHANGELOG.ja.md) |

系列ごとにREADME・版・変更履歴を持ちます。リリースのtag `v1.*`・`v2.*` は、その系列の変更履歴の節を公開します。1.x系のコマンドは `v1/` で、2.x系のimageのbuildと台本はcheckoutのルートで実行します（[手順書](v2/SETUP.ja.md)）。`state/` と `records/` は追跡対象外で、checkoutのルートに置きます。

ライセンス：[LICENSE](LICENSE)（Apache-2.0）、[NOTICE](NOTICE)、[第三者の表示](THIRD_PARTY_NOTICES.md)。貢献の手引き：[CONTRIBUTING.ja.md](CONTRIBUTING.ja.md)。
