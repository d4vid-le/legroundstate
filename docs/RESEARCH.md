# LeGroundstate — Research Notes

**Date:** 2026-11-17
**Project name:** LeGroundstate (repo/package/CLI: `legroundstate`)
**Purpose:** Ground the project in prior work, the EBM/JEPA recipe, human preference learning, and the QT Py evidence.

---

## 1. The Enso recipe, in detail

Enso is an independent replication of Logical Intelligence's **Kona 1.0**, a Sudoku EBM. Kona reported 96.2% on hard Sudoku in ~313 ms; frontier LLMs reportedly managed ~2% combined. Enso reports **96.6% puzzle accuracy** with a 36.5M-parameter model.

### 1.1 Architecture

| Component | Detail |
|---|---|
| Context encoder | 8-layer Transformer, `d_model=512`, 8 heads, Sudoku-aware row/col/box positional encoding |
| Target encoder | Same architecture, EMA of the context encoder, no gradients |
| Predictor | 3-layer MLP, hidden 1024, maps `(z_context, z) → z_pred` |
| Decoder | 4-layer Transformer, `d_cell=128`, 8 heads, per-cell digit logits, hard-enforces clues |
| Latent `z` | 256-d, `z = L2_normalize(z_encoder(z_target)) + noise` |
| Energy | `||z_pred − z_target||²` |
| Inference | Langevin: 50–100 steps, 4–16 chains, temperature annealing |
| Training | 9M puzzles, 20 epochs, batch 2048 |

### 1.2 Training lessons that matter more than the architecture

From `training-log.md`:

1. **VICReg on the wrong tensor collapses the model.** Apply it to `z_context`, not `z_pred`.
2. **`z` must be informative but not a lookup table.** Enso's early `z` had L2 norm ~144 vs. noise ~11; the decoder ignored the energy. L2-normalizing and reducing noise to ~1:1 SNR fixed it.
3. **Inference energy must match training energy.** Enso's first Langevin runs optimized `||z_pred||²` while training used `||z_pred − z_target||²`; Langevin made accuracy worse. Self-consistency (decode → re-encode → compare) fixed it.
4. **Constraints must appear during training.** Adding the Sudoku constraint penalty to the training loss is what made Langevin help (+1.0%).
5. **Checkpoint on the target metric, not the loss.** Lowest energy saved collapsed models.
6. **Scale helped, but the recipe mattered more.** 7.4M → 36.5M params produced +13.1% puzzle accuracy at the same data; the Langevin gain stayed ~+1%.

### 1.3 What is genuinely novel here

Enso's domain is a 9×9 discrete grid with exact labels and a small, fixed rule set. PCB routing is:

- **Geometric:** continuous coordinates, widths, clearances, 45° angles.
- **Hierarchical:** global allocation and local detail.
- **Data-poor:** no 9M-board dataset with exact labels.
- **Verifiable:** KiCad DRC gives an exact, external pass/fail.

The research question is whether the latent EBM recipe survives that transition. The negative space is much larger, the labels are noisier, and the output must be geometrically legal. That is the interesting part.

### 1.4 What we can and cannot use from Enso

Enso has **no license**, so this is a clean-room implementation. The legal distinction is simple:

| Category | Can we use it? | Notes |
|---|---|---|
| Ideas, algorithms, architecture | **Yes** | Not copyrightable; cite the source |
| Published hyperparameters / results | **Yes** | Facts; cite |
| Training lessons (VICReg, latent norm, energy alignment) | **Yes** | Summarize in our own words; cite |
| Source code, comments, docstrings, identifiers | **No** | Do not copy |
| README prose, figures, tables | **No** | Do not copy; write our own |
| Model weights | **No** | None needed; train from scratch |
| Project name “Enso” | **No** | Use our own name |

We implement from the public method descriptions and the JEPA papers (I-JEPA, IRED,
JEPA-Reasoner), not by translating Enso's PyTorch files. See `docs/PROVENANCE.md` for the
process and release checklist.

---

## 2. Prior art: classical routing

| Idea | What it does | Relevance |
|---|---|---|
| **Lee/maze routing** | BFS on a grid from source to target | The detailed router's core; our L2 |
| **A\*** | Heuristic shortest path | Fast per-net routing; baseline |
| **Rip-up and reroute** | Remove blocking nets, re-route them | Repairs sequential commitment; our repair loop |
| **Negotiated congestion (PathFinder)** | Iteratively price overused edges; allow temporary violations | The classical answer to global congestion; our L0 capacity energy is a soft analogue |
| **Freerouting** | Open-source Java autorouter; DSN flow | Baseline; already used on the QT Py (2.5.0) |
| **KRT / OrthoRoute** | KiCad-integrated routers | External baselines via PCBWorld |
| **Steiner trees** | Minimum tree connecting multi-terminal nets | The structure our flow should approximate |

**Lesson:** classical routers are strong. A learned model should either (a) produce a better global plan than negotiated congestion, or (b) be much faster, or (c) handle constraints that are hard to encode. "End-to-end pixels" is not automatically better.

---

## 3. Prior art: learned routing

| Work | Approach | Takeaway |
|---|---|---|
| **CNN routability prediction + A\*** (Zhang et al.) | Predict routing regions, then A* | Learned guidance + classical detail is a proven pattern; this is our hybrid's ancestor |
| **Deep reinforcement learning for global routing** | Policy over a grid graph | Sample efficiency and reward design are hard; boards generalize poorly |
| **MCTS + DRL PCB routing** | MCTS rollouts guided by a policy | Search + learning beats either alone; supports our Langevin + repair loop |
| **PCBench** | 1,182-board dataset, PCB-RDL JSON, RL environment | The closest public benchmark; use for evaluation and fine-tuning |
| **PCBWorld** | KiCad-native Gymnasium environment, DRC-scored, synthetic + 679 real boards | The strongest engine-grounded benchmark; adopt its metrics and protocol |
| **DeepPCB / Quilter** | Commercial physics/RL routers | Strong vendor claims (e.g., 92/99 DRC-clean one-attempt on PCBWorld-Bench); treat as context, not verified baselines |

### 3.1 PCBWorld numbers (from the paper/repo)

D3-A: 99 small open-source PCBench boards. Metrics: clean pass (CP), potential gain (Pot.), routability (Rout.), time.

| Method | CP ↑ | Pot. ↑ | Rout. ↑ | Time (s) ↓ |
|---|---:|---:|---:|---:|
| Reference (original traces) | 1.00 | 23.16 | 1.00 | — |
| Freerouting | 0.80 | 22.71 | 0.91 | 7.09 |
| KRT | 0.74 | 20.00 | 0.94 | 0.65 |
| LLM agent, GPT-5.4 | 0.65 | 19.42 | 0.91 | 231.15 |
| PPO transformer | 0.86 | 21.46 | 0.95 | 1.83 |

**Implications for us:**

- A clean pass requires fully connected **and** zero DRC errors. This is the right bar.
- Freerouting is fast (7 s) and strong (0.80 CP). Beating it is a real research result, not a baseline formality.
- The best learned policy (PPO) is 0.86 CP at 1.83 s, but it uses KiCad's interactive router as the action space, not pixel generation. This supports a hybrid/engine-grounded design.
- The reference is 1.00 CP; our QT Py target is 0/0, which is the same "clean pass" idea.

### 3.2 PCBench

- Public dataset of open-source PCB designs with `raw.kicad_pcb`, `processed.kicad_pcb`, `final.json` (PCB-RDL), metadata, and an RL environment.
- PCBWorld uses a 1,182-board KiCad 9 conversion; public release counts vary by version.
- Licenses are per-board; a manifest is required before training or redistribution.

### 3.3 Human-in-the-loop routing and preference learning

DRC is necessary but not sufficient. A clean route can still be bad engineering. The relevant
literature is human preference learning:

| Work | Idea | Relevance |
|---|---|---|
| **Christiano et al., 2017** | Deep RL from human preferences: learn a reward from pairwise comparisons | The template for A/B route preferences |
| **Bradley–Terry model** | `P(A ≻ B) = σ(score(A) − score(B))` | A principled loss for ranking routes by energy |
| **RLHF / preference optimization** | Use human comparisons to shape a model's objective | We use it to shape the energy, not an LLM policy |
| **Active learning** | Query the human on the most informative examples | Label the uncertain/disagreement cases, not random boards |

For an EBM, this is a natural fit: the energy is already a scalar quality function. Human
comparisons tell it which of two DRC-clean routes should have lower energy. The loss is simple:

```
L_pref = max(0, margin + E(rejected) − E(preferred))
```

The research question is whether preference-calibrated energy generalizes better than
DRC-only energy. This is RQ7 in the plan. See `docs/LABELING.md` for the human workflow.

---

## 4. Prior art: JEPA and energy-based reasoning

| Work | Idea | Relevance |
|---|---|---|
| **I-JEPA** (Assran et al., 2023) | Predict representations of masked targets, not pixels | The context/target/predictor pattern |
| **IRED** (Du et al., 2024) | Iterative reasoning as energy diffusion | Langevin/energy optimization for reasoning |
| **JEPA-Reasoner** (Liu et al., 2025) | Decouple latent reasoning from token generation | Supports non-autoregressive latent reasoning |
| **Kona 1.0** | EBM for Sudoku, test-time latent optimization | The direct inspiration; 96.2% hard Sudoku |
| **Enso** | Open replication of Kona | The recipe we are adapting |

**Caveat:** the Enso README's links for IRED and JEPA-Reasoner are imprecise. Correct references are in §8.

---

## 5. The QT Py evidence

The prior project is a careful reconstruction, not an independent route. The distinction matters:

| Claim | Reality |
|---|---|
| "0 unconnected / 0 DRC" | True for the final board, but the signal routing is Adafruit's reference geometry |
| "Independent routing" | Peaked at 9 unconnected (2-layer) / 8 (4-layer targeted); never reached 0 |
| "4-layer" | The source is 4-layer; the earlier 2-layer premise was wrong |
| "Routing is the bottleneck" | Supported: the failure was global allocation and pour fragmentation, not local pathfinding |

### 5.1 Failure anatomy

- **GND pour fragmentation:** 14 islands; stitching vias could not bridge islands separated by signal tracks.
- **Power/signal coupling:** the reference +3V3/GND geometry assumed a different signal route; substituting it produced 17–32 shorts and clearance errors.
- **Sequential commitment:** Freerouting left 24 unconnected on the first try; targeted 4-layer attempts reached 8; each fix displaced another net.
- **Tooling friction:** `pcbnew.LoadBoard()` unreliable outside KiCad; Eagle importer maps user layers to `UNDEFINED`; MCP `add_zone` unimplemented. The S-expression workaround is the reliable path.

### 5.2 What a better router must do

1. **Allocate globally before detailing.** Decide which nets get which layers/corridors.
2. **Treat power/ground as a plane problem**, not traces to be routed one by one.
3. **Revise early decisions.** Rip-up and reroute is mandatory; a single forward pass will not suffice.
4. **Verify with the engine.** DRC, not a proxy.
5. **Report failures precisely.** "9 unconnected" is more useful than "mostly routed."

---

## 6. Data landscape

| Source | Size | Labels | License | Use |
|---|---:|---|---|---|
| Synthetic generator (ours) | unlimited | exact, DRC-filtered | ours | Pretraining, ablations |
| Human gold set (David) | 300–1,000 | quality, difficulty, issues, preferences | ours (consent) | Fine-tune, preference ranking, eval |
| QT Py | 1 | reference route | CC BY-SA 3.0 (Adafruit) | Held-out test |
| PCBench | ~1,182 (varies) | routed boards | per-board | Eval / fine-tune |
| PCBWorld D3 | 679 real | routed boards, DRC-scored | code BSD-3; boards per-project | External benchmark |
| KiCad demos | tens | routed boards | per-project | Sanity checks |
| Open hardware (Adafruit/SparkFun/etc.) | hundreds–thousands | routed boards | mostly CC BY-SA / MIT / CERN-OHL | Eval, with manifest |

**The bottleneck is not architecture; it is trustworthy labels.** Every machine label must be
DRC-verified and license-tracked; every human label must be consistent and versioned. A
10k-board synthetic set with exact labels plus a 500-board human gold set is worth more than
100k scraped boards with unknown legality and no quality signal.

### 6.1 Two-Mac MLX distributed compute

MLX supports distributed data parallelism over a Thunderbolt ring:

- `mx.distributed.init()`, `all_sum`, and `tree_map` average gradients across hosts.
- `mlx.distributed_config --backend ring` discovers the TB ring and writes a hostfile.
- `mlx.launch --hosts ...` runs the same script on each host.

For our workload, **task parallelism is more valuable than data parallelism**: the M4 Pro
generates boards and runs DRC while the M5 Pro trains. Distributed training is an optional
1.5–1.8× stretch, not a requirement. See `docs/notes/two-mac.md`.

---

## 7. Design implications

1. **Use a routing graph and per-net flow, not per-cell net IDs.** Connectivity and DRC are edge properties.
2. **Work coarse-to-fine.** 0.5 mm for global reasoning, 0.25 mm for corridors, 0.0762 mm for DRC-exact detail.
3. **Keep the EBM at the coarse level.** It cannot resolve 6 mil geometry; it can allocate corridors and layers.
4. **Use a classical legalizer and KiCad DRC.** The model proposes; the engine disposes.
5. **Train on synthetic boards first.** Real boards are for evaluation and fine-tuning, not pretraining.
6. **Hold out the QT Py.** Otherwise G4 is meaningless.
7. **Measure clean pass, not "looks routed."** Fully connected + zero DRC.
8. **Benchmark against Freerouting.** It is fast and strong; a model that loses to it is a result, not a failure.
9. **Use human labels for quality, not legality.** DRC is the legality oracle; the human is the taste oracle. Preference pairs calibrate the energy.

---

## 8. References

### EBM / JEPA

- Assran et al., *I-JEPA: Self-Supervised Learning from Images with a Joint-Embedding Predictive Architecture*, CVPR 2023. https://arxiv.org/abs/2301.08243
- Du et al., *Learning Iterative Reasoning through Energy Diffusion*, ICML 2024. https://arxiv.org/abs/2406.11179
- Liu et al., *JEPA-Reasoner: Decoupling Latent Reasoning from Token Generation*, 2025. https://arxiv.org/abs/2512.19171
- Logical Intelligence, *Kona 1.0 Sudoku demo*. https://sudoku.logicalintelligence.com/
- Logical Intelligence, *EBM vs. LLMs: 96% vs. 2%*. https://logicalintelligence.com/blog/energy-based-model-sudoku-demo
- Enso (MVPandey), commit `8013c8f`. https://github.com/MVPandey/Enso

### PCB routing

- Zhang & Zheng, *Towards Automated PCB Routing: Leveraging Machine Learning and Heuristic Techniques*, Iowa State University. https://dr.lib.iastate.edu/server/api/core/bitstreams/baa06fe6-541d-4f4a-888d-94f3083cd518/content
- PCBench. https://github.com/PCBench/PCBench
- Song et al., *PCBWorld: A Benchmark Environment for Engine-Grounded PCB Design Automation*, KDD 2026 Workshop. https://arxiv.org/abs/2607.05915
- PCBWorld code. https://github.com/LGAI-Research/PCBWorld
- Freerouting. https://github.com/freerouting/freerouting
- Quilter, *The PCB Autorouter Was the Right Idea. Completion Rate Was the Wrong Target.* https://www.quilter.ai/blog/pcb-autorouter-was-the-right-idea
- DeepPCB benchmark claim (vendor). https://deeppcb.ai/benchmark/pcbworld-bench-deeppcb-results/

### Human preference / active learning

- Christiano et al., *Deep Reinforcement Learning from Human Preferences*, NeurIPS 2017. https://arxiv.org/abs/1706.03741
- Bradley & Terry, *Rank Analysis of Incomplete Block Designs: I. The Method of Paired Comparisons*, Biometrika 1952. https://doi.org/10.1093/biomet/39.3-4.324
- Settles, *Active Learning Literature Survey*, 2009. https://burrsettles.com/pub/settles.activelearning.pdf

### KiCad / tooling

- KiCad IPC API. https://dev-docs.kicad.org/en/apis-and-binding/ipc-api/
- kicad-python (`kipy`). https://pypi.org/project/kicad-python/
- MLX. https://github.com/ml-explore/mlx
- MLX docs. https://ml-explore.github.io/mlx/
- MLX distributed (ring / Thunderbolt). https://ml-explore.github.io/mlx/build/html/usage/distributed.html
- MLX launching distributed jobs. https://ml-explore.github.io/mlx/build/html/usage/launching_distributed.html

### The reference board

- Adafruit QT Py ESP32-S2 product. https://www.adafruit.com/product/5325
- Adafruit QT Py ESP32-S2 PCB source. https://github.com/adafruit/Adafruit-QT-Py-ESP32-S2-PCB
- Our reconstruction. https://github.com/d4vid-le/qt-py-esp32-s2-experiment
