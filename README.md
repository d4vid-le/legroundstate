# PCB-Enso

**An experiment in latent-space energy-based routing for KiCad.**

Can an Energy-Based Model that reasons globally over a whole board help an AI agent route
PCBs better than sequential, greedy trace generation? This repo is the plan, the benchmark,
and eventually the model.

> **Status: planning (Phase 0 not started).** No routing model has been trained yet.
> The main deliverable so far is [`docs/PLAN.md`](docs/PLAN.md).

---

## Why

On a previous QT Py ESP32-S2 reconstruction, placement and connectivity were tractable;
routing was not. The independent route peaked at **9 unconnected nets** (2-layer) and **8**
(4-layer targeted). The final board passed only by falling back to Adafruit's reference
signal geometry. The failure was global — signal tracks fragmented the ground pours, and
power geometry was coupled to a different route — not a local pathfinding problem.

That is the kind of coupled constraint satisfaction an EBM is supposed to be good at.
This project tests whether it actually is.

**The honest version:** Enso's Sudoku weights cannot be fine-tuned into a router. We are
adapting the *recipe* — context/target encoders, a latent variable, an energy, and Langevin
optimization — and pairing it with a deterministic detailed router and KiCad's DRC. The EBM
proposes; KiCad disposes.

---

## Approach at a glance

```
unrouted board
     │
     ▼
KiCad compiler ──► 3-level routing graph ──► global EBM (0.5 mm, all nets)
                                                   │ corridors + ordering
                                                   ▼
                                        per-net refinement (0.25 mm)
                                                   │
                                                   ▼
                                        A*/rip-up detail (0.0762 mm)
                                                   │
                                                   ▼
                                        KiCad DRC + repair loop
                                                   │
                                                   ▼
                                     routed .kicad_pcb + report
```

| Level | Resolution | Role |
|---|---|---|
| L0 | 0.5 mm | Global plan: net order, corridors, layer/congestion allocation |
| L1 | 0.25 mm | Per-net corridor refinement |
| L2 | 0.0762 mm | Exact geometry, DRC, repair |

The learned levels are deliberately **not** DRC-exact. The fine router and `kicad-cli pcb drc`
are the legality guarantee.

---

## The first milestone

Route the **signal nets** of a from-scratch, unrouted QT Py ESP32-S2 to:

- **0 signal-net unconnected**
- **0 error-level DRC violations**
- verified by a fresh `kicad-cli pcb drc` run on the saved board

Power/ground planes are handled classically and measured separately. The prior independent
peak was 8–9 unconnected on the **full board** (including power nets), so the comparison is
reported with the scope difference, not as a direct win.

---

## Training on this machine

- **Apple M5 Pro Mac mini**, 18-core CPU, 64 GB unified memory
- **MLX 0.32.4**, Python 3.13
- Preliminary synthetic benchmark: a 10.8M-parameter transformer at 81 tokens, batch 64,
  runs at ~21 ms/step (~3,000 boards/s) and 5.8 GB peak. A 25.5M model at 121 tokens runs
  at ~56 ms/step and 15.5 GB.

Details and caveats: [`docs/notes/mlx-benchmark.md`](docs/notes/mlx-benchmark.md).
The practical bottleneck will be label generation and DRC, not the neural step.

---

## Repository layout

```
docs/
  PLAN.md              master plan, gates, risks, budget
  SPEC.md              technical spec v0.2 (tensors, model, energy, inference)
  RESEARCH.md          prior art, Enso notes, QT Py evidence, references
  DECISIONS.md         ADR log
  JOURNAL.md           progress log
  briefs/              the original v0.1 brief (kept verbatim)
  notes/               benchmark and research notes
boards/
  qt-py-esp32-s2/      reference board snapshot + prior reports (upstream history preserved locally)
third_party/
  README.md            Enso provenance and fetch instructions (source is not committed)
scripts/
  check_env.sh         verify KiCad, MLX, uv, disk
  fetch_enso.sh        fetch pinned upstream Enso (gitignored, no license)
  bench_mlx.py         reproducible MLX throughput benchmark
src/pcb_enso/          implementation (empty until Phase 0)
```

`data/`, `artifacts/`, `third_party/enso/`, and the board's local git history are gitignored.

---

## Quick start

```bash
# 1. Check the toolchain (KiCad 10, MLX, uv, disk)
scripts/check_env.sh

# 2. Read the plan
open docs/PLAN.md

# 3. Optional: reproduce the MLX benchmark
uv run python scripts/bench_mlx.py

# 4. Optional: fetch the pinned Enso reference (not redistributed)
scripts/fetch_enso.sh
```

---

## Key documents

| If you want to… | Read |
|---|---|
| Understand the project and gates | [`docs/PLAN.md`](docs/PLAN.md) |
| See the tensor/model design | [`docs/SPEC.md`](docs/SPEC.md) |
| See prior art and evidence | [`docs/RESEARCH.md`](docs/RESEARCH.md) |
| See why decisions were made | [`docs/DECISIONS.md`](docs/DECISIONS.md) |
| See what happened today | [`docs/JOURNAL.md`](docs/JOURNAL.md) |
| See the original idea | [`docs/briefs/original-spec.md`](docs/briefs/original-spec.md) |

---

## Licensing and provenance

- **Our code:** Apache-2.0 (proposed — see ADR-0008).
- **Our docs:** CC BY 4.0 (proposed).
- **Enso:** no LICENSE file upstream; default copyright. We do **not** redistribute its code.
  `scripts/fetch_enso.sh` fetches it locally for reference, and `third_party/enso/` is
  gitignored. The plan is a clean-room MLX reimplementation of the published recipe.
- **QT Py reference:** Adafruit's design is CC BY-SA 3.0. The reconstruction retains
  attribution; Adafruit's source files are not committed. See `boards/qt-py-esp32-s2/README.md`.
- **PCBench / PCBWorld:** per-board licenses; a manifest is required before training or
  releasing data. See `docs/RESEARCH.md` §6.

This is independent research. It is not affiliated with or endorsed by Logical Intelligence,
the Enso authors, Adafruit, or the KiCad project. Nothing here is fabrication-ready.
