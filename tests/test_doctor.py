# tests/test_doctor.py
import harness_lib as h
import doctor as d


def test_env_keys_report_presence_only(tmp_path):
    p = tmp_path / ".env"
    p.write_text("ELEVENLABS_API_KEY=secret-value\nHF_KEY=\n", encoding="utf-8")
    r = d.check_env_keys(p, ["ELEVENLABS_API_KEY", "HF_KEY", "MISSING"])
    assert r == {"ELEVENLABS_API_KEY": True, "HF_KEY": False, "MISSING": False}
    assert "secret-value" not in repr(r)


def test_needed_keys():
    c = h.default_config()
    assert d.needed_keys(c) == []
    c["modules"]["voice"]["mode"] = "cloud"
    c["modules"]["higgsfield"]["auth"] = "api-key"
    assert d.needed_keys(c) == ["ELEVENLABS_API_KEY", "HF_KEY"]


def test_diagnose_flags_missing_venv_and_unrun_smoke(tmp_path):
    c = h.default_config()
    c["status"]["installed"] = ["tools-venv"]
    items = d.diagnose(tmp_path, c, {"tools": {}, "missing_required": ["ffmpeg"], "editors": {}})
    by = {i["item"]: i for i in items}
    assert by["ffmpeg"]["state"] == "fail" and by["ffmpeg"]["fix"]
    assert by["도구/.venv"]["state"] == "fail"
    assert by["스모크 테스트"]["state"] == "warn"


def _channel(name="채널A"):
    return {
        "id": "ch-a",
        "name": name,
        "format": "9:16",
        "kind": "narration-shorts",
        "target_seconds": 60,
        "language": "ko",
    }


def _frame_md(status):
    return f"---\nstatus: {status}\nchannel: \"채널A\"\n---\n\n## 개요\n"


def test_channel_frame_missing_is_fail(tmp_path):
    c = h.default_config()
    c["channels"] = [_channel()]
    items = d.diagnose(tmp_path, c, {"tools": {}, "missing_required": [], "editors": {}})
    by = {i["item"]: i for i in items}
    assert by["채널A frame.md"]["state"] == "fail"
    assert by["채널A frame.md"]["fix"]


def test_channel_frame_draft_is_warn(tmp_path):
    c = h.default_config()
    c["channels"] = [_channel()]
    frame_dir = tmp_path / "채널A" / "03_편집프로젝트" / "_채널공용"
    frame_dir.mkdir(parents=True)
    (frame_dir / "frame.md").write_text(_frame_md("draft"), encoding="utf-8")

    items = d.diagnose(tmp_path, c, {"tools": {}, "missing_required": [], "editors": {}})
    by = {i["item"]: i for i in items}
    assert by["채널A frame.md"]["state"] == "warn"
    assert by["채널A frame.md"]["detail"] == "초안(draft)"


def test_channel_frame_approved_is_ok(tmp_path):
    c = h.default_config()
    c["channels"] = [_channel()]
    frame_dir = tmp_path / "채널A" / "03_편집프로젝트" / "_채널공용"
    frame_dir.mkdir(parents=True)
    (frame_dir / "frame.md").write_text(_frame_md("approved"), encoding="utf-8")

    items = d.diagnose(tmp_path, c, {"tools": {}, "missing_required": [], "editors": {}})
    by = {i["item"]: i for i in items}
    assert by["채널A frame.md"]["state"] == "ok"


def test_status_failed_entries_surface_as_fail_items(tmp_path):
    c = h.default_config()
    c["status"]["failed"] = [
        {"module": "stock", "step": "stock 안내", "log": str(tmp_path / "도구/logs/install-stock.log")}
    ]
    items = d.diagnose(tmp_path, c, {"tools": {}, "missing_required": [], "editors": {}})
    by = {i["item"]: i for i in items}
    assert by["stock 설치"]["state"] == "fail"
    assert "stock 안내" in by["stock 설치"]["detail"]


def test_smoke_test_passed_is_ok(tmp_path):
    c = h.default_config()
    c["status"]["smoke_test"] = "passed"
    items = d.diagnose(tmp_path, c, {"tools": {}, "missing_required": [], "editors": {}})
    by = {i["item"]: i for i in items}
    assert by["스모크 테스트"]["state"] == "ok"


def test_capcut_item_only_for_capcut_editor(tmp_path):
    c = h.default_config()
    c["modules"]["handoff"]["editor"] = "premiere"
    items = d.diagnose(tmp_path, c, {"tools": {}, "missing_required": [], "editors": {}})
    assert "CapCut 버전" not in {i["item"] for i in items}

    c["modules"]["handoff"]["editor"] = "capcut"
    items = d.diagnose(tmp_path, c, {"tools": {}, "missing_required": [], "editors": {}})
    by = {i["item"]: i for i in items}
    assert by["CapCut 버전"]["state"] == "warn"


def test_env_values_never_appear_in_cli_output(tmp_path, monkeypatch, capsys):
    c = h.default_config()
    c["modules"]["voice"]["mode"] = "cloud"
    h.save_config(tmp_path, c)
    (tmp_path / ".env").write_text("ELEVENLABS_API_KEY=super-secret-value\n", encoding="utf-8")

    monkeypatch.setattr(
        d.pf,
        "build_report",
        lambda workspace: {"tools": {}, "missing_required": [], "editors": {}},
    )

    d.main([str(tmp_path)])
    out = capsys.readouterr().out
    assert "super-secret-value" not in out

    d.main([str(tmp_path), "--json"])
    out_json = capsys.readouterr().out
    assert "super-secret-value" not in out_json


# --- Fix-report additions (review findings) -------------------------------------


def test_missing_stock_trace_fixes_via_scaffold_not_install_module(tmp_path):
    c = h.default_config()
    c["modules"]["sources"] = ["own-footage", "stock"]
    items = d.diagnose(tmp_path, c, {"tools": {}, "missing_required": [], "editors": {}})
    by = {i["item"]: i for i in items}
    item = by["도구/stock/search.py"]
    assert item["state"] == "fail"
    assert "scaffold.py" in item["fix"]
    assert "install_module.py" not in item["fix"]


def test_missing_export_trace_fixes_via_scaffold_not_install_module(tmp_path):
    c = h.default_config()
    c["modules"]["handoff"]["editor"] = "premiere"
    items = d.diagnose(tmp_path, c, {"tools": {}, "missing_required": [], "editors": {}})
    by = {i["item"]: i for i in items}
    item = by["도구/export/"]
    assert item["state"] == "fail"
    assert "scaffold.py" in item["fix"]
    assert "install_module.py" not in item["fix"]


def test_missing_transcribe_venv_fixes_via_install_module(tmp_path):
    c = h.default_config()
    items = d.diagnose(tmp_path, c, {"tools": {}, "missing_required": [], "editors": {}})
    by = {i["item"]: i for i in items}
    item = by["도구/transcribe/.venv"]
    assert item["state"] == "fail"
    assert 'install_module.py" run' in item["fix"]
    assert "transcribe" in item["fix"]


def test_missing_style_script_fixes_via_scaffold(tmp_path):
    c = h.default_config()
    items = d.diagnose(tmp_path, c, {"tools": {}, "missing_required": [], "editors": {}})
    by = {i["item"]: i for i in items}
    item = by["도구/style/check_style.py"]
    assert item["state"] == "fail"
    assert "scaffold.py" in item["fix"]


def test_missing_transcribe_script_fixes_via_scaffold(tmp_path):
    c = h.default_config()
    items = d.diagnose(tmp_path, c, {"tools": {}, "missing_required": [], "editors": {}})
    by = {i["item"]: i for i in items}
    item = by["도구/transcribe/transcribe.py"]
    assert item["state"] == "fail"
    assert "scaffold.py" in item["fix"]


def test_chrome_noaudio_trace_only_for_hyperframes_engine(tmp_path):
    c = h.default_config()
    c["modules"]["render"]["engine"] = "remotion"
    items = d.diagnose(tmp_path, c, {"tools": {}, "missing_required": [], "editors": {}})
    assert "도구/chrome-noaudio.py" not in {i["item"] for i in items}

    c["modules"]["render"]["engine"] = "hyperframes"
    items = d.diagnose(tmp_path, c, {"tools": {}, "missing_required": [], "editors": {}})
    by = {i["item"]: i for i in items}
    assert by["도구/chrome-noaudio.py"]["state"] == "fail"
    assert "scaffold.py" in by["도구/chrome-noaudio.py"]["fix"]


def test_handoff_detection_item_warns_until_recorded(tmp_path):
    c = h.default_config()
    c["modules"]["handoff"]["editor"] = "premiere"
    items = d.diagnose(tmp_path, c, {"tools": {}, "missing_required": [], "editors": {}})
    by = {i["item"]: i for i in items}
    assert by["handoff.premiere 감지"]["state"] == "warn"
    assert 'install_module.py" run' in by["handoff.premiere 감지"]["fix"]
    assert "handoff-premiere" in by["handoff.premiere 감지"]["fix"]

    c["modules"]["handoff"]["premiere"] = {"installed": True, "version": None}
    items = d.diagnose(tmp_path, c, {"tools": {}, "missing_required": [], "editors": {}})
    by = {i["item"]: i for i in items}
    assert by["handoff.premiere 감지"]["state"] == "ok"


# --- Coverage gaps flagged by review ----------------------------------------------


def test_channel_frame_malformed_status_is_warn(tmp_path):
    c = h.default_config()
    c["channels"] = [_channel()]
    frame_dir = tmp_path / "채널A" / "03_편집프로젝트" / "_채널공용"
    frame_dir.mkdir(parents=True)
    (frame_dir / "frame.md").write_text('---\nchannel: "채널A"\n---\n\n## 개요\n', encoding="utf-8")

    items = d.diagnose(tmp_path, c, {"tools": {}, "missing_required": [], "editors": {}})
    by = {i["item"]: i for i in items}
    assert by["채널A frame.md"]["state"] == "warn"


def test_smoke_test_failed_is_fail(tmp_path):
    c = h.default_config()
    c["status"]["smoke_test"] = "failed"
    items = d.diagnose(tmp_path, c, {"tools": {}, "missing_required": [], "editors": {}})
    by = {i["item"]: i for i in items}
    assert by["스모크 테스트"]["state"] == "fail"
    assert by["스모크 테스트"]["fix"]


def test_invalid_config_is_fail_item(tmp_path):
    c = h.default_config()
    c["modules"]["render"]["engine"] = "invalid-engine"
    items = d.diagnose(tmp_path, c, {"tools": {}, "missing_required": [], "editors": {}})
    by = {i["item"]: i for i in items}
    assert by["설정 파일"]["state"] == "fail"


# --- 조치(fix) 문자열은 그대로 복사해 실행할 수 있어야 한다 (I2) ---


def _all_fix_strings(tmp_path) -> list[str]:
    """조치 문장이 붙는 모든 분기를 한 번에 태운다."""
    c = h.default_config()
    c["modules"]["voice"]["mode"] = "cloud"
    c["modules"]["handoff"]["editor"] = "capcut"
    c["modules"]["sources"] = ["stock"]
    c["channels"] = [_channel()]
    c["status"]["failed"] = [{"module": "transcribe", "step": "패키지 설치", "log": "x.log"}]
    report = {"tools": {}, "missing_required": ["ffmpeg"], "editors": {}, "hints": {}}
    items = d.diagnose(tmp_path, c, report)
    return [i["fix"] for i in items if i.get("fix")]


def test_no_fix_string_contains_the_unresolvable_skill_placeholder(tmp_path):
    fixes = _all_fix_strings(tmp_path)
    assert fixes
    for fix in fixes:
        assert "<skill>" not in fix, fix


def test_script_fixes_use_real_quoted_script_paths(tmp_path):
    for fix in _all_fix_strings(tmp_path):
        for name in ("install_module.py", "scaffold.py", "smoke_test.py"):
            if name not in fix:
                continue
            expected = f'"{h.scripts_dir() / name}"'
            assert expected in fix, (fix, expected)
            assert (h.scripts_dir() / name).is_file()


def test_script_fixes_follow_the_platform_interpreter(tmp_path, monkeypatch):
    """Windows에서는 `python3`가 아니라 `python`이어야 한다 (SKILL.md 명령 규칙)."""
    monkeypatch.setattr(h, "python_cmd", lambda: "python")
    for fix in _all_fix_strings(tmp_path):
        assert "python3 " not in fix, fix


def test_workspace_path_is_quoted_in_fixes(tmp_path):
    spaced = tmp_path / "내 작업 공간"
    spaced.mkdir()
    for fix in _all_fix_strings(spaced):
        if ".py" not in fix:
            continue
        assert f'"{spaced}"' in fix, fix


# --- 출발점(workflow)이 비어 있는 채널은 주의로만 알린다 ---


def test_channel_without_workflow_is_warn_with_a_runnable_fix(tmp_path):
    c = h.default_config()
    c["channels"] = [_channel(name="첫채널"), _channel(name="둘째채널")]
    c["channels"][0]["workflow"] = "footage-first"

    items = d.diagnose(tmp_path, c, {"tools": {}, "missing_required": [], "editors": {}})
    by = {i["item"]: i for i in items}

    assert "첫채널 출발점" not in by
    item = by["둘째채널 출발점"]
    assert item["state"] == "warn"
    assert "출발점이 정해지지 않았습니다" in item["detail"]
    # 조치 명령에 미리 들어간 값을 그대로 쓰지 말고 바꿔 실행하라는 안내가 있어야 한다.
    assert "맞는 값으로 바꿔" in item["detail"]
    assert "script-first" in item["detail"] and "per-episode" in item["detail"]
    # 실제 목록 번호(두 번째 채널 = 1)를 짚어야 그대로 복사해 실행할 수 있다.
    assert "channels.1.workflow" in item["fix"]
    assert f'"{h.scripts_dir() / "config_tool.py"}"' in item["fix"]
    assert f'"{tmp_path}"' in item["fix"]


def test_missing_workflow_does_not_add_a_blocking_problem(tmp_path):
    """`주의`는 전체 상태(`문제 있음`)를 바꾸지 않는다 — 출발점이 비어도 세팅은 완료될 수 있다."""
    report = {"tools": {}, "missing_required": [], "editors": {}}
    c = h.default_config()
    c["channels"] = [_channel()]

    without = d.diagnose(tmp_path, c, report)
    c["channels"][0]["workflow"] = "script-first"
    with_workflow = d.diagnose(tmp_path, c, report)

    def fails(items):
        return sorted(i["item"] for i in items if i["state"] == "fail")

    assert any(i["item"].endswith("출발점") for i in without)
    assert fails(without) == fails(with_workflow)
