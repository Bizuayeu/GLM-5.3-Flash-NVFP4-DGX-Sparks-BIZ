# Repository instructions

The repository holds two serving lines: 1.x (vLLM) in v1/ and 2.x (TensorFold) in v2/. Each line holds everything that runs it, and the checkout root holds only what no recipe needs to run (release and publication tooling, licenses, CI). Paths below without a prefix are inside the line's directory. Read its README.md before changing that deployment; v1/docs/README.md lists every 1.x document's role and which file owns each fact. Keep pinned model revisions and runtime settings explicit. Put CPU contract tests in tests/ and reproducible validation summaries in docs/.

For deployment, read SETUP.md and its linked operations/validation documents first. Acceptance for routine use is a record, not a command: the line's SETUP.md states what its serving profile is accepted for (1.x step 6, 2.x §8) and where each item's evidence is, and nothing outside that declared scope is qualified. Do not record a PASS without evidence, extend the acceptance to another scope by inference, or bypass 1.x's `server preflight`. Respect explicitly paused downloads and preserve other workloads. Record each action and its evidence privately under records/ at the checkout root.

Use `python -m glm53_setup` from v1/ of the checkout; state/ and records/ stay at the checkout root. After relevant changes run, in each line's directory and at the checkout root, `python -m unittest discover -s tests -t . -v` and the Ruff checks that .github/workflows/ci.yml runs, and `python tools/check_publication.py` from the checkout root. Keep every English/Japanese document pair consistent; v1/docs/README.md lists the pairs of the whole repository (the root's and 2.x's included) and the pages that are English-only by design. Original code uses Apache-2.0; preserve all adapted-code notices.

Releases follow tags, per line: bump the line's version, add its CHANGELOG section in both languages, then push the `vX.Y.Z` annotated tag. `.github/workflows/release.yml` (at the checkout root) reads `v1/` for a `v1.*` tag and `v2/` for a `v2.*` tag and publishes that section as the GitHub Release; do not create or edit the Release by hand.

Credentials (.env), generated state, local records, upstream checkouts and model weights are not tracked. Do not print keys or include raw private logs in commits. Keep hardware checks distinct from real-model inference results.

Implementation plans live in docs/plans/ at the checkout root, untracked and excluded from publication; docs/plans/README.md indexes them and each plan's own leading status line owns its state. Add a line to that index when creating a plan, and update the status line rather than the body when closing one.

This repository can be used independently. Resolve source/data paths relative to this repository or an explicit argument; do not depend on a parent workspace. Changes must preserve existing generation settings unless the task asks to change them.
