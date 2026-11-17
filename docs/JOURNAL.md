# Journal

Newest entries at the bottom. Each entry: goal, what happened, evidence, lesson, next.

---

## 2026-11-17 — Workspace audit and v0.2 plan

**Goal:** Understand the assets, check the Enso license, verify the training stack, and turn the first-draft spec into an executable plan.

**Did:**

- Audited the workspace and the QT Py reconstruction.
- Extracted and inspected Enso (`third_party/enso/`), confirmed the archive matches upstream commit `8013c8f95e9e4402faaa91c99835c4ccedc54ef9`.
- Checked the Enso license: **none**. No `LICENSE` file; GitHub API `license: null`; `pyproject.toml` has no license field. Default copyright applies. We will not redistribute the code.
- Inventoried the QT Py board:
  - 4 layers, 17.78 × 20.701 mm, 1.6 mm.
  - 34 nets, 159 pads.
  - 425 track segments, 43 vias, 344.1 mm total copper.
  - Min track/space 0.1524 mm (6 mil).
- Read the prior routing reports. The final "0 unconnected / 0 DRC" board is a **verified reconstruction** using Adafruit's signal routing; the independent route peaked at **9 unconnected (2-layer)** and **8 (4-layer targeted)**.
- Checked the toolchain:
  - KiCad 10.0.7 at `/Applications/KiCad/KiCad.app`; `kicad-cli` exists but is not on `PATH`.
  - `uv` 0.12.19; Python 3.13.15 available via uv.
  - Apple M5 Pro Mac mini, 18-core CPU, 64 GB unified memory, 424 GB free.
- Installed MLX 0.32.4 and benchmarked it on this machine.
- Wrote the v0.2 plan, spec, research notes, and ADRs.

**Evidence:**

```
Enso zip SHA-256: 0781c0f4c9125161a6232c2155572a196baa1030bc1686681d96992bd519cb35
Enso upstream HEAD: 8013c8f95e9e4402faaa91c99835c4ccedc54ef9
QT Py board commit: 73ff5db45dbd12750827df8c329c6ddfcb41cfe0
KiCad: 10.0.7
MLX: 0.32.4
```

MLX benchmark highlights (synthetic, forward+backward, compiled):

| Config | Params | Time/step | Throughput | Peak |
|---|---:|---:|---:|---:|
| B=64, T=81, d=384, 6L | 10.8M | 21.4 ms | ~2,995 boards/s | 5.8 GB |
| B=64, T=121, d=512, 8L | 25.5M | 56.1 ms | ~1,141 boards/s | 15.5 GB |
| 4096³ matmul, bf16 | — | 4.94 ms | 27.8 TFLOPS | — |

Full details: `docs/notes/mlx-benchmark.md`.

**Learned / surprised by:**

- **No license on Enso.** "Open-source replication" in the README does not make it legally open source. Clean-room implementation is the right call.
- **The coarse grid maps beautifully to Enso's scale.** At 0.5 mm, the QT Py is 36×42; with 6×6 patches it is 42 tokens. That is Enso's 9×9 neighborhood. The EBM belongs at the coarse level, not on the 254k-cell fine grid.
- **MLX is fast enough.** A 10M model at 81 tokens trains at ~2,900 boards/s on synthetic tensors. The bottleneck will be label generation and DRC, not the neural step.
- **The previous failure was global, not local.** The GND pours fragmented because signal routing took the corridors; fixing it required rerouting signals. This is exactly the kind of coupled constraint an EBM should reason about — or fail to, which is the experiment.
- **The board in this folder is the ESP32-S2, not the S3.** The brief mentions an S3; the copy here is the S2. Need to confirm the G4 target.

**Revision (same day):** The user confirmed the training target is this Mac mini (M5 Pro, 64 GB) with **MLX**, not cloud/PyTorch. The plan was revised to v0.2:

- MLX-first implementation; PyTorch is not a dependency.
- Model sized for local throughput (5–15M params, 0.5 mm coarse grid, 42–121 tokens).
- Three-level hierarchy added so the fine 0.0762 mm grid is convolutional/classical, not attention.
- Compute section is now local-only, $0; the measured MLX benchmark replaced the H200 assumptions.
- Enso license confirmed absent; clean-room reimplementation is an explicit ADR.

**Next:**

1. Confirm repo visibility/license and the G4 board (S2 vs. S3).
2. Build the KiCad reader → canonical board model → tensorizer.
3. Build the DRC runner and round-trip test (Gate G0).
4. Build the Freerouting and A* baselines.
5. Only then start the synthetic data engine.

**Blockers / open questions:**

- The `/Volumes/dblab/Development/projects/kicad` path does not exist on this machine. We are using the copy at `boards/qt-py-esp32-s2/`.
- Enso upstream has no license; if we want to reuse any code, ask the author first.
- Need a decision on whether PCBench/PCBWorld boards are acceptable for training or only evaluation.

---

## 2026-11-17 — Session 2: own EBM, human labels, rename

**Goal:** Resolve the Enso dependency, decide whether to build our own model, plan human labeling, and account for the second Mac.

**Decisions (user):**

- **No license → build our own.** Use the research/ideas, not the code. Clean-room MLX implementation.
- **Rename the project.** “Enso” is out. Working title: **Groundstate** (recommended); alternatives: Etch, Innerlayer, Weft. Final name pending.
- **Human labels are a first-class data source.** David will review, label, and sort boards for quality. The pipeline must make this fast and consistent.
- **Second Mac available.** M4 Pro mini, 64 GB, connected via Thunderbolt 5. Use it if needed.
- **Start in a few days.** Today is planning only.

**What changed in the docs:**

- `docs/NAMING.md` — candidates, recommendation, rename checklist.
- `docs/PROVENANCE.md` — Enso license findings, clean-room rules, release gate.
- `docs/LABELING.md` — review schema, UI, QC, active learning, preference loss.
- `docs/notes/two-mac.md` — TB5, MLX ring, task-parallel vs. data-parallel.
- `docs/PLAN.md` v0.3 — own EBM, human labels, two-Mac compute, updated gates.
- `docs/SPEC.md` v0.3 — quality head + preference-ranking energy.
- `docs/DECISIONS.md` — ADR-0010…0014.

**Key technical conclusions:**

1. **Task parallelism beats distributed training for this workload.** The M4 Pro should generate boards and run DRC while the M5 Pro trains. MLX data-parallel over TB5 is an optional 1.5–1.8× stretch.
2. **Human labels are not bulk labels.** 300–500 gold boards + 200–500 preference pairs is a realistic target; 10k human labels is not.
3. **Preference learning is the most interesting EBM lever.** Pairwise “A is better than B” labels directly shape the energy landscape, which is what an EBM is for. It also gives an energy-specific evaluation metric.
4. **The project name should not carry Enso.** Using “Groundstate” as a working title avoids implying affiliation while we finalize.

**Next:**

1. Choose the project name (human decision).
2. Confirm the G4 board (S2 copy vs. S3) and repo visibility/license.
3. Build the KiCad reader + DRC harness → G0.
4. Toy 16×16 EBM spike → G0.5.
5. Labeling app + 50-board calibration → G1.
