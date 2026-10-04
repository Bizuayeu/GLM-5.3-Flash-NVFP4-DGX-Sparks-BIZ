# ホストのツール

[English](README.md) · [2.x README](../README.ja.md) · [セットアップ手順](../SETUP.ja.md)

持続負荷でGB10の電源が落ちることへの、ホスト側のツールです。GPUクロックの上限、常時記録、長い要求の合間に呼ぶ冷却gate、エンジンを止める熱の見張りからなります。どれもエンジンの一部ではなくホストの設定で、コンテナの外のホストで動きます。上限と閾値は参照機（MSI EdgeXpert GB10）で決めました。上限の根拠と測った代償は[GPUクロックの上限](../../v1/docs/operations.ja.md#gpuクロックの上限)にあります。他の機は自分の記録で確かめてください。

## ファイル

| ファイル | 役割 |
|---|---|
| `gb10-clock-cap.service` | systemdのoneshot。起動のたびに `nvidia-smi -lgc` でGPUクロックの範囲を固定し、止めるときに `-rgc` で外す |
| `gb10-telemetry` | Pythonの記録係。2秒ごとに1行のJSONを `/var/log/gb10-telemetry/<UTCの日付>.jsonl` に書き、電源断でも直前の標本が残るよう1行ずつfsyncする。14日分を残す |
| `gb10-telemetry.service` | 記録係をサービスのユーザーで常駐させる（`Restart=always`） |
| `install.sh` | 2つのunitを据え付けて有効にし、状態、固定したクロック、記録の最後の1行を表示する |
| `cool-gate` | 記録を読み、ホストが冷えるまで待つ |
| `thermal-watch` | 記録を読み、ホストが熱いままならエンジンを止める |

Pythonのツールは標準ライブラリだけを使います。`cool-gate` と `thermal-watch` は `/var/log/gb10-telemetry`、または `GB10_TELEMETRY_DIR` のディレクトリを読みます。記録係もそこへ書きます。

## 記録の項目

| 項目 | 意味 |
|---|---|
| `epoch` | 標本のUnix時刻（秒） |
| `acpi_c` | ACPIの全thermal zoneをzone順に（°C）。読めなかったzoneは `null` |
| `gpu_c` | GPUの温度（°C） |
| `power_w` | GPUの消費電力（W） |
| `clock_mhz` | グラフィックスクロック（MHz） |
| `util_pct` | GPUの使用率（%） |
| `event_reasons` | `nvidia-smi` が表示する `clocks_event_reasons.active` |
| `load1` | 1分のload average |
| `mem_available_gib` | `MemAvailable`（GiB） |

下の2つのツールは、`acpi_c` のうち `null` でない最高値で熱を判断します。参照機の `nvidia-persistenced` は `--no-persistence-mode` で動くので、記録係が走らせ続ける `nvidia-smi` がGPUのクライアントとしても張り付きます。上限が効いているかは、負荷時の `clock_mhz` に表れます。

## 据え付け

各ホストで、このディレクトリから：

```bash
sudo sh install.sh          # 記録係はsudoを呼んだユーザーで動く
sudo sh install.sh <user>   # または既存の別のユーザーで
```

rootでなければ実行を断ります。記録係のunitにユーザーを書き込み、そのユーザーが所有する `/var/log/gb10-telemetry` を作り、最後に `installed for <user>` を表示します。

外すとき：`sudo systemctl disable --now gb10-clock-cap.service gb10-telemetry.service`（上限のunitを止めると上限が外れます）、`/etc/systemd/system/` の2つのunitと `/usr/local/sbin/gb10-telemetry` を消し、`sudo systemctl daemon-reload`。

## 長い運転の間

エンジン自身のprefillの熱の待ち（`TF_GLM_HEAT_HIGH`・`TF_GLM_HEAT_LOW`、[2.x README](../README.ja.md)）は要求の中で働きます。この2つのツールは要求の外で働きます。

**冷却gate。** 長い要求の前ごとに、各ホストでcheckoutのルートから：

```bash
python3 v2/host/cool-gate --label <text>
```

ACPIの最高温度が `--band`（既定60 °C）以下になるか、`--cap` 秒（既定600）たつと戻り、1行のJSONを表示します。戻った理由（`cool` か `cap`）、待った秒数、始めと終わりの温度です。終了コード0なら続けます。2は記録が無いか30秒より古いことを示し、記録の無いまま運転を続けるべきではありません。既定値は参照機の記録から来ています。60 °Cはそこで測ったアイドルの帯のすぐ上で、600秒はそこで測ったその帯への戻りの最も遅いものより長い時間です。

**熱の見張り。** エンジンが配信している間、各ホストで：

```bash
python3 v2/host/thermal-watch ~/glm53-tf/logs/therm-<label>.log &
```

2秒ごとに、時刻、記録の行のepoch、ACPIの最高温度、GPUの温度・電力・クロックをlogに足します。94.0 °C以上が2回続くと、コンテナの中の `pkill -f` でエンジンを止めます。この規則は参照機の記録から来ており、電源断なしに終わった最高の値は93.7 °Cでした。`--threshold` と `--readings` で変えられます。エンジンはコンテナの中でrootとして動くので、見張りは `docker exec` を通して探し、止めます。`therm-<label>.stop`（logの名前の末尾を `.stop` にしたもの）ができるか、エンジンがいなくなると終わります。

見張りはこの系のエンジン、つまり既定値のコンテナ `glm53-tf` とプロセス `tensorfold serve` で確かめました。`--container` で別のコンテナを指定できます。たとえば別の `CONTAINER` で作ったコンテナです。
