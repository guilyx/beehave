"""The documentation site serves exact copies of the brand files in ``.branding/``."""

from __future__ import annotations

import importlib.util
from pathlib import Path
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from types import ModuleType

ROOT = Path(__file__).resolve().parents[2]
BRANDING = ROOT / ".branding"
SERVED = ROOT / "docs" / "assets" / "brand"
FIX = "run `python3 scripts/sync_brand_assets.py` to refresh the copies"


def _load_sync_script() -> ModuleType:
    path = ROOT / "scripts" / "sync_brand_assets.py"
    spec = importlib.util.spec_from_file_location("sync_brand_assets", path)
    assert spec is not None
    assert spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


SYNC = _load_sync_script()
ASSETS: dict[str, str] = SYNC.ASSETS


@pytest.mark.parametrize(("name", "source"), sorted(ASSETS.items()))
def test_served_copy_matches_its_source(name: str, source: str) -> None:
    copy = SERVED / name

    assert copy.is_file(), f"docs/assets/brand/{name} is missing; {FIX}"
    assert copy.read_bytes() == (BRANDING / source).read_bytes(), (
        f"docs/assets/brand/{name} differs from .branding/{source}; {FIX}"
    )


def test_every_served_file_has_a_source() -> None:
    served = {path.name for path in SERVED.iterdir()}

    assert served == set(ASSETS), f"unlisted files: {sorted(served - set(ASSETS))}"


def test_check_passes_on_the_repository(capsys: pytest.CaptureFixture[str]) -> None:
    assert SYNC.main(["--check"]) == 0
    assert capsys.readouterr().out == ""


def test_sync_copies_then_detects_drift(tmp_path: Path) -> None:
    assert sorted(SYNC.sync(target_dir=tmp_path)) == sorted(ASSETS)
    assert SYNC.stale_assets(target_dir=tmp_path) == []
    assert SYNC.sync(target_dir=tmp_path) == []

    (tmp_path / "tokens.css").write_text("/* edited by hand */\n", encoding="utf-8")
    (tmp_path / "mark.svg").unlink()

    assert sorted(SYNC.stale_assets(target_dir=tmp_path)) == ["mark.svg", "tokens.css"]
