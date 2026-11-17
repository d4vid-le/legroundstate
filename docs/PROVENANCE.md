# Provenance and clean-room policy

**Purpose:** Record exactly what we take from the Enso/Kona research, what we do not, and how
we keep the implementation independent. This matters because the upstream Enso repository has
**no license**.

---

## 1. The license situation

| Item | Finding |
|---|---|
| Upstream | https://github.com/MVPandey/Enso |
| Pinned commit | `8013c8f95e9e4402faaa91c99835c4ccedc54ef9` |
| LICENSE file | **None** |
| GitHub license metadata | `null` |
| `pyproject.toml` license field | None |
| Implication | Default copyright. We do not have permission to copy or redistribute the source. |
| Local copy | `third_party/enso/`, gitignored, fetched by `scripts/fetch_enso.sh` |
| Project name | We do **not** use “Enso” as our project name. |

## 2. What we may use

Ideas, methods, algorithms, facts, and experimental results are not copyrightable. We may:

- Read the public README, training log, and architecture description.
- Use the *concept* of a JEPA-style latent EBM with a context encoder, target encoder,
  predictor, decoder, energy, and Langevin inference.
- Use published hyperparameters and training lessons as **facts** (with citation).
- Cite the reported results (e.g., 96.6% puzzle accuracy, +1.0% from Langevin).
- Reimplement the method independently in MLX.
- Compare against the reported numbers in a related-work section.

## 3. What we must not do

- Copy source code, comments, docstrings, identifiers, or tests from Enso.
- Copy prose, figures, or tables from the README/training log into our docs.
- Redistribute the Enso archive or source in this repository.
- Use Enso model weights (none are needed; none are released here).
- Imply endorsement, affiliation, or that our model is “Enso”.
- Name the project, package, CLI, or artifacts after Enso.

## 4. Clean-room process

1. **Primary sources:** implement from public method descriptions and papers — I-JEPA,
   IRED, JEPA-Reasoner, the Kona blog, and the Enso README's high-level description.
2. **No copy/paste:** write the MLX modules from the design in `docs/SPEC.md`, not by
   translating Enso's PyTorch files line by line.
3. **Review:** before public release, diff our code against Enso for verbatim strings,
   comments, and identifiers; record the result.
4. **Local reference only:** `third_party/enso/` stays gitignored; `scripts/fetch_enso.sh`
   fetches it for study, not for redistribution.
5. **Permission:** if we later want to reuse a specific code fragment, open an issue with the
   upstream author and get written permission; then add the appropriate license/notice.

## 5. Attribution

Use this wording in the README, paper, or blog:

> This project is independent research. It is inspired by the Enso replication of
> Logical Intelligence's Kona 1.0 Sudoku EBM, and by the JEPA line of work (I-JEPA, IRED,
> JEPA-Reasoner). It does not include or redistribute Enso source code, and it is not
> affiliated with or endorsed by the Enso authors or Logical Intelligence.

References:

- Enso: https://github.com/MVPandey/Enso (commit `8013c8f`)
- Kona 1.0: https://logicalintelligence.com/blog/energy-based-model-sudoku-demo
- I-JEPA: https://arxiv.org/abs/2301.08243
- IRED: https://arxiv.org/abs/2406.11179
- JEPA-Reasoner: https://arxiv.org/abs/2512.19171

## 6. Our code and data

- Our code: Apache-2.0 (proposed; see ADR-0008).
- Our docs: CC BY 4.0 (proposed).
- Human labels: owned by the project; published only with the reviewer's consent and without
  personal information.
- Third-party boards: per-board licenses; see `docs/RESEARCH.md` §6 and `data/README.md`.
- QT Py reference: CC BY-SA 3.0 (Adafruit); attribution retained; source files not committed.

## 7. Release gate

Before any public release:

- [ ] No Enso code/prose/figure copied.
- [ ] No “Enso” in the project/package/CLI names.
- [ ] Attribution text present.
- [ ] License files added for our code/docs.
- [ ] Data manifest with per-source licenses.
- [ ] Human-label consent recorded.
- [ ] A short provenance note in the release.
