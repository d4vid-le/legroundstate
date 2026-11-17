#!/usr/bin/env bash
# Verify the local toolchain for LeGroundstate.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

KICAD_CLI="${KICAD_CLI:-/Applications/KiCad/KiCad.app/Contents/MacOS/kicad-cli}"
BOARD="boards/qt-py-esp32-s2/rebuild/qt-py-esp32-s2.kicad_pcb"
ok=0

printf 'LeGroundstate environment check\n'
printf 'workspace: %s\n\n' "$ROOT"

printf '%-22s' "macOS:"
sw_vers -productVersion

printf '%-22s' "hardware:"
system_profiler SPHardwareDataType 2>/dev/null | awk -F': ' '/Chip:|Memory:/{printf "%s ", $2} END{print ""}'

printf '%-22s' "free disk:"
df -h "$ROOT" | awk 'NR==2{print $4}'

printf '%-22s' "uv:"
if command -v uv >/dev/null 2>&1; then uv --version; else printf 'MISSING\n'; ok=1; fi

printf '%-22s' "python (system):"
python3 --version 2>&1 || true

printf '%-22s' "KiCad CLI:"
if [ -x "$KICAD_CLI" ]; then
  "$KICAD_CLI" version
else
  printf 'MISSING at %s\n' "$KICAD_CLI"
  ok=1
fi

printf '%-22s' "MLX venv:"
if [ -x "$ROOT/.venv/bin/python" ]; then
  "$ROOT/.venv/bin/python" -c 'import mlx.core as mx; print(mx.__version__ if hasattr(mx, "__version__") else "installed")' 2>/dev/null || {
    printf 'venv exists, mlx not installed (run: uv sync)\n'
    ok=1
  }
else
  printf 'missing .venv (run: uv sync)\n'
  ok=1
fi

printf '%-22s' "reference board:"
if [ -f "$BOARD" ]; then
  nets=$(grep -o '(net "[^"]*")' "$BOARD" | sort -u | wc -l | tr -d ' ')
  segs=$(grep -c '(segment' "$BOARD" || true)
  vias=$(grep -c '(via' "$BOARD" || true)
  printf '%s nets, %s segments, %s vias\n' "$nets" "$segs" "$vias"
else
  printf 'MISSING at %s\n' "$BOARD"
  ok=1
fi

printf '\n'
if [ "$ok" -eq 0 ]; then
  printf 'OK: toolchain looks ready.\n'
else
  printf 'Some checks failed. See docs/PLAN.md Phase 0.\n'
fi
exit "$ok"
