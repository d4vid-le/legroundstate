# Third-party components and attribution

LeGroundstate's original code is MIT-licensed. This file lists components that
carry different licenses or attribution requirements.

## `boards/qt-py-esp32-s2/` — QT Py ESP32-S2 reconstruction

- **Reference design:** Adafruit QT Py ESP32-S2 (Product 5325, Rev C).
- **Reference license:** CC BY-SA 3.0 Unported.
- **Upstream reference:** https://github.com/adafruit/Adafruit-QT-Py-ESP32-S2-PCB
- **Reconstruction:** https://github.com/d4vid-le/qt-py-esp32-s2-experiment
- **Attribution:** The reference design is Adafruit's work, licensed CC BY-SA 3.0.
  Adafruit's Eagle/PDF/image source files are **not** included in this repository;
  they are fetched locally by the reconstruction project's `scripts/fetch-reference.sh`.
- **Scope:** The snapshot is included as a held-out benchmark fixture. Its license
  applies to that directory; the root MIT license does not override it.

## Enso (research reference only — not included)

- **Upstream:** https://github.com/MVPandey/Enso
- **License:** none (default copyright). No source code, prose, figures, or weights
  from Enso are included in this repository.
- **Use:** research inspiration only; see `docs/PROVENANCE.md`.

## PCBench / PCBWorld (not included)

- **PCBench:** https://github.com/PCBench/PCBench — per-board licenses; a manifest is
  required before training or redistribution.
- **PCBWorld:** https://github.com/LGAI-Research/PCBWorld — code BSD-3-Clause; the
  boards retain their original licenses.
- **Scope:** no datasets are committed. Any released dataset will include a per-board
  license manifest and a data card.

## Python dependencies

- **MLX** — MIT. https://github.com/ml-explore/mlx
- **NumPy** — BSD-3-Clause.
- **Pydantic** — MIT.
- **Typer** — MIT.
- **Rich** — MIT.
- **pytest / ruff** — MIT.

Dependency licenses are resolved by the package manager; see `uv.lock`.

## KiCad

- **KiCad** — GPLv3. https://www.kicad.org/
- The project invokes KiCad's CLI and file formats; it does not link KiCad code.

## No fabrication

Nothing in this repository is fabrication-ready. Boards are experimental and require
human electrical review before manufacturing.
