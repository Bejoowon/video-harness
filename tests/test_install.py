# tests/test_install.py
"""한 줄 설치 스크립트가 `skills/` 아래의 스킬을 **전부** 설치하는지 본다.

임시 HOME과 `VIDEO_HARNESS_SOURCE`로 돌리므로 인터넷도, 실제 홈 디렉터리도 건드리지 않는다.
"""

import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]
INSTALL_SH = ROOT / "install.sh"
INSTALL_PS1 = ROOT / "install.ps1"
SKILL_NAMES = sorted(p.parent.name for p in (ROOT / "skills").glob("*/SKILL.md"))

BASH = shutil.which("bash")
needs_bash = pytest.mark.skipif(
    sys.platform.startswith("win") or BASH is None, reason="bash가 없어 건너뜀 (Windows 포함)"
)


def _run(home: Path, *args):
    env = {**os.environ, "HOME": str(home), "VIDEO_HARNESS_SOURCE": str(ROOT)}
    return subprocess.run(
        [BASH, str(INSTALL_SH), *args],
        env=env,
        capture_output=True,
        text=True,
        timeout=180,
    )


@needs_bash
def test_install_sh_installs_every_skill(tmp_path):
    result = _run(tmp_path, "--claude")
    assert result.returncode == 0, result.stdout + result.stderr

    installed = tmp_path / ".claude" / "skills"
    assert len(SKILL_NAMES) >= 2, SKILL_NAMES
    for name in SKILL_NAMES:
        assert (installed / name / "SKILL.md").is_file(), (name, result.stdout)


@needs_bash
def test_install_sh_final_message_lists_both_trigger_phrases(tmp_path):
    result = _run(tmp_path, "--claude")
    for name in SKILL_NAMES:
        assert name in result.stdout, name
    assert "영상 하네스 세팅을 시작해줘" in result.stdout
    assert "레퍼런스 찾아줘" in result.stdout


@needs_bash
def test_install_sh_backs_each_skill_up_separately_on_reinstall(tmp_path):
    assert _run(tmp_path, "--claude").returncode == 0
    marker = tmp_path / ".claude" / "skills" / SKILL_NAMES[0] / "직접_적은_메모.md"
    marker.write_text("지우면 안 된다", encoding="utf-8")

    assert _run(tmp_path, "--claude").returncode == 0

    backups = sorted(p.name for p in (tmp_path / ".claude" / "skills-backup").iterdir())
    for name in SKILL_NAMES:
        assert any(b.startswith(f"{name}-") for b in backups), (name, backups)
    moved = [p for p in (tmp_path / ".claude" / "skills-backup").rglob("직접_적은_메모.md")]
    assert moved, "예전 설치본을 지우지 않고 옮겨 두어야 한다"
    assert not marker.exists()


@needs_bash
def test_install_sh_leaves_no_pycache_behind(tmp_path):
    assert _run(tmp_path, "--claude").returncode == 0
    assert not list((tmp_path / ".claude" / "skills").rglob("__pycache__"))


@needs_bash
def test_install_sh_can_target_codex_only(tmp_path):
    assert _run(tmp_path, "--codex").returncode == 0
    assert (tmp_path / ".codex" / "skills" / SKILL_NAMES[0] / "SKILL.md").is_file()
    assert not (tmp_path / ".claude" / "skills").exists()


def test_install_ps1_also_walks_the_skills_folder():
    """Windows는 실제로 돌려 보지 못했으므로, 스킬 이름을 박아 두지 않았는지만 본다."""
    text = INSTALL_PS1.read_text(encoding="utf-8")
    for name in SKILL_NAMES:
        assert f'"{name}"' not in text, name
    assert "SKILL.md" in text
    assert "영상 하네스 세팅을 시작해줘" in text
    assert "레퍼런스 찾아줘" in text


def test_install_sh_does_not_hard_code_a_skill_name():
    text = INSTALL_SH.read_text(encoding="utf-8")
    for name in SKILL_NAMES:
        assert f'SKILL="{name}"' not in text, name
    assert "VIDEO_HARNESS_SOURCE" in text
