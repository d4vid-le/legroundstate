# Configs

Versioned YAML experiment configs. Keep secrets out; use `.env` (gitignored) for tokens.

Planned configs:

- `l0_tiny.yaml` — 4–8 nets, 2 layers, smoke test
- `l0_base.yaml` — 16 nets, 4 layers, main L0 run
- `l1_base.yaml` — per-net corridor refinement
- `eval_qtpy_signal.yaml` — Gate G4 benchmark
- `eval_pcbworld_subset.yaml` — external benchmark

A config must record: grid resolution, model sizes, loss weights, batch size, LR schedule,
seed, dataset manifest hash, and the exact evaluation set. See `docs/SPEC.md` §10.
