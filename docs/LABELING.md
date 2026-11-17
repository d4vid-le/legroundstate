# Human Labeling

**Status:** Plan
**Owner of labels:** David Le (domain expert)
**Purpose:** Turn human judgment into a small, high-value dataset that teaches the energy model
what “good routing” means beyond “DRC-clean.”

---

## 1. Why human labels

A classical router can produce a DRC-clean route that is still bad engineering:

- unnecessarily long detours;
- too many vias;
- traces crowded around a sensitive net;
- poor layer balance;
- acute angles / acid traps;
- differential pairs with avoidable skew;
- power/return paths that will be painful later;
- routes that are technically legal but hard to inspect or rework.

DRC cannot rank those. A human can. The labels are how the EBM learns a **quality landscape**,
not just a legality checker.

## 2. What to label — and what not to

**Label:**

1. **Accept / reject / needs fix** — would you put this route on a board you care about?
2. **Quality 1–5** — overall engineering quality, independent of DRC.
3. **Difficulty 1–5** — how hard was this board to route? Useful for curriculum and analysis.
4. **Issue tags** — clearance risk, via spam, detour, acute angle, length/skew, layer imbalance,
   current/width, keep-out, aesthetic, other.
5. **Preference pairs** — given two DRC-clean routes for the same board, which is better?
6. **Corrections** — optional: edit the route in KiCad and save the diff. This is the most
   valuable but slowest label.

**Do not label:**

- DRC violations (the engine already does this, exactly).
- Connectivity (the engine already does this).
- Net names or pad coordinates (parsed from the board).
- “Looks nice” without a reason; use the issue tags.

### 2.1 Board curation (before route review)

Not every collected board belongs in the dataset. Before labeling routes, curate the raw
boards:

| Question | Why |
|---|---|
| Is the license permissive enough to use? | Legal provenance; see `data/README.md` |
| Is the netlist complete and parseable? | A broken netlist cannot be routed or scored |
| Does the board load and DRC-run in KiCad? | Baseline sanity |
| Is it a useful routing example? | Density, layer count, net classes, package variety |
| Is it duplicate/near-duplicate of another board? | Avoid leakage and wasted labels |
| What is the family and difficulty? | Splits and curriculum |

Decision: **include / exclude / needs cleanup**. Record the reason. This is faster than route
review and prevents the reviewer from spending time on unusable boards.

Add fields to the `boards` table: `curated` (0/1), `curator`, `curation_notes`, `curated_at`.

## 3. Label schema

SQLite is the source of truth; JSONL exports feed training.

```sql
-- One row per candidate board/route
CREATE TABLE boards (
  id            TEXT PRIMARY KEY,
  family        TEXT NOT NULL,
  seed          INTEGER,
  source        TEXT,              -- synthetic | pcbench | qtpy | ...
  license       TEXT,
  pcb_path      TEXT,
  render_path   TEXT,
  drc_json      TEXT,
  auto_metrics  TEXT,              -- JSON: wirelength, vias, skew, ...
  curated       INTEGER DEFAULT 0, -- 0 pending, 1 include, -1 exclude
  curator       TEXT,
  curation_notes TEXT,
  curated_at    TEXT,
  created_at    TEXT
);

-- One row per human review
CREATE TABLE reviews (
  id            INTEGER PRIMARY KEY,
  board_id      TEXT NOT NULL REFERENCES boards(id),
  reviewer      TEXT NOT NULL,
  decision      TEXT NOT NULL,     -- accept | reject | needs_fix | uncertain
  quality       INTEGER,           -- 1..5
  difficulty    INTEGER,           -- 1..5
  confidence    INTEGER,           -- 1..3
  notes         TEXT,
  time_ms       INTEGER,
  label_version TEXT NOT NULL,
  created_at    TEXT
);

CREATE TABLE issues (
  review_id     INTEGER REFERENCES reviews(id),
  tag           TEXT NOT NULL,
  severity      INTEGER,           -- 1..3
  net           TEXT,
  bbox          TEXT,              -- JSON [x0,y0,x1,y1] in mm
  note          TEXT
);

CREATE TABLE preferences (
  id            INTEGER PRIMARY KEY,
  board_id      TEXT NOT NULL,
  route_a       TEXT NOT NULL,
  route_b       TEXT NOT NULL,
  preferred     TEXT NOT NULL,     -- a | b | tie
  reviewer      TEXT NOT NULL,
  confidence    INTEGER,
  time_ms       INTEGER,
  created_at    TEXT
);
```

**Rules:**

- Append-only. Corrections are new rows with a new `label_version`.
- One reviewer ID per person; no personal data beyond that.
- Every label records the time spent; labeling speed is a design metric.
- Export to `data/labels/<version>/{reviews,preferences,issues}.jsonl` with a manifest hash.

## 4. Review tool

A local web app, no cloud, runs on either Mac.

**Screen:**

```
┌───────────────────────────────┬──────────────────────────────┐
│  bare board  │  routed board  │  net list + lengths/vias     │
│  (toggle)    │  (DRC overlay) │  DRC violations              │
│                               │  auto metrics                │
│   zoom/pan, layer toggles     │  issue tags                  │
├───────────────────────────────┴──────────────────────────────┤
│  A accept  R reject  F needs-fix  U uncertain  ←/→ next      │
│  Quality 1–5   Difficulty 1–5   Confidence 1–3   Notes       │
└──────────────────────────────────────────────────────────────┘
```

**Requirements:**

- Keyboard-first: `A` accept, `R` reject, `F` needs fix, `U` uncertain, `1–5` quality,
  `Shift+1–5` difficulty, `←/→` previous/next, `Z` undo, `Space` toggle overlay.
- Show bare vs. routed side by side; toggle layer visibility; highlight a net on hover.
- DRC overlay: red for shorts/clearance, yellow for warnings; click to zoom.
- Blind A/B mode: hide which router produced each route; randomize left/right.
- Auto-advance after a decision; progress bar; resume where you left off.
- Save immediately; SQLite WAL; no data loss on refresh/crash.
- Export button and a `--review` CLI flag.
- No login, no network access outside localhost.

**Implementation:** FastAPI + SQLite + a single static HTML/JS page. Images from
`kicad-cli pcb render` or SVG export; DRC from `kicad-cli pcb drc --format json`.

## 5. Workflow

```
generator / classical router
        │
        ▼
auto-filter: unconnected, DRC errors, degenerate routes
        │
        ▼
agent pre-score: wirelength, vias, layer balance, acute angles, skew, congestion
        │
        ▼
human queue (prioritized by uncertainty / disagreement / family)
        │
        ▼
review → accept/reject/quality/issues
        │
        ▼
SQLite → JSONL export → training + evaluation
        │
        └──► active learning: model uncertainty selects the next batch
```

**The human never sees the obvious failures.** The agent filters DRC-broken, unconnected, and
degenerate candidates first. The human's time goes to borderline, high-information boards.

## 6. Quality control

- **Hidden duplicates:** 5% of the queue is a duplicate of an earlier board. Measure
  self-consistency. If it drops below ~85%, the rubric or UI is unclear.
- **Calibration set:** 50 boards reviewed once, then again after a week. Track drift.
- **Rubric:** one page with 2–3 positive and negative examples per issue tag.
- **Time tracking:** flag boards that take > 2 minutes; they are either hard or the UI is slow.
- **Blind review:** the reviewer should not know which method produced a route.
- **DRC is not optional:** a route that fails DRC cannot be “accepted” regardless of looks.
- **One reviewer for now.** If a second reviewer joins, report Cohen's κ on the calibration set.

## 7. Volume and time

| Stage | Boards | Time estimate |
|---|---:|---:|
| Calibration | 50 | ~45 min |
| Gold evaluation set | 100 | 1.5–2.5 hours |
| Preference pairs | 100–200 | 1.5–3 hours |
| Optional expansion | 300+ | later, after label consistency is proven |

Start with **50 calibration + 100 gold**. Do not attempt 10k human labels. Human labels are
the gold set; synthetic/classical labels are the bulk pretraining set. Expand to 300+ only if
the first 100 are consistent and actually improve the model.

## 8. How labels are used

### 8.1 Supervised flow labels (no human)

Classical-router routes provide the bulk per-edge labels. These are cheap and DRC-verified but
teach imitation, not quality.

### 8.2 Quality regression / rejection

Train an auxiliary head or energy term to predict `quality` (1–5) or `accept` probability. The
energy should be lower for accepted, high-quality routes.

### 8.3 Preference ranking (the valuable part)

Given two DRC-clean routes A and B for the same board, the human says which is better. Train the
energy with a margin or Bradley–Terry loss:

```
L_pref = mean(max(0, margin + E(rejected) − E(preferred)))
```

or

```
L_BT = −mean(log σ(E(rejected) − E(preferred)))
```

This directly shapes the energy landscape around human judgment, which is exactly what an EBM
is for. It also gives us a way to evaluate the energy independently of the decoder.

### 8.4 Active learning

Prioritize boards where:

- the model's energy is uncertain across Langevin chains (high variance);
- the model and the classical router disagree;
- DRC has near-misses (clearance just above the limit);
- the board family is underrepresented.

### 8.5 Evaluation

The gold set is frozen and family-split. Report:

- accept rate;
- mean quality;
- preference accuracy (does the energy rank the human-preferred route lower?);
- correlation between energy and human quality;
- DRC clean pass (engine-checked).

## 9. Splits and leakage

- Split by **design family**, not by board.
- The QT Py is held out entirely until G4 is frozen.
- Human-labeled boards can appear in train/val; never in the frozen test set.
- Keep a `labels_v1` manifest with file hashes; never silently edit old labels.

## 10. Tooling plan

**Phase 1 deliverables:**

- `tools/review/` — FastAPI + SQLite + static frontend.
- `legroundstate label` CLI — import boards, export labels.
- `scripts/collect_boards.py` — download/scan candidate boards, record source + license.
- `scripts/curate.py` — import a board into the review queue; run DRC/tensor sanity.
- `scripts/export_labels.py` — immutable JSONL export + manifest hash.

**Acceptance criteria:**

- 50 boards labeled in under 45 minutes by one person.
- Keyboard-only flow for the common case.
- Board curation and route review are separate modes.
- Blind A/B mode works.
- Crash-safe; resume works.
- Export produces JSONL + a manifest hash.
- No network access beyond localhost.

## 11. Privacy and publication

- Reviewer identified by a stable ID, not a real name, in the public release.
- Notes are reviewed before publication; remove anything personal.
- Publish labels only with the reviewer's consent.
- The dataset card states who labeled, when, the rubric, and the QC results.

## 12. First labeling session (after Phase 1)

1. Generate 200 synthetic boards with 8–16 nets, 2 layers.
2. Auto-filter to ~120 DRC-clean candidates.
3. Agent pre-scores and selects 50 for calibration.
4. Review with the rubric; measure time and self-consistency.
5. Adjust the rubric/UI; freeze `labels_v1`.
6. Only then expand to the 100-board gold set.
