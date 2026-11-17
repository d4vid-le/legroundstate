# MLX benchmark — 2026-11-17

**Machine:** Apple M5 Pro Mac mini (Mac17,16), 18-core CPU (6 super + 12 performance), 64 GB unified memory, `applegpu_g17s`, 424 GB free disk.
**Worker (not yet benchmarked):** Apple M4 Pro Mac mini, 64 GB, Thunderbolt 5.
**Software:** macOS 27.2.1, Python 3.13.15 (uv-managed), MLX 0.32.4, `mlx-metal` 0.32.4.
**Script:** `scripts/bench_mlx.py` (reproducible; synthetic tensors).

These are **preliminary synthetic benchmarks**, not end-to-end PCB model numbers. They exclude data loading, the full encoder/decoder, fine-grid decoding, and DRC.

## Raw results

### Matrix multiplication

| Dtype | Time | TFLOPS |
|---|---:|---:|
| float32 | 7.85 ms | 17.5 |
| bfloat16 | 4.94 ms | 27.8 |

### Transformer forward + backward (uncompiled, AdamW outside the timed eval)

| Config | Params | Time/step | Throughput | Peak memory |
|---|---:|---:|---:|---:|
| B=16, T=576, d=384, 6 layers | 10.6M | 81.4 ms | 113k tok/s | 14.4 GB |
| B=8, T=1024, d=512, 8 layers | 25.2M | 433.7 ms | 19k tok/s | 22.8 GB |
| B=8, T=2304, d=512, 8 layers | 25.2M | 1,544 ms | 12k tok/s | 51.1 GB |

### Transformer train step (`mx.compile`, forward + backward + optimizer update)

| Config | Params | Time/step | Throughput | Peak memory |
|---|---:|---:|---:|---:|
| B=64, T=81, d=384, 6 layers, fp32 | 10.8M | 21.4 ms | 243k tok/s, ~2,995 boards/s | 5.8 GB |
| B=64, T=121, d=512, 8 layers, fp32 | 25.5M | 56.1 ms | 138k tok/s, ~1,141 boards/s | 15.5 GB |

bf16 was also tested: ~21.1 ms and ~55.6 ms respectively. It was **not faster** than fp32
on this stack, so fp32 is the default for stability. The bf16 memory numbers were measured
before `mx.reset_peak_memory()` was added and are not comparable.

### Convolution

| Config | Time/step |
|---|---:|
| B=8, 128×128, 16→64 channels, 5 convs | 65.4 ms |
| B=8, 256×256, 16→64 channels, 5 convs | 55.0 ms |

(The 256×256 result is faster than 128×128, which is suspicious; likely cache/allocation noise. Re-measure with more iterations before using it for sizing.)

### Memory bandwidth

| Operation | Time | Bandwidth |
|---|---:|---:|
| 512 MB copy (`x + 1`) | 6.23 ms | 172 GB/s |

## Interpretation

1. **The Enso-scale coarse model is comfortably trainable locally.** A 10.8M transformer at 81 tokens × batch 64 runs at ~22 ms/step. At 10k boards × 20 epochs, the neural compute is on the order of minutes to a few hours, not days.
2. **A 25M model at 121 tokens is also viable** (~56 ms/step, 15.5 GB), but leaves less memory headroom for the full model and data pipeline.
3. **Flat attention over the fine grid is not viable.** T=2304 already hits 51 GB and 1.5 s/step. The fine grid must be convolutional/classical.
4. **bf16 is not faster on this stack.** Default to fp32 for stability; revisit after the model is correct.
5. **The data/label/DRC pipeline will dominate wall-clock.** Optimize the classical router and tensorizer, not just the neural step.

## Caveats

- The train-step benchmark measures `mx.eval(loss)`; the optimizer update is issued inside the compiled step but its parameter eval may be deferred. Treat boards/s as an upper bound.
- Peak memory is cumulative across runs in the same process; the per-run numbers are approximate.
- No gradient accumulation, checkpointing, or validation overhead.
- The actual model has a CNN stem, a target encoder (forward only), a decoder, and a larger output head; expect 2–5× the per-step cost.

## Recommended starting config

- L0: 0.5 mm, 36×42, 6×6 patches → 42 tokens.
- Model: 6 transformer layers, `d_model=384`, 6 heads, CNN stem 32–64 channels.
- Batch: 32–64, gradient accumulation to effective 128–256.
- fp32; `mx.compile` fixed shapes; `mx.set_memory_limit(48 GB)`.
- Checkpoint every epoch; validate clean-pass on B0/B2.
