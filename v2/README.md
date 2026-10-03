# NVFP4 BIZ 2.x (TensorFold)

[日本語](README.ja.md) · [Repository index](../README.md) · [Changelog](CHANGELOG.md)

The 2.x line serves the same pinned NVIDIA GLM-5.3-Flash NVFP4 checkpoint as 1.x, with TensorFold in place of vLLM. It is being prepared for 2.0.0 and has no release yet; until then the [1.x line](../v1/README.md) is the released one.

## Contents (filled in for 2.0.0)

- Setup: the engine pin, the container image and the launch scripts for two hosts at TP=2 and three hosts at TP=3
- Serving profiles: FP8 latent KV, two NCCL rails, the context window
- Validation: the decode check, the NLL scoring set and the acceptance table, item for item as in 1.x
- Licensing: [LICENSE](../LICENSE), [NOTICE](../NOTICE) and [third-party notices](../THIRD_PARTY_NOTICES.md) at the repository root
