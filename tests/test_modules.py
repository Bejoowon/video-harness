# tests/test_modules.py
from pathlib import Path
import harness_lib as h
import module_registry as m

MAC = {"os": "darwin", "arch": "arm64", "apple_silicon": True}
WIN = {"os": "windows", "arch": "AMD64", "apple_silicon": False}


def cfg(platform=MAC, **mods):
    c = h.default_config()
    c["platform"] = platform
    for k, v in mods.items():
        c["modules"][k] = v
    return c


def flat(steps):
    return " ".join(" ".join(s["cmd"]) if s["cmd"] else s["manual"] for s in steps)


def test_modules_for_order():
    c = cfg(voice={"mode": "local-mlx"}, sources=["own-footage", "stock"], handoff={"editor": "premiere"})
    mods = m.modules_for(c)
    assert mods[0] == "tools-venv" and mods[-1] == "fonts"
    assert {"hyperframes", "voice-local-mlx", "transcribe", "stock", "handoff-premiere"} <= set(mods)
    assert "higgsfield" not in mods and "remotion" not in mods


def test_transcribe_engine_by_platform(tmp_path):
    assert "mlx-whisper" in flat(m.plan("transcribe", tmp_path, cfg(MAC)))
    assert "faster-whisper" in flat(m.plan("transcribe", tmp_path, cfg(WIN)))


def test_local_mlx_skips_download_when_model_path_given(tmp_path):
    c = cfg(voice={"mode": "local-mlx", "model_path": "/somewhere/model"})
    assert "snapshot_download" not in flat(m.plan("voice-local-mlx", tmp_path, c))


def test_local_mlx_download_uses_xet_fallback_env(tmp_path):
    steps = m.plan("voice-local-mlx", tmp_path, cfg(voice={"mode": "local-mlx"}))
    dl = next(s for s in steps if s["cmd"] and "snapshot_download" in " ".join(s["cmd"]))
    assert dl["env"].get("HF_HUB_DISABLE_XET") == "1" and dl["background"] and dl["needs_network"]


def test_secrets_are_manual_never_commands(tmp_path):
    for module, c in [("voice-cloud", cfg(voice={"mode": "cloud"})),
                      ("higgsfield", cfg(higgsfield={"auth": "api-key"}))]:
        steps = m.plan(module, tmp_path, c)
        assert any(s["manual"] and ".env" in s["manual"] for s in steps)
        assert not any(s["cmd"] and "KEY" in " ".join(s["cmd"]) for s in steps)


def test_higgsfield_account_warns_about_credits(tmp_path):
    assert "크레딧" in flat(m.plan("higgsfield", tmp_path, cfg(higgsfield={"auth": "account"})))


def test_watch_module_uses_verified_repo_install_command(tmp_path):
    # 저장소(bradautomates/claude-video) README 확인 결과 실제 설치 명령은 -g(전역) 플래그가
    # 붙는다 — references/module-watch.md 작성 중 검증했다 (task-13-brief 해소 항목).
    assert "npx skills add bradautomates/claude-video -g" in flat(m.plan("watch", tmp_path, cfg()))


def test_tools_venv_pins_pycapcut_when_handoff_is_capcut(tmp_path):
    # to_capcut.py의 JSON 후처리는 pycapcut 0.0.3을 대상으로 작성·검증됐으므로 고정 버전으로
    # 설치해야 한다 (task-13 리뷰 반영).
    steps = m.plan("tools-venv", tmp_path, cfg(handoff={"editor": "capcut"}))
    assert f"pycapcut=={m.PYCAPCUT_VERSION}" in flat(steps)
    assert m.PYCAPCUT_VERSION == "0.0.3"


def test_tools_venv_skips_pycapcut_when_handoff_is_not_capcut(tmp_path):
    # "pycapcut" 자체는 쓰지 않는다 — pytest tmp_path가 이 테스트 이름을 따서 폴더를 만들기
    # 때문에 경로 안에 우연히 "pycapcut" 부분 문자열이 들어간다. 패키지 지정 표기("==")로
    # 구분한다.
    steps = m.plan("tools-venv", tmp_path, cfg(handoff={"editor": "premiere"}))
    assert "pycapcut==" not in flat(steps)


def test_venv_steps_windows_python_path(tmp_path):
    steps = m.venv_steps(tmp_path / ".venv", ["pyyaml"], uv_available=False, platform=WIN)
    assert "Scripts" in flat(steps)


def test_no_absolute_user_paths_in_plans(tmp_path):
    c = cfg(voice={"mode": "local-mlx"}, sources=["stock", "higgsfield"], higgsfield={"auth": "account"})
    for mod in m.modules_for(c):
        text = flat(m.plan(mod, tmp_path, c)).replace(str(tmp_path), "")
        assert "/Users/" not in text and "/opt/" not in text, mod


# --- 아래는 브리프의 모호성 해소 항목들(핸들러, download_pretendard, run_module)에 대한
# 추가 커버리지. 위 8개는 브리프의 "전문" 블록 그대로다. ---

import io
import json
import zipfile

import install_module as im


def test_venv_steps_uv_available_uses_uv():
    steps = m.venv_steps(Path("/tmp/x/.venv"), ["pyyaml"], uv_available=True, platform=MAC)
    assert steps[0]["cmd"][0] == "uv"
    assert steps[1]["cmd"][:2] == ["uv", "pip"]


def test_venv_steps_no_packages_skips_install_step():
    steps = m.venv_steps(Path("/tmp/x/.venv"), [], uv_available=False, platform=MAC)
    assert len(steps) == 1


def test_handoff_capcut_and_premiere_plan_the_same_shared_detect_step(tmp_path):
    # 설치 여부는 run 시점에만 알 수 있으므로 plan()은 감지 Step 하나만 내놓는다
    # (manual 안내를 여기서 조건부로 추가하지 않는다 — 죽은 분기 제거).
    c = cfg(handoff={"editor": "capcut"})
    capcut_steps = m.plan("handoff-capcut", tmp_path, c)
    premiere_steps = m.plan("handoff-premiere", tmp_path, c)
    assert len(capcut_steps) == 1 and capcut_steps[0]["manual"] is None
    assert len(premiere_steps) == 1 and premiere_steps[0]["manual"] is None
    assert capcut_steps[0]["title"] == premiere_steps[0]["title"] == m.HANDOFF_EDITOR_DETECT_TITLE
    assert capcut_steps[0]["cmd"] is not None


def _fake_zip_bytes() -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w") as zf:
        zf.writestr("public/static/Pretendard-Bold.otf", b"bold-bytes")
        zf.writestr("public/static/Pretendard-Medium.otf", b"medium-bytes")
        zf.writestr("public/static/Pretendard-ExtraBold.otf", b"extrabold-bytes")
    return buf.getvalue()


class _FakeResponse:
    def __init__(self, data: bytes):
        self._data = data

    def read(self) -> bytes:
        return self._data

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def _fake_opener(release_json: dict, zip_bytes: bytes):
    def opener(url):
        if url == im.PRETENDARD_RELEASE_API:
            return _FakeResponse(json.dumps(release_json).encode("utf-8"))
        return _FakeResponse(zip_bytes)

    return opener


def test_download_pretendard_extracts_only_bold_and_medium(tmp_path):
    release = {
        "assets": [
            {"name": "PretendardJP-1.3.9.zip", "browser_download_url": "https://example.test/jp.zip"},
            {"name": "Pretendard-1.3.9.zip", "browser_download_url": "https://example.test/pretendard.zip"},
        ]
    }
    dest = tmp_path / "fonts"
    result = im.download_pretendard(dest, opener=_fake_opener(release, _fake_zip_bytes()))

    names = {p.name for p in result}
    assert names == {"Pretendard-Bold.otf", "Pretendard-Medium.otf"}
    assert (dest / "Pretendard-Bold.otf").read_bytes() == b"bold-bytes"
    assert (dest / "Pretendard-Medium.otf").read_bytes() == b"medium-bytes"
    assert not (dest / "Pretendard-ExtraBold.otf").exists()


def test_download_pretendard_does_not_overwrite_existing(tmp_path):
    dest = tmp_path / "fonts"
    dest.mkdir(parents=True)
    (dest / "Pretendard-Bold.otf").write_bytes(b"already-here")
    (dest / "Pretendard-Medium.otf").write_bytes(b"already-here-too")

    def opener(url):
        raise AssertionError("이미 폰트가 있으면 네트워크를 호출하면 안 됩니다")

    result = im.download_pretendard(dest, opener=opener)
    assert (dest / "Pretendard-Bold.otf").read_bytes() == b"already-here"
    assert len(result) == 2


def test_hyperframes_browser_path_handler_records_chrome_path(tmp_path):
    config = h.default_config()
    im._handle_hyperframes_browser_path(tmp_path, config, "npx 진행 로그\n/usr/local/bin/chromium\n", "hyperframes")
    assert (tmp_path / "도구" / "chrome-path.txt").read_text(encoding="utf-8").strip() == "/usr/local/bin/chromium"
    assert config["paths"]["chrome"] == "/usr/local/bin/chromium"


def test_voice_model_download_handler_records_model_path(tmp_path):
    config = h.default_config()
    im._handle_voice_model_download(tmp_path, config, "다운로드 완료", "voice-local-mlx")
    expected = str(tmp_path / m.VOICE_MODEL_REL_DIR)
    assert config["modules"]["voice"]["model_path"] == expected


def test_handoff_editor_detect_handler_records_editors_and_reminds_only_for_missing_one(tmp_path):
    config = h.default_config()
    output = json.dumps(
        {
            "editors": {
                "capcut": {"installed": True, "version": "1.0", "drafts_dir": None},
                "premiere": {"installed": False, "version": None},
            }
        }
    )
    capcut_reminders = im._handle_handoff_editor_detect(tmp_path, config, output, "handoff-capcut")
    assert config["modules"]["handoff"]["capcut"]["installed"] is True
    assert config["modules"]["handoff"]["premiere"]["installed"] is False
    assert capcut_reminders == []  # capcut is installed: no reminder for the capcut run

    premiere_reminders = im._handle_handoff_editor_detect(tmp_path, config, output, "handoff-premiere")
    assert premiere_reminders and "Premiere" in premiere_reminders[0]


def test_run_module_success_updates_status(tmp_path):
    config = h.default_config()
    h.save_config(tmp_path, config)

    def fake_run(cmd, cwd=None, env=None, log=None, timeout=None):
        return 0, "ok"

    result = im.run_module(tmp_path, "voice-record", run_fn=fake_run)
    assert result["ok"] is True
    assert result["manual"]
    assert result["ran"] == []

    saved = h.load_config(tmp_path)
    assert "voice-record" in saved["status"]["installed"]


def test_run_module_failure_records_failed_step(tmp_path):
    config = h.default_config()
    h.save_config(tmp_path, config)

    def fake_run(cmd, cwd=None, env=None, log=None, timeout=None):
        return 1, "boom"

    result = im.run_module(tmp_path, "tools-venv", run_fn=fake_run)
    assert result["ok"] is False
    assert result["failed_step"]

    saved = h.load_config(tmp_path)
    assert saved["status"]["failed"][0]["module"] == "tools-venv"


def test_run_module_missing_config_reports_error(tmp_path):
    result = im.run_module(tmp_path, "tools-venv")
    assert "error" in result


def test_run_module_resolves_npx_before_executing(tmp_path, monkeypatch):
    """계획에는 짧은 이름을 보여 주되, 실제 실행은 which로 푼 경로로 한다.

    Windows의 `CreateProcess`는 PATHEXT를 보지 않아 bare `npx`로는 `npx.cmd`를
    띄우지 못한다.
    """
    config = cfg(render={"engine": "hyperframes"})
    h.save_config(tmp_path, config)
    monkeypatch.setattr(h, "which", lambda name: f"C:\\node\\{name}.cmd" if name in ("npx", "npm") else None)

    calls: list[list[str]] = []

    def fake_run(cmd, cwd=None, env=None, log=None, timeout=None):
        calls.append(list(cmd))
        return 0, "ok"

    im.run_module(tmp_path, "hyperframes", run_fn=fake_run)

    assert calls, "hyperframes 모듈은 명령을 실행해야 한다"
    assert all(c[0] == "C:\\node\\npx.cmd" for c in calls), calls
    # 계획 자체는 사람이 읽는 것이므로 짧은 이름 그대로 남는다.
    assert m.plan("hyperframes", tmp_path, config)[0]["cmd"][0] == "npx"


def test_run_module_does_not_duplicate_failed_entries_on_retry(tmp_path):
    """같은 모듈을 N번 재시도해도 status.failed에는 한 줄만 남아야 한다."""
    config = h.default_config()
    h.save_config(tmp_path, config)

    def fake_run(cmd, cwd=None, env=None, log=None, timeout=None):
        return 1, "boom"

    for _ in range(3):
        im.run_module(tmp_path, "tools-venv", run_fn=fake_run)

    failed = h.load_config(tmp_path)["status"]["failed"]
    assert [f["module"] for f in failed] == ["tools-venv"]


def _fake_editor_report(capcut_installed: bool, premiere_installed: bool) -> str:
    return json.dumps(
        {
            "editors": {
                "capcut": {"installed": capcut_installed, "version": None, "drafts_dir": None},
                "premiere": {"installed": premiere_installed, "version": None},
            }
        }
    )


def test_run_handoff_premiere_installed_records_and_has_no_reminder(tmp_path):
    config = cfg(handoff={"editor": "premiere"})
    h.save_config(tmp_path, config)

    def fake_run(cmd, cwd=None, env=None, log=None, timeout=None):
        return 0, _fake_editor_report(capcut_installed=False, premiere_installed=True)

    result = im.run_module(tmp_path, "handoff-premiere", run_fn=fake_run)
    assert result["ok"] is True
    assert not any("설치" in text for text in result["manual"])

    saved = h.load_config(tmp_path)
    assert saved["modules"]["handoff"]["premiere"]["installed"] is True


def test_run_handoff_premiere_missing_adds_reminder(tmp_path):
    config = cfg(handoff={"editor": "premiere"})
    h.save_config(tmp_path, config)

    def fake_run(cmd, cwd=None, env=None, log=None, timeout=None):
        return 0, _fake_editor_report(capcut_installed=False, premiere_installed=False)

    result = im.run_module(tmp_path, "handoff-premiere", run_fn=fake_run)
    assert result["ok"] is True
    assert any("Premiere" in text for text in result["manual"])

    saved = h.load_config(tmp_path)
    assert saved["modules"]["handoff"]["premiere"]["installed"] is False


def test_run_handoff_capcut_installed_records_and_has_no_reminder(tmp_path):
    config = cfg(handoff={"editor": "capcut"})
    h.save_config(tmp_path, config)

    def fake_run(cmd, cwd=None, env=None, log=None, timeout=None):
        return 0, _fake_editor_report(capcut_installed=True, premiere_installed=False)

    result = im.run_module(tmp_path, "handoff-capcut", run_fn=fake_run)
    assert result["ok"] is True
    assert not any("CapCut" in text for text in result["manual"])

    saved = h.load_config(tmp_path)
    assert saved["modules"]["handoff"]["capcut"]["installed"] is True


def test_run_handoff_capcut_missing_adds_reminder(tmp_path):
    config = cfg(handoff={"editor": "capcut"})
    h.save_config(tmp_path, config)

    def fake_run(cmd, cwd=None, env=None, log=None, timeout=None):
        return 0, _fake_editor_report(capcut_installed=False, premiere_installed=False)

    result = im.run_module(tmp_path, "handoff-capcut", run_fn=fake_run)
    assert result["ok"] is True
    assert any("CapCut" in text for text in result["manual"])

    saved = h.load_config(tmp_path)
    assert saved["modules"]["handoff"]["capcut"]["installed"] is False


def test_cmd_plan_invalid_config_exits_1(tmp_path, capsys):
    config = h.default_config()
    config["modules"]["render"]["engine"] = "not-a-real-engine"
    h.save_config(tmp_path, config)

    args = im.build_parser().parse_args(["plan", str(tmp_path), "--all"])
    code = im.cmd_plan(args)
    captured = capsys.readouterr()

    assert code == 1
    payload = json.loads(captured.err)
    assert "error" in payload
