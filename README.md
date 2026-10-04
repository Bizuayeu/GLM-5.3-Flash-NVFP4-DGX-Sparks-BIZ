# GLM-5.3-Flash-NVFP4-DGX-Sparks-BIZ

[日本語](README.ja.md)

**NVFP4 BIZ** serves NVIDIA's pinned GLM-5.3-Flash NVFP4 checkpoint as distributed, on DGX Spark or compatible GB10 systems. This repository carries one directory per serving line:

| Line | Engine | Directory | Changelog |
|---|---|---|---|
| 1.x | vLLM | [v1/](v1/README.md) | [v1/CHANGELOG.md](v1/CHANGELOG.md) |
| 2.x | TensorFold | [v2/](v2/README.md): TP=2 and TP=3, FP8 KV, text and tool calls ([setup](v2/SETUP.md)) | [v2/CHANGELOG.md](v2/CHANGELOG.md) |

Each line has its own README, version and changelog; a release tag `v1.*` or `v2.*` publishes the section of that line's changelog. Run 1.x's commands from `v1/`; 2.x builds its image and runs its scripts from the checkout root ([setup](v2/SETUP.md)). `state/` and `records/` are untracked and stay at the checkout root.

Licensing: [LICENSE](LICENSE) (Apache-2.0), [NOTICE](NOTICE) and [third-party notices](THIRD_PARTY_NOTICES.md). Contributions: [CONTRIBUTING.md](CONTRIBUTING.md).
