#!/usr/bin/env python
"""Reproducible MLX throughput benchmark for PCB-Enso.

This measures synthetic tensors only: it is an upper bound on the neural
compute, not an end-to-end PCB model or data-pipeline benchmark.

Usage:
    uv run python scripts/bench_mlx.py
    uv run python scripts/bench_mlx.py --quick
"""

from __future__ import annotations

import argparse
import json
import time
from dataclasses import asdict, dataclass

import mlx.core as mx
import mlx.nn as nn
import mlx.optimizers as optim
from mlx.utils import tree_flatten


@dataclass
class Result:
    name: str
    params_m: float
    batch: int
    tokens: int
    ms_per_step: float
    tokens_per_s: float
    boards_per_s: float
    peak_gb: float


def _time(fn, warmup: int, iters: int) -> float:
    for _ in range(warmup):
        mx.eval(fn())
    t0 = time.perf_counter()
    for _ in range(iters):
        mx.eval(fn())
    return (time.perf_counter() - t0) / iters


def bench_matmul(size: int = 4096, iters: int = 5) -> list[dict]:
    out = []
    for dtype in (mx.float32, mx.bfloat16):
        a = mx.random.normal((size, size)).astype(dtype)
        b = mx.random.normal((size, size)).astype(dtype)
        seconds = _time(lambda: a @ b, warmup=2, iters=iters)
        out.append(
            {
                "op": f"matmul {size}^3",
                "dtype": str(dtype).split(".")[-1],
                "ms": round(seconds * 1e3, 3),
                "tflops": round(2 * size**3 / seconds / 1e12, 2),
            }
        )
    return out


class Block(nn.Module):
    def __init__(self, d: int, heads: int):
        super().__init__()
        self.attn = nn.MultiHeadAttention(d, heads)
        self.ln1 = nn.LayerNorm(d)
        self.ln2 = nn.LayerNorm(d)
        self.ff = nn.Sequential(nn.Linear(d, 4 * d), nn.GELU(), nn.Linear(4 * d, d))

    def __call__(self, x):
        h = self.ln1(x)
        x = x + self.attn(h, h, h)
        return x + self.ff(self.ln2(x))


class Encoder(nn.Module):
    def __init__(self, d: int, heads: int, layers: int):
        super().__init__()
        self.blocks = [Block(d, heads) for _ in range(layers)]
        self.head = nn.Linear(d, d)

    def __call__(self, x):
        for block in self.blocks:
            x = block(x)
        return self.head(x)


def bench_transformer(
    name: str,
    *,
    batch: int,
    tokens: int,
    d: int,
    heads: int,
    layers: int,
    iters: int,
) -> Result:
    model = Encoder(d, heads, layers)
    x = mx.random.normal((batch, tokens, d))
    y = mx.random.normal((batch, tokens, d))
    params = model.parameters()
    optimizer = optim.AdamW(learning_rate=1e-4)

    def loss_fn(p, x, y):
        model.update(p)
        return mx.mean((model(x) - y) ** 2)

    value_and_grad = mx.value_and_grad(loss_fn)
    step = mx.compile(value_and_grad)

    def train():
        loss, grads = step(params, x, y)
        optimizer.update(model, grads)
        return loss

    mx.reset_peak_memory()
    seconds = _time(train, warmup=2, iters=iters)
    peak_gb = mx.get_peak_memory() / 1e9
    n_params = sum(p.size for _, p in tree_flatten(model.parameters()))
    mx.clear_cache()

    return Result(
        name=name,
        params_m=round(n_params / 1e6, 1),
        batch=batch,
        tokens=tokens,
        ms_per_step=round(seconds * 1e3, 2),
        tokens_per_s=round(batch * tokens / seconds, 0),
        boards_per_s=round(batch / seconds, 1),
        peak_gb=round(peak_gb, 1),
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--quick", action="store_true", help="Run only the two main configs")
    parser.add_argument("--iters", type=int, default=5)
    args = parser.parse_args()

    info = mx.device_info()
    print("MLX benchmark")
    print(f"  device: {info.get('device_name')} ({info.get('architecture')})")
    print(f"  memory: {info.get('memory_size', 0) / 1e9:.1f} GB")
    print()

    print("Matmul")
    print(json.dumps(bench_matmul(iters=args.iters), indent=2))
    print()

    configs = [
        ("L0-small", dict(batch=64, tokens=81, d=384, heads=6, layers=6)),
        ("L0-wide", dict(batch=64, tokens=121, d=512, heads=8, layers=8)),
    ]
    if not args.quick:
        configs.append(("L1-patch", dict(batch=32, tokens=378, d=384, heads=6, layers=6)))

    results = [bench_transformer(name, iters=args.iters, **cfg) for name, cfg in configs]
    print("Transformer train step (synthetic, mx.compile)")
    for r in results:
        print(json.dumps(asdict(r)))
    print()
    print("Note: synthetic forward+backward only. Excludes data loading, target encoder,")
    print("decoder, fine-grid geometry, and KiCad DRC. Treat as an upper bound.")


if __name__ == "__main__":
    main()
