import json
from datetime import date

import config_tool as ct
import harness_lib as h


def _init(ws, *extra):
    return ct.main(["init", str(ws), "--name", "내작업실", *extra])


def _add_channel(ws, name, *extra):
    return ct.main(
        [
            "add-channel", str(ws),
            "--name", name,
            "--format", "9:16",
            "--kind", "narration-shorts",
            "--target-seconds", "60",
            "--language", "ko",
            *extra,
        ]
    )


# --- init ---


def test_init_creates_valid_config_with_today_and_platform(tmp_path):
    assert _init(tmp_path) == 0
    cfg = h.load_config(tmp_path)
    assert cfg["workspace"]["name"] == "내작업실"
    assert cfg["created"] == date.today().isoformat()
    assert cfg["platform"] == h.platform_info()
    assert cfg["agents"] == ["claude"]
    assert h.validate_config(cfg) == []


def test_init_accepts_agent_list(tmp_path):
    assert _init(tmp_path, "--agents", "claude,codex") == 0
    assert h.load_config(tmp_path)["agents"] == ["claude", "codex"]


def test_init_refuses_when_config_exists(tmp_path, capsys):
    _init(tmp_path)
    before = (tmp_path / "harness.config.json").read_bytes()
    capsys.readouterr()

    assert _init(tmp_path, "--agents", "codex") == 1
    err = capsys.readouterr().err
    assert "이미" in err
    assert (tmp_path / "harness.config.json").read_bytes() == before


# --- set ---


def test_set_parses_json_value(tmp_path):
    _init(tmp_path)
    assert ct.main(["set", str(tmp_path), "modules.render.engine", '"remotion"']) == 0
    assert h.load_config(tmp_path)["modules"]["render"]["engine"] == "remotion"


def test_set_treats_bare_word_as_string(tmp_path):
    _init(tmp_path)
    assert ct.main(["set", str(tmp_path), "modules.handoff.editor", "capcut"]) == 0
    assert h.load_config(tmp_path)["modules"]["handoff"]["editor"] == "capcut"


def test_set_accepts_list_and_bool_and_int(tmp_path):
    _init(tmp_path)
    assert ct.main(["set", str(tmp_path), "modules.sources", '["own-footage","stock"]']) == 0
    assert ct.main(["set", str(tmp_path), "modules.reference.watch", "true"]) == 0
    assert ct.main(["set", str(tmp_path), "rules.sample_seconds", "8"]) == 0
    cfg = h.load_config(tmp_path)
    assert cfg["modules"]["sources"] == ["own-footage", "stock"]
    assert cfg["modules"]["reference"]["watch"] is True
    assert cfg["rules"]["sample_seconds"] == 8


def test_set_rejects_invalid_value_and_leaves_file_untouched(tmp_path, capsys):
    _init(tmp_path)
    before = (tmp_path / "harness.config.json").read_bytes()
    capsys.readouterr()

    assert ct.main(["set", str(tmp_path), "modules.render.engine", "aftereffects"]) == 1
    err = capsys.readouterr().err
    assert "render.engine" in err
    assert (tmp_path / "harness.config.json").read_bytes() == before


def test_set_refuses_unknown_top_level_key(tmp_path, capsys):
    _init(tmp_path)
    capsys.readouterr()

    assert ct.main(["set", str(tmp_path), "modual.render.engine", "remotion"]) == 1
    assert "modual" in capsys.readouterr().err
    assert "modual" not in h.load_config(tmp_path)


def test_set_refuses_to_descend_into_non_mapping(tmp_path, capsys):
    _init(tmp_path)
    capsys.readouterr()

    assert ct.main(["set", str(tmp_path), "version.major", "2"]) == 1
    err = capsys.readouterr().err
    assert "version" in err and "하위 키" in err


def test_set_rejects_misspelled_leaf_key_and_lists_valid_ones(tmp_path, capsys):
    _init(tmp_path)
    capsys.readouterr()

    assert ct.main(["set", str(tmp_path), "modules.render.engien", '"remotion"']) == 1
    err = capsys.readouterr().err
    assert "engien" in err and "engine" in err
    assert "engien" not in h.load_config(tmp_path)["modules"]["render"]


def test_set_rejects_misspelled_channel_key(tmp_path, capsys):
    _init(tmp_path)
    _add_channel(tmp_path, "동네한바퀴")
    capsys.readouterr()

    assert ct.main(["set", str(tmp_path), "channels.0.fromat", '"16:9"']) == 1
    err = capsys.readouterr().err
    assert "fromat" in err and "format" in err


def test_set_allows_optional_channel_fields_that_are_not_there_yet(tmp_path):
    _init(tmp_path)
    _add_channel(tmp_path, "동네한바퀴")
    for key, value in [
        ("concept", '"우리 동네 가게를 1분에 소개한다"'),
        ("opening", '"오늘은 여기입니다"'),
        ("style_start", '"preset"'),
        ("consistency", '"fixed"'),
        ("references", '[{"url": "https://example.com/a", "likes": "컷이 빠르다", "status": "pending"}]'),
    ]:
        assert ct.main(["set", str(tmp_path), f"channels.0.{key}", value]) == 0, key
    channel = h.load_config(tmp_path)["channels"][0]
    assert channel["style_start"] == "preset" and channel["consistency"] == "fixed"
    assert channel["references"][0]["likes"] == "컷이 빠르다"


def test_set_allows_voice_model_path_that_is_not_there_yet(tmp_path):
    """기존에 받아 둔 로컬 목소리 복제 모델을 재사용할 때, 모델을 새로 내려받지 않고
    `modules.voice.model_path`를 직접 기록할 수 있어야 한다(install_module.py가
    다운로드 뒤 자동으로 채우는 것과 같은 자리)."""
    _init(tmp_path)
    assert ct.main(["set", str(tmp_path), "modules.voice.model_path", '"/models/기존모델"']) == 0
    assert h.load_config(tmp_path)["modules"]["voice"]["model_path"] == "/models/기존모델"


def test_set_rejects_unknown_intermediate_key(tmp_path, capsys):
    _init(tmp_path)
    capsys.readouterr()

    assert ct.main(["set", str(tmp_path), "modules.hendoff.editor", '"capcut"']) == 1
    assert "hendoff" in capsys.readouterr().err
    assert "hendoff" not in h.load_config(tmp_path)["modules"]


def test_set_reaches_a_channel_by_index(tmp_path):
    """채택한 채널의 기본값(9:16·내레이션 쇼츠)을 고치려면 목록 안으로 들어가야 한다."""
    _init(tmp_path)
    _add_channel(tmp_path, "기존채널")
    assert ct.main(["set", str(tmp_path), "channels.0.format", '"16:9"']) == 0
    assert ct.main(["set", str(tmp_path), "channels.0.kind", "longform-vlog"]) == 0
    channel = h.load_config(tmp_path)["channels"][0]
    assert channel["format"] == "16:9"
    assert channel["kind"] == "longform-vlog"


def test_set_rejects_bad_list_index(tmp_path, capsys):
    _init(tmp_path)
    _add_channel(tmp_path, "기존채널")
    capsys.readouterr()

    assert ct.main(["set", str(tmp_path), "channels.7.format", '"16:9"']) == 1
    assert "channels.7.format" in capsys.readouterr().err
    assert ct.main(["set", str(tmp_path), "channels.첫째.format", '"16:9"']) == 1
    assert capsys.readouterr().err.strip() != ""


def test_set_without_config_fails(tmp_path, capsys):
    assert ct.main(["set", str(tmp_path), "agents", '["codex"]']) == 1
    assert "harness.config.json" in capsys.readouterr().err


# --- add-channel ---


def test_add_channel_prints_channel_with_slug_id(tmp_path, capsys):
    _init(tmp_path)
    capsys.readouterr()

    assert _add_channel(tmp_path, "My Channel", "--concept", "하루 한 장면") == 0
    printed = json.loads(capsys.readouterr().out)
    assert printed["id"] == "my-channel"
    assert printed["name"] == "My Channel"
    assert printed["concept"] == "하루 한 장면"

    cfg = h.load_config(tmp_path)
    assert [c["id"] for c in cfg["channels"]] == ["my-channel"]
    assert h.validate_config(cfg) == []


def test_add_channel_stores_references_with_pending_status(tmp_path):
    _init(tmp_path)
    assert _add_channel(
        tmp_path, "동네한바퀴",
        "--reference", "https://example.com/a::자막이 크고 가운데에 겹친다",
        "--reference", "레퍼런스/b.mp4::컷 템포가 빠르다",
    ) == 0
    refs = h.load_config(tmp_path)["channels"][0]["references"]
    assert refs == [
        {"url": "https://example.com/a", "likes": "자막이 크고 가운데에 겹친다", "status": "pending"},
        {"url": "레퍼런스/b.mp4", "likes": "컷 템포가 빠르다", "status": "pending"},
    ]


def test_add_channel_stores_style_start_and_consistency(tmp_path):
    _init(tmp_path)
    assert _add_channel(tmp_path, "동네한바퀴", "--style-start", "reference", "--consistency", "fixed") == 0
    channel = h.load_config(tmp_path)["channels"][0]
    assert channel["style_start"] == "reference"
    assert channel["consistency"] == "fixed"
    assert h.validate_config(h.load_config(tmp_path)) == []


def test_add_channel_rejects_duplicate_name(tmp_path, capsys):
    _init(tmp_path)
    _add_channel(tmp_path, "동네한바퀴")
    capsys.readouterr()

    assert _add_channel(tmp_path, "동네한바퀴") == 1
    assert "동네한바퀴" in capsys.readouterr().err
    assert len(h.load_config(tmp_path)["channels"]) == 1


def test_add_channel_suffixes_colliding_id(tmp_path, capsys):
    _init(tmp_path)
    _add_channel(tmp_path, "My Channel")
    _add_channel(tmp_path, "my channel")
    capsys.readouterr()

    assert _add_channel(tmp_path, "MY  CHANNEL") == 0
    assert [c["id"] for c in h.load_config(tmp_path)["channels"]] == [
        "my-channel", "my-channel-2", "my-channel-3",
    ]


def test_add_channel_without_config_fails(tmp_path, capsys):
    assert _add_channel(tmp_path, "동네한바퀴") == 1
    assert "harness.config.json" in capsys.readouterr().err


# --- remove-channel ---


def test_remove_channel_drops_it_from_config_only(tmp_path, capsys):
    _init(tmp_path)
    _add_channel(tmp_path, "동네한바퀴")
    _add_channel(tmp_path, "남는채널")
    channel_dir = tmp_path / "동네한바퀴"
    channel_dir.mkdir()
    (channel_dir / "메모.md").write_text("그대로", encoding="utf-8")
    cid = h.load_config(tmp_path)["channels"][0]["id"]
    capsys.readouterr()

    assert ct.main(["remove-channel", str(tmp_path), cid]) == 0
    out = capsys.readouterr().out
    assert "동네한바퀴" in out and "폴더" in out
    assert [c["name"] for c in h.load_config(tmp_path)["channels"]] == ["남는채널"]
    assert (channel_dir / "메모.md").read_text(encoding="utf-8") == "그대로"


def test_remove_channel_rejects_unknown_id(tmp_path, capsys):
    _init(tmp_path)
    _add_channel(tmp_path, "동네한바퀴")
    capsys.readouterr()

    assert ct.main(["remove-channel", str(tmp_path), "없는채널"]) == 1
    assert "없는채널" in capsys.readouterr().err
    assert len(h.load_config(tmp_path)["channels"]) == 1


# --- show / validate ---


def test_show_prints_config_without_ascii_escapes(tmp_path, capsys):
    _init(tmp_path)
    capsys.readouterr()

    assert ct.main(["show", str(tmp_path)]) == 0
    out = capsys.readouterr().out
    assert "내작업실" in out
    assert json.loads(out)["workspace"]["name"] == "내작업실"


def test_validate_passes_on_fresh_config(tmp_path):
    _init(tmp_path)
    assert ct.main(["validate", str(tmp_path)]) == 0


def test_validate_reports_errors_on_broken_config(tmp_path, capsys):
    _init(tmp_path)
    cfg = h.load_config(tmp_path)
    cfg["modules"]["voice"]["mode"] = "텔레파시"
    h.save_config(tmp_path, cfg)
    capsys.readouterr()

    assert ct.main(["validate", str(tmp_path)]) == 1
    assert "voice.mode" in capsys.readouterr().err


# --- 편집기를 바꾸면 이전 확인값은 무효다 (Codex 관찰 12) ---


def test_changing_the_handoff_editor_clears_the_user_verification(tmp_path, capsys):
    ct.main(["init", str(tmp_path), "--name", "작업실"])
    ct.main(["set", str(tmp_path), "modules.handoff.editor", '"capcut"'])
    ct.main(["set", str(tmp_path), "status.handoff_verified_by_user", "true"])
    assert h.load_config(tmp_path)["status"]["handoff_verified_by_user"] is True

    capsys.readouterr()
    assert ct.main(["set", str(tmp_path), "modules.handoff.editor", '"premiere"']) == 0

    saved = h.load_config(tmp_path)
    assert saved["status"]["handoff_verified_by_user"] is False
    assert "확인" in capsys.readouterr().out


def test_setting_the_same_handoff_editor_keeps_the_verification(tmp_path):
    ct.main(["init", str(tmp_path), "--name", "작업실"])
    ct.main(["set", str(tmp_path), "modules.handoff.editor", '"capcut"'])
    ct.main(["set", str(tmp_path), "status.handoff_verified_by_user", "true"])

    ct.main(["set", str(tmp_path), "modules.handoff.editor", '"capcut"'])

    assert h.load_config(tmp_path)["status"]["handoff_verified_by_user"] is True


def test_config_tool_saves_through_the_shared_validation_gate(tmp_path, monkeypatch):
    """모든 기록은 harness_lib.save_validated 한 곳을 지나가야 한다 (design §7)."""
    ct.main(["init", str(tmp_path), "--name", "작업실"])
    calls = []
    real = h.save_validated
    monkeypatch.setattr(h, "save_validated", lambda ws, cfg: (calls.append(str(ws)), real(ws, cfg))[1])

    ct.main(["set", str(tmp_path), "rules.sample_seconds", "15"])

    assert calls == [str(tmp_path)]


def test_set_always_prints_a_single_json_object(tmp_path, capsys):
    """`set`의 stdout은 어떤 경우에도 JSON 하나로 파싱돼야 한다 (SKILL.md 명령 규칙)."""
    ct.main(["init", str(tmp_path), "--name", "작업실"])
    ct.main(["set", str(tmp_path), "modules.handoff.editor", '"capcut"'])
    ct.main(["set", str(tmp_path), "status.handoff_verified_by_user", "true"])

    capsys.readouterr()
    ct.main(["set", str(tmp_path), "modules.handoff.editor", '"premiere"'])
    out = capsys.readouterr().out

    parsed = json.loads(out)
    assert parsed["modules.handoff.editor"] == "premiere"
    assert "확인" in parsed["note"]


def test_set_without_a_note_has_no_note_key(tmp_path, capsys):
    ct.main(["init", str(tmp_path), "--name", "작업실"])
    capsys.readouterr()
    ct.main(["set", str(tmp_path), "rules.sample_seconds", "15"])
    parsed = json.loads(capsys.readouterr().out)
    assert parsed == {"rules.sample_seconds": 15}


# --- 출발점(workflow)과 --kind 자동 결정 ---


def _add_channel_raw(ws, *extra):
    return ct.main(["add-channel", str(ws), "--name", "동네한바퀴", "--target-seconds", "60", *extra])


def test_add_channel_stores_workflow(tmp_path):
    _init(tmp_path)
    assert _add_channel(tmp_path, "동네한바퀴", "--workflow", "footage-first") == 0
    assert h.load_config(tmp_path)["channels"][0]["workflow"] == "footage-first"
    assert h.validate_config(h.load_config(tmp_path)) == []


def test_add_channel_derives_kind_from_workflow_and_format(tmp_path):
    cases = [
        ("script-first", "9:16", "narration-shorts"),
        ("script-first", "16:9", "narration-shorts"),
        ("footage-first", "9:16", "footage-shorts"),
        ("footage-first", "16:9", "longform-vlog"),
        ("per-episode", "9:16", "footage-shorts"),
        ("per-episode", "16:9", "longform-vlog"),
    ]
    for workflow, fmt, expected in cases:
        ws = tmp_path / f"{workflow}-{fmt.replace(':', 'x')}"
        _init(ws)
        assert _add_channel_raw(ws, "--format", fmt, "--workflow", workflow) == 0, (workflow, fmt)
        channel = h.load_config(ws)["channels"][0]
        assert channel["kind"] == expected, (workflow, fmt)
        assert h.validate_config(h.load_config(ws)) == []


def test_add_channel_keeps_an_explicit_kind_over_the_derived_one(tmp_path):
    _init(tmp_path)
    assert _add_channel_raw(tmp_path, "--format", "9:16", "--workflow", "script-first", "--kind", "footage-shorts") == 0
    assert h.load_config(tmp_path)["channels"][0]["kind"] == "footage-shorts"


def test_add_channel_without_kind_or_workflow_fails_in_korean(tmp_path, capsys):
    _init(tmp_path)
    capsys.readouterr()

    assert _add_channel_raw(tmp_path, "--format", "9:16") == 1
    err = capsys.readouterr().err
    assert "--workflow" in err and "--kind" in err
    assert h.load_config(tmp_path)["channels"] == []


def test_set_allows_workflow_that_is_not_there_yet(tmp_path):
    _init(tmp_path)
    _add_channel(tmp_path, "동네한바퀴")
    assert ct.main(["set", str(tmp_path), "channels.0.workflow", "per-episode"]) == 0
    assert h.load_config(tmp_path)["channels"][0]["workflow"] == "per-episode"
