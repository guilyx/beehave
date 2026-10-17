"""Copy the brand files that the documentation site serves from ``.branding/``.

The site is built from ``docs/`` and cannot reference files outside it, so the
logo, favicons, design tokens and social preview are copied to
``docs/assets/brand/``. ``.branding/`` stays the source of truth:
``tests/unit/test_brand_assets.py`` fails as soon as a copy differs from its
source.

Run it from anywhere after changing a brand file::

    python3 scripts/sync_brand_assets.py          # refresh the copies
    python3 scripts/sync_brand_assets.py --check  # exit 1 if a copy is stale
"""

from __future__ import annotations

import argparse
import shutil
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
SOURCE_DIR = ROOT / ".branding"
TARGET_DIR = ROOT / "docs" / "assets" / "brand"

# Name under docs/assets/brand/ -> path under .branding/.
ASSETS: dict[str, str] = {
    "tokens.css": "tokens/tokens.css",
    "mark.svg": "logo/mark.svg",
    "favicon.svg": "logo/favicon.svg",
    "favicon-32.png": "logo/favicon-32.png",
    "apple-touch-icon.png": "logo/apple-touch-icon.png",
    "social-preview.png": "social/social-preview.png",
}


def stale_assets(source_dir: Path = SOURCE_DIR, target_dir: Path = TARGET_DIR) -> list[str]:
    """List the copies that are missing or differ from their source.

    Args:
        source_dir: The brand folder, normally ``.branding/``.
        target_dir: The folder the site serves, normally ``docs/assets/brand/``.

    Returns:
        Names (keys of ``ASSETS``) whose copy is missing or not byte-identical.
    """
    stale = []
    for name, source in ASSETS.items():
        target = target_dir / name
        if not target.is_file() or target.read_bytes() != (source_dir / source).read_bytes():
            stale.append(name)
    return stale


def sync(source_dir: Path = SOURCE_DIR, target_dir: Path = TARGET_DIR) -> list[str]:
    """Copy every stale asset from the brand folder to the site.

    Args:
        source_dir: The brand folder, normally ``.branding/``.
        target_dir: The folder the site serves, normally ``docs/assets/brand/``.

    Returns:
        Names of the files that were written.
    """
    target_dir.mkdir(parents=True, exist_ok=True)
    written = stale_assets(source_dir, target_dir)
    for name in written:
        shutil.copyfile(source_dir / ASSETS[name], target_dir / name)
    return written


def main(argv: list[str] | None = None) -> int:
    """Run the command line.

    Args:
        argv: Arguments without the program name; ``None`` reads ``sys.argv``.

    Returns:
        The exit status: 1 when ``--check`` finds a stale copy, else 0.
    """
    parser = argparse.ArgumentParser(
        description="Copy the brand files that the documentation site serves from .branding/."
    )
    parser.add_argument("--check", action="store_true", help="report stale copies, write nothing")
    args = parser.parse_args(argv)
    if args.check:
        stale = stale_assets()
        for name in stale:
            print(f"stale: docs/assets/brand/{name} (source: .branding/{ASSETS[name]})")
        return 1 if stale else 0
    for name in sync():
        print(f"copied .branding/{ASSETS[name]} -> docs/assets/brand/{name}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
