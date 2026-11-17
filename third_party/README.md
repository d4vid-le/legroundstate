# Third-party references

## Enso (Sudoku EBM)

- **Upstream:** https://github.com/MVPandey/Enso
- **Pinned commit:** `8013c8f95e9e4402faaa91c99835c4ccedc54ef9` (HEAD of `main` at the time of download)
- **Archive SHA-256:** `0781c0f4c9125161a6232c2155572a196baa1030bc1686681d96992bd519cb35`
- **Local path:** `third_party/enso/` (gitignored)
- **Fetch:** `scripts/fetch_enso.sh`

### License status

The upstream repository has **no LICENSE file**, and GitHub reports no license. Under default
copyright, we do not have permission to copy or redistribute the source. "Open-source
replication" in the README is a description, not a license grant.

**Rules for this project:**

1. Do not commit `third_party/enso/` or the archive.
2. Do not copy Enso source into `src/` or any committed file.
3. Use it only as a local reference for architecture, hyperparameters, and training lessons.
4. Implement PCB-Enso independently in MLX and cite Enso/Kona.
5. If we want to reuse code, ask the upstream author for explicit permission first.

### Why keep it at all?

The training log contains hard-won lessons (VICReg placement, latent normalization,
train/inference energy alignment, constraint loss) that are valuable even though the code
cannot be redistributed. We summarize those lessons in `docs/RESEARCH.md`; the source stays
local.

## QT Py ESP32-S2 reconstruction

See `boards/README.md`. It is vendored as a snapshot, not a submodule, because it is a
fixture for this project and the copy here was already fully pushed to its own remote.
