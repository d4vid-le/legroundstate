# Decisions (ADR log)

Format: **Status — Context — Decision — Consequences.** Append-only; supersede with a new ADR rather than rewriting history.

---

## ADR-0001 — MLX-first, local M5 Pro training

**Status:** Accepted (2026-11-17)

**Context:** The machine is an Apple M5 Pro Mac mini with 64 GB unified memory. The user wants to train locally with MLX. Enso is PyTorch/CUDA-oriented; cloud GPUs are not in the base plan.

**Decision:** Implement Groundstate in MLX 0.32.4 + Python 3.13. Use PyTorch only as an optional reference for parity checks, never as the training path. Design model sizes and grid resolutions around the measured local throughput.

**Consequences:**

- No CUDA kernels or flash-attention; use MLX ops and `mx.compile`.
- Prefer CNNs/local attention over very long flat transformers.
- Experiments are sized for hours, not days.
- MLX ecosystem gaps are a real risk; keep the model architecture conservative.
- Cloud is an optional escape hatch, not a dependency.

**Evidence:** Synthetic MLX benchmark, 2026-11-17: 10.8M transformer, 81 tokens, batch 64 → 21 ms/step (~3,000 boards/s), 5.8 GB peak. 25.5M, 121 tokens → 56 ms/step (~1,140 boards/s), 15.5 GB. bf16 matmul ~28 TFLOPS. See `docs/notes/mlx-benchmark.md`.

---

## ADR-0002 — Adapt the Enso recipe, not its weights; clean-room implementation

**Status:** Accepted (2026-11-17)

**Context:** Enso is a Sudoku model (10-channel 9×9 input, digit output). Its repository has no LICENSE file; GitHub reports no license. Default copyright applies, so we cannot copy or redistribute its code. The user wants to explore the EBM idea, not clone a Sudoku solver.

**Decision:** Reimplement the JEPA/EBM **recipe** in MLX from our own understanding and the public README/paper concepts. Do not copy Enso source into this repository. Keep the upstream zip local and gitignored. Cite Enso and Kona. Do not use Enso weights (none are needed).

**Consequences:**

- Slower start than forking, but clean provenance.
- We may diverge from Enso's exact implementation; that is acceptable if documented.
- A license audit is required before public release.
- If we want to reuse specific code, ask the upstream author for permission first.

---

## ADR-0003 — Per-net edge flow, not per-cell net IDs

**Status:** Accepted (2026-11-17)

**Context:** The original brief proposed `(L,H,W,C)` with `C` holding a positive integer net ID per cell. Net IDs are arbitrary, and a cell label does not encode connectivity or edge-based DRC.

**Decision:** Represent routing as a 3D graph with per-net edge flow, flow conservation, and shared edge capacity. The model predicts per-net edge/via probabilities; paths are extracted from the flow.

**Consequences:**

- Output tensors are larger per net, but structurally meaningful.
- Conservation/capacity losses are differentiable and local.
- Path extraction is well-defined; blobs are eliminated.
- The model can reason about multiple nets without ordinal net-ID channels.

---

## ADR-0004 — Three-level coarse-to-fine hierarchy

**Status:** Accepted (2026-11-17)

**Context:** A DRC-exact grid for the QT Py is 234 × 272 × 4 ≈ 254k cells; a flat transformer over that is infeasible on the M5. A 0.25 mm grid cannot represent 6 mil (0.1524 mm) track/space rules.

**Decision:** Use three levels:

- **L0:** 0.5 mm, all nets, EBM global plan (42–99 patch tokens).
- **L1:** 0.25 mm, per-net corridor refinement (CNN/conditional EBM).
- **L2:** 0.0762 mm, classical A*/rip-up + legalizer + KiCad DRC.

**Consequences:**

- The learned model never claims DRC-exact geometry.
- The global EBM operates at an Enso-like token count.
- The detailed router must be strong; it is the legality guarantee.
- Mapping between levels must be lossless enough to preserve corridors; test this at G2.

---

## ADR-0005 — Hybrid propose → extract → verify → repair; KiCad DRC is the judge

**Status:** Accepted (2026-11-17)

**Context:** Soft DRC penalties cannot guarantee legality. The prior project's failures were geometric and global; a learned energy alone is not a manufacturability guarantee.

**Decision:** The model proposes corridors/flows. A deterministic extractor produces paths, a legalizer produces tracks/vias, and `kicad-cli pcb drc` is the ground truth. A repair loop rips up violating nets and re-routes them. No DRC waivers.

**Consequences:**

- The system is more complex than end-to-end generation, but far more trustworthy.
- The model's contribution can be measured separately from the router's.
- Failures are reported with exact violating items.
- Runtime includes DRC and repair, not just neural inference.

---

## ADR-0006 — Signal nets first; power/ground planes handled classically

**Status:** Accepted (2026-11-17)

**Context:** The QT Py failure was largely GND pour fragmentation and power geometry coupling. Routing GND/+3V3 as traces is the wrong abstraction; they want planes/zones and stitching.

**Decision:** The learned router handles signal nets. GND/+3V3/VBUS power distribution is handled by a separate zone/plane step and measured separately. Gate G4 is scoped to signal nets on a board with power planes already handled.

**Consequences:**

- The learned problem is smaller and better defined.
- The G4 comparison to the prior "0/0" must state the scope explicitly.
- Full-board routing (signals + planes + stitching) is a later phase.
- The model is not expected to learn copper pours.

---

## ADR-0007 — Board snapshot vendored; Enso is fetch-only

**Status:** Accepted (2026-11-17)

**Context:** The QT Py copy has its own git history and a public remote. Enso has no license. The workspace should be a self-contained monorepo without nested-repo confusion.

**Decision:** Vendor the QT Py snapshot under `boards/qt-py-esp32-s2/` with its nested `.git` preserved locally as `.git-disabled` and gitignored. Link the upstream repo and commit in `boards/README.md`. Do not vendor Enso; provide `scripts/fetch_enso.sh` pinned to commit `8013c8f`, and gitignore `third_party/enso/`.

**Consequences:**

- The top-level repo contains the board as regular files and keeps its history available locally.
- Enso can be fetched reproducibly without redistributing unlicensed code.
- The board's own `.gitignore` still excludes Adafruit's reference files.
- Repo size grows by the board's committed artifacts (~40 MB), acceptable.

---

## ADR-0008 — License proposal

**Status:** Proposed — pending human approval

**Context:** We will publish code, docs, data manifests, and possibly model weights. Enso is unlicensed; the QT Py reference is CC BY-SA 3.0; PCBench/PCBWorld boards have per-board licenses.

**Decision (proposal):**

- Our code: **Apache-2.0** (patent grant; friendly to research and commercial reuse).
- Our docs: **CC BY 4.0**.
- Our model weights (if released): **Apache-2.0**, subject to a data-provenance review.
- Enso: not redistributed; cited only.
- QT Py: attribution + share-alike notice; no Adafruit source files redistributed.
- PCBench/PCBWorld: per-board manifest; only permissive boards in any released dataset.

**Consequences:**

- A license audit is a release gate.
- If the user prefers MIT or a private repo, only this ADR changes.

---

## ADR-0009 — Primary benchmark and held-out protocol

**Status:** Accepted (2026-11-17)

**Context:** The QT Py is the only fully documented board we have. Training on it would invalidate the milestone. PCBWorld/PCBench provide external validity.

**Decision:**

- **G4 primary:** a from-scratch, unrouted QT Py ESP32-S2, signal nets, 0 unconnected / 0 error-level DRC. The QT Py is **never** used for training or hyperparameter selection before G4 is frozen.
- **G5 external:** 20–50 PCBench/PCBWorld boards, clean-pass rate vs. Freerouting/A*.
- **B0/B2 synthetic:** development and ablations.
- Report `@1` and `@5` where meaningful; always report the worse number too.

**Consequences:**

- No tuning on the final test.
- Synthetic-to-real generalization is measured, not assumed.
- The benchmark harness must be built before the model (G0/G1).

---

## ADR-0010 — Build our own EBM; Enso is research inspiration only

**Status:** Accepted (2026-11-17)

**Context:** Enso has no license, and the user wants to build our own model rather than fork it. The method (JEPA-style latent EBM with Langevin inference) is published; the code and prose are not licensed for reuse.

**Decision:** Implement a clean-room MLX model from public research (I-JEPA, IRED, JEPA-Reasoner, Kona/Enso descriptions). Do not copy Enso code, comments, prose, figures, or weights. Keep the upstream source local and gitignored. Do not use the Enso name for the project.

**Consequences:**

- More implementation work, but clean provenance.
- The architecture will diverge to fit spatial PCB data.
- A release gate checks for copied material; see `docs/PROVENANCE.md`.
- If we ever want to reuse specific code, ask the upstream author for written permission.

---

## ADR-0011 — Human-in-the-loop labels and preference learning

**Status:** Accepted (2026-11-17)

**Context:** DRC-clean is necessary but not sufficient. A route can pass DRC and still be poor engineering. The user is willing to review and label boards, and their judgment is the scarce, high-value signal.

**Decision:** Treat human labels as a first-class data source:

- Machine labels (classical routes + DRC) provide the bulk pretraining data.
- Human labels provide a gold set: accept/reject, quality, difficulty, issue tags, and blind A/B preferences.
- Train a quality head and a preference-ranking energy term.
- Use active learning to spend the reviewer's time on uncertain/disagreement cases.
- Label schema and tool: `docs/LABELING.md`.

**Consequences:**

- The data pipeline includes a review UI and label versioning.
- Human labels are small; they fine-tune/evaluate, not pretrain.
- The energy can be calibrated beyond DRC, which is the central research bet.
- Reviewer time becomes a tracked project resource.

---

## ADR-0012 — Two-Mac local cluster; task-parallel first

**Status:** Accepted (2026-11-17)

**Context:** An M4 Pro Mac mini with 64 GB is available over Thunderbolt 5. MLX supports distributed data parallelism over a TB ring, but the data pipeline is the bottleneck.

**Decision:**

1. **Default:** task-parallel. M4 Pro generates boards, runs classical routing/DRC, and hosts the labeling app; M5 Pro trains.
2. **Optional:** data-parallel training via `mlx.distributed_config --backend ring` + `mlx.launch`, if Phase 3 is compute-bound.
3. Single M5 Pro is sufficient for G0–G4. The M4 is an accelerator, not a requirement.

**Consequences:**

- No distributed-training complexity in the critical path.
- Shared storage or `rsync` is required for datasets and labels.
- Benchmark the M4 before assigning it training work.
- See `docs/notes/two-mac.md`.

---

## ADR-0013 — Working title Groundstate; rename pending

**Status:** Proposed (2026-11-17)

**Context:** The user wants a name other than Enso. The project currently lives in a folder and package named `pcb-enso`, which is a working title and implies a relationship we do not have.

**Decision:** Use **Groundstate** as the working title in docs. Keep the directory and package names until the user confirms. Perform the rename once, in a single commit, using the checklist in `docs/NAMING.md`.

**Consequences:**

- No half-renamed code.
- Docs say “Groundstate (working title)” and `pcb-enso` is marked as the legacy/working path.
- The final repo/package/CLI name is a human decision.

---

## ADR-0014 — Labels are append-only and versioned

**Status:** Accepted (2026-11-17)

**Context:** Human labels are expensive and subjective. Silent edits would make experiments irreproducible and hide reviewer drift.

**Decision:** Store labels in SQLite with an append-only `label_version`; corrections are new rows. Export immutable JSONL shards with a manifest hash. Never train on the frozen test split. Record reviewer ID, time spent, and confidence.

**Consequences:**

- Reproducible datasets and audits.
- Slightly more storage; trivial compared to the review time.
- The UI must support undo as a new label, not a destructive edit.
