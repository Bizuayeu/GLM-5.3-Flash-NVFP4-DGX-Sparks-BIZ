# GLM-5.3-Flash-NVFP4-DGX-Sparks-BIZ

[日本語](README.ja.md)

**NVFP4 BIZ** serves NVIDIA's pinned GLM-5.3-Flash NVFP4 checkpoint as distributed, on DGX Spark or compatible GB10 systems. This repository carries one directory per serving line:

| Line | Engine | Directory | Changelog |
|---|---|---|---|
| 1.x | vLLM | [v1/](v1/README.md) | [v1/CHANGELOG.md](v1/CHANGELOG.md) |

Each line has its own README, setup runbook, version and changelog; a release tag `v1.*` publishes the 1.x changelog section. Run a line's commands from its directory. `state/` and `records/` are untracked and stay at the checkout root.

Licensing: [LICENSE](LICENSE) (Apache-2.0), [NOTICE](NOTICE) and [third-party notices](THIRD_PARTY_NOTICES.md). Contributions: [CONTRIBUTING.md](CONTRIBUTING.md).
