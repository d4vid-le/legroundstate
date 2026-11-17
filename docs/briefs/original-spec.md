# Original brief — v0.1

**Source:** Summary of a prior agent conversation, provided by David Le on 2026-11-17.
**Status:** Input document, kept verbatim for traceability. Superseded by `docs/SPEC.md` v0.3.

> The v0.3 spec changes the representation, grid resolution, architecture, energy,
> inference, and integration assumptions. It also replaces the “Enso reimplementation”
> framing with an independent, clean-room EBM. See `docs/SPEC.md` §11 and
> `docs/DECISIONS.md` ADR-0003…ADR-0005, ADR-0010.

---

## Technical Specification: "PCB-Enso" — Latent-Space Energy-Based Autorouter

### Objective

Adapt the Enso Energy-Based Model (EBM) architecture—originally built for discrete constraint satisfaction (Sudoku)—to perform simultaneous, non-autoregressive global trace routing for printed circuit boards (PCBs) like an ESP32 QT Py breakout.

### 1. Problem Formulation & Tensor Representation

Unlike standard LLMs that generate traces sequentially (token-by-token), the PCB-Enso model evaluates the entire board simultaneously in continuous space.

**Board Tensor Shape:** `(L, H, W, C)`

- **L (Layers):** Copper layer count (e.g., 2-layer or 4-layer board).
- **H, W (Grid Resolution):** Discretized board dimensions (e.g., 0.25 mm spatial grid resolution).
- **C (Channels):**
  - **Channel 0:** Obstacles & Keep-outs (Component courtyards, mounting holes, ESP32 antenna clearance zone).
  - **Channel 1:** Pin / Pad Terminals (Source and destination coordinates mapped to specific Net IDs).
  - **Channel 2:** Routing State (Current Net ID assignment per cell: 0 for empty space, or positive integers for specific nets like GND, 3V3, SDA, SCL).

### 2. Core Architecture Components (Mirrored from Enso)

- **Context Encoder (SudokuEncoder equivalent):** An 8-layer Transformer with spatial/pin-aware positional encoding. Takes the unrouted board tensor (obstacles, pads, netlist constraints) and encodes it into a context representation vector: `z_context`.
- **Target Encoder:** Same transformer architecture processing fully routed ground-truth board layouts. Updated via Exponential Moving Average (EMA) to prevent representation collapse.
- **Latent Predictor (LatentPredictor equivalent):** A 3-layer MLP mapping `(z_context, z) -> z_pred`, where `z ~ N(0, I)` is a continuous latent noise vector.
- **Decoder:** A lightweight 4-layer Transformer decoding `z` into per-cell trace logits across layers, while hard-enforcing fixed pin terminals.

### 3. Differentiable PCB Loss Function (`E(z)`)

To replace Sudoku row/col/box uniqueness rules, the energy landscape is defined by physical Design Rule Checks (DRC):

```
E(z) = λ1 L_energy + λ2 L_connectivity + λ3 L_clearance + λ4 L_vias + λ5 L_antenna
```

- **L_energy:** L2 distance between predicted latent representation and target representation (`||z_pred - z_target||²`).
- **L_connectivity:** Penalizes broken paths (ensures all pads belonging to the same Net ID have a continuous chain of adjacent cells).
- **L_clearance:** Evaluated via 2D spatial convolutions; penalizes adjacent cells belonging to different Net IDs to prevent short-circuits.
- **L_vias:** Discourages excessive layer transitions.
- **L_antenna:** Assigns an infinite energy penalty to any trace entering the restricted antenna keep-out zone of the ESP32 module.

### 4. Inference via Langevin Dynamics

Instead of greedy decoding:

- Initialize latent variable chains from Gaussian noise: `z0 ~ N(0, I)`.
- Decode `z` into a candidate 3D trace grid.
- Compute the board's total energy `E(z)` using the differentiable DRC loss function.
- Update `z` iteratively via gradient descent with temperature annealing (Langevin dynamics):

```
z <- z - η ∇_z E + noise
```

- Select the lowest-energy chain and convert it into discrete copper traces.

### 5. Integration Workflow with KiCad

- **Agent Setup:** The agent places components, defines net names, and sets design rules inside KiCad.
- **Export:** The agent exports the board state, pad coordinates, and netlist (via KiCad's Python API `pcbnew` or `.dsn` export).
- **Inference:** The PCB-Enso model runs Langevin optimization in latent space (~hundreds of milliseconds) to resolve all traces simultaneously without short-circuits.
- **Import:** The agent receives the final route coordinates and executes `pcbnew.CreateTrack()` to draw the traces back into the `.kicad_pcb` file.
