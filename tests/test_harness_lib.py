import json
import pytest
import harness_lib as h


def test_load_config_missing_returns_none(tmp_path):
    assert h.load_config(tmp_path) is None


def test_save_then_load_roundtrip(tmp_path):
    cfg = h.default_config()
    cfg["workspace"]["name"] = "작업실"
    path = h.save_config(tmp_path, cfg)
    assert path.name == "harness.config.json"
    assert h.load_config(tmp_path)["workspace"]["name"] == "작업실"
    assert "작업실" in path.read_text(encoding="utf-8")  # ensure_ascii=False


def test_default_config_is_valid():
    assert h.validate_config(h.default_config()) == []


def test_validate_rejects_unknown_engine():
    cfg = h.default_config()
    cfg["modules"]["render"]["engine"] = "aftereffects"
    errors = h.validate_config(cfg)
    assert any("render.engine" in e for e in errors)


def test_validate_rejects_local_mlx_off_apple_silicon():
    cfg = h.default_config()
    cfg["platform"] = {"os": "windows", "arch": "AMD64", "apple_silicon": False}
    cfg["modules"]["voice"]["mode"] = "local-mlx"
    assert any("local-mlx" in e for e in h.validate_config(cfg))


def _channel(**extra):
    base = {
        "id": "ch",
        "name": "동네한바퀴",
        "format": "9:16",
        "kind": "narration-shorts",
        "target_seconds": 60,
        "language": "ko",
    }
    base.update(extra)
    return base


def test_validate_accepts_optional_channel_style_fields():
    cfg = h.default_config()
    cfg["channels"] = [_channel(style_start="reference", consistency="decide-later")]
    assert h.validate_config(cfg) == []
    cfg["channels"] = [_channel()]
    assert h.validate_config(cfg) == []


def test_validate_rejects_unknown_style_start_and_consistency():
    cfg = h.default_config()
    cfg["channels"] = [_channel(style_start="느낌대로", consistency="아무거나")]
    errors = h.validate_config(cfg)
    assert any("style_start" in e for e in errors)
    assert any("consistency" in e for e in errors)


def test_validate_rejects_non_integer_sample_seconds():
    cfg = h.default_config()
    cfg["rules"]["sample_seconds"] = "12"
    assert any("sample_seconds" in e for e in h.validate_config(cfg))


def test_node_cmd_uses_resolved_path_when_which_finds_one(monkeypatch):
    """Windows에서 `npx`는 `npx.cmd`라 bare argv[0]로는 실행되지 않는다."""
    monkeypatch.setattr(h, "which", lambda name: f"C:\\\\node\\\\{name}.cmd")
    assert h.node_cmd("npx") == "C:\\\\node\\\\npx.cmd"


def test_node_cmd_falls_back_to_bare_name_when_not_found(monkeypatch):
    monkeypatch.setattr(h, "which", lambda name: None)
    assert h.node_cmd("npm") == "npm"


def test_save_validated_writes_only_when_valid(tmp_path):
    cfg = h.default_config()
    assert h.save_validated(tmp_path, cfg) == []
    assert h.load_config(tmp_path)["version"] == h.CONFIG_VERSION

    cfg["modules"]["render"]["engine"] = "aftereffects"
    errors = h.save_validated(tmp_path, cfg)
    assert errors and any("render.engine" in e for e in errors)
    # 검증에 걸리면 파일은 그대로다.
    assert h.load_config(tmp_path)["modules"]["render"]["engine"] == "hyperframes"


def test_render_template_replaces_and_fails_on_missing():
    assert h.render_template("안녕 {{name}}", {"name": "동네한바퀴"}) == "안녕 동네한바퀴"
    with pytest.raises(KeyError):
        h.render_template("{{없는키}}", {})


def test_slugify_channel_korean_gets_stable_hash():
    a, b = h.slugify_channel("동네한바퀴"), h.slugify_channel("동네한바퀴")
    assert a == b and a.startswith("channel-") and len(a) == len("channel-") + 8
    assert h.slugify_channel("My Channel 2") == "my-channel-2"


def test_run_captures_output_and_logs(tmp_path):
    log = tmp_path / "x.log"
    code, out = h.run([h.python_cmd(), "-c", "print('hi')"], log=log)
    assert code == 0 and "hi" in out and "hi" in log.read_text()


def test_run_does_not_raise_on_invalid_utf8_output():
    code, out = h.run(
        [h.python_cmd(), "-c", "import sys; sys.stdout.buffer.write(b'ok\\xff\\xfe')"]
    )
    assert code == 0
    assert "ok" in out


def test_run_disables_pyc_writing_so_tools_leave_no_pycache(tmp_path):
    """도구/의 파이썬 스크립트가 서로 import해도 __pycache__가 남지 않아야 한다."""
    mod = tmp_path / "helper.py"
    mod.write_text("VALUE = 1\n", encoding="utf-8")
    main = tmp_path / "main.py"
    main.write_text("import helper\nprint(helper.VALUE)\n", encoding="utf-8")

    code, out = h.run([h.python_cmd(), str(main)], cwd=tmp_path)

    assert code == 0 and "1" in out
    assert not (tmp_path / "__pycache__").exists()


def test_run_still_applies_caller_env_on_top_of_pyc_default(tmp_path):
    code, out = h.run(
        [h.python_cmd(), "-c", "import os; print(os.environ.get('MY_KEY'))"],
        env={"MY_KEY": "값"},
    )
    assert code == 0 and "값" in out


def test_validate_rejects_boolean_sample_seconds():
    """`True`는 int의 부분집합이라 그냥 isinstance로는 통과해 "True초"로 렌더된다."""
    cfg = h.default_config()
    cfg["rules"]["sample_seconds"] = True
    assert any("sample_seconds" in e for e in h.validate_config(cfg))


def test_script_fix_builds_a_runnable_quoted_command(tmp_path):
    spaced = tmp_path / "내 작업 공간"
    fix = h.script_fix("scaffold.py", f'"{spaced}"', "--channel", "ch-1")
    assert fix.startswith(h.python_cmd() + " ")
    assert f'"{h.scripts_dir() / "scaffold.py"}"' in fix
    assert f'"{spaced}"' in fix
    assert (h.scripts_dir() / "scaffold.py").is_file()
