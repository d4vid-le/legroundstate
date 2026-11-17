# Two-Mac setup (M5 Pro + M4 Pro over Thunderbolt 5)

**Status:** Plan — not yet configured or benchmarked
**Purpose:** Use the second Mac as a data/labeling/evaluation worker, with optional
data-parallel training.

---

## 1. Hardware

| Role | Machine | Memory | Notes |
|---|---|---|---|
| **Primary** | Mac mini M5 Pro (18-core CPU) | 64 GB | Training, inference, model development |
| **Worker** | Mac mini M4 Pro | 64 GB | Data generation, labeling server, DRC/eval, optional data-parallel training |
| **Link** | Thunderbolt 5 cable | — | Data plane for MLX ring / RDMA; SSH control over Ethernet/Wi-Fi |

Both machines have unified memory; each must fit its own model replica. Data-parallel training
does **not** pool memory like a single 128 GB machine.

## 2. Recommended first use: task parallel, not distributed training

The data pipeline is the bottleneck, not the neural step. The highest-value split is:

```
M4 Pro:  generate synthetic boards → classical route → DRC filter → labeling queue
M5 Pro:  train the EBM → evaluate → iterate
```

This requires only SSH + a shared folder or `rsync`; no distributed training complexity.

**Do this first.** It turns a 1–3 day label-generation job into a parallel background job while
training continues on the M5.

## 3. Optional: data-parallel training with MLX

MLX supports distributed data parallelism:

```python
from mlx.utils import tree_map


def all_reduce_grads(grads):
    world = mx.distributed.init()
    if world.size() == 1:
        return grads
    return tree_map(lambda x: mx.distributed.all_sum(x) / world.size(), grads)
```

Thunderbolt ring setup (from the MLX docs):

```bash
# Once: discover the Thunderbolt ring and print/setup the hostfile.
mlx.distributed_config --verbose --hosts <m5-host>,<m4-host> --backend ring

# Launch the same script on both hosts.
mlx.launch --hosts <m5-ip>,<m4-ip> scripts/train_l0.py
```

Requirements:

- SSH access to both hosts over Ethernet/Wi-Fi (not necessarily Thunderbolt).
- Thunderbolt cable(s) connected; the ring backend uses them for the data plane.
- The Python binary and script at the **same path** on both hosts.
- `--auto-setup` needs password-less sudo; otherwise run the printed commands manually.
- Both hosts must be awake (use `caffeinate`) and reachable.

Expected gain: **~1.5–1.8×**, not 2×, because of synchronization and the slower M4 Pro. Measure
before committing to it. Do not use it for the first milestone.

## 4. Shared data and code

Options, in order of preference:

1. **External SSD** (Thunderbolt/USB) mounted at the same path on both machines.
2. **Network share** over Thunderbolt bridge/Ethernet.
3. **`rsync` shards** before each run (simple, robust, no shared filesystem).

The dataset manifest and label DB should have one owner. Put the **labeling SQLite DB on the
M4** (where the review server runs) and export immutable JSONL shards for training on the M5.

## 5. Setup checklist

```bash
# On both machines
scripts/check_env.sh
uv sync
uv run python scripts/bench_mlx.py --quick

# SSH (control plane)
ssh <m4-host> 'hostname; sw_vers -productVersion'
ssh <m5-host> 'hostname; sw_vers -productVersion'

# Thunderbolt ring (from the M5, after both are reachable by SSH)
mlx.distributed_config --verbose --hosts <m5-host>,<m4-host> --backend ring

# Smoke test (future script)
mlx.launch --hosts <m5-ip>,<m4-ip> scripts/dist_smoke.py
```

- [ ] Both machines on the same macOS major version (or close).
- [ ] Same `uv`/Python 3.13 paths; `uv run` works on both.
- [ ] Passwordless SSH keys (no host prompts).
- [ ] Thunderbolt cable is a **data** cable, not charge-only.
- [ ] Thunderbolt bridge disabled if using the ring backend (the config tool handles this).
- [ ] Firewall allows SSH on the local network only.
- [ ] Sleep disabled during runs (`caffeinate -dimsu`).
- [ ] Shared SSD mounted at the same path, or `rsync` script ready.
- [ ] Label DB backed up.
- [ ] Both machines have adequate cooling/ventilation.

## 6. Failure modes

| Symptom | Likely cause | Fix |
|---|---|---|
| `mlx.launch` cannot connect | SSH key/host prompt/firewall | `ssh` manually; add key; allow local SSH |
| Ring setup fails | Thunderbolt bridge enabled / wrong cable | Disable bridge; use a data cable; rerun config |
| Different Python paths | `uv` env created at different paths | Recreate at the same path or use `--print-python` |
| One host sleeps mid-run | macOS energy settings | `caffeinate`; disable sleep |
| Slow training, no speedup | Sync overhead > compute | Use task-parallel mode instead |
| Data not found on worker | Different paths | Shared SSD or `rsync` |

## 7. Security

- Local network only; no port forwarding, no public SSH.
- SSH keys, not passwords.
- No secrets in the repo; `.env` is gitignored.
- The review server binds to `127.0.0.1` (or the local LAN only if needed).
- Do not expose the labeling DB or model checkpoints to the internet.

## 8. Decision

- **Base plan:** single M5 Pro. It is sufficient for G0–G4.
- **M4 Pro:** use for data generation, labeling, DRC/eval from Phase 1.
- **Distributed training:** optional stretch, only if single-node Phase 3 training is too slow.
  Benchmark before adopting.
