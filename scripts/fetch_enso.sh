#!/usr/bin/env bash
# Fetch the pinned upstream Enso reference for local study.
#
# Enso has NO LICENSE file upstream; default copyright applies.
# The source is gitignored and must not be redistributed from this repository.
# We use it only as a reference for a clean-room MLX implementation.
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

COMMIT="8013c8f95e9e4402faaa91c99835c4ccedc54ef9"
URL="https://codeload.github.com/MVPandey/Enso/zip/${COMMIT}"
DEST="third_party/enso"
EXPECTED_README_SHA="3864dbae595f19c1853b8afbbab83d29e07aceac34a3031a7f759cab0b03a25e"

force=0
if [ "${1:-}" = "--force" ]; then force=1; fi

if [ -d "$DEST" ] && [ "$force" -ne 1 ]; then
  printf 'Already present: %s\n' "$DEST"
  printf 'Use --force to replace it.\n'
  exit 0
fi

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

printf 'Fetching Enso at %s\n' "$COMMIT"
curl -fL --retry 3 -o "$TMP/enso.zip" "$URL"

printf 'Extracting...\n'
unzip -q "$TMP/enso.zip" -d "$TMP/src"
SRC="$(find "$TMP/src" -maxdepth 1 -mindepth 1 -type d | head -1)"
if [ -z "$SRC" ]; then
  printf 'Could not find extracted source directory.\n' >&2
  exit 1
fi

actual="$(shasum -a 256 "$SRC/README.md" | awk '{print $1}')"
if [ "$actual" != "$EXPECTED_README_SHA" ]; then
  printf 'README checksum mismatch.\n  expected: %s\n  actual:   %s\n' "$EXPECTED_README_SHA" "$actual" >&2
  printf 'Upstream may have changed. Verify manually before using as a reference.\n' >&2
  exit 1
fi

rm -rf "$DEST"
mv "$SRC" "$DEST"

printf 'Installed: %s\n' "$DEST"
printf '\n'
printf 'LICENSE: none upstream. Do not copy this code into the repository.\n'
printf 'Use it as a reference for a clean-room MLX implementation; cite the upstream project.\n'
