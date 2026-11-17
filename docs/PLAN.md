# PCB-Enso — Project Plan

**Version:** 0.2 (MLX-first revision)
**Date:** 2026-11-17
**Owner:** David Le
**Lead agent:** DeepSeek V4.1 Flash
**Status:** Draft for discussion — planning only, no model trained yet

**Reference board:** Adafruit QT Py ESP32-S2 reconstruction (4-layer, 34 nets, 159 pads)
**Training machine:** Apple M5 Pro Mac mini, 64 GB unified memory, MLX 0.32.4
**Upstream inspiration:** [Enso](https://github.com/MVPandey/Enso) — a Sudoku EBM/JEPA. Pinned, not vendored (no license).

> This is independent research. It is not affiliated with or endorsed by Logical Intelligence,
> the Enso authors, Adafruit, or the KiCad project. Nothing here is fabrication-ready.

---

## 0. One-page summary

**The bottleneck.** In the QT Py reconstruction, placement and connectivity were tractable; routing was not. The independent 2-layer route peaked at **9 unconnected nets**, the targeted 4-layer attempt at **8**, and the final board passed only by falling back to the reference geometry. The failure was not local pathfinding — it was global allocation: signal tracks fragmented the GND pours, and the power geometry was coupled to a different signal route.

**The hypothesis.** Enso's recipe — a global context encoder, a low-dimensional latent variable, an energy landscape, and Langevin optimization at inference — is a good fit for problems where a solution must satisfy many constraints simultaneously. PCB routing is exactly that. We want to test whether a latent EBM can propose a **globally consistent routing plan** that a deterministic detailed router and KiCad's DRC can turn into legal copper.

**The honest caveat.** The Enso weights are Sudoku-specific and cannot be fine-tuned into a router. We are adapting the **architecture and training recipe**, not the trained model. The hard problems are representation, data, and legality — not the EBM code.

**The proposed system.** A three-level router:

1. **Global EBM (coarse, learned):** reason over a 0.5 mm grid with all nets, producing net ordering, corridors, and congestion allocation.
2. **Net-conditional refinement (medium, learned):** 0.25 mm per-net corridors and layer choices.
3. **Detailed routing (fine, classical):** 0.0762 mm A*/rip-up inside the proposed corridors, then KiCad DRC and repair.

The EBM is the **global planner**, not the geometry generator. KiCad's DRC is the ground truth. This hybrid is deliberately less glamorous than end-to-end pixel routing, and much more likely to produce a board that passes.

**First real milestone (Gate G4).** On a from-scratch, unrouted QT Py ESP32-S2 board, route the **signal nets** to **0 unconnected / 0 DRC errors**, beating the prior 8–9 unconnected peak. Power/ground planes are handled classically and measured separately.

**First two weeks.** Build the KiCad I/O + DRC harness, the board tensorizer, the classical baselines, and the MLX training skeleton. Do not train a routing model until Gate G0 (I/O fidelity) passes.

**Why this can fail — and what we still learn.** The model may not beat Freerouting. If it does not, we will still have: a reproducible KiCad routing benchmark, a rigorous ablation of latent EBM vs. feed-forward vs. classical routing, and a clear answer to whether test-time energy minimization helps constrained geometric design. That is a publishable result either way.

---

## 1. The problem we are actually solving

### 1.1 Formal statement

Given a board

```
B = (outline, stackup, pads, nets, obstacles, design_rules)
```

find a set of copper tracks and vias `T` such that:

1. every net's pads are electrically connected;
2. no track/via violates the board's clearance, width, drill, edge, or keep-out rules;
3. a quality objective is minimized (wirelength, vias, bends, skew, layer balance);
4. the result loads in KiCad and passes `kicad-cli pcb drc`.

This is a constrained, multi-commodity path-planning problem on a 3D graph. It is NP-hard in general. Classical routers solve it with maze routing, rip-up and reroute, and negotiated congestion. Humans solve it with hierarchy: plan the big moves first, then detail.

### 1.2 Why the previous attempt stalled

The QT Py experiment is unusually well documented, which makes it a good baseline:

| Metric | Value |
|---|---|
| Board | 17.78 × 20.701 mm, 4-layer, 1.6 mm FR4 |
| Components / nets / pads | 45 / 34 / 159 |
| Final tracks / vias / copper | 425 segments / 43 vias / 344.1 mm |
| Min track / space | 0.1524 mm (6 mil) |
| Independent 2-layer peak | 9 unconnected, 0 DRC errors |
| Targeted 4-layer peak | 8 unconnected, 0 DRC errors |
| Final result | 0 unconnected / 0 DRC errors, **reference-assisted** |
| USB skew | 1.093 mm |

Root causes, from the experiment report:

- **Global coupling.** Signal routing fragmented the GND pours into 14 islands. Fixing the pours required rerouting the signal tracks that blocked them, not adding stitches.
- **Sequential commitment.** A net routed early can make a later net unreachable. Greedy routers cannot revise the early choice without rip-up.
- **Power geometry is not independent.** The reference +3V3/GND geometry assumed Adafruit's signal route; substituting it into a different signal route produced dozens of shorts and clearance errors.

That is precisely the failure mode an EBM is supposed to address: evaluate the whole board, revise globally, and optimize all constraints together. Whether it actually does is the research question.

### 1.3 Scope

**In scope (v0.2):**

- Rigid boards, 2 and 4 copper layers.
- Signal nets first; power/ground planes handled by zones + stitching heuristics.
- Rectilinear and 45° tracks; through vias.
- FR4 stackups, 6 mil (0.1524 mm) minimum track/space as the initial hard case.
- KiCad 9/10 `.kicad_pcb`, macOS, single machine.

**Out of scope (initially):**

- HDI, microvias, blind/buried vias, flex/rigid-flex.
- Impedance-controlled high-speed nets beyond simple length/skew penalties.
- RF tuning, thermal co-design, EMC sign-off.
- Fabrication release. Output is experimental and requires human review.
- Beating a commercial router on arbitrary boards. We start with small boards and a strong baseline.

---

## 2. Starting assets and evidence

| Asset | Location | Notes |
|---|---|---|
| Enso source (Sudoku EBM) | `third_party/enso/` (gitignored) | Upstream commit `8013c8f`, MLX reimplementation planned |
| Enso archive | `third_party/Enso-main.zip` (gitignored) | SHA-256 `0781c0f4…519cb35` |
| QT Py ESP32-S2 project | `boards/qt-py-esp32-s2/` | Full reconstruction, reports, KiCad board, exports |
| Board snapshot commit | `73ff5db` | Preserved locally as `.git-disabled`; upstream repo linked in `boards/README.md` |
| KiCad | `/Applications/KiCad/KiCad.app` | 10.0.7, `kicad-cli` available |
| MLX | `.venv` | 0.32.4, Metal GPU, 64 GB unified memory |
| Prior plan input | `docs/briefs/original-spec.md` | The first-draft technical spec, kept for traceability |

### 2.1 What Enso actually is

Enso is an independent replication of Logical Intelligence's Kona 1.0 Sudoku EBM. It trains a JEPA-style model:

- **Context encoder:** 8-layer Transformer, `d_model=512`, 8 heads, encodes the puzzle.
- **Target encoder:** same architecture, EMA of the context encoder, encodes the solution.
- **Predictor:** 3-layer MLP mapping `(z_context, z) → z_pred`.
- **Decoder:** 4-layer Transformer, per-cell digit logits, hard-enforces clues.
- **Energy:** `||z_pred − z_target||²`.
- **Inference:** Langevin dynamics in latent space; 50–100 steps, 4–16 chains.
- **Result:** 36.5M parameters, 96.6% puzzle accuracy, +1.0% from Langevin.
- **Compute:** 22 hours on an H200 for 9M puzzles × 20 epochs.

The important lessons from the Enso training log are not the Sudoku numbers. They are:

1. **Representation collapse is the default failure.** VICReg must be applied to the right tensor (`z_context`), not the predictor output.
2. **`z` must carry information, but not too much.** A high-norm `z` becomes a lookup table; the decoder ignores the energy. L2-normalize and calibrate noise.
3. **Training and inference energies must match.** Enso's first Langevin attempts made accuracy worse because inference optimized a different objective than training.
4. **Constraints must be seen during training.** Adding the constraint penalty to the training loss is what made Langevin help.
5. **Checkpoint on the metric you care about.** Lowest energy is not the same as best puzzle accuracy.

### 2.2 What we are not claiming

- Enso's Sudoku weights do not transfer. The input is 10 channels of 9×9 digits; ours is a multi-layer spatial board. We will train from scratch.
- "Open-source" is not the same as "licensed." The upstream repository has **no LICENSE file** and GitHub reports no license. Default copyright applies. We will not copy its code into this repo. See §12.
- A 36.5M-parameter model on an H200 is not the target. We are designing for a 64 GB M5 Pro and a much smaller, spatially structured model.

---

## 3. What transfers from Enso — and what does not

| Enso component / idea | Transfers? | PCB-Enso adaptation |
|---|---|---|
| Context encoder | **Yes, as a pattern** | CNN + patch transformer over the board; global `z_context` |
| Target encoder + EMA | **Yes** | EMA copy over routed-board labels |
| Predictor `(z_context, z) → z_pred` | **Yes** | Same role; smaller MLP |
| Decoder | **Yes, structurally** | Per-cell/edge flow logits instead of digit logits |
| Energy = latent L2 | **Yes, plus terms** | Latent + flow conservation + capacity + clearance + via/length |
| VICReg anti-collapse | **Yes** | On `z_context`, with the same variance/covariance terms |
| Constraint penalty in training | **Yes** | Differentiable DRC surrogates, not just at inference |
| Langevin inference | **Yes, but as an outer loop** | Optimize `z`; then extract paths and legalize |
| Self-consistency energy | **Yes** | Decode → re-encode → compare, plus DRC terms |
| Sudoku weights | **No** | Different modality, shape, and output |
| 9×9 grid / 10 input channels | **No** | Board-specific tensors |
| Per-cell digit cross-entropy | **No** | Edge/flow loss + connectivity |
| ~300 ms inference | **No** | Target seconds to minutes initially |
| 36.5M params / H200 | **No** | 5–15M params; M5 Pro; coarse-to-fine |

**The core transfer is the recipe:** learn a latent representation of a *solved* board, predict it from an *unsolved* board, and at test time optimize a latent variable against an energy that encodes the constraints. The domain-specific parts are ours.

---

## 4. Research questions

This is an exploration of EBM limits, not only a product build. The questions we want to answer:

**RQ1 — Does global latent reasoning beat a feed-forward decoder?**
Compare a single forward pass of the EBM decoder against the same decoder with Langevin optimization. Metric: DRC-clean completion rate on held-out boards.

**RQ2 — Does an EBM beat strong classical baselines?**
Freerouting and our own A*/rip-up router are the baselines. A model that loses to them is still a result, but it must be measured honestly.

**RQ3 — How much does coarse global planning buy a fine detailed router?**
Ablate: classical detailed routing alone vs. classical routing inside EBM-proposed corridors. This isolates the value of the global plan.

**RQ4 — Does it generalize from synthetic to real boards?**
Train on procedurally generated boards; test zero-shot on the QT Py and a subset of PCBench/PCBWorld boards. Report the gap.

**RQ5 — What is the test-time compute trade-off?**
Quality vs. Langevin steps, chains, and latent dimension. If +10× compute buys +1% completion, that is a different result from +10× buying +20%.

**RQ6 — Can the energy landscape be inspected?**
Does the energy correlate with DRC violations, congestion, and rip-up count? An interpretable energy is a useful engineering signal even if the routes are not better.

**Success is not only "0 unconnected."** A rigorous negative result on RQ1/RQ2, with a working benchmark, is a valid outcome. The project fails only if we cannot produce reproducible evidence either way.

---

## 5. Technical approach

### 5.1 Representation: a routing graph, not a net-ID image

The original brief proposed a tensor `(L, H, W, C)` with `C` containing the net ID as a positive integer. That representation has three problems:

1. **Net IDs are arbitrary.** An integer channel makes net 27 "closer" to net 28 than to net 3, and makes the model depend on KiCad's numbering.
2. **A cell does not encode connectivity.** A cell belongs to a net, but not to a direction, so a connected path and a blob are indistinguishable.
3. **DRC is edge- and geometry-based.** Clearance, shorts, and via rules depend on what crosses a cell boundary, not just what occupies a cell.

We replace it with a **3D routing graph** and **per-net edge flow**:

- Vertices: grid cells × copper layers.
- Edges: 4 in-plane neighbors per layer (plus 45° later) and vertical via edges.
- Per net `n`, a non-negative flow `f_n(e)` on each edge.
- Terminals impose supply/demand; flow conservation at non-terminal nodes.
- Capacity: the sum of flows on an edge is limited (one trace per edge; blocked edges have zero capacity).
- A routed trace is a path in this graph; a via is a vertical edge.

This is the standard multi-commodity flow formulation used by global routers, with a differentiable relaxation for learning.

**Why this is better for an EBM:**

- Connectivity has a precise meaning: flow conservation.
- DRC has a precise meaning: capacity/clearance on edges and nodes.
- Path extraction is possible: decompose the flow into paths.
- The model can reason about all nets simultaneously without an ordinal net-ID channel.

### 5.2 Three-level hierarchy

A 0.0762 mm grid on this board is 233 × 272 × 4 ≈ 254k cells. A flat transformer over 254k tokens is not trainable on this machine. We use a hierarchy that mirrors how humans and classical routers work:

| Level | Resolution | Grid (QT Py) | Role | Method |
|---|---|---|---|---|
| **L0 — global** | 0.5 mm | 36 × 42 | Net ordering, corridors, congestion, layer allocation | EBM over all nets |
| **L1 — regional** | 0.25 mm | 71 × 83 | Per-net corridor refinement, layer/via choices | Conditional CNN/EBM |
| **L2 — detailed** | 0.0762 mm | 233 × 272 | Exact centerlines, widths, vias, DRC | A*/rip-up + legalizer |

0.0762 mm = 3 mil is chosen because the board's 6 mil (0.1524 mm) track/space rule maps exactly to 4 grid cells of spacing (0.3048 mm). A 0.25 mm grid cannot represent 6 mil rules without wasting space or producing illegal geometry.

**The Enso-scale insight.** At 0.5 mm, the QT Py is 36 × 42 cells. Patchified 6×6, that is 6 × 7 = 42 tokens; patchified 4×4, 9 × 11 = 99 tokens. That is almost exactly Sudoku's 81 cells. The global EBM can operate at a token count where a small transformer is fast on MLX. The fine grid is handled by convolutions and classical routing, not attention.

### 5.3 Architecture

```
                 unrouted board
                       │
              board compiler (KiCad → graph/tensors)
                       │
        ┌──────────────┴──────────────┐
        │  context encoder (CNN +     │
        │  patch transformer)         │
        └──────────────┬──────────────┘
                       │ z_context
        z ~ N(0, I) ──► predictor ──► z_pred
                       │
                 decoder (CNN) ──► per-net edge flow logits
                       │
              flow extraction / path decomposition
                       │
              detailed router (A*/rip-up)
                       │
                 KiCad DRC + repair loop
                       │
                 routed .kicad_pcb + report
```

**Context encoder (L0):**
- Input: obstacle/pad/layer/rule tensors, plus per-net features.
- A small CNN over the 36×42×4 grid (32–64 channels, 4–6 blocks).
- Patchify to 4×4 or 6×6 tokens; 4–6 transformer layers, `d_model=256–384`.
- Output: global `z_context` (256-d) and per-patch features for the decoder.

**Target encoder:** same architecture, fed the routed flow labels; EMA of the context encoder (momentum 0.996 → 1.0). No gradients.

**Predictor:** 3-layer MLP, `(z_context, z) → z_pred`, hidden 512–1024. Deliberately limited capacity so it cannot ignore `z`.

**Decoder:** CNN conditioned on `(z_context, z)` via FiLM (scale/shift), producing per-net per-edge flow logits at L0. A second decoder head produces L1 corridors for a selected net.

**Parameter budget:** 5–15M total. The MLX benchmark suggests a 10.8M transformer at 81 tokens × batch 64 runs at ~22 ms/step on this machine; the CNN adds cost but is cheap at these grid sizes. This is deliberately much smaller than Enso's 36.5M.

### 5.4 Energy and losses

Training loss:

```
L = L_energy + λ_v L_VICReg + λ_d L_decode + λ_c L_constraint
```

- `L_energy = ||z_pred − z_target||²`, with `z_target` from the EMA target encoder.
- `L_VICReg` on `z_context` (variance + covariance), to prevent collapse.
- `L_decode` = per-edge flow cross-entropy / BCE on routed edges, plus terminal constraints.
- `L_constraint` = differentiable DRC surrogates (below).

Inference energy `E(z)`:

```
E(z) = ||z_pred − z_target_est||²
     + λ_conn  E_connectivity
     + λ_cap   E_capacity
     + λ_clear E_clearance
     + λ_via   E_via
     + λ_len   E_length_skew
     + λ_keep  E_keepout
```

**Connectivity.** Use a soft shortest-path / Bellman-Ford relaxation per net: propagate a reachability field from the terminals through soft edges, and penalize the distance to the remaining terminals. For the flow representation, the primary constraint is **flow conservation**: `||B f_n − b_n||²` at every node. This is differentiable with a fixed conv/stencil and is exact in the hard limit.

**Capacity/clearance.** At each edge and cell, penalize `relu(Σ_n f_n − cap)`. For clearance, dilate each net's occupancy by the clearance radius (in cells) and penalize overlap between different nets. These are 2D convolutions with fixed kernels.

**Vias.** Cost per vertical edge; forbid via-in-pad by a hard mask; penalize via-to-via spacing.

**Length/skew.** Expected length = `Σ length(e) · f_n(e)`. For differential pairs, penalize `|L+ − L−|`; for max-length nets, penalize `relu(L − L_max)`.

**Keep-outs.** Hard mask: obstacle, board-edge, and antenna keep-out cells have zero capacity. A log-barrier or projected logits prevents any flow there.

**Hard projection.** Obstacles and pad terminals are enforced by masking logits and clamping terminal flow, not only by penalty. A soft penalty alone cannot guarantee DRC.

### 5.5 Inference: propose → extract → verify → repair

1. Encode the unrouted board once → `z_context`.
2. Initialize `K` latent chains from `N(0, I)`.
3. For `T` steps: decode flows, compute `E(z)`, take `∇z`, update with temperature-annealed noise (Langevin).
4. Decode the lowest-energy chain to hard edges.
5. **Extract paths per net** with a constrained shortest path on `−log p`, restricted to the model's high-probability corridor. This guarantees a connected path when one exists, and removes blobs/fragments.
6. **Legalize**: convert paths to tracks/vias at the correct width; run KiCad DRC.
7. **Repair**: rip up violating nets, re-route them with A* using the other nets as obstacles, and re-run DRC. Optionally feed the violation map back as an extra input channel and re-run the model.
8. Emit `routed.kicad_pcb`, `drc.json`, and a human-readable proposal report.

The EBM never gets the final say on legality. KiCad does.

### 5.6 Integration with KiCad and the agent

**Read path:** prefer a version-tolerant S-expression parser for `.kicad_pcb` (the prior project already has one), with `pcbnew`/`kipy` as an optional path when running inside KiCad. The prior report found `pcbnew.LoadBoard()` unreliable outside KiCad; do not depend on it.

**Write path:** S-expression injection for tracks/vias, or the KiCad IPC API (`kipy`) with a commit transaction when a live KiCad instance is available. Pin KiCad 10.0.7 for the first milestone; test KiCad 9 compatibility later.

**Verification:** `kicad-cli pcb drc --format json` is the ground truth. No self-reported DRC, no waivers.

**Agent tool surface:**

```
pcb-enso inspect   board.kicad_pcb                 → board summary + tensor preview
pcb-enso route     board.kicad_pcb --scope signal  → routed board + DRC report
pcb-enso suggest   board.kicad_pcb --net SDA       → corridor/ordering proposal
pcb-enso score     board.kicad_pcb                 → metrics + violations
pcb-enso repair    board.kicad_pcb --drc drc.json  → repaired board
```

Two modes:

- **Batch mode:** model proposes a full route; classical router/legalizer produces copper; agent reviews the DRC report.
- **Copilot mode:** model ranks nets and proposes corridors; the agent routes interactively in KiCad. This is lower-risk and likely useful sooner.

The agent (me) uses the tool, checks the DRC, and makes the electrical judgement. The model does not get autonomous commit access to a board.

---

## 6. Data strategy

This is the critical path. Enso had 9M Sudoku puzzles with exact labels. PCB routing does not. Without a data engine, the model will not learn.

### 6.1 Sources

| Source | Volume | Use | License / caveat |
|---|---|---|---|
| Procedural synthetic boards | 10k–100k | Pretraining, ablations, curriculum | Generated by us; own the labels |
| QT Py ESP32-S2 | 1 board | Held-out final test only | Adafruit reference CC BY-SA 3.0; reconstruction repo |
| PCBench | ~1,182 boards (public releases vary) | Real-board evaluation / fine-tune | Per-board open-source licenses; maintain manifest |
| PCBWorld D3 | 679 real boards, KiCad 9 | External benchmark | Code BSD-3; boards retain original licenses |
| KiCad demo/open hardware | tens–hundreds | Sanity checks | Per-project licenses |

**Do not train on the QT Py.** It is the final held-out test. If we tune on it, Gate G4 means nothing.

### 6.2 Synthetic generator

A controllable generator is worth more than a small scraped dataset. It must produce:

- Board outlines: rectangular, rounded, notched; 2/4 layers; stackups.
- Components/pads: SMD, THT, connectors, courtyards, mounting holes.
- Nets: 2–8 terminals, trees and chains; signal/power/ground/diff classes.
- Obstacles: courtyards, holes, edge clearance, antenna keep-out.
- Design rules: track width, clearance, via drill/annular ring, edge clearance.
- Difficulty knobs: net count, density, obstacle fraction, layer count, via cost.
- Domain randomization: rotation, grid offset, pad shapes, rule variations.

Two labeling strategies:

1. **Route-then-derive:** generate a hidden legal route first, place pads at its endpoints, and derive the netlist. Guarantees a label exists, but can produce unrealistic geometry.
2. **Place-then-route:** generate placement and netlist, then label with a strong classical router (Freerouting + our A*/rip-up, multiple seeds). Reject any label that does not pass DRC. More realistic; slower.

Use both. Keep multiple solutions per board where possible (different seeds) to teach diversity rather than a single "correct" route.

### 6.3 Label quality

- Every label is re-opened and checked with `kicad-cli pcb drc`.
- Reject labels with error-level violations.
- Store the label's cost (length, vias) and the router/seed that produced it.
- Prefer multiple diverse DRC-clean labels over one "optimal" label.

### 6.4 Splits

- **By design family**, not by random board. Boards from the same author/project must not appear in both train and test.
- Held-out: QT Py (final), a PCBench family subset, and a synthetic "hard" split with denser nets.
- Report zero-shot and fine-tuned numbers separately.

### 6.5 Volume estimates

| Level | Per-board tensor | 10k boards | 50k boards |
|---|---|---|---|
| L0 (0.5 mm, all nets, uint8) | ~1 MB | ~10 GB | ~50 GB |
| L1 (0.25 mm, per-net sparse) | ~2–5 MB | ~20–50 GB | ~100–250 GB |
| L2 (0.0762 mm) | not stored densely | generated on demand | generated on demand |

Start with L0 only. Add L1 after G2. Keep L2 generated on demand; do not store 254k-cell tensors for every board.

---

## 7. Evaluation

### 7.1 Primary metric

**Clean pass (CP):** fraction of boards that are fully connected **and** have zero error-level DRC violations. This is the headline. It matches PCBWorld's definition and the prior project's pass bar.

Secondary metrics:

| Metric | Definition | Direction |
|---|---|---|
| Routability | fraction of required connections routed | ↑ |
| DRV | error-level DRC violations | ↓ |
| Wirelength | total copper, mm | ↓ |
| Vias | count | ↓ |
| Skew | differential-pair length mismatch, mm | ↓ |
| Runtime | wall-clock seconds | ↓ |
| Generalization gap | synthetic vs. real clean-pass rate | ↓ |

Use PCBWorld's `@5` protocol for external comparisons where applicable: five rollouts, keep the best by potential, average over boards. Report `@1` too, because deterministic methods and our model may differ.

### 7.2 Benchmark sets

| Set | Contents | Purpose |
|---|---|---|
| **B0 — tiny** | 20–50 synthetic boards, 4–8 nets, 2 layers | Debugging; fast iteration |
| **B1 — QT Py** | Held-out signal nets, from-scratch board | Milestone G4 |
| **B2 — synthetic hard** | 200 boards, dense, 4 layers, 16–32 nets | Main learned benchmark |
| **B3 — real** | 20–50 PCBench/PCBWorld boards | External validity |
| **B4 — stress** | 100+ nets, fine pitch, diff pairs | Limits; not a gate initially |

### 7.3 Baselines

- **Freerouting** (already used in the prior project; 2.5.0).
- **Sequential A* + rip-up** (our own; deterministic, strong, fast).
- **Reference geometry** (quality upper bound, not a method).
- **Feed-forward model** (same decoder, no Langevin).
- **Random/restart Langevin** (control for the optimizer).
- **Classical detailed router inside EBM corridors** (isolates the value of the global plan).
- External context only: PCBWorld PPO, DeepPCB/Quilter vendor claims. Do not compare directly on our board without running them.

### 7.4 Protocol

- Fixed seeds; five runs where stochastic.
- Every result has a JSON artifact: config, commit, seed, metrics, DRC summary.
- No cherry-picked boards. Report per-board and aggregate.
- Failures are reported with the same prominence as successes.
- A board is "passed" only if a fresh `kicad-cli pcb drc` run on the saved file says so.

---

## 8. Roadmap and gates

**Assumption:** part-time, roughly 10–15 focused hours per week, with the agent doing most implementation. Calendar estimates are ranges, not commitments.

### Phase 0 — Foundations and KiCad harness (weeks 1–2)

**Deliverables:**

- Repo structure, docs, license decision, environment check.
- KiCad reader → canonical board model (outline, stackup, pads, nets, rules, obstacles).
- Tensorizer at L0/L1/L2 with visual overlays.
- `kicad-cli pcb drc` runner + metrics JSON.
- Round-trip no-op writer.
- Freerouting baseline + A* baseline harness.
- MLX training skeleton (module tree, optimizer, checkpoint, smoke test).

**Gate G0 — I/O fidelity (hard):**
- Parse the QT Py board: 34 nets, 159 pads, 425 segments, 43 vias.
- Write a no-op board; DRC result identical (0 errors).
- Tensorizer overlay matches the board render within visual tolerance.
- A deliberately broken track produces the expected DRC failure.

### Phase 1 — Data engine v0 (weeks 3–5)

**Deliverables:**

- Synthetic board generator v0 (2 layers, 4–16 nets, controllable density).
- Classical labeler (A*/rip-up + Freerouting), DRC filtering, multi-seed diversity.
- Dataset schema, sharding, splits, manifest, license metadata.
- 10k L0 boards + 1k L1 boards with verified labels.
- Enso recipe smoke test on a tiny Sudoku subset (optional; validates the MLX training loop, not the PCB model).

**Gate G1 — Dataset v0:**
- 10k boards generated reproducibly.
- ≥90% of labels DRC-clean on easy boards; ≥60% on hard.
- Baseline success rates measured and documented.
- No train/test family leakage.

### Phase 2 — Representation bake-off (weeks 6–7)

Compare three representations on B0/B2:

- **A. Per-cell net one-hot** (original brief, coarse resolution).
- **B. Per-net edge occupancy** (no flow conservation).
- **C. Per-net edge flow** (recommended; conservation + capacity).

Train a small supervised model for each. Evaluate after path extraction + legalization. Ablate the decoder backbone (CNN vs. patch transformer).

**Gate G2 — Representation decision:**
- One representation wins clearly on connectivity and DRC-clean rate.
- The winner trains stably on MLX (no collapse, reproducible within noise).
- If C does not beat B, simplify; do not carry unnecessary complexity.

### Phase 3 — EBM adaptation (weeks 8–10)

**Deliverables:**

- PCB-JEPA in MLX: context encoder, EMA target, predictor, decoder.
- Energy terms: latent, flow conservation, capacity, clearance, via, length/skew, keep-out.
- Langevin inference with path extraction.
- Ablations: no Langevin, no VICReg, no constraint loss, no global context.
- Training on B2; zero-shot B3.

**Gate G3 — Does Langevin help?**
- On held-out B2, Langevin improves clean-pass rate by ≥3 percentage points over a single forward pass, at a stated compute budget.
- If it does not, document the negative result and pivot to the feed-forward/classical hybrid. This is a legitimate outcome.

### Phase 4 — Hybrid router and KiCad integration (weeks 11–13)

**Deliverables:**

- `pcb-enso` CLI: inspect, route, suggest, score, repair.
- Detailed router + legalizer + DRC repair loop.
- Batch mode and copilot mode.
- QT Py signal-net run from scratch.
- MCP/agent interface (optional but desirable).

**Gate G4 — QT Py signal route (headline):**
- From a from-scratch, unrouted board, route all signal nets.
- **0 unconnected / 0 error-level DRC violations.**
- Power/ground plane handling measured separately; no hidden waivers.
- Beat the prior 8–9 unconnected peak on the same scope.
- Report wirelength/vias vs. reference; do not require beating the reference.

### Phase 5 — Scale, external benchmark, write-up (weeks 14+)

- 20–50 real boards from PCBench/PCBWorld.
- Compare clean-pass rate to Freerouting and A*.
- 4-layer, diff pairs, length matching.
- Paper/blog, model weights, dataset card, reproduction script.
- Decide whether to release weights and data; license audit first.

### Gate summary

| Gate | Question | Pass criterion | If fail |
|---|---|---|---|
| G0 | Can we read/write/verify boards faithfully? | Round-trip + DRC parity | Fix I/O before any ML |
| G1 | Do we have enough trustworthy labels? | 10k boards, 90% easy clean | Improve generator/labeler |
| G2 | Which representation? | Clear winner on clean pass | Simplify; pick B if C ties |
| G3 | Does Langevin add value? | +3 pts clean pass | Pivot to feed-forward hybrid |
| G4 | Does it route the QT Py? | 0 unconnected / 0 DRC | Narrow scope; report honestly |
| G5 | Does it generalize? | Competitive with Freerouting on B3 | Publish negative result + harness |

### First ten working sessions

1. Repo, docs, environment check, license audit.
2. KiCad S-expression reader → canonical board model.
3. DRC runner + metrics JSON + golden test.
4. Tensorizer L0/L1/L2 + overlay render.
5. No-op round-trip → **G0**.
6. Freerouting baseline + A* baseline.
7. Synthetic generator v0.
8. Labeler + DRC filter.
9. Dataset sharding + splits + manifest.
10. **G1** review + go/no-go.

---

## 9. Compute plan on the M5 Pro

### 9.1 Measured baseline (MLX 0.32.4)

Preliminary synthetic benchmark, not the full model:

| Workload | Params | Tokens | Batch | Time/step | Throughput | Peak memory |
|---|---|---:|---:|---:|---:|---:|
| Transformer, 6 layers, d=384 | 10.8M | 81 | 64 | 21 ms | ~3,000 boards/s | 5.8 GB |
| Transformer, 8 layers, d=512 | 25.5M | 121 | 64 | 56 ms | ~1,140 boards/s | 15.5 GB |
| Matmul 4096³, bf16 | — | — | — | 4.8 ms | ~28 TFLOPS | — |

These are forward+backward on synthetic tensors; the full model, data loading, fine-grid decoding, and DRC will add substantial overhead. Treat them as an upper bound on neural compute, not an end-to-end estimate.

**Implication:** a 5–15M coarse-grid model is comfortably trainable locally. The bottleneck will be **label generation and DRC evaluation**, not the MLX training step.

### 9.2 Memory plan

- 64 GB unified memory; keep peak allocation under ~48 GB.
- `mx.set_memory_limit` / `mx.set_wired_limit` to avoid swap pressure.
- Start with `batch=32–64` at L0; use gradient accumulation for an effective batch of 128–256.
- Use `mx.compile` with fixed shapes; bucket boards by grid size to avoid recompiles.
- bf16 is not faster in the preliminary benchmark; default to fp32 for stability, test bf16 later.

### 9.3 Wall-clock estimates

| Task | Estimate |
|---|---|
| L0 training, 10k boards × 20 epochs, 10M model | 2–10 hours (including data pipeline) |
| Representation bake-off (3 reps × 3 seeds) | 1–3 days |
| Langevin ablation (5 settings × 3 seeds) | 1–2 days |
| Label generation, 10k boards, classical router | 1–3 days (parallel CPU) |
| QT Py end-to-end route + DRC + repair | seconds to minutes per attempt |

### 9.4 Cost

- Compute: $0 (local machine; electricity).
- Storage: ~100 GB working set; 424 GB free.
- Optional cloud: only if we scale beyond local capacity. Not in the base plan.

---

## 10. Risks and mitigations

| # | Risk | Likelihood | Impact | Mitigation | Trigger |
|---|---|---|---|---|---|
| 1 | Representation cannot express clean routes | High | High | Edge/flow graph, path extraction, bake-off at G2 | G2 fails |
| 2 | Labels are too scarce / unrealistic | High | High | Synthetic generator + classical labels + DRC filter | G1 fails |
| 3 | Model loses to classical baselines | Medium | Medium | Strong baselines; publish negative result; hybrid fallback | G3/G5 |
| 4 | Langevin does not help | Medium | Medium | Ablate early; pivot to feed-forward planner | G3 |
| 5 | DRC-invalid outputs | High | High | Hard masks, legalizer, KiCad DRC, repair loop | Any DRC error |
| 6 | Overfits to the QT Py | Medium | High | Held-out board; family splits; B3 real boards | G4 vs. G5 gap |
| 7 | MLX limitation / missing op | Medium | Medium | Conv/local losses; `mx.linalg`; custom Metal only if needed | Blocked >1 day |
| 8 | Local compute too slow | Low–Medium | Medium | Small models, coarse grids, `mx.compile`, fixed shapes | Throughput < target |
| 9 | License / provenance problem | Medium | High | No Enso code copied; per-board data manifest; legal review before release | Pre-release |
| 10 | Scope creep | High | High | Signal nets first; 2/4 layers; no HDI; gates | Any out-of-scope work |
| 11 | Silent DRC waivers / cherry-picking | Low | High | Fresh `kicad-cli` DRC on saved board; JSON artifacts; journal | Any claim |
| 12 | Board damage / bad fabrication | Low | High | Experimental only; human review; no fabrication | Release |

---

## 11. Working agreement

### 11.1 Evidence rules

- **No claim without an artifact.** Every result points to a config, seed, commit, command, and JSON output.
- **KiCad DRC is the judge.** Not a proxy, not a screenshot, not "looks routed."
- **No waivers.** Unconnected items and error-level violations are reported, not hidden.
- **Failures are first-class.** The journal records what did not work, with the same detail as successes.
- **Held-out means held-out.** The QT Py is not used for training or hyperparameter selection until G4 is frozen.

### 11.2 Repo conventions

- `main` is stable; experiments on `exp/<name>`.
- Commit prefixes: `docs:`, `feat:`, `fix:`, `exp:`, `data:`, `eval:`, `chore:`.
- One logical change per commit; include the command/result in the body when relevant.
- Large artifacts (checkpoints, datasets) are not committed; use `artifacts/` (gitignored) and publish via GitHub Releases/Hugging Face when ready.
- Every experiment gets a JSON result and a journal entry.

### 11.3 Journal cadence

Append to `docs/JOURNAL.md` after each session:

```
## YYYY-MM-DD — short title
Goal:
Did:
Evidence (commands, files, metrics):
Learned / surprised by:
Next:
```

### 11.4 Human approval gates

The human approves:

- Scope changes and new board families.
- Any spend (cloud, data, tools).
- License/provenance decisions before public release.
- Any claim of "0 DRC" that will be published.
- Fabrication. Nothing is fabricated without explicit approval.

### 11.5 Agent role

I am the lead implementation agent: I write the code, run experiments, maintain the benchmark, write the docs, and report honestly. I do not make electrical-safety or fabrication decisions, and I do not push to GitHub without approval.

---

## 12. Open decisions

1. **Repo visibility and license.** Proposal: public repo, Apache-2.0 for our code, CC BY 4.0 for docs, no Enso code redistributed. Confirm or choose MIT/private.
2. **Board identity.** The copy here is the **ESP32-S2** QT Py; the brief mentions an **ESP32-S3**. Which board is the G4 target? If the S3 board is on the unmounted `/Volumes/dblab` drive, we need a copy.
3. **Scope of "success."** Is G4 (QT Py signal nets, 0/0) enough, or is the goal a reusable tool for arbitrary boards? This changes how much time goes into generalization vs. the demo.
4. **Power/ground strategy.** Confirm signal-first, with GND/+3V3 planes handled classically. The prior failure was largely a pour-fragmentation problem; treating power as a separate plane problem is the pragmatic choice.
5. **Data licensing.** Are PCBench/PCBWorld boards acceptable for training, or only evaluation? We need a per-board manifest before publishing.
6. **Enso permission.** Do we want to open an issue with the upstream author to ask for a license, or keep our implementation clean-room and cite only?
7. **Time budget.** Part-time (10–15 h/week) vs. a focused push. The gate estimates assume part-time.

---

## Appendix A — Glossary

| Term | Meaning |
|---|---|
| **EBM** | Energy-based model: learns a scalar energy, low for valid solutions |
| **JEPA** | Joint Embedding Predictive Architecture: predict in representation space, not pixels |
| **Langevin dynamics** | Gradient descent on an energy with added noise and temperature annealing |
| **EMA** | Exponential moving average; used for the target encoder |
| **VICReg** | Variance/covariance regularizer that prevents representation collapse |
| **DRC** | Design rule check: clearance, width, drill, edge, shorts |
| **CP** | Clean pass: fully connected and zero error-level DRC violations |
| **MCF** | Multi-commodity flow: per-net flow with shared capacity |
| **L0/L1/L2** | Coarse global / regional / fine detailed routing levels |
| **Freerouting** | Open-source classical autorouter used as a baseline |

## Appendix B — Key links

- Enso upstream: https://github.com/MVPandey/Enso (commit `8013c8f`)
- Kona 1.0 / Logical Intelligence: https://logicalintelligence.com/blog/energy-based-model-sudoku-demo
- I-JEPA: https://arxiv.org/abs/2301.08243
- IRED: https://arxiv.org/abs/2401.02361
- PCBWorld: https://github.com/LGAI-Research/PCBWorld
- PCBench: https://github.com/PCBench/PCBench
- KiCad IPC API: https://dev-docs.kicad.org/en/apis-and-binding/ipc-api/
- MLX: https://github.com/ml-explore/mlx
- QT Py experiment: https://github.com/d4vid-le/qt-py-esp32-s2-experiment
