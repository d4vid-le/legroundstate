# Naming

**Status:** Open — working title **Groundstate**, final name pending
**Date:** 2026-11-17

The project needs a name that is:

- **Not Enso.** We are not affiliated with the Enso/Kona work and should not imply otherwise.
- **Domain-native.** A PCB engineer should have a hint of what it does.
- **Research-credible.** It should sound like a method/project, not a generic SaaS product.
- **Short and unambiguous.** It becomes a repo, Python package, CLI, and model name.
- **Low-collision.** Avoid names already used by EDA, ML, or routing projects.
- **Trademark-clean enough for a public research repo.** Not a guarantee; a sanity check.

## Candidates

| Name | Rationale | Pros | Cons |
|---|---|---|---|
| **Groundstate** *(recommended)* | EBM inference finds a low-energy **ground state**; the board has a **ground plane**. | Strong double meaning; short; research-y; `groundstate route` reads well | Physics/quantum associations; not PCB-specific on its own |
| **Etch** | PCB copper is **etched** to leave traces. | Very short; domain-native; memorable; `etch route` | Generic verb; doesn't convey EBM/latent; possible etching-service confusion |
| **Innerlayer** | PCB **inner layers** + latent/hidden layers in a neural network. | Clever double meaning; unique; `innerlayer route` | Longer; sounds like a PCB stackup tool |
| **Ariadne** | Ariadne's thread guided Theseus through the labyrinth; traces are threads through a routing maze. | Evocative; strong metaphor | Longer; `ariadne-routing` already exists (network routing); literary |
| **Weft** | The crosswise thread in weaving; traces weave through the board. | Short; unique; evocative | Obscure; no PCB/EBM hint |
| **Copperflow** | Copper + flow-based routing representation. | Descriptive; fits the method | `copperflow` repo already exists; generic product sound |
| **Anneal** | Langevin/annealing is the inference method. | Method-native; short | Common word; many ML projects |

**Collision notes (quick GitHub search, 2026-11-17):**

- `copperflow` — existing repo (`kurpeeren/copperflow`, circuits-in-code).
- `ariadne-routing` — existing repo.
- `groundstate pcb`, `etch pcb routing`, `innerlayer pcb`, `weft routing` — no obvious PCB-routing collision in the quick search.

## Recommendation

**Groundstate** — “Groundstate: energy-based routing for KiCad.”

Why:

1. The EBM's whole idea is finding a low-energy state; “ground state” is the physics term for the minimum.
2. Every PCB has a ground plane; the name is native to the domain without being literal.
3. It reads well as a project, a model, and a CLI: **Groundstate**, the Groundstate EBM, `groundstate route`.
4. It does not ride on the Enso name or imply affiliation.
5. It leaves room for a method name: **Latent Flow EBM** (the model), **Groundstate** (the project).

Runner-up: **Etch** — if we want something shorter and more product-like.

## If Groundstate is chosen

Rename checklist:

- [ ] GitHub repository: `d4vid-le/groundstate`
- [ ] Workspace folder: `groundstate/` (use `mv` + `opencode.session_move` if needed)
- [ ] Python package: `src/groundstate/`, imports `groundstate.*`
- [ ] `pyproject.toml`: `name = "groundstate"`, script entry `groundstate`
- [ ] README title, badges, quick start
- [ ] All docs titles and cross-links
- [ ] `scripts/` names and help text
- [ ] Model artifact names: `groundstate-l0-*.safetensors`
- [ ] Dataset names: `groundstate-l0-v0`
- [ ] Environment variables: `GROUNDSTATE_*`
- [ ] Citation/acknowledgement: “formerly working title PCB-Enso”
- [ ] Add a `PROVENANCE.md` note that the rename avoids implying affiliation with Enso

Do the rename **once**, after the name is confirmed, in a single commit. Until then, docs
use “Groundstate (working title)” and the directory remains `pcb-enso`.

## Naming rules for the codebase

- The model is a **JEPA-style latent EBM**, not “Enso”.
- In docs, say “inspired by Enso/Kona” only in the research/provenance sections.
- Never use “Enso” in the project name, package name, CLI, or model artifact names.
- In a paper/blog, cite Enso and Kona; do not imply endorsement.
