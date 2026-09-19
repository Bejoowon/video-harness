import harness_lib as h
import scaffold as s


def cfg(tmp_path, agents=("claude", "codex")):
    c = h.default_config()
    c["workspace"]["name"] = "테스트작업실"
    c["agents"] = list(agents)
    c["channels"] = [{"id": "dongne-hanbakwi", "name": "동네한바퀴", "format": "9:16", "kind": "narration-shorts",
                      "target_seconds": 60, "language": "ko", "concept": "진짜 이야기", "opening": ""}]
    return c


def test_workspace_creates_docs_and_dirs(tmp_path):
    r = s.scaffold_workspace(tmp_path, cfg(tmp_path))
    assert (tmp_path / "AGENTS.md").is_file()
    assert (tmp_path / "CLAUDE.md").read_text(encoding="utf-8").strip() == "@AGENTS.md"
    assert (tmp_path / "스타일_라이브러리/06_참고영상").is_dir()
    assert "AGENTS.md" in " ".join(r["created"])


def test_no_claude_md_when_codex_only(tmp_path):
    s.scaffold_workspace(tmp_path, cfg(tmp_path, agents=("codex",)))
    assert not (tmp_path / "CLAUDE.md").exists()


def test_idempotent_never_overwrites(tmp_path):
    s.scaffold_workspace(tmp_path, cfg(tmp_path))
    (tmp_path / "AGENTS.md").write_text("내가 고친 내용", encoding="utf-8")
    r = s.scaffold_workspace(tmp_path, cfg(tmp_path))
    assert (tmp_path / "AGENTS.md").read_text(encoding="utf-8") == "내가 고친 내용"
    assert any("AGENTS.md" in x for x in r["skipped"])


def test_channel_layout(tmp_path):
    c = cfg(tmp_path)
    s.scaffold_channel(tmp_path, c, c["channels"][0])
    base = tmp_path / "동네한바퀴"
    for d in s.CHANNEL_DIRS:
        assert (base / d).is_dir(), d
    guide = (base / "채널기준.md").read_text(encoding="utf-8")
    assert "동네한바퀴" in guide and "진짜 이야기" in guide
    assert (base / "03_편집프로젝트/_채널공용/frame.md").is_file()


def test_reference_list_rendered(tmp_path):
    c = cfg(tmp_path)
    c["channels"][0]["references"] = [{"url": "https://youtube.com/shorts/abc", "likes": "자막: 크고 가운데", "status": "pending"}]
    s.scaffold_workspace(tmp_path, c)
    s.scaffold_channel(tmp_path, c, c["channels"][0])
    ref_dir = tmp_path / "동네한바퀴/02_기획과자막/스타일레퍼런스"
    listing = (ref_dir / "레퍼런스_목록.md").read_text(encoding="utf-8")
    assert "https://youtube.com/shorts/abc" in listing and "자막: 크고 가운데" in listing and "미분석" in listing
    assert (ref_dir / "레퍼런스_모으는_법.md").is_file()
    forms = tmp_path / "스타일_라이브러리/06_참고영상/_양식"
    for name in ["원본정보.md", "구조분석.md", "스타일분석.md", "적용규칙.md", "metadata.json"]:
        assert (forms / name).is_file(), name


def test_reference_list_empty_has_later_note(tmp_path):
    c = cfg(tmp_path)
    s.scaffold_channel(tmp_path, c, c["channels"][0])
    listing = (tmp_path / "동네한바퀴/02_기획과자막/스타일레퍼런스/레퍼런스_목록.md").read_text(encoding="utf-8")
    assert "나중에" in listing


def test_agents_md_has_core_rules(tmp_path):
    s.scaffold_workspace(tmp_path, cfg(tmp_path))
    text = (tmp_path / "AGENTS.md").read_text(encoding="utf-8")
    musts = [
        "01_원본영상", "작업 공간 루트에서 실행", "locked", "미확인", "_채널공용",
        "원본은 보존", "승인", "분석용", ".env", "본인 동의",
    ]
    for must in musts:
        assert must in text, must


def test_recording_guide_created_for_record_and_local_mlx(tmp_path):
    for mode in ("record", "local-mlx"):
        c = cfg(tmp_path)
        c["modules"]["voice"]["mode"] = mode
        s.scaffold_workspace(tmp_path / mode, c)
        assert (tmp_path / mode / "도구/tts/녹음가이드.md").is_file(), mode


def test_recording_dir_only_for_local_mlx(tmp_path):
    c = cfg(tmp_path)
    c["modules"]["voice"]["mode"] = "local-mlx"
    s.scaffold_workspace(tmp_path, c)
    assert (tmp_path / "도구/tts/녹음").is_dir()


def test_recording_guide_absent_for_cloud(tmp_path):
    c = cfg(tmp_path)
    c["modules"]["voice"]["mode"] = "cloud"
    s.scaffold_workspace(tmp_path, c)
    assert not (tmp_path / "도구/tts/녹음가이드.md").exists()
    assert not (tmp_path / "도구/tts").exists()


def test_channel_provenance_forms_created(tmp_path):
    c = cfg(tmp_path)
    s.scaffold_channel(tmp_path, c, c["channels"][0])
    forms = tmp_path / "동네한바퀴/02_기획과자막/_양식"
    assert (forms / "출처와제작기록.md").is_file()
    assert (forms / "provenance.json").is_file()


def test_adopt_existing_registers_without_touching(tmp_path):
    (tmp_path / "동네한바퀴/01_원본영상").mkdir(parents=True)
    (tmp_path / "AGENTS.md").write_text("기존 규칙", encoding="utf-8")
    c = h.default_config()
    found = s.adopt_existing(tmp_path, c)
    assert [x["name"] for x in found] == ["동네한바퀴"] and found[0]["adopted"] is True
    assert (tmp_path / "AGENTS.md").read_text(encoding="utf-8") == "기존 규칙"


def test_copy_tools_follows_modules(tmp_path):
    c = cfg(tmp_path)
    c["modules"]["sources"] = ["own-footage"]
    c["modules"]["handoff"]["editor"] = "none"
    s.copy_tools(tmp_path, c)
    assert not (tmp_path / "도구/stock").exists()
    assert not (tmp_path / "도구/export").exists()
    assert (tmp_path / "도구/style/check_style.py").is_file()


def test_copy_tools_includes_export_tools_when_handoff_editor_set(tmp_path):
    c = cfg(tmp_path)
    c["modules"]["handoff"]["editor"] = "premiere"
    s.copy_tools(tmp_path, c)
    assert (tmp_path / "도구/export/to_premiere_xml.py").is_file()
    assert (tmp_path / "도구/export/handoff_common.py").is_file()
    assert (tmp_path / "도구/export/to_capcut.py").is_file()


def test_copy_tools_includes_stock_search_when_selected(tmp_path):
    c = cfg(tmp_path)
    c["modules"]["sources"] = ["stock"]
    s.copy_tools(tmp_path, c)
    assert (tmp_path / "도구/stock/search.py").is_file()


def test_channel_frame_md_canvas_matches_9x16_format(tmp_path):
    c = cfg(tmp_path)
    c["channels"][0]["format"] = "9:16"
    s.scaffold_channel(tmp_path, c, c["channels"][0])
    frame_text = (tmp_path / "동네한바퀴/03_편집프로젝트/_채널공용/frame.md").read_text(encoding="utf-8")
    assert "canvas: {width: 1080, height: 1920, fps: 30}" in frame_text


def test_channel_frame_md_canvas_matches_16x9_format(tmp_path):
    c = cfg(tmp_path)
    c["channels"][0]["format"] = "16:9"
    s.scaffold_channel(tmp_path, c, c["channels"][0])
    frame_text = (tmp_path / "동네한바퀴/03_편집프로젝트/_채널공용/frame.md").read_text(encoding="utf-8")
    assert "canvas: {width: 1920, height: 1080, fps: 30}" in frame_text


def _frame_text(tmp_path, channel_extra):
    c = cfg(tmp_path)
    c["channels"][0].update(channel_extra)
    s.scaffold_channel(tmp_path, c, c["channels"][0])
    return (tmp_path / "동네한바퀴/03_편집프로젝트/_채널공용/frame.md").read_text(encoding="utf-8")


def test_frame_md_records_interview_answers_with_defaults(tmp_path):
    text = _frame_text(tmp_path, {})
    assert "style_start: later" in text
    assert "consistency_level: decide-later" in text


def test_frame_md_records_chosen_style_start_and_consistency(tmp_path):
    text = _frame_text(tmp_path, {"style_start": "reference", "consistency": "variation"})
    assert "style_start: reference" in text
    assert "consistency_level: variation" in text


def test_frame_md_fixed_consistency_locks_accent_and_transitions(tmp_path):
    text = _frame_text(tmp_path, {"consistency": "fixed"})
    assert '"motion.transitions"' in text and '"colors.accent"' in text
    assert "choose: {}" in text
    # 포맷 고정형은 삽화 색도 frame.md의 색으로 제한한다 — 검사기가 아니라 선언이 정한다.
    assert 'free: ["footage"]' in text
    assert "illustration_colors" not in text.split("consistency:\n")[1]


def test_frame_md_variation_and_decide_later_keep_default_block(tmp_path):
    for value in ("variation", "decide-later"):
        text = _frame_text(tmp_path / value, {"consistency": value})
        assert "choose: {" in text and "choose: {}" not in text
        locked_line = [l for l in text.splitlines() if l.strip().startswith("locked:")][0]
        assert "colors.accent" not in locked_line and "motion.transitions" not in locked_line


def test_channel_guide_shows_style_choices_in_korean(tmp_path):
    c = cfg(tmp_path)
    c["channels"][0].update({"style_start": "reference", "consistency": "fixed"})
    s.scaffold_channel(tmp_path, c, c["channels"][0])
    guide = (tmp_path / "동네한바퀴/채널기준.md").read_text(encoding="utf-8")
    assert "레퍼런스" in guide and "포맷 고정형" in guide
    # 영상 유형도 사용자가 읽는 문서에서는 한국어로 보여 준다 (원시 id를 읽히지 않는다).
    assert "내레이션 쇼츠" in guide and "narration-shorts" not in guide


def test_channel_scaffold_copies_remotion_template_when_engine_remotion(tmp_path):
    c = cfg(tmp_path)
    c["modules"]["render"]["engine"] = "remotion"
    s.scaffold_channel(tmp_path, c, c["channels"][0])
    dest = tmp_path / "동네한바퀴/03_편집프로젝트/_채널공용/회차템플릿-remotion"
    assert (dest / "package.json").is_file()


def test_channel_scaffold_skips_remotion_template_when_engine_hyperframes(tmp_path):
    c = cfg(tmp_path)
    c["modules"]["render"]["engine"] = "hyperframes"
    s.scaffold_channel(tmp_path, c, c["channels"][0])
    dest = tmp_path / "동네한바퀴/03_편집프로젝트/_채널공용/회차템플릿-remotion"
    assert not dest.exists()


def test_copy_asset_dir_ignores_pycache_and_dotfiles(tmp_path):
    src = tmp_path / "src"
    pycache = src / "__pycache__"
    pycache.mkdir(parents=True)
    (pycache / "build_tokens.cpython-312.pyc").write_bytes(b"junk")
    (src / "build_tokens.py").write_text("print(1)", encoding="utf-8")
    (src / ".DS_Store").write_bytes(b"junk")

    dest = tmp_path / "dest"
    report = {"created": [], "skipped": []}
    s._copy_asset_dir(src, dest, report)

    assert (dest / "build_tokens.py").is_file()
    assert not (dest / "__pycache__").exists()
    assert not (dest / ".DS_Store").exists()


# --- 아래는 최종 리뷰 I3·I4·I5·M3에 대한 커버리지다. ---


def _hyperframes_template(tmp_path, channel_format):
    c = cfg(tmp_path)
    c["channels"][0]["format"] = channel_format
    s.scaffold_channel(tmp_path, c, c["channels"][0])
    return tmp_path / "동네한바퀴/03_편집프로젝트/_채널공용/회차템플릿"


def test_copied_hyperframes_template_keeps_portrait_canvas_for_9x16(tmp_path):
    index = (_hyperframes_template(tmp_path, "9:16") / "index.html").read_text(encoding="utf-8")
    assert 'data-width="1080" data-height="1920"' in index
    assert 'content="width=1080, height=1920"' in index


def test_copied_hyperframes_template_is_rewritten_to_landscape_for_16x9(tmp_path):
    """16:9 채널이 세로 템플릿을 받으면 첫 회차부터 캔버스가 어긋난다."""
    index = (_hyperframes_template(tmp_path, "16:9") / "index.html").read_text(encoding="utf-8")
    assert 'data-width="1920" data-height="1080"' in index
    assert 'content="width=1920, height=1080"' in index
    assert "1080, height=1920" not in index


def _remotion_theme(tmp_path, channel_format):
    c = cfg(tmp_path)
    c["modules"]["render"]["engine"] = "remotion"
    c["channels"][0]["format"] = channel_format
    s.scaffold_channel(tmp_path, c, c["channels"][0])
    dest = tmp_path / "동네한바퀴/03_편집프로젝트/_채널공용/회차템플릿-remotion"
    return (dest / "src" / "theme.ts").read_text(encoding="utf-8")


def test_copied_remotion_theme_keeps_portrait_canvas_for_9x16(tmp_path):
    theme = _remotion_theme(tmp_path, "9:16")
    assert "width: 1080," in theme and "height: 1920," in theme


def test_copied_remotion_theme_is_rewritten_to_landscape_for_16x9(tmp_path):
    theme = _remotion_theme(tmp_path, "16:9")
    assert "width: 1920," in theme and "height: 1080," in theme


def test_set_frame_canvas_raises_when_the_canvas_line_is_missing(tmp_path):
    """정규식이 빗나가면 조용히 통과하지 말고 멈춘다(M3)."""
    import pytest

    with pytest.raises(ValueError):
        s._set_frame_canvas("---\nstatus: draft\n---\n", "16:9")


def test_set_frame_consistency_raises_when_the_canvas_line_is_missing():
    import pytest

    with pytest.raises(ValueError):
        s._set_frame_consistency("---\nstatus: draft\n---\n", {})


def test_copy_tools_restores_a_deleted_tool_without_touching_an_edited_one(tmp_path):
    """도구 디렉터리는 파일 단위로 멱등이어야 doctor의 '다시 실행하세요'가 참이 된다(I5)."""
    c = cfg(tmp_path)
    s.copy_tools(tmp_path, c)

    style_dir = tmp_path / "도구/style"
    (style_dir / "check_style.py").unlink()
    (style_dir / "build_tokens.py").write_text("# 내가 고친 내용", encoding="utf-8")

    report = s.copy_tools(tmp_path, c)

    assert (style_dir / "check_style.py").is_file()
    assert (style_dir / "build_tokens.py").read_text(encoding="utf-8") == "# 내가 고친 내용"
    assert any("check_style.py" in x for x in report["created"])
    assert any("build_tokens.py" in x for x in report["skipped"])


def test_copy_asset_dir_copies_binary_files(tmp_path):
    src = tmp_path / "src"
    (src / "nested").mkdir(parents=True)
    (src / "nested" / "blob.png").write_bytes(b"\x89PNG\x00\xff")
    dest = tmp_path / "dest"
    s._copy_asset_dir(src, dest, {"created": [], "skipped": []})
    assert (dest / "nested" / "blob.png").read_bytes() == b"\x89PNG\x00\xff"


def test_adopt_without_config_fails_in_korean_and_creates_nothing(tmp_path, capsys):
    """`--adopt`가 config를 지어내면 이후 `init`이 막혀 복구할 길이 없어진다(I4)."""
    (tmp_path / "동네한바퀴/01_원본영상").mkdir(parents=True)

    code = s.main([str(tmp_path), "--adopt"])

    assert code == 1
    assert not (tmp_path / "harness.config.json").exists()
    err = capsys.readouterr().err
    assert "harness.config.json" in err and "config_tool.py" in err


def test_adopt_with_config_registers_channels_through_validation(tmp_path):
    (tmp_path / "동네한바퀴/01_원본영상").mkdir(parents=True)
    h.save_config(tmp_path, cfg(tmp_path) | {"channels": []})

    code = s.main([str(tmp_path), "--adopt"])

    assert code == 0
    saved = h.load_config(tmp_path)
    assert [c["name"] for c in saved["channels"]] == ["동네한바퀴"]
    assert h.validate_config(saved) == []


def test_adopt_refuses_to_save_when_the_existing_config_is_invalid(tmp_path, capsys):
    (tmp_path / "동네한바퀴/01_원본영상").mkdir(parents=True)
    broken = cfg(tmp_path)
    broken["channels"] = []
    broken["modules"]["render"]["engine"] = "aftereffects"
    h.save_config(tmp_path, broken)

    code = s.main([str(tmp_path), "--adopt"])

    assert code == 1
    assert h.load_config(tmp_path)["channels"] == []
    assert "render.engine" in capsys.readouterr().err


def test_agents_md_tells_how_to_regenerate_the_token_files(tmp_path):
    """workspace로 가는 문서만이 에이전트가 읽는 규칙이다 (I7)."""
    s.scaffold_workspace(tmp_path, cfg(tmp_path))
    text = (tmp_path / "AGENTS.md").read_text(encoding="utf-8")
    assert "build_tokens.py" in text
    assert "--css" in text and "--ts" in text
    assert "check_style.py" in text
    assert "손으로 고치지 않는다" in text


def test_agents_md_tells_how_to_pass_the_transcribe_settings(tmp_path):
    """`modules.transcribe.*`를 읽는 사람이 아무도 없으면 기록이 무의미하다 (I9)."""
    s.scaffold_workspace(tmp_path, cfg(tmp_path))
    text = (tmp_path / "AGENTS.md").read_text(encoding="utf-8")
    assert "transcribe.py" in text
    assert "modules.transcribe.model" in text and "modules.transcribe.engine" in text


def test_agents_md_does_not_point_at_the_empty_parts_folder(tmp_path):
    """`부품/`은 세팅이 채우지 않는다. 참조하라고 시키지 않는다 (I6)."""
    s.scaffold_workspace(tmp_path, cfg(tmp_path))
    text = (tmp_path / "AGENTS.md").read_text(encoding="utf-8")
    assert "제목바·자막·출처표기는 `_채널공용/부품/`을 참조한다" not in text
    assert "비어 있는 자리" in text


def test_parts_folder_is_created_but_stays_empty(tmp_path):
    c = cfg(tmp_path)
    s.scaffold_channel(tmp_path, c, c["channels"][0])
    parts = tmp_path / "동네한바퀴/03_편집프로젝트/_채널공용/부품"
    assert parts.is_dir() and list(parts.iterdir()) == []


def test_sub_exactly_once_rejects_a_second_occurrence():
    """한 번만 치환하고 나머지를 남기면 반쪽짜리 결과가 성공으로 보고된다."""
    import re

    import pytest

    pattern = re.compile(r"width=\d+")
    with pytest.raises(ValueError):
        s._sub_exactly_once(pattern, "width=1920", "width=1080 그리고 width=1080", "두 번 나오는 자리")


def test_sub_exactly_once_accepts_a_single_occurrence():
    import re

    pattern = re.compile(r"width=\d+")
    assert s._sub_exactly_once(pattern, "width=1920", "a width=1080 b", "한 번") == "a width=1920 b"


# --- 출발점(workflow)이 채널기준.md의 "작업 순서"를 정한다 ---


def _channel_guide(tmp_path, channel_extra=None, sample_seconds=None):
    c = cfg(tmp_path)
    if channel_extra:
        c["channels"][0].update(channel_extra)
    if sample_seconds is not None:
        c["rules"]["sample_seconds"] = sample_seconds
    s.scaffold_channel(tmp_path, c, c["channels"][0])
    return (tmp_path / "동네한바퀴/채널기준.md").read_text(encoding="utf-8")


def test_channel_guide_shows_workflow_in_korean():
    labels = {"footage-first": "찍은 영상 먼저", "script-first": "대본 먼저", "per-episode": "회차마다 정함"}
    for value, label in labels.items():
        assert s.WORKFLOW_LABELS[value] == label, value


def test_channel_guide_records_footage_first_order(tmp_path):
    guide = _channel_guide(tmp_path, {"workflow": "footage-first"})
    assert "- 출발점: 찍은 영상 먼저" in guide
    assert "## 작업 순서" in guide
    assert "촬영본 확인" in guide and "전사" in guide
    assert "전사 결과가 원본" in guide
    assert "footage-first" not in guide


def test_channel_guide_records_script_first_order(tmp_path):
    guide = _channel_guide(tmp_path, {"workflow": "script-first"})
    assert "- 출발점: 대본 먼저" in guide
    assert "레퍼런스 분석" in guide and "대본이 자막의 원본" in guide
    assert "촬영본 확인" not in guide


def test_channel_guide_renders_both_orders_for_per_episode(tmp_path):
    guide = _channel_guide(tmp_path, {"workflow": "per-episode"})
    assert "- 출발점: 회차마다 정함" in guide
    assert "촬영본이 있는가" in guide
    assert "촬영본 확인" in guide and "대본이 자막의 원본" in guide


def test_channel_guide_falls_back_when_workflow_is_missing(tmp_path):
    guide = _channel_guide(tmp_path)
    assert "- 출발점: (아직 정하지 않음)" in guide
    assert "원본 확인 → 레퍼런스 분석 → 기획·대본" in guide


def test_workflow_steps_use_the_configured_sample_seconds(tmp_path):
    guide = _channel_guide(tmp_path, {"workflow": "script-first"}, sample_seconds=8)
    assert "8초 샘플" in guide
    assert "12초 샘플" not in guide


def test_agents_md_defers_the_work_order_to_each_channel(tmp_path):
    s.scaffold_workspace(tmp_path, cfg(tmp_path))
    text = (tmp_path / "AGENTS.md").read_text(encoding="utf-8")
    assert "채널기준.md" in text
    # 채널에 순서가 없을 때 쓰는 공통 순서는 그대로 남아 있어야 한다.
    assert "원본 확인 → 레퍼런스 분석 → 기획·대본" in text
    assert "샘플을 먼저 만든다" in text


# --- 대본 운율(script_rhythm): 새로 쓰는 내레이션의 기본값 ---


def _agents_md(tmp_path, script_rhythm=...):
    c = cfg(tmp_path)
    if script_rhythm is ...:
        pass
    elif script_rhythm is None:
        del c["rules"]["script_rhythm"]
    else:
        c["rules"]["script_rhythm"] = script_rhythm
    s.scaffold_workspace(tmp_path, c)
    return (tmp_path / "AGENTS.md").read_text(encoding="utf-8")


def _rhythm_section(text):
    """AGENTS.md의 "대본 쓰기" 절만 떼어 본다 (폴더 구조 목록과 섞이지 않게)."""
    assert text.index("## 대본 쓰기") < text.index("## 음성과 자막")
    return text.split("## 대본 쓰기", 1)[1].split("## 음성과 자막", 1)[0]


def test_agents_md_carries_the_rhythm_rule_by_default(tmp_path):
    text = _agents_md(tmp_path)
    assert "- 대본 운율: 3·4조 네 마디 (기본)" in text
    section = _rhythm_section(text)
    assert "3~4음절이 기본, 5음절까지 허용" in section
    assert "네 마디가 기본" in section
    assert "뜻이 먼저다" in section
    # 보조 도구지 관문이 아니다. 실제 CLI 모양과 `--strip`이 함께 적혀 있어야 한다.
    assert "도구/script/check_rhythm.py" in section
    assert "--strip" in section


def test_a_config_without_the_key_is_treated_as_meter(tmp_path):
    assert _agents_md(tmp_path, None) == _agents_md(tmp_path / "again", "meter")


def test_free_turns_the_rule_into_one_sentence(tmp_path):
    text = _agents_md(tmp_path, "free")
    assert "- 대본 운율: 자유" in text
    section = _rhythm_section(text)
    assert "운율 규칙을 적용하지 않는다" in section
    assert "3~4음절" not in section
    assert "check_rhythm.py" not in section


def test_channel_guide_records_the_rhythm_with_an_override_note(tmp_path):
    guide = _channel_guide(tmp_path)
    assert "- 대본 운율: 3·4조 네 마디 (기본) (이 채널만 다르게 하려면 여기에 적는다)" in guide


def _script_form(tmp_path, script_rhythm=None):
    c = cfg(tmp_path)
    if script_rhythm is not None:
        c["rules"]["script_rhythm"] = script_rhythm
    s.scaffold_channel(tmp_path, c, c["channels"][0])
    return (tmp_path / "동네한바퀴/02_기획과자막/_양식/대본_양식.md").read_text(encoding="utf-8")


def test_script_form_sits_next_to_the_provenance_form_with_the_rule_and_examples(tmp_path):
    form = _script_form(tmp_path)
    assert (tmp_path / "동네한바퀴/02_기획과자막/_양식/출처와제작기록.md").is_file()
    assert "동네한바퀴" in form
    assert "뜻이 먼저다" in form
    for example in ("오늘은 / 우리 동네 / 숨은 맛집 / 가 볼게", "냉장고에 / 남은 재료 / 이것만은 / 꼭 넣어", "딱 하나만 / 기억하세요"):
        assert example in form, example
    assert "3/4/4/3" in form and "4/5" in form
    assert "check_rhythm.py" in form and "--strip" in form


def test_script_form_is_plain_when_the_workspace_writes_freely(tmp_path):
    form = _script_form(tmp_path, "free")
    assert "동네한바퀴" in form
    assert "운율" not in form
    assert "check_rhythm.py" not in form


def test_script_form_is_never_overwritten(tmp_path):
    _script_form(tmp_path)
    path = tmp_path / "동네한바퀴/02_기획과자막/_양식/대본_양식.md"
    path.write_text("내가 고친 대본 양식", encoding="utf-8")
    _script_form(tmp_path)
    assert path.read_text(encoding="utf-8") == "내가 고친 대본 양식"


def test_copy_tools_always_delivers_the_rhythm_checker(tmp_path):
    c = cfg(tmp_path)
    s.copy_tools(tmp_path, c)
    assert (tmp_path / "도구/script/check_rhythm.py").is_file()
