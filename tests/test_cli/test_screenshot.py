"""`screenshot` — capture the viewport (or a target Control) to a file.

Requires a real renderer (`godot_display` marker) — `--headless` produces a
64x64 dummy buffer with no pixel data."""

from __future__ import annotations

from pathlib import Path

import pytest

from .conftest import CLIRunner, find_node

PNG_HEADER = b"\x89PNG\r\n\x1a\n"
JPEG_SOI = b"\xff\xd8\xff"


@pytest.mark.godot_project("simple-ui")
@pytest.mark.godot_display
async def test_screenshot_writes_png(cli: CLIRunner, tmp_path: Path) -> None:
    out = tmp_path / "shot.png"
    result = cli("screenshot", "--filename", str(out))
    assert out.read_bytes()[: len(PNG_HEADER)] == PNG_HEADER
    assert str(out) in result.stdout


@pytest.mark.godot_project("simple-ui")
@pytest.mark.godot_display
async def test_screenshot_jpeg_format(cli: CLIRunner, tmp_path: Path) -> None:
    out = tmp_path / "shot.jpeg"
    cli("screenshot", "--format", "jpeg", "--filename", str(out)).assert_ok()
    assert out.read_bytes()[: len(JPEG_SOI)] == JPEG_SOI


@pytest.mark.godot_project("simple-ui")
@pytest.mark.godot_display
async def test_screenshot_target_ref_crops(cli: CLIRunner, tmp_path: Path) -> None:
    snap = cli("snapshot", "--json").json()["snapshot"]
    submit_ref = find_node(snap, name="SubmitButton")["ref"]

    full_path = tmp_path / "full.png"
    crop_path = tmp_path / "submit.png"
    cli("screenshot", "--filename", str(full_path)).assert_ok()
    cli("screenshot", submit_ref, "--filename", str(crop_path)).assert_ok()

    # Cropped to a button rect — must be smaller than the full viewport image.
    assert crop_path.stat().st_size < full_path.stat().st_size
    assert crop_path.read_bytes()[: len(PNG_HEADER)] == PNG_HEADER


@pytest.mark.godot_project("simple-ui")
@pytest.mark.godot_display
async def test_screenshot_json_emits_filename(cli: CLIRunner, tmp_path: Path) -> None:
    out = tmp_path / "shot.png"
    payload = cli("screenshot", "--filename", str(out), "--json").json()
    assert payload == {"filename": str(out)}
