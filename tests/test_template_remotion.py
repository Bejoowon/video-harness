import json, re
from pathlib import Path

T = Path(__file__).resolve().parents[1] / "skills/video-harness-setup/assets/episode-template-remotion"


def test_package_pins_remotion_4():
    pkg = json.loads((T / "package.json").read_text(encoding="utf-8"))
    assert pkg["dependencies"]["remotion"].startswith("4.")
    assert pkg["dependencies"]["@remotion/cli"] == pkg["dependencies"]["remotion"]


def test_parts_use_theme_only():
    for f in (T / "src/parts").glob("*.tsx"):
        text = f.read_text(encoding="utf-8")
        assert not re.findall(r"#[0-9a-fA-F]{6}\b", text), f.name
        assert "theme" in text, f.name


def test_root_registers_episode_portrait():
    root = (T / "src/Root.tsx").read_text(encoding="utf-8")
    assert 'id="Episode"' in root and "calculateMetadata" in root
    assert "theme.canvas.width" in root and "theme.canvas.height" in root
