# tests/test_preflight.py
from pathlib import Path
import preflight as p

MAC = {"os": "darwin", "arch": "arm64", "apple_silicon": True}
WIN = {"os": "windows", "arch": "AMD64", "apple_silicon": False}


def fake_which(found):
    return lambda name: f"/bin/{name}" if name in found else None


def fake_run(versions):
    def run(cmd, **kw):
        return 0, versions.get(Path(cmd[0]).name, "1.0.0")
    return run


def test_node_below_22_is_not_ok():
    tools = p.check_tools(fake_which({"node"}), fake_run({"node": "v20.11.0"}))
    assert tools["node"]["found"] and not tools["node"]["ok"]


def test_node_22_is_ok():
    tools = p.check_tools(fake_which({"node"}), fake_run({"node": "v22.23.1"}))
    assert tools["node"]["ok"]


def test_missing_tool_reported():
    tools = p.check_tools(fake_which(set()), fake_run({}))
    assert not tools["ffmpeg"]["found"] and not tools["ffmpeg"]["ok"]


def test_install_hint_per_platform():
    assert "brew install ffmpeg" in p.install_hint("ffmpeg", MAC)
    assert "winget" in p.install_hint("ffmpeg", WIN)


LINUX = {"os": "linux", "arch": "x86_64", "apple_silicon": False}


def test_install_hint_maps_bundled_tools_to_parent_package():
    # ffprobe/npx/npm은 독립 패키지가 아니다 — 상위 패키지(ffmpeg/node) 안내를 줘야 한다.
    for platform in (MAC, WIN, LINUX):
        assert p.install_hint("ffprobe", platform) == p.install_hint("ffmpeg", platform)
        assert p.install_hint("npx", platform) == p.install_hint("node", platform)
        assert p.install_hint("npm", platform) == p.install_hint("node", platform)
    assert "ffprobe" not in p.install_hint("ffprobe", MAC)
    assert "npx" not in p.install_hint("npx", MAC)


def test_audio_warning_for_usb_mic():
    out = "AKG Ara USB Microphone:\n  Default Output Device: Yes\n  Manufacturer: AKG\n"
    assert p.audio_output_warning(MAC, lambda cmd, **kw: (0, out)) is not None


def test_audio_warning_none_for_speakers_and_non_mac():
    out = "MacBook Pro Speakers:\n  Default Output Device: Yes\n"
    assert p.audio_output_warning(MAC, lambda cmd, **kw: (0, out)) is None
    assert p.audio_output_warning(WIN, lambda cmd, **kw: (0, "")) is None


def test_detects_existing_workspace(tmp_path):
    (tmp_path / "동네한바퀴" / "01_원본영상").mkdir(parents=True)
    report = p.build_report(tmp_path)
    assert report["looks_like_existing_workspace"] and not report["existing_config"]


def test_detect_editors_mac(tmp_path):
    drafts = tmp_path / "Movies/CapCut/User Data/Projects/com.lveditor.draft"
    drafts.mkdir(parents=True)
    editors = p.detect_editors(MAC, tmp_path)
    assert editors["capcut"]["drafts_dir"] == str(drafts)


def test_detect_editors_windows(tmp_path):
    local_appdata = tmp_path / "AppData/Local"
    drafts = local_appdata / "CapCut/User Data/Projects/com.lveditor.draft"
    drafts.mkdir(parents=True)
    program_files = tmp_path / "Program Files/Adobe"
    (program_files / "Adobe Premiere Pro 2025").mkdir(parents=True)

    editors = p.detect_editors(WIN, tmp_path, apps_root=local_appdata, system_apps_root=program_files)

    assert editors["capcut"]["installed"]
    assert editors["capcut"]["drafts_dir"] == str(drafts)
    assert editors["premiere"]["installed"]


def test_detect_editors_picks_latest_premiere(tmp_path):
    apps_root = tmp_path / "Applications"
    for name in ("Adobe Premiere Pro 2023", "Adobe Premiere Pro 2025", "Adobe Premiere Pro 2024"):
        (apps_root / name / "Contents").mkdir(parents=True)

    def fake_run(cmd, **kw):
        plist_target = cmd[2]
        return (0, "25.0.0") if "2025" in plist_target else (0, "0.0.0")

    editors = p.detect_editors(MAC, tmp_path, apps_root=apps_root, run_fn=fake_run)

    assert editors["premiere"]["installed"]
    assert editors["premiere"]["version"] == "25.0.0"


def test_node_with_unparsable_version_is_not_ok():
    """버전을 못 읽으면 `< 22` 관문을 건너뛰고 통과시키면 안 된다 (M8)."""
    tools = p.check_tools(fake_which({"node"}), fake_run({"node": "custom build"}))
    assert tools["node"]["found"] and not tools["node"]["ok"]
    assert tools["node"]["note"]
