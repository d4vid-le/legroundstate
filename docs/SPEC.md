# PCB-Enso — Technical Specification v0.2

**Status:** Draft
**Date:** 2026-11-17
**Supersedes:** the per-cell net-ID formulation in `docs/briefs/original-spec.md`
**Implementation target:** MLX 0.32.4 on Apple M5 Pro, 64 GB unified memory

---

## 1. Scope and assumptions

This spec defines a **research router**, not a production autorouter.

**Assumptions:**

- Board is rigid, 2 or 4 copper layers, FR4, through vias.
- Signal nets are the learned problem. Power/ground planes and zones are handled by a separate classical step.
- The board is described by a `.kicad_pcb` file that loads in KiCad 10.0.7.
- The fine detailed router operates on a 0.0762 mm (3 mil) grid; the learned levels are coarser and allocate corridors, not final copper.
- KiCad's DRC is the final authority. The learned energy is a surrogate.

**Non-goals:** HDI, microvias, blind/buried vias, flex, RF tuning, thermal/EMC sign-off, fabrication release.

---

## 2. Coordinate system and grids

- Board-local Cartesian coordinates in millimetres, origin at the board bounding-box minimum.
- KiCad uses a y-down board coordinate system in file space; the compiler normalizes to y-up for tensor work and converts back on write.
- Grid index: `i = floor((x - x0) / r)`, `j = floor((y - y0) / r)`.
- Cell centre: `(x0 + (i + 0.5) r, y0 + (j + 0.5) r)`.

| Level | Resolution `r` | QT Py grid (W×H) | Padded | Role |
|---|---:|---:|---:|---|
| L0 | 0.5 mm | 36 × 42 | 36 × 42 | Global plan, all nets |
| L1 | 0.25 mm | 72 × 84 | 72 × 84 | Per-net corridor refinement |
| L2 | 0.0762 mm | 234 × 272 | 234 × 272 | Detailed routing / DRC |

**Why 0.0762 mm:** the board's minimum track/space is 0.1524 mm (6 mil). Four 3-mil cells = 0.3048 mm = track + space, exactly. A 0.25 mm grid cannot represent this without waste or illegal geometry.

**Why L0 = 0.5 mm:** 36 × 42 = 1,512 cells/layer. With 6×6 patches, that is 6 × 7 = **42 spatial tokens**, close to Sudoku's 81 cells. This is the scale at which a small transformer is cheap on MLX.

The learned levels are **not DRC-exact**. They predict corridors, capacity, and layer allocation. L2 enforces geometry.

---

## 3. Routing graph

### 3.1 Graph definition

```
G = (V, E)
V = { (layer l, row j, col i) }
E = E_plane ∪ E_via
E_plane: (l,j,i) ↔ (l,j,i+1)   [east]
         (l,j,i) ↔ (l,j+1,i)   [south]
E_via:   (l,j,i) ↔ (l+1,j,i)
```

Start with a 4-neighbour Manhattan graph, but store only the **canonical east/south** edge variables (the west/north neighbours are the same physical edges). Add 8-neighbour diagonal edges in a later revision; 45° geometry is produced in the L2 post-process.

### 3.2 Flow variables

For each net `n`:

- `f_n(e) ≥ 0` on each undirected in-plane edge and via edge. For conservation, give each edge a fixed orientation (lower cell index → higher); the sign is applied by the incidence operator.
- Supply/demand `b_n(v)`: one root terminal has `+1`, the other terminals have `-1/(k-1)`, all other nodes 0.
- Conservation: `Σ_{e out of v} f_n(e) − Σ_{e into v} f_n(e) = b_n(v)`.
- Capacity: `Σ_n f_n(e) ≤ cap(e)`, where `cap(e) ∈ {0,1}` (one trace per physical edge; blocked edges are 0).
- Via capacity: `Σ_n f_n(e_via) ≤ cap_via(e_via)` and via-in-pad is 0.

A hard routed net is integral flow: `f_n(e) ∈ {0,1}` and conservation holds. The learned model predicts a relaxation in `[0,1]`.

### 3.3 Why flow instead of per-cell net IDs

| Property | Per-cell net ID | Per-net edge flow |
|---|---|---|
| Connectivity | Implicit, not enforced | Explicit conservation |
| Multiple nets crossing on different layers | Hard to represent | Natural |
| Shorts / clearance | Cell-level only | Edge/cell capacity |
| Path extraction | Ambiguous blobs | Flow decomposition |
| Net identity | Ordinal integer (bad) | Permutation-invariant per-net channels |
| DRC mapping | Weak | Direct |

---

## 4. Tensors

### 4.1 L0 (all nets)

Let `N` = number of nets, `L` = layers, `H=36`, `W=42`, `E=2` canonical in-plane directions (east, south).

| Tensor | Shape | Type | Description |
|---|---|---|---|
| `obs` | `[L,H,W]` | bool | Obstacle/keep-out/edge-clearance mask |
| `pad_mask` | `[N,L,H,W]` | bool | Pad cells per net; hard terminals |
| `pad_root` | `[N]` | int | Index of the root terminal |
| `net_feat` | `[N,F]` | float | Net class, width, clearance, current, diff-pair id, length target |
| `rules` | `[R]` | float | Global design rules |
| `cap_e` | `[L,H,W,E]` | bool | In-plane edge capacity |
| `cap_v` | `[L-1,H,W]` | bool | Via capacity |
| `gt_flow` | `[N,L,H,W,E]` | float | Ground-truth edge occupancy |
| `gt_via` | `[N,L-1,H,W]` | float | Ground-truth vias |
| `b` | `[N,L,H,W]` | float | Supply/demand |

Memory per board at L0: `34×4×36×42×2 ≈ 0.41M` floats for `gt_flow` (1.6 MB fp32; 0.4 MB uint8). With batch 32, ~52 MB fp32. Fine.

### 4.2 L1 (net-conditional)

For a selected net `n`:

| Tensor | Shape | Description |
|---|---|---|
| `obs` | `[L,84,72]` | Obstacle mask |
| `pads` | `[L,84,72]` | This net's terminals |
| `context` | `[L,84,72,C]` | Other nets' occupancy, congestion from L0, net features broadcast |
| `gt_flow` | `[L,84,72,E]` | Target edges |
| `gt_via` | `[L-1,84,72]` | Target vias |

Memory per sample: `4×84×72×2 ≈ 48k` floats. Batch 64 → 3.1M floats (~12 MB). Fine.

### 4.3 L2 (detailed)

`234 × 272 × 4` cells. Do not store dense labels for every board. The detailed router consumes:

- The L1 corridor mask (a small set of allowed cells/edges).
- The exact pad geometry, design rules, and obstacles.
- The other nets' committed geometry.

It produces track segments and vias with exact coordinates.

---

## 5. Model

### 5.1 Overview

```
x_board ──► context encoder ──► z_context ──┐
                                            ├──► predictor ──► z_pred
z ~ N(0,I) ────────────────────────────────┘
                                            │
z_context, z ──► decoder ──► flow logits ──► path extraction
```

### 5.2 Context encoder

Input: `obs`, `pad_mask`, `net_feat`, `rules`, plus a learned net embedding broadcast to pad cells.

1. **Stem:** concatenate layers as channels → `[H,W,L·C_in]`; 3×3 conv → 64 channels; GroupNorm + GELU.
2. **Body:** 4 residual blocks at 64 → 128 → 192 channels, dilations 1/2/4/8, same spatial size (padding `same`). Dilation gives global context without destroying the 36×42 grid.
3. **Patchify:** 6×6 conv with stride 6 on the 36×42 grid → 6×7 = 42 tokens; linear projection to `d_model=384`.
4. **Positional encoding:** learned 2D patch embedding.
5. **Transformer:** 6 layers, 6 heads, `d_ffn=1536`, pre-norm, GELU.
6. **Outputs:** global token → `z_context ∈ R^256`; per-patch features for the decoder.

Parameter estimate: 8–12M including the CNN stem.

### 5.3 Target encoder

Same architecture, different input projection:

- Input: `gt_flow`, `gt_via`, `obs`, `pad_mask`.
- No gradients; EMA of the context encoder weights.
- EMA momentum: `m_t = 0.996 + (1 − 0.996) · min(1, t/T)` → 1.0.
- Update only parameters with matching shapes; the input projection differs.

### 5.4 Predictor

```
h = concat(z_context, z)          # 256 + 256
h = GELU(Linear(h, 512))
h = GELU(Linear(h, 512))
z_pred = Linear(h, 256)
z_pred = L2_normalize(z_pred)
```

Deliberately limited capacity. Enso's lesson: if the predictor is too powerful, it ignores `z`.

### 5.5 Decoder

Two heads:

- **L0 flow head:** FiLM-conditioned CNN over the patch grid, upsampled to 36×42, output `[N,L,H,W,E]` and `[N,L-1,H,W]` logits.
- **L1 corridor head:** a smaller U-Net conditioned on `z` and the selected net embedding, output `[L,84,72,E]` logits.
- **Priority head:** a per-net scalar logit from the global token, used as the routing/rip-up order. This is the model's "net ordering" output; it is trained from the label's rip-up difficulty or a simple criticality heuristic (start with net length / congestion).

FiLM: `γ = Linear(z, C)`, `β = Linear(z, C)`, `h = γ · h + β` per block.

Hard constraints applied to logits:

- Blocked edges: `logit = -1e9` where `cap_e = 0`.
- Via-in-pad / blocked via: `logit = -1e9`.
- Terminal cells: the net's flow into/out of the terminal is clamped to the required direction; other nets' terminals are masked.

### 5.6 Parameter budget

| Component | Params (target) |
|---|---:|
| CNN stem/body | 2–4M |
| Patch transformer (6 layers, d=384) | 7–8M |
| Decoder | 2–4M |
| Predictor | 0.5–1M |
| **Total** | **12–17M** |

Start smaller (5–8M) for the bake-off. Scale only after G2.

---

## 6. Energy and losses

### 6.1 Training objective

```
L = L_energy
  + λ_v  L_VICReg(z_context)
  + λ_d  L_flow(flow_logits, gt_flow)
  + λ_c  L_constraint(flow_logits)
```

**L_energy:** `mean(||z_pred − z_target||²)`, with `z_target = L2_normalize(z_encoder(target_encoder(gt)))`.

**L_VICReg:** variance + covariance on `z_context` across the batch. Enso's weights: similarity 25, variance 1, covariance 0.01. Start with variance 1, covariance 0.01, and no invariance term (there is no augmented pair yet).

**L_flow:** binary cross-entropy with logits on `gt_flow` and `gt_via`. Positive edges are sparse; use `pos_weight` ~5–20 and weight by edge length. Mask blocked edges.

**L_constraint:** differentiable surrogates:

- Conservation: `mean((div(f) − b)²)`, where `f = sigmoid(flow_logits)`.
- Capacity: `mean(relu(Σ_n f_n − cap)²)`.
- Clearance: `Σ_{n≠m} <dilate(f_n, r_c), f_m> / (N(N−1))`, with `r_c` from the rule set.
- Via-in-pad: `mean(via_prob · pad_mask_other_nets)`.
- Keep-out: `mean(f · keepout_mask) · 1e3`.

### 6.2 Inference energy

```
E(z) = ||z_pred − z_target_est||²
     + λ_conn  · E_conservation
     + λ_cap   · E_capacity
     + λ_clear · E_clearance
     + λ_via   · E_via
     + λ_len   · E_length
     + λ_keep  · E_keepout
```

`z_target_est` comes from decoding the current `z`, re-encoding through the target encoder, and comparing — Enso's self-consistency trick. This aligns inference with training.

**Temperature annealing:** `T_t = 1 − t/T`. Update:

```
z ← z − η ∇_z E(z) + sqrt(2 η T_t) · ε,   ε ~ N(0, I)
```

**Chains:** `K = 4–16`; select the lowest final energy. Report energy, not just the route.

### 6.3 Why the energy is not just DRC

A soft DRC penalty can be reduced by shrinking all flows to zero. The energy must include a **coverage/connectivity** term that rewards flow from terminals to terminals, and a **cost** term that rewards short routes. The capacity/clearance terms then penalize conflicts. The balance is delicate; log-barriers and hard masks help.

**Anti-degenerate terms:**

- Terminal reachability: each terminal must have at least the required flow out.
- Flow magnitude: `Σ f` should be close to the minimum Steiner length, not zero.
- Entropy bonus on edge probabilities early in training, decayed later.

---

## 7. Inference pipeline

### 7.1 Pseudocode

```
def route(board):
    ctx = compile_board(board)              # L0 tensors, graph
    z_ctx = context_encoder(ctx)
    z = init_chains(K, d_latent)
    for step in range(T):
        logits = decoder(z_ctx, z, ctx)
        f = sigmoid(logits.flow)
        E = energy(z, z_ctx, f, ctx)
        g = grad(E, z)
        z = z - lr * g + noise(step, T)
    best = argmin_chains(E)
    hard = threshold(best.flow)
    paths = extract_paths(hard, ctx)        # per net, constrained shortest path
    tracks = to_geometry(paths)             # width, 45° chamfer, vias
    drc = kicad_drc(tracks)
    for i in range(max_repair):
        if drc.clean: break
        tracks = repair(tracks, drc, ctx)   # A* rip-up, violation map
        drc = kicad_drc(tracks)
    return tracks, drc, report
```

### 7.2 Path extraction

For each net:

1. Build edge costs `c(e) = −log(sigmoid(logit_e)) + λ_len · length(e) + λ_via · via(e)`.
2. Run Dijkstra/A* from the root terminal to each remaining terminal, restricted to edges with probability above a threshold and to the L1 corridor.
3. Union the paths; remove cycles; check connectivity.
4. If a terminal is unreachable, mark the net unconnected and record the blocking edges.

This step guarantees that a decoded net is a **path**, not a blob. It also gives a precise failure signal: the cut edges.

### 7.3 Legalization

- Convert grid paths to polyline segments; optional 45° chamfering.
- Assign width from the net class (minimum width + margin).
- Place vias at layer transitions; check via-in-pad and drill rules.
- Resolve same-net overlaps by merging; different-net overlaps are errors routed to repair.

### 7.4 Repair

- Sort violations by severity: shorts > clearance > hole > edge.
- Rip up the lower-priority net(s) involved.
- Re-route with A* using the committed geometry as obstacles, within a small detour budget.
- If repair fails after `max_repair`, return the failure with the violating items and the model's energy. Do not waive.

### 7.5 Reporting

Every run writes:

- `routed.kicad_pcb`
- `drc.json` (raw `kicad-cli` output)
- `metrics.json` (CP, routability, DRV, WL, vias, runtime, energy, chains)
- `proposal.json` (net order, corridors, confidence, predicted conflicts)
- `run.json` (commit, config, seed, board hash, KiCad version)

---

## 8. KiCad integration

### 8.1 Read

Preferred: a version-tolerant S-expression parser (the prior project's `extract_kicad_netlist.py` is a starting point). It must extract:

- Outline (`Edge.Cuts`), stackup (`layers`, `setup`), design rules (`.kicad_dru`, board setup).
- Footprints, pads, pad nets, pad shapes, layers, drill.
- Existing tracks/vias/zones.
- Net names and net classes.

Fallback: KiCad IPC (`kipy`) when a live KiCad instance is available. Do **not** depend on `pcbnew.LoadBoard()` outside KiCad; the prior report found it broken in this environment.

### 8.2 Write

- Add `segment` and `via` S-expressions with new UUIDs.
- Preserve existing items; support "replace only this net" for repair.
- Write atomically; keep a `.bak`.
- Validate by reloading with the parser and running DRC.

### 8.3 DRC

```
/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli pcb drc \
  --format json --output drc.json board.kicad_pcb
```

Parse error-level violations and unconnected items. Treat warnings separately; do not count them as passes or waivers.

### 8.4 Version support

- Primary: KiCad 10.0.7 (installed).
- Test: KiCad 9 file format on a fixture board.
- Do not use features that require KiCad 11.

---

## 9. Data schema

### 9.1 Board record

```json
{
  "id": "synth_000123",
  "family": "grid_dense_v1",
  "source": "synthetic",
  "license": "generated",
  "outline": [[0,0],[17.78,0],[17.78,20.701],[0,20.701]],
  "stackup": {"layers": 4, "thickness": 1.6},
  "nets": [{"name": "N1", "class": "signal", "pads": [[x,y,layer], ...]}],
  "rules": {"track": 0.1524, "space": 0.1524, "via_drill": 0.3, "via_ring": 0.15},
  "obstacles": [{"type": "courtyard", "polygon": [[...]]}],
  "route": {"N1": [{"start": [x,y,l], "end": [x,y,l], "width": 0.1524}]}
}
```

### 9.2 Tensor shard

```
data/l0/train/shard_00000.npz
  obs        uint8  [B,L,H,W]
  pad_mask   uint8  [B,N,L,H,W]
  gt_flow    uint8  [B,N,L,H,W,E]
  gt_via     uint8  [B,N,L-1,H,W]
  b          float16[B,N,L,H,W]
  ids        <U32  [B]
```

Use `N` padded to a fixed maximum per shard (e.g., 64 nets). Mask absent nets.

### 9.3 Manifest

One JSONL line per board:

```
{"id","family","split","seed","router","drc_errors","drc_unconnected","wirelength","vias","license","source_url","sha256"}
```

Splits are by `family`, not by random row.

---

## 10. MLX implementation notes

### 10.1 Module layout

```
src/pcb_enso/
  mlx/
    encoder.py      # CNN + patch transformer
    decoder.py      # FiLM CNN, flow heads
    predictor.py
    jepa.py         # orchestrator, EMA, forward
    energy.py       # conservation, capacity, clearance, via, length
    langevin.py     # inference loop, chain selection
    train.py        # loss, step, optimizer, checkpoint
  kicad/
    sexpr.py        # read/write
    board.py        # canonical model
    drc.py          # kicad-cli wrapper
  geometry/
    grid.py
    rasterize.py
    extract.py
    legalize.py
  data/
    synthetic.py
    labeler.py
    dataset.py
    manifest.py
  eval/
    metrics.py
    baselines.py
```

### 10.2 MLX specifics

- **Lazy evaluation:** build the graph, call `mx.eval(loss, model.parameters(), optimizer.state)` once per step. Do not call `.item()` inside the loop.
- **Compilation:** `mx.compile` the train step with fixed shapes. Bucket boards by `(H,W,N)`; avoid dynamic shapes.
- **Gradients:** `nn.value_and_grad(model, loss_fn)` for parameter grads; `mx.value_and_grad` for Langevin `z` grads.
- **EMA:** `tree_map(lambda t, c: m*t + (1-m)*c, target_params, online_params)`; update only matching shapes.
- **Checkpoints:** `model.save_weights("model.safetensors")`, optimizer state via `tree_flatten` + `mx.save_safetensors`, plus a JSON sidecar with step/config/seed.
- **Memory:** `mx.set_memory_limit(48 * 2**30)`, `mx.set_wired_limit(...)`; monitor `mx.get_peak_memory()`; call `mx.clear_cache()` between phases.
- **Mixed precision:** fp32 default (bf16 was not faster in the preliminary benchmark and complicates the energy); test bf16 after G2.
- **Determinism:** `mx.random.seed(seed)`; record the seed; expect small nondeterminism from Metal.
- **No float64:** not supported on the GPU; use float32 for all geometry/loss math.

### 10.3 Training loop

```
for batch in loader:
    loss, grads = compiled_step(params, batch)
    optimizer.update(model, grads)
    ema_update()
    mx.eval(loss, model.parameters(), optimizer.state)
    log every N steps
    validate every epoch
    checkpoint on clean-pass / energy, not loss alone
```

### 10.4 Preliminary throughput

Measured on this machine (MLX 0.32.4, synthetic tensors, forward+backward):

| Model | Tokens | Batch | ms/step | Boards/s | Peak |
|---|---:|---:|---:|---:|---:|
| 10.8M, 6 layers, d=384 | 81 | 64 | 21 | ~3,000 | 5.8 GB |
| 25.5M, 8 layers, d=512 | 121 | 64 | 56 | ~1,140 | 15.5 GB |

These exclude data loading, the fine decoder, and DRC. Use them to size experiments, not to promise end-to-end speed.

---

## 11. Changes from the original brief (v0.1)

| Original brief | v0.2 | Why |
|---|---|---|
| `(L,H,W,C)` with net ID as an integer | Per-net edge flow on a 3D graph | Net IDs are ordinal; connectivity is edge-based |
| Cell occupancy only | Edge occupancy + via edges | Paths and DRC are edge properties |
| 0.25 mm grid | 0.5 / 0.25 / 0.0762 mm hierarchy | 0.25 mm cannot represent 6 mil rules |
| Flat 8-layer transformer over all cells | CNN + patch transformer at L0 | 254k tokens is infeasible; 42 patch tokens is Enso-scale |
| Soft DRC penalties only | Hard masks + soft surrogates + L2 legalizer + KiCad DRC | Soft penalties cannot guarantee legality |
| Pure latent Langevin → final copper | Langevin → path extraction → legalizer → repair | Latent optimization alone does not produce DRC-clean geometry |
| "Hundreds of milliseconds" | Seconds to minutes initially | Honest target; optimize later |
| Fine-tune Enso Sudoku weights | Train from scratch; reuse the recipe | Modality/shape mismatch |
| All nets simultaneously | Global EBM all-net plan + net-conditional refinement | Per-net dense tensors at fine resolution are too large |
| Cloud/H200 assumptions | Local M5 Pro + MLX | User constraint; measured throughput supports it |

---

## 12. Open technical questions

1. **Flow relaxation:** Is `sigmoid(flow)` + conservation residual enough, or do we need a differentiable min-cost-flow solver? Test both at G2.
2. **Steiner trees:** A single root + multiple sinks is a flow, but the extracted path is a union of root-to-sink paths, not a minimum Steiner tree. Is that good enough, or do we need a Steiner relaxation?
3. **Negative samples:** JEPA trains on positives. Do we need corrupted routes (broken, shifted, shorted) as explicit high-energy negatives? Enso did not, but routing has a much larger invalid space.
4. **Energy calibration:** How do we ensure the energy correlates with DRC violations across board families? Measure rank correlation; if it is poor, the Langevin signal is weak.
5. **Clearance at coarse resolution:** L0/L1 cannot resolve 6 mil clearance. How much clearance information must be passed down to L2? A distance-to-obstacle channel may be enough.
6. **Layer assignment:** Should vias be decided at L0 or L1? Early via decisions are hard to revise; test both.
7. **Diff pairs:** Route as two coupled nets with a skew penalty, or route independently and length-match later? Start later.
8. **Power planes:** How to represent zone/plane intent without teaching the model to route copper pours? Keep it out of the learned problem initially.
9. **Evaluation:** Is clean-pass rate on 20 real boards enough to claim generalization, or do we need 100+? Start with 20–50 and report confidence intervals.
10. **MLX limits:** Are there ops we need that MLX lacks (e.g., sparse solves, complex eigendecomposition)? Prefer conv/local formulations; fall back to CPU NumPy for one-off geometry.
