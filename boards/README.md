# Boards

## `qt-py-esp32-s2/` — reference reconstruction

A personal, non-production reconstruction of the **Adafruit QT Py ESP32-S2** (product 5325,
Rev C) in KiCad, used here as the held-out routing benchmark.

- **Upstream project:** https://github.com/d4vid-le/qt-py-esp32-s2-experiment
- **Snapshot commit:** `73ff5db45dbd12750827df8c329c6ddfcb41cfe0`
- **Board:** 4-layer, 17.78 × 20.701 mm, 34 nets, 159 pads
- **Final state:** 0 unconnected / 0 DRC errors, **reference-assisted** signal routing;
  independent routing peaked at 9 unconnected (2-layer) / 8 (4-layer targeted)
- **License:** the reference design is Adafruit's, CC BY-SA 3.0; see the project README.
  Adafruit's Eagle/PDF/image files are not committed; `reference/` is gitignored and
  fetched by the project's `scripts/fetch-reference.sh`.

### Why is it a plain directory instead of a submodule?

The copy in this workspace had its own git history and a public remote. To keep the
monorepo self-contained without nested-repo warnings, the nested `.git` was renamed to
`.git-disabled` (gitignored). All commits are preserved locally and on the upstream remote.

To restore the standalone repo:

```bash
cd boards/qt-py-esp32-s2
mv .git-disabled .git
git status
```

### What to use it for

- **Gate G0:** parse/write/DRC round-trip fidelity.
- **Gate G4:** held-out signal-net routing test.
- **Evidence:** prior reports, DRC JSON, renders, and the board file itself.

### What not to do

- Do not train on this board before G4 is frozen.
- Do not modify the board in place to make a route pass; work on copies.
- Do not redistribute Adafruit's reference files (they are gitignored).
