# tests/test_smoke.py
from pathlib import Path
import harness_lib as h
import smoke_test as st

# `npx`/`npm`은 Windows의 `.cmd` 때문에 `which`로 풀어서 실행한다(harness_lib.node_cmd).
NPX = h.node_cmd("npx")
NPM = h.node_cmd("npm")

T = Path(__file__).resolve().parents[1] / "skills/video-harness-setup/assets/episode-template-hyperframes/index.html"


def test_fill_template_sets_text_and_duration():
    out = st.fill_template(T.read_text(encoding="utf-8"), "세팅 확인", "자막이 보이면 성공", "테스트", 12.0)
    assert ">세팅 확인</h1>" in out and ">자막이 보이면 성공</p>" in out
    assert 'data-composition-id="main"' in out and 'data-duration="12"' in out
    assert 'data-start="0.4" data-duration="11.6"' in out
    assert 'data-duration="10"' not in out


def test_fill_template_escapes_html():
    out = st.fill_template(T.read_text(encoding="utf-8"), "<b>x</b>", "a & b", "s", 10.0)
    assert "&lt;b&gt;x&lt;/b&gt;" in out and "a &amp; b" in out


def test_verify_flags_problems():
    ok = {"width": 1080, "height": 1920, "duration": 10.1, "has_audio": True}
    assert st.verify(ok, 1080, 1920, 9.5) == []
    bad = {"width": 1920, "height": 1080, "duration": 3.0, "has_audio": False}
    assert len(st.verify(bad, 1080, 1920, 9.5)) == 3


def test_probe_parses_ffprobe_json():
    fake = '{"streams":[{"codec_type":"video","width":1080,"height":1920},{"codec_type":"audio"}],"format":{"duration":"10.033"}}'
    p = st.probe(Path("x.mp4"), run_fn=lambda cmd, **kw: (0, fake))
    assert p == {"width": 1080, "height": 1920, "duration": 10.033, "has_audio": True}


# --- 아래는 브리프의 모호성 해소 항목들(width/height, wire_fonts, render_env, 오케스트레이션)에
# 대한 추가 커버리지. 위 4개는 브리프의 "전문" 블록 그대로다. ---

import json
import shutil

import harness_lib as h


def test_fill_template_sets_width_height_when_given():
    out = st.fill_template(T.read_text(encoding="utf-8"), "t", "c", "s", 10.0, width=1920, height=1080)
    assert 'data-width="1920"' in out and 'data-height="1080"' in out
    assert 'data-width="1080"' not in out and 'data-height="1920"' not in out


def test_fill_template_leaves_width_height_when_not_given():
    out = st.fill_template(T.read_text(encoding="utf-8"), "t", "c", "s", 10.0)
    assert 'data-width="1080"' in out and 'data-height="1920"' in out


def test_wire_fonts_prepends_url_for_available_family_only():
    out = st.wire_fonts(T.read_text(encoding="utf-8"), {"Pretendard": "assets/fonts/Pretendard-Bold.otf"})
    assert 'src: url("assets/fonts/Pretendard-Bold.otf"), local("Pretendard")' in out
    assert 'font-family: "Paperlogy"; font-weight: 900; src: local("Paperlogy")' in out


def test_wire_fonts_leaves_html_unchanged_when_none_available():
    html_in = T.read_text(encoding="utf-8")
    assert st.wire_fonts(html_in, {}) == html_in


def test_render_env_returns_empty_without_wrapper(tmp_path):
    config = h.default_config()
    assert st.render_env(tmp_path, config, False) == {}


def test_render_env_returns_chrome_vars_with_wrapper(tmp_path):
    config = h.default_config()
    config["paths"]["chrome"] = "/usr/local/bin/chromium"
    env = st.render_env(tmp_path, config, True)
    assert env == {
        "HYPERFRAMES_BROWSER_PATH": str(tmp_path / "도구" / "chrome-noaudio.py"),
        "HARNESS_CHROME": "/usr/local/bin/chromium",
    }


def test_render_env_falls_back_to_chrome_path_file(tmp_path):
    config = h.default_config()
    tools_dir = tmp_path / "도구"
    tools_dir.mkdir(parents=True)
    (tools_dir / "chrome-path.txt").write_text("/opt/chrome\n", encoding="utf-8")
    env = st.render_env(tmp_path, config, True)
    assert env["HARNESS_CHROME"] == "/opt/chrome"


def test_find_reference_recording_skips_ds_store(tmp_path):
    rec_dir = tmp_path / "녹음"
    rec_dir.mkdir()
    (rec_dir / ".DS_Store").write_bytes(b"junk")
    (rec_dir / "ref.wav").write_bytes(b"audio")
    (rec_dir / "ref.txt").write_text("대본", encoding="utf-8")

    found = st._find_reference_recording(rec_dir)
    assert found is not None
    ref_audio, ref_text = found
    assert ref_audio.name == "ref.wav"
    assert ref_text.name == "ref.txt"


def test_find_reference_recording_only_ds_store_and_txt_is_not_ready(tmp_path):
    rec_dir = tmp_path / "녹음"
    rec_dir.mkdir()
    (rec_dir / ".DS_Store").write_bytes(b"junk")
    (rec_dir / "ref.txt").write_text("대본", encoding="utf-8")

    assert st._find_reference_recording(rec_dir) is None


def test_parse_json_object_ignores_nested_meta_object_and_log_lines():
    # 실제 `hyperframes check --json`은 로그 줄 뒤에 최상위 JSON 하나를 찍는데,
    # 그 객체의 마지막 키(`_meta`)도 그 자체로 유효한 JSON 객체라서 "마지막으로
    # 성공하는 파싱"을 고르면 엉뚱하게 `_meta`만 돌려주는 버그가 있었다(통합 테스트로 발견).
    text = (
        "npm 진행 로그\n"
        '{"ok": true, "lint": {"ok": true}, "_meta": {"version": "0.8.43"}}\n'
    )
    parsed = st._parse_json_object(text)
    assert parsed == {"ok": True, "lint": {"ok": True}, "_meta": {"version": "0.8.43"}}


# --- 오케스트레이션(run_smoke_test)을 가짜 run_fn으로 검증한다 ---

SKILL_ROOT = Path(__file__).resolve().parents[1] / "skills/video-harness-setup"
MAC = {"os": "darwin", "arch": "arm64", "apple_silicon": True}


def _frame_text_with_canvas(channel_name: str, canvas: tuple[int, int] | None) -> str:
    """frame.md.tmpl을 채널명으로 치환하고, `canvas`가 주어지면 그 해상도로 다시 쓴다.

    실제 스캐폴드(`scaffold.py`의 `_set_frame_canvas`)가 채널 포맷에 맞춰 canvas를
    쓰는 것을 흉내 낸다 — smoke_test.py의 canvas 불일치 가드를 독립적으로 검증하려고
    테스트 쪽에서 직접 채널 포맷과 어긋나거나 맞는 canvas를 만들어 준다.
    """
    import re

    frame_text = h.render_template(
        (SKILL_ROOT / "assets" / "templates" / "frame.md.tmpl").read_text(encoding="utf-8"),
        {"channel_name": channel_name},
    )
    if canvas is not None:
        width, height = canvas
        frame_text = re.sub(
            r"^canvas:\s*\{[^}]*\}\s*$",
            f"canvas: {{width: {width}, height: {height}, fps: 30}}",
            frame_text,
            count=1,
            flags=re.MULTILINE,
        )
    return frame_text


def _setup_workspace(tmp_path, voice_mode="record", canvas=None):
    """채널 하나짜리 최소 작업 공간을 실제 파일로 만든다(회차템플릿·frame.md·도구 venv 표시)."""
    workspace = tmp_path / "ws"
    config = h.default_config()
    config["platform"] = MAC
    config["modules"]["voice"]["mode"] = voice_mode
    config["workspace"] = {"name": "테스트", "path": "."}
    config["channels"] = [
        {
            "id": "test-channel",
            "name": "테스트채널",
            "format": "9:16",
            "kind": "narration-shorts",
            "target_seconds": 60,
            "language": "ko",
        }
    ]
    h.save_config(workspace, config)

    channel_base = workspace / "테스트채널" / "03_편집프로젝트" / "_채널공용"
    shutil.copytree(SKILL_ROOT / "assets" / "episode-template-hyperframes", channel_base / "회차템플릿")
    frame_text = _frame_text_with_canvas("테스트채널", canvas)
    (channel_base / "frame.md").write_text(frame_text, encoding="utf-8")

    import module_registry as m

    venv_python = m._venv_python(workspace / "도구" / ".venv", MAC)
    venv_python.parent.mkdir(parents=True, exist_ok=True)
    venv_python.write_text("", encoding="utf-8")

    return workspace


def _touch_output(cmd: list[str]) -> None:
    """가짜 ffmpeg/render 호출이 만들었을 출력 파일을 실제로 만든다(뒤이은 복사/probe용)."""
    out_path = Path(cmd[-1])
    out_path.parent.mkdir(parents=True, exist_ok=True)
    if not out_path.exists():
        out_path.write_bytes(b"fake")


def _ffprobe_payload(cmd: list[str]) -> str:
    target = Path(cmd[-1]).name
    if target == "narration.wav":
        payload = {"streams": [{"codec_type": "audio"}], "format": {"duration": "3.000"}}
    else:
        payload = {
            "streams": [
                {"codec_type": "video", "width": 1080, "height": 1920},
                {"codec_type": "audio"},
            ],
            "format": {"duration": "10.500"},
        }
    return json.dumps(payload)


def test_wrapper_retry_on_navigation_timeout(tmp_path):
    workspace = _setup_workspace(tmp_path)
    calls: list[list[str]] = []

    def fake_run(cmd, cwd=None, env=None, log=None, timeout=None):
        calls.append(cmd)
        env = env or {}
        if cmd[0] == "ffprobe":
            return 0, _ffprobe_payload(cmd)
        if cmd[0] == "ffmpeg":
            _touch_output(cmd)
            return 0, ""
        if cmd[1].endswith("build_tokens.py"):
            return 0, ""
        if cmd[1].endswith("check_style.py"):
            return 0, json.dumps({"errors": [], "warnings": [], "free_notes": []})
        if cmd[0] == NPX and "check" in cmd:
            if "HYPERFRAMES_BROWSER_PATH" in env:
                return 0, '{"ok": true}'
            return 1, "일부 로그\nNavigation timeout exceeded\n"
        if cmd[0] == NPX and "render" in cmd:
            _touch_output(["ignored", cmd[cmd.index("--output") + 1]])
            return 0, "render ok"
        raise AssertionError(f"unexpected command: {cmd}")

    result = st.run_smoke_test(workspace, run_fn=fake_run)

    assert result["passed"] is True
    assert result["used_chrome_wrapper"] is True
    check_calls = [c for c in calls if c[0] == NPX and "check" in c]
    assert len(check_calls) == 2

    saved = h.load_config(workspace)
    assert saved["paths"]["use_chrome_wrapper"] is True
    assert saved["status"]["smoke_test"] == "passed"


def test_failure_when_check_is_not_ok(tmp_path):
    workspace = _setup_workspace(tmp_path)
    calls: list[list[str]] = []

    def fake_run(cmd, cwd=None, env=None, log=None, timeout=None):
        calls.append(cmd)
        if cmd[0] == "ffprobe":
            return 0, _ffprobe_payload(cmd)
        if cmd[0] == "ffmpeg":
            _touch_output(cmd)
            return 0, ""
        if cmd[1].endswith("build_tokens.py"):
            return 0, ""
        if cmd[0] == NPX and "check" in cmd:
            return 1, json.dumps({"ok": False, "lint": {"errors": ["뭔가 잘못됨"]}})
        raise AssertionError(f"unexpected command (render should not run): {cmd}")

    result = st.run_smoke_test(workspace, run_fn=fake_run)

    assert result["passed"] is False
    assert result["check_ok"] is False
    assert not any(c[0] == NPX and "render" in c for c in calls)

    saved = h.load_config(workspace)
    assert saved["status"]["smoke_test"] == "failed"


def test_sine_fallback_when_tts_prerequisites_missing(tmp_path):
    # voice.mode는 local-mlx지만 모델·venv·녹음 중 아무것도 준비돼 있지 않다.
    workspace = _setup_workspace(tmp_path, voice_mode="local-mlx")
    calls: list[list[str]] = []

    def fake_run(cmd, cwd=None, env=None, log=None, timeout=None):
        calls.append(cmd)
        if cmd[0] == "ffprobe":
            return 0, _ffprobe_payload(cmd)
        if cmd[0] == "ffmpeg":
            _touch_output(cmd)
            return 0, ""
        if cmd[1].endswith("build_tokens.py"):
            return 0, ""
        if cmd[1].endswith("check_style.py"):
            return 0, json.dumps({"errors": [], "warnings": [], "free_notes": []})
        if cmd[0] == NPX and "check" in cmd:
            return 0, '{"ok": true}'
        if cmd[0] == NPX and "render" in cmd:
            _touch_output(["ignored", cmd[cmd.index("--output") + 1]])
            return 0, "render ok"
        raise AssertionError(f"unexpected command: {cmd}")

    result = st.run_smoke_test(workspace, run_fn=fake_run)

    assert result["narration"] == "sine"
    assert result["passed"] is True
    assert not any("generate_local_mlx.py" in part for c in calls for part in c)


def test_missing_episode_template_fails_with_korean_message_instead_of_raising(tmp_path):
    workspace = _setup_workspace(tmp_path)
    template_dir = workspace / "테스트채널" / "03_편집프로젝트" / "_채널공용" / "회차템플릿"
    shutil.rmtree(template_dir)

    def fake_run(cmd, cwd=None, env=None, log=None, timeout=None):
        raise AssertionError(f"no command should run when the template is missing: {cmd}")

    result = st.run_smoke_test(workspace, channel_id="test-channel", run_fn=fake_run)

    assert result["passed"] is False
    assert "회차템플릿" in result["error"]
    assert "scaffold.py" in result["error"]

    saved = h.load_config(workspace)
    assert saved["status"]["smoke_test"] == "failed"


# --- Remotion 엔진 경로: 가짜 run_fn으로 오케스트레이션(_run_remotion_smoke_test)을
# 검증한다. 실제 npm/remotion CLI 동작은 통합 확인(Step 4, 수동)에서 검증한다. ---


def _setup_remotion_workspace(tmp_path, channel_format="9:16", canvas=None):
    """채널 하나짜리 최소 작업 공간을 만든다. 엔진은 remotion, 회차템플릿은 실제 템플릿을 복사한다.

    `canvas`를 주면 frame.md의 canvas를 그 값으로 다시 쓴다(기본은 템플릿 기본값인
    1080x1920 그대로) — 채널 포맷과 canvas가 맞는/어긋나는 경우를 모두 테스트하려고.
    """
    workspace = tmp_path / "ws"
    config = h.default_config()
    config["platform"] = MAC
    config["modules"]["voice"]["mode"] = "record"
    config["modules"]["render"]["engine"] = "remotion"
    config["workspace"] = {"name": "테스트", "path": "."}
    config["channels"] = [
        {
            "id": "test-channel",
            "name": "테스트채널",
            "format": channel_format,
            "kind": "narration-shorts",
            "target_seconds": 60,
            "language": "ko",
        }
    ]
    h.save_config(workspace, config)

    channel_base = workspace / "테스트채널" / "03_편집프로젝트" / "_채널공용"
    shutil.copytree(
        SKILL_ROOT / "assets" / "episode-template-remotion", channel_base / "회차템플릿-remotion"
    )
    frame_text = _frame_text_with_canvas("테스트채널", canvas)
    (channel_base / "frame.md").write_text(frame_text, encoding="utf-8")

    import module_registry as m

    venv_python = m._venv_python(workspace / "도구" / ".venv", MAC)
    venv_python.parent.mkdir(parents=True, exist_ok=True)
    venv_python.write_text("", encoding="utf-8")

    return workspace


def _remotion_fake_run(cmd, cwd=None, env=None, log=None, timeout=None):
    if cmd[0] == "ffprobe":
        return 0, _ffprobe_payload(cmd)
    if cmd[0] == "ffmpeg":
        _touch_output(cmd)
        return 0, ""
    if len(cmd) >= 2 and str(cmd[1]).endswith("build_tokens.py"):
        return 0, ""
    if len(cmd) >= 2 and str(cmd[1]).endswith("check_style.py"):
        return 0, json.dumps({"errors": [], "warnings": [], "free_notes": []})
    if cmd[0] == NPM and "install" in cmd:
        return 0, "installed"
    if cmd[0] == NPX and "render" in cmd:
        mp4_path = cmd[cmd.index("render") + 3]
        _touch_output(["ignored", mp4_path])
        return 0, "render ok"
    raise AssertionError(f"unexpected command: {cmd}")


def test_remotion_smoke_test_passes_with_fake_run(tmp_path):
    workspace = _setup_remotion_workspace(tmp_path)

    result = st.run_smoke_test(workspace, run_fn=_remotion_fake_run)

    assert result["passed"] is True
    assert result["engine"] == "remotion"
    assert result["npm_install_ran"] is True
    assert "npx remotion studio" in result["studio_hint"]
    assert result["narration"] == "sine"

    saved = h.load_config(workspace)
    assert saved["status"]["smoke_test"] == "passed"


def test_remotion_smoke_test_render_command_shape(tmp_path):
    workspace = _setup_remotion_workspace(tmp_path)
    calls: list[list[str]] = []

    def fake_run(cmd, cwd=None, env=None, log=None, timeout=None):
        calls.append(cmd)
        return _remotion_fake_run(cmd, cwd=cwd, env=env, log=log, timeout=timeout)

    st.run_smoke_test(workspace, run_fn=fake_run)

    render_calls = [c for c in calls if c[0] == NPX and "render" in c]
    assert len(render_calls) == 1
    render_cmd = render_calls[0]
    assert render_cmd[:5] == [NPX, "remotion", "render", "src/index.ts", "Episode"]
    assert any(part.startswith("--props=") for part in render_cmd)


def test_remotion_smoke_test_missing_template_fails_with_korean_message(tmp_path):
    workspace = _setup_remotion_workspace(tmp_path)
    shutil.rmtree(workspace / "테스트채널" / "03_편집프로젝트" / "_채널공용" / "회차템플릿-remotion")

    def fake_run(cmd, cwd=None, env=None, log=None, timeout=None):
        raise AssertionError(f"no command should run when the template is missing: {cmd}")

    result = st.run_smoke_test(workspace, channel_id="test-channel", run_fn=fake_run)

    assert result["passed"] is False
    assert "Remotion 회차템플릿" in result["error"]
    assert "scaffold.py" in result["error"]

    saved = h.load_config(workspace)
    assert saved["status"]["smoke_test"] == "failed"


def test_remotion_smoke_test_render_failure_is_reported(tmp_path):
    workspace = _setup_remotion_workspace(tmp_path)

    def fake_run(cmd, cwd=None, env=None, log=None, timeout=None):
        if cmd[0] == NPX and "render" in cmd:
            return 1, "boom"
        return _remotion_fake_run(cmd, cwd=cwd, env=env, log=log, timeout=timeout)

    result = st.run_smoke_test(workspace, run_fn=fake_run)

    assert result["passed"] is False
    assert "렌더에 실패" in result["error"]


def test_engine_both_without_flag_defaults_to_hyperframes(tmp_path):
    workspace = _setup_workspace(tmp_path)
    config = h.load_config(workspace)
    config["modules"]["render"]["engine"] = "both"
    h.save_config(workspace, config)

    result = st.run_smoke_test(workspace, run_fn=_handoff_fake_run())

    assert result["passed"] is True
    assert result["engine"] == "hyperframes"


def test_remotion_smoke_test_skips_npm_install_when_node_modules_present(tmp_path):
    workspace = _setup_remotion_workspace(tmp_path)
    calls: list[list[str]] = []

    def fake_run(cmd, cwd=None, env=None, log=None, timeout=None):
        calls.append(cmd)
        if len(cmd) >= 2 and str(cmd[1]).endswith("build_tokens.py"):
            # theme.ts 경로(--ts 다음 인자)에서 project_dir을 얻어 node_modules를 미리
            # 만들어 둔다 — "이미 설치돼 있으면 npm install을 건너뛴다" 분기를 태우려고.
            theme_ts = Path(cmd[cmd.index("--ts") + 1])
            (theme_ts.parent.parent / "node_modules").mkdir(parents=True, exist_ok=True)
            return 0, ""
        return _remotion_fake_run(cmd, cwd=cwd, env=env, log=log, timeout=timeout)

    result = st.run_smoke_test(workspace, run_fn=fake_run)

    assert result["passed"] is True
    assert result["npm_install_ran"] is False
    assert not any(c[0] == NPM for c in calls)


def _ffprobe_payload_16x9(cmd: list[str]) -> str:
    target = Path(cmd[-1]).name
    if target == "narration.wav":
        payload = {"streams": [{"codec_type": "audio"}], "format": {"duration": "3.000"}}
    else:
        payload = {
            "streams": [
                {"codec_type": "video", "width": 1920, "height": 1080},
                {"codec_type": "audio"},
            ],
            "format": {"duration": "10.500"},
        }
    return json.dumps(payload)


def test_remotion_smoke_test_16x9_channel_uses_matching_canvas(tmp_path):
    workspace = _setup_remotion_workspace(tmp_path, channel_format="16:9", canvas=(1920, 1080))

    def fake_run(cmd, cwd=None, env=None, log=None, timeout=None):
        if cmd[0] == "ffprobe":
            return 0, _ffprobe_payload_16x9(cmd)
        return _remotion_fake_run(cmd, cwd=cwd, env=env, log=log, timeout=timeout)

    result = st.run_smoke_test(workspace, run_fn=fake_run)

    assert result["passed"] is True
    assert result["verify_problems"] == []


def test_remotion_smoke_test_fails_when_frame_canvas_disagrees_with_channel_format(tmp_path):
    # 채널 포맷은 9:16인데 frame.md의 canvas가 16:9로 어긋난 경우 — 렌더 전에 걸러내야 한다.
    workspace = _setup_remotion_workspace(tmp_path, channel_format="9:16", canvas=(1920, 1080))

    def fake_run(cmd, cwd=None, env=None, log=None, timeout=None):
        raise AssertionError(f"canvas 불일치를 먼저 걸러내야 하는데 명령이 실행됨: {cmd}")

    result = st.run_smoke_test(workspace, run_fn=fake_run)

    assert result["passed"] is False
    assert "canvas" in result["error"]
    assert "1920x1080" in result["error"] and "1080x1920" in result["error"]


def test_hyperframes_smoke_test_fails_when_frame_canvas_disagrees_with_channel_format(tmp_path):
    # HyperFrames는 canvas 값을 직접 쓰지 않지만, frame.md가 채널 포맷과 어긋나 있으면
    # 나중에 엔진을 Remotion으로 바꿀 때 조용히 잘못된 해상도가 나올 수 있으므로 여기서도 막는다.
    workspace = _setup_workspace(tmp_path, canvas=(1920, 1080))

    def fake_run(cmd, cwd=None, env=None, log=None, timeout=None):
        raise AssertionError(f"canvas 불일치를 먼저 걸러내야 하는데 명령이 실행됨: {cmd}")

    result = st.run_smoke_test(workspace, run_fn=fake_run)

    assert result["passed"] is False
    assert "canvas" in result["error"]


# --- handoff(편집기 넘기기) 연동: 가짜 run_fn으로 to_premiere_xml.py/to_capcut.py를
# 흉내 낸다. 실제 CLI 동작은 tests/test_handoff.py에서 검증한다. ---


def _base_fake_run(cmd: list[str]) -> tuple[int, str] | None:
    """렌더 파이프라인 공통 단계를 흉내 낸다. 처리했으면 (code, output), 아니면 None."""
    if cmd[0] == "ffprobe":
        return 0, _ffprobe_payload(cmd)
    if cmd[0] == "ffmpeg":
        _touch_output(cmd)
        return 0, ""
    if cmd[1].endswith("build_tokens.py"):
        return 0, ""
    if cmd[1].endswith("check_style.py"):
        return 0, json.dumps({"errors": [], "warnings": [], "free_notes": []})
    if cmd[0] == NPX and "check" in cmd:
        return 0, '{"ok": true}'
    if cmd[0] == NPX and "render" in cmd:
        _touch_output(["ignored", cmd[cmd.index("--output") + 1]])
        return 0, "render ok"
    return None


def _handoff_fake_run(pycapcut_available: bool = True):
    def fake_run(cmd, cwd=None, env=None, log=None, timeout=None):
        base = _base_fake_run(cmd)
        if base is not None:
            return base

        if len(cmd) >= 2 and str(cmd[1]).endswith("to_premiere_xml.py"):
            out_dir = Path(cmd[cmd.index("--out") + 1])
            out_dir.mkdir(parents=True, exist_ok=True)
            name = json.loads(Path(cmd[2]).read_text(encoding="utf-8"))["name"]
            files = []
            for suffix in (f"{name}.xml", f"{name}.srt", "가져오는_방법.md"):
                p = out_dir / suffix
                p.write_text("x", encoding="utf-8")
                files.append(str(p))
            return 0, json.dumps({"files": files})

        if len(cmd) >= 2 and str(cmd[1]).endswith("to_capcut.py"):
            if "--bundle-out" in cmd:
                out_dir = Path(cmd[cmd.index("--bundle-out") + 1])
                out_dir.mkdir(parents=True, exist_ok=True)
                name = json.loads(Path(cmd[2]).read_text(encoding="utf-8"))["name"]
                files = []
                for suffix in (f"{name}.srt", "컷목록.md", "오버레이_파일_목록.md", "가져오는_방법.md"):
                    p = out_dir / suffix
                    p.write_text("x", encoding="utf-8")
                    files.append(str(p))
                return 0, json.dumps({"files": files})
            if "--drafts-dir" in cmd:
                drafts_dir = Path(cmd[cmd.index("--drafts-dir") + 1])
                name = json.loads(Path(cmd[2]).read_text(encoding="utf-8"))["name"]
                draft_path = drafts_dir / name
                draft_path.mkdir(parents=True, exist_ok=True)
                (draft_path / "draft_content.json").write_text("{}", encoding="utf-8")
                return 0, json.dumps({"draft": str(draft_path), "files": [str(draft_path)]})

        if cmd[-1] == "import pycapcut":
            return (0, "") if pycapcut_available else (1, "ModuleNotFoundError: No module named 'pycapcut'")

        raise AssertionError(f"unexpected command: {cmd}")

    return fake_run


def test_handoff_absent_when_editor_none(tmp_path):
    workspace = _setup_workspace(tmp_path)  # 기본 config는 handoff.editor == "none"

    def fake_run(cmd, cwd=None, env=None, log=None, timeout=None):
        result = _base_fake_run(cmd)
        if result is None:
            raise AssertionError(f"unexpected command: {cmd}")
        return result

    result = st.run_smoke_test(workspace, run_fn=fake_run)
    assert "handoff" not in result


def test_handoff_premiere_exports_xml_srt_guide(tmp_path):
    workspace = _setup_workspace(tmp_path)
    config = h.load_config(workspace)
    config["modules"]["handoff"]["editor"] = "premiere"
    h.save_config(workspace, config)

    result = st.run_smoke_test(workspace, run_fn=_handoff_fake_run())

    assert result["passed"] is True
    handoff = result["handoff"]
    assert handoff["editor"] == "premiere"
    assert handoff["structure_ok"] is True
    assert len(handoff["files"]) == 3
    assert all(Path(p).exists() for p in handoff["files"])
    assert "Premiere" in handoff["ask_user"]


def test_handoff_capcut_bundle_only_when_pycapcut_unavailable(tmp_path):
    workspace = _setup_workspace(tmp_path)
    config = h.load_config(workspace)
    config["modules"]["handoff"]["editor"] = "capcut"
    h.save_config(workspace, config)

    result = st.run_smoke_test(workspace, run_fn=_handoff_fake_run(pycapcut_available=False))

    handoff = result["handoff"]
    assert handoff["editor"] == "capcut"
    assert handoff["structure_ok"] is True
    assert len(handoff["files"]) == 4
    assert "CapCut" in handoff["ask_user"]


def test_handoff_capcut_also_builds_draft_when_pycapcut_available(tmp_path):
    workspace = _setup_workspace(tmp_path)
    config = h.load_config(workspace)
    config["modules"]["handoff"]["editor"] = "capcut"
    h.save_config(workspace, config)

    result = st.run_smoke_test(workspace, run_fn=_handoff_fake_run(pycapcut_available=True))

    handoff = result["handoff"]
    assert handoff["structure_ok"] is True
    assert len(handoff["files"]) == 5  # 수동 묶음 4개 + 초안 폴더
    draft_dir = Path(handoff["files"][-1])
    assert draft_dir.name == "capcut-draft"
    assert draft_dir.is_dir()
    assert (draft_dir / "draft_content.json").is_file()


def test_prepare_project_tolerates_an_existing_run_dir(tmp_path):
    """같은 초에 두 번 돌면 run 디렉터리가 겹친다. 날 FileExistsError로 죽지 않는다 (M9)."""
    template = tmp_path / "회차템플릿"
    template.mkdir()
    (template / "index.html").write_text("<html></html>", encoding="utf-8")

    project_dir = tmp_path / "run" / "project"
    project_dir.mkdir(parents=True)

    import module_registry as m

    config = h.default_config()
    venv_python = Path(m._venv_python(tmp_path / "도구" / ".venv", config["platform"]))
    venv_python.parent.mkdir(parents=True, exist_ok=True)
    venv_python.write_text("", encoding="utf-8")

    prep = st._prepare_project(
        tmp_path, config, {"name": "채널", "id": "ch"}, template, project_dir, "회차템플릿"
    )

    assert prep["ok"] is True
    assert (project_dir / "index.html").is_file()


# --- 오류 문장의 조치 명령도 그대로 복사해 실행할 수 있어야 한다 (재리뷰 1) ---


def _prepare_errors_for(workspace: Path) -> list[str]:
    """`_prepare_project`의 두 실패 분기(템플릿 없음 / 도구 venv 없음) 문장을 모은다."""
    import module_registry as m

    config = h.default_config()
    channel = {"name": "채널", "id": "ch"}
    errors = []

    missing_template = workspace / "없는템플릿"
    prep = st._prepare_project(workspace, config, channel, missing_template, workspace / "p1", "회차템플릿")
    errors.append(prep["error"])

    template = workspace / "회차템플릿"
    template.mkdir(parents=True, exist_ok=True)
    (template / "index.html").write_text("<html></html>", encoding="utf-8")
    prep = st._prepare_project(workspace, config, channel, template, workspace / "p2", "회차템플릿")
    errors.append(prep["error"])

    assert all(e for e in errors)
    return errors


def test_prepare_project_errors_name_real_quoted_script_paths(tmp_path):
    workspace = tmp_path / "내 작업 공간"
    workspace.mkdir()
    for error in _prepare_errors_for(workspace):
        assert "<skill>" not in error
        assert f'"{workspace}"' in error, error
        for name in ("scaffold.py", "install_module.py"):
            if name in error:
                assert f'"{h.scripts_dir() / name}"' in error, error


def test_prepare_project_errors_follow_the_platform_interpreter(tmp_path, monkeypatch):
    monkeypatch.setattr(h, "python_cmd", lambda: "python")
    workspace = tmp_path / "내 작업 공간"
    workspace.mkdir()
    for error in _prepare_errors_for(workspace):
        assert "python3 " not in error, error
