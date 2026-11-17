#!/usr/bin/env python
"""Check local Markdown links and fenced code blocks.

Skips vendored/third-party directories. Intended for CI and local pre-commit.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path

SKIP_PARTS = {'.git', '.venv', 'third_party', 'boards', 'dist', 'build', 'node_modules'}
LINK_RE = re.compile(r'\]\(([^)]+)\)')


def markdown_files(root: Path) -> list[Path]:
    return [path for path in root.rglob('*.md') if not any(part in SKIP_PARTS for part in path.parts)]


def main() -> int:
    root = Path(__file__).resolve().parents[1]
    missing: list[tuple[Path, str]] = []
    unbalanced: list[Path] = []

    for md in markdown_files(root):
        text = md.read_text(encoding='utf-8')
        if text.count('```') % 2:
            unbalanced.append(md)

        for target in LINK_RE.findall(text):
            if target.startswith(('http://', 'https://', '#', 'mailto:')):
                continue
            local = target.split('#', 1)[0]
            if local and not (md.parent / local).exists():
                missing.append((md, target))

    for md, target in missing:
        print(f'missing link: {md.relative_to(root)} -> {target}')
    for md in unbalanced:
        print(f'unbalanced fences: {md.relative_to(root)}')

    if missing or unbalanced:
        return 1

    print(f'OK: checked {len(markdown_files(root))} Markdown files')
    return 0


if __name__ == '__main__':
    sys.exit(main())
