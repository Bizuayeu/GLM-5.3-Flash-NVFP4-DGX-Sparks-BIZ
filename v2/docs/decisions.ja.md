# 決定（2.x）

[English](decisions.md) · [2.x系の概要](../README.ja.md) · [検証](validation.ja.md) · [ベンチマークの方法](benchmarks.ja.md)

2.x系のために何を試し、何を採り、何を採らなかったかを、日付、測った効果、決定を開き直す条件と一緒に並べます。1.x系の[施策台帳](../../v1/docs/optimization-catalog.ja.md)にあたる2.x系の頁です。効果は参照機でGPUクロックの上限の下、各決定をしたときの開発版で測りました。行にTP=3とない限り、対でのTP=2です。prefillは38,960 tokenのpromptを3回測った中央値です（[ベンチマークの方法](benchmarks.ja.md)）。リリースそのものの値は[リリースでの測定値](../README.ja.md#リリースでの測定値)に、基準値は[検証](validation.ja.md)にあります。「—」は、記録に決定を開き直す条件が無いことを示します。

## エンジン

| 決定 | 日付 | 測った効果 | 開き直す条件 |
|---|---|---|---|
| vLLMの代わりにTensorFoldで配信する | 2026-10-02 | 厳密性がエンジンの契約である（draftした応答はserialと同じ、再開は最初からと同じ、結果はchunkの切り方によらない）。1.x系はvLLMのスイッチを入れて反復性を買っている（[1.x系との違い](../README.ja.md#1x系との違い)） | — |
| 上流のTensorFoldから始めてGLMに要るものだけを移植し、MiaAI-LabのTensorFoldのレシピの上には作らない | 2026-10-02 | そのFP8 latent KV（patch 0038）は先行するpatch約37本の上に乗っており、上流0.6.1へのdry runはほぼ全hunkが失敗したので、上流の上で書き直した（約600行） | — |
| 上流のリリースに追従し、衝突は上流の側を採る | 2026-10-03 | v0.6.2、v0.6.3、v0.6.4、続いてv0.6.5（2.1.0、衝突なし）。v0.6.4ではTP=3の交換を上流の通信のinterface（#219）の上に載せ直した。全rankでの停止は上流のpull request #301をそのまま取り込み、新しく書いていない | 上流が#320か#301をmergeする、またはこの系列のissueと#333を取り込む（[Next Action](../README.ja.md#next-action)） |
| 配信のcontainerにCPUの集合を設定しない（`create_container.sh` は配置をkernelに任せる） | 2026-10-05 | 固定しないとエンジンのスレッドは高効率コアを含む20コアすべてで動きました。両rankを性能コアに固定しても（`docker update --cpuset-cpus 5-9,15-19`）、decodeとprefillの差は揺れの内でした（counting 41.35 → 41.36 tok/s、prefill 1,327 → 1,329 tok/s）。1.x系には固定が要ります（[CPU配置](../../v1/docs/benchmarks.ja.md#参照対でのcpu配置2026-09-26)） | 同じ設定で片方のrankのdecodeだけが遅い |

## 精度とメモリ

| 決定 | 日付 | 測った効果 | 開き直す条件 |
|---|---|---|---|
| FP8のlatent KV（`TF_GLM_KV=fp8`）、行ごとに2のべき乗のscale | 2026-10-02 | 1 tokenのKVはlatent cacheを持つ12層（DSAの11層とMTPの層）でrankあたり12,912 byte、BF16のKVでは19,200（−33%）。TP=2の窓はBF16のKVで344,820 token、その版のFP8で約490K。draftした応答はserialと同じまま。BF16のKVに対しては非可逆（[制限](../README.ja.md#制限)）。checkpointはFP8のKVを宣言するがKVのscaleを持たない（vLLMは1.0を使う）ので、行ごとのscaleにした。同じpatchのindexerのring（keyとgateをringに持つ）は移植していない。BF16の既定の配置を変えるため | rankあたりの窓をもっと要する。次の一手がring |
| routed expertとdense MLPはW4A16、`--precision checkpoint` は拒む | 2026-10-02 | 上流のgrouped NVFP4 expert kernelはBF16の行しか受けず、input scaleの経路が無い。固定のcheckpointで活性のscaleを使って変わるのはdenseの0〜2層だけ | — |
| MTP層のrouted expertをdraft専用にNVFP4へ量子化する | 2026-10-02 | checkpointではBF16（13.5 GiB）。TP=2でrankあたり6.75 GiBが1.90 GiBになる。draftしたtokenは全部フルモデルが検証するので、応答は変わらない | — |
| KDAのconvの係数を保存されたとおりfp32に保つ | 2026-10-02 | 以前の版はkernelのためにBF16へ丸めていた。kernelはfp32を直接読むようになり、1.x系のvLLMと同じくfp32のまま。係数がBF16のMLXとEXL3のcheckpointは、tokenもcacheも以前と同じ（12通り中12） | — |
| TP=3の分担は単位の境界で切り、余りを若いrankへ | 2026-10-03 | 頭22/21/21、MoEの幅704/704/640、語彙51,648/51,648/51,584。ゼロの行を作らず、重みに手を加えない。2 rankではすべてのテンソルで半分割とbyte単位で一致。重みの見積もりはrank 0/1/2で63.04/62.87/57.70 GiB | — |
| 公開したAXLの重みには対応しない | 2026-10-04 | 容量のためには要らない：固定の重みでTP=2は1.x系より大きな窓を持つ。TP=3で効くのはprefillのうち長さで伸びない部分だけで、最大でchunkあたり12 ms、その部分の約1%（2026-10-03） | 一度に複数の系列を扱うようになる。1.x系はAXLを2系列で測った |

## 窓・上限・範囲

| 決定 | 日付 | 測った効果 | 開き直す条件 |
|---|---|---|---|
| TP=2の窓は300,000 token、`--context 0` の567,255にしない | 2026-10-04 | 他の会話の保持promptに既定の3 GiBを残す（[300,000の理由](../README.ja.md#配信の既定)） | 配備が別の `--context` を渡す |
| TP=3の窓は収まる最大（`--context 0`） | 2026-10-03から使い、2026-10-04に配布の既定 | 参照機のリングで1,048,576 token、モデルの上限 | — |
| 要求が上限を指定しないときの応答は最大32,768 token | 2026-10-03 | — | — |
| 4,096行のprefillのchunk | 2026-10-02に不採用 | 同じ版の2,048行の1,169.9 tok/sに対し1,076.1、窓は約490Kから約405Kへ縮む。ビットは同じだった | — |
| 一度に1系列 | 2026-10-02 | エンジンのCUDAの経路はGLMの要求を一度に一つずつdecodeする | 上流が#243をmergeする |
| 2.0.0では画像入力なし | 2026-10-04 | エンジンはCUDAのGLMで画像を拒む | 先に上流のpull request #194を読む（[Next Action](../README.ja.md#next-action)） |
| 画像入力は上流のpull request #194を3 rankへ広げたもの。既定で有効（例のrankのファイルは `VISION=1`） | 2026-10-05 | #194はrank 0でencodeして特徴量を送り、3 rankではその集めの幅を広げるだけで済みました。2.1.0の受け入れでは両TPで、1枚、prompt 7,966 tokenの4:3の画像、2枚の順番、単色、toolの結果の画像を読み、有効にしても画像なしのtoken idは2.0.0のままでした。窓は変わりません。TP=2では1.05 GiBのtowerの分、保持promptは3 GiBのうち2.4 GiBになり、それを承知で画像を既定にしました | 上流が#194をmergeする。TP=2の保持promptの2.4 GiBが長い会話で足りないと分かる |

## draft

| 決定 | 日付 | 測った効果 | 開き直す条件 |
|---|---|---|---|
| checkpointのMTP headでdraftする（`--drafter none`）、DFlash2は使わない | 2026-10-04 | 明示する：エンジンの `--drafter auto` は、DFlash2の重みがcacheにあるとTP=2ではそれを使い、TP=3では拒む（2 rankにしか分けられない）。1.x系がDFlash2を使わない理由は、その重みの条件 | — |
| draftの深さはエンジンの方針（`auto`）に任せ、`--mtp-drafts` で固定しない | 2026-10-05 | 深さ4と5の固定をautoと比べたdecode：countingは+8%と+14%、proseは−15%と−20%、codeは−2%。温度1.0でもautoが上でした（proseで24.7対深さ4の20.9 tok/s）。token idは温度0でも1.0でも、どの深さでもserialの返事でも同じでした。autoが勝つ理由：各roundはdraftを1回のforwardでまとめて検証し、最初に外れたところまでを確定します。検証する行はどれも時間がかかります。autoはdraftを最大3つにし、温度0ではMTPのheadの次のdraftの確率が0.35を下回ったところで鎖を止め、標本化では直近の受理率に応じて深さを1〜3で動かします。固定の深さは毎roundN個をdraftするので、外れやすいproseでは捨てる行の検証に時間を払い、3つがほぼ必ず当たるcountingでは深いほど得をします（エンジンが起動時に測るコストはMTPとDFlash2の選択に使い、この深さには使いません） | ほぼ全部が当たる文のために、autoの上限3を上げられるようになったとき |

## fabric

| 決定 | 日付 | 測った効果 | 開き直す条件 |
|---|---|---|---|
| リンクごとに2本のrail | 2026-10-02（TP=2）、2026-10-03（TP=3） | TP=2のprefillは同じ版で+4%（2本のrailの値が[検証](validation.ja.md#prefillとdecodeの速さ)のTP=2の基準）、TP=3 1,225.1 → 1,384.7 tok/s（+13%）。decodeは変わらず、decode検査のhashはどちらも同じ | — |
| TP=3：NCCLのchannel 4本、NCCL自身のIBの経路（`NCCL_NET_PLUGIN=none`）、subnet-aware routing | 2026-10-03 | 2本目のrailで8 MiBの片が1,530から約900 µsになった（channelが2・4・8・64本のどれでも同じ）。4本のchannelは32 MiBの塊を縮めた（1 railで9,236 → 5,072 µs、2 railで3,622 → 3,346）。decodeの大きさの交換（23〜51 µs）は誤差の範囲で動いた。`NCCL_CROSS_NIC` とimageの既定のnetwork pluginは何も変えなかった | — |
| TP=2：NCCLのchannelを4本にし、rankのファイルにTP=3と同じくIBのtransportを書く | 2026-10-05 | NCCLが自分で開く64本と比べ、decodeは+0.8〜1.0%、起動時の見積もりの余地は約1.5 GiB増、空きメモリの最低は1〜2 GiB上、prefillは0.4%以内でした（8本も同様）。`NCCL_NET=IB` などを書いても測った値は変わりません。もともと全接続がNET/IBでした | — |

## prefill

| 決定 | 日付 | 測った効果 | 開き直す条件 |
|---|---|---|---|
| NVFP4のrouted expertのprompt用kernel（`b0fa0a5`） | 2026-10-02 | promptあたりのexpertの時間18.55 → 9.2秒、prefill 769.3 → 913.7 tok/s（+19%）。promptのビットはdecodeのkernelと違う（pairのビットは行とexpertだけで決まるので、chunkの切り方では変わらない）ため、decode検査のhashはここで一度変わった。基準のhashはこの後のもの。Kの全体をtensor coreの中で一つの和にする速い形（2.5〜2.6倍に対し2.64倍）は、down projectionの誤差が5倍で不採用 | — |
| promptのBF16のmatmulはKの片をregisterの中で足す（#333）。DSAのpromptのkernelを多くのprogramへ | 2026-10-02 | 943.7 → 1,068.2 tok/s、同じビット | — |
| prompt chunkの交換を4つの行の片に分け、2本目のstreamで重ねる | 2026-10-02 | 1,068.2 → 1,150.7 tok/s。片が2と8では1,119.6と1,116.6 | — |
| KDAのpromptのstep kernelをblockあたり8 warpに | 2026-10-02 | 1,150.7 → 1,169.9 tok/s、同じビット | — |
| BF16のsplit-Kの部分和は短い窓のためだけに確保する | 2026-10-02 | `--context 0` の窓が約490Kから567,255 tokenに増えた。prefillは変わらない | — |
| prefillの交換の既定を `split` に（`TF_GLM_PREFILL_REDUCE`） | 2026-10-03 | TP=3、一続きの起動の中で：それまでの `gather`（1,394〜1,398 tok/s）に対し `scatter` +6.8%、`split` +19.6%。decode検査のhashもNLL採点セットも変わらない。rankどうしが送り合えるところで採り、それ以外は `gather`。TP=2ではリリースで初めて走り、hashは変わらなかった。TP=2の伸びのうちの寄与は単独では測っていない | — |
| indexerのpromptの仕事：programあたり16行、選択が読むpoolの列だけを採点、長い行の読みを5回から3回に | 2026-10-03 | 実のDSAの層で1 GPU、1M tokenでのchunkのtokenの選択が209.5 → 165.5 ms（−21%）、同じビット。上の交換の仕事と合わせ、200Kと500Kの実測に当てた1Mのprefillの見積もりは短くなった（[長い入力](validation.ja.md#長い入力)）。試して遅かったもの：histogramを採点に融合、11 bitで3 pass、persistent grid、2,048のblock | — |
| ビットが変わるprefillの案 | 2026-10-02と03に不採用 | 行のblockの32頭を一つのGEMMで採点し頭の和を後に回す（採点が2倍速くなれば1Mのprefillで約240秒の短縮と見積もり）、FP8のtensor coreでの採点、chunked KDA（その漸化式は38,960 tokenのpromptで2.06秒で、得は多くて数%）、MiaAI-Labの1 passのsparse attention。どれも基準のhashとNLLの元のビットを変える、または変え得る | — |

## 熱

| 決定 | 日付 | 測った効果 | 開き直す条件 |
|---|---|---|---|
| prefillはchunkの合間に92 °Cで待ち、88 °Cまで、全rankそろって | 2026-10-04 | 待ちが無いと、TP=3の1M tokenのpromptは6分半で熱の見張りの94 °Cに達した。待ちがあるとpromptは最後まで走った（[熱](../README.ja.md#リリースでの測定値)）。chunkごとに最高温度を交換する費用は38,960 tokenのprefillの約0.2%。92 °Cは停止の2 °C下（頂上付近の上がり方は1分に0.5〜1 °C、chunkは数秒）。88 °Cはprefillが速くなる前の1Mのprefillが保った88.8〜89.6 °Cの下で、`serve.sh` は仮置きとしている | 上流がissue #339に答える。帯はrankのファイルで変えられる |
| 待ちの作り | 2026-10-04 | 各chunkの前に1語を単独でgatherする（既存の交換には相乗りしない。その結果はhostが読まない）。熱の見張りと冷却gateと同じくACPIのzoneだけを読む（どの記録でもGPUは約9 °C低い）。待ちに上限を置かない（熱い部屋は要求を止め、熱の見張りが最後の守りのまま）。両方の帯を設定しない限り切れている（上流の既定は変わらない） | — |

## 他で名前を挙げていないエンジンのcommit

リリースのbranchは、上流v0.6.5に[変更履歴](../CHANGELOG.ja.md)がまとめて挙げるcommitを足したものです。次は、試験とrecipeの文面を除き、そこで名前を挙げていないものです：

- `0c9e8da`：GLMの `/v1/completions` がtoken idのpromptを受け、vLLMの形の `prompt_logprobs` を返す。NLLの検査（`score-nll`）はこれを使う。指定の無い要求は変わらず、指定のある要求は保持promptから再開しない。
- `68a7e6a`：NVFP4のrouted expertのprompt用kernel（上）。
- `e190c7b`、`9c51f2f`：KDAのconvの係数をfp32で（上）。
- `aac7927`：DSAのpromptのabsorbとexpandを行のblockごとに、indexerのpoolの採点をprogramあたり4行に（MiaAI-Labのpatch 0009に倣う）。
- `2caf43c`：8 warpのKDAのpromptのstep kernel（上）。
- `bee087d`：BF16のsplit-Kの部分和は短い窓だけ（上）。
- `c35cfd9`：起動時の見積もりがdraft headの行を詰めた数で数え、3 rankのどれもちょうど見積もりどおりを読み込む。
- `c3ec51d`：上流の通信のinterfaceに任意の機能として `send_recv` を足す。`split` がこれを使う。
- `d5e65e2`：rankが選んだ層だけを読み込める。実のcheckpointでの試験のため。
- `9c78e43`・`aba0f21`・`4a41c21`・`d21c834`：2.1.0が上流のpull request #194（その7本、`4fcfb10` から `f9ee1d9`）に足したもの。1枚の画像をcheckpointの上限8,000の視覚tokenまで、rank 0の画像の作業域をtowerの実測から、3 rankの全rankへの画像の特徴量、hostとGPUがメモリを共有するGPUでの `--vision-offload` の拒否。

## 1.x系の施策で2.x系では未評価のもの

未決の項目です。1.x系は測りましたが、2.x系にはどちらの結果もありません。

- **MTU。** 1.x系は9000と1500を比べて1500のままにしました（[チャネル数](../../docs/nccl-validation.ja.md#チャネル数)）。2.x系では変えていません。
- **LPA。** 1.x系の後段Prefill近似は実験機能で、1.x系でもバッチ用のopt-inです（[LPA](../../v1/docs/lpa.ja.md)）。長いprefillの結果を設計上変えます。2.x系には対応するものが無く、基準のhashとNLLは厳密なprefillのものです。
