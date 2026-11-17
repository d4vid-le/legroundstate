# Naming

**Status:** Decided — **LeGroundstate** (2026-11-17)
**Display name:** LeGroundstate
**Repository / Python package / CLI:** `legroundstate`

---

## Decision

**LeGroundstate** — “LeGroundstate: energy-based routing for KiCad.”

The name combines:

- **“Le”** — David Le's name; personal ownership of the project.
- **“Groundstate”** — the low-energy state an EBM searches for, and the ground plane of a PCB.

It is distinctive, memorable, and does not use the Enso name or imply affiliation.

### Styling rules

| Context | Form |
|---|---|
| Prose, docs, paper title | **LeGroundstate** |
| GitHub repository | `legroundstate` |
| Python package / imports | `legroundstate` |
| CLI | `legroundstate` |
| Model artifacts | `legroundstate-l0-*.safetensors` |
| Dataset names | `legroundstate-l0-v0` |

Avoid all-caps `LEGROUNDSTATE` and the spaced `Le Groundstate` in code. In a wordmark,
“Le” may be lighter than “Groundstate,” but the repo stays lowercase.

## Why not the alternatives

| Name | Why not |
|---|---|
| **Etch** | Strong PCB-native name, but generic and doesn't convey the EBM/energy angle |
| **Innerlayer** | Clever PCB + latent-layer pun, but long and sounds like a stackup tool |
| **Ariadne** | Great labyrinth metaphor, but `ariadne-routing` already exists |
| **Weft** | Evocative, but obscure and no PCB/EBM hint |
| **Copperflow** | Descriptive, but an existing `copperflow` repo |

LeGroundstate keeps the energy/ground-plane meaning and adds a personal signature.

## Rename executed (2026-11-17)

- [x] GitHub repository: `d4vid-le/legroundstate` (public)
- [x] Workspace folder: `legroundstate/`
- [x] Python package: `src/legroundstate/`, imports `legroundstate.*`
- [x] `pyproject.toml`: `name = "legroundstate"`
- [x] README title, docs, scripts
- [x] Model/dataset naming convention
- [x] Provenance note: formerly working title `PCB-Enso`; no affiliation with Enso/Kona
- [x] MIT license for code; CC BY 4.0 for docs

## Rules

- The model is a **JEPA-style latent EBM**, not “Enso”.
- In docs, say “inspired by Enso/Kona” only in research/provenance sections.
- Never use “Enso” in the project name, package, CLI, or model artifact names.
- In a paper/blog, cite Enso and Kona; do not imply endorsement.
