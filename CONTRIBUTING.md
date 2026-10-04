# Contributing

[日本語](CONTRIBUTING.ja.md)

This is an engineering project with a measured scope. Keep claims limited to the exact hardware, image, weights, precision and workload tested.

Use Python 3.11 or newer. The 1.x line (vLLM) lives in `v1/` and the 2.x line (TensorFold) in `v2/`; run the 1.x checks from `v1/`:

```sh
python -m unittest discover -s tests -t . -v
ruff check glm53_setup tests tools
ruff format --check glm53_setup tests tools
python tools/check_publication.py
```

GPU checks are separate from CPU tests. Use the pinned image and record effective arguments, output completeness, numerical differences and failures. The validation procedures are each line's: [1.x](v1/docs/validation.md) and [2.x](v2/docs/validation.md).

- Do not commit credentials, local site configuration, model weights, raw logs or private experiment records.
- Keep model/cache artifacts read-only during inference and preserve failed runs.
- Do not relax a runtime guard or a numerical criterion just to obtain a passing result.
- Keep original notices for copied/adapted code. New project contributions are submitted under Apache-2.0; third-party portions keep their applicable notices.
- Mark modified upstream files prominently and review the [licensing guide](v1/docs/licensing.md) for the actual distribution scope.
- Keep ZCode and Claude Code results separate in the [harness acceptance matrix](v1/docs/harnesses.md); never mark unexecuted cases passed.
- Update the English and Japanese versions of every paired document together when user-visible content changes; the [document map](v1/docs/README.md) lists the pairs.
