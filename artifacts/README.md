# Artifacts

Gitignored working directory for things that are large or generated:

- MLX checkpoints (`*.safetensors`)
- Optimizer state and training logs
- Per-run JSON metrics and DRC reports
- Rendered boards, plots, and videos

## Naming

```
artifacts/<experiment>/<run-id>/
  config.yaml
  metrics.json
  drc.json
  routed.kicad_pcb
  model.safetensors
  log.txt
```

`run-id` includes the UTC timestamp and a short seed, e.g. `20261117T1542Z-s42`.

## Publishing

Do not commit checkpoints. When a result is ready:

- model weights → Hugging Face Hub or a GitHub Release
- datasets → Hugging Face dataset with a data card
- metrics/plots → commit the small JSON/CSV/PNG evidence, not the checkpoint

A run is only citable if its `run.json` contains the git commit, config, seed, and the exact
command that produced it.
