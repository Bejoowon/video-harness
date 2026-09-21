# tests/test_finder_tool.py
import json
import re

import finder_tool as f
import harness_lib as h


def _workspace(tmp_path, **channel_extra):
    """레퍼런스 찾기가 읽을 작업 공간을 하나 만든다. 설정은 세팅 스킬의 형식 그대로다."""
    config = h.default_config()
    config["workspace"]["name"] = "내작업실"
    channel = {
        "id": "dongne-hanbakwi",
        "name": "동네한바퀴",
        "format": "9:16",
        "kind": "narration-shorts",
        "target_seconds": 60,
        "language": "ko",
    }
    channel.update(channel_extra)
    config["channels"] = [channel]
    h.save_config(tmp_path, config)
    return config


def _which(found):
    return lambda name: f"/bin/{name}" if name in found else None


ANSWERS = {
    "field": "건강",
    "audience": "40대 직장인",
    "format": "9:16",
    "workflow": "script-first",
    "platforms": ["youtube", "tiktok"],
    "focus": ["자막", "컷 템포"],
}


# --- detect ---


def test_detect_standalone_folder_has_no_channels(tmp_path):
    report = f.detect(tmp_path, which_fn=_which(set()))
    assert report["mode"] == "standalone"
    assert report["channels"] == []
    assert report["aside"] == {"found": False, "path": None}
    assert report["watch_installed"] is False


def test_detect_workspace_lists_channels_with_index_and_reference_count(tmp_path):
    _workspace(tmp_path, references=[{"url": "https://example.com/a", "likes": "자막", "status": "pending"}])
    report = f.detect(tmp_path, which_fn=_which(set()))
    assert report["mode"] == "workspace"
    channel = report["channels"][0]
    assert channel["index"] == 0
    assert channel["id"] == "dongne-hanbakwi"
    assert channel["name"] == "동네한바퀴"
    assert channel["format"] == "9:16"
    assert channel["references_count"] == 1


def test_detect_only_reports_direction_keys_that_exist(tmp_path):
    _workspace(tmp_path, audience="30~40대 동네 주민", workflow="footage-first")
    channel = f.detect(tmp_path, which_fn=_which(set()))["channels"][0]
    assert channel["audience"] == "30~40대 동네 주민"
    assert channel["workflow"] == "footage-first"
    for absent in ("scope", "tone", "platforms"):
        assert absent not in channel, absent


def test_detect_finds_aside_on_the_path(tmp_path):
    report = f.detect(tmp_path, which_fn=_which({"aside"}))
    assert report["aside"]["found"] is True
    assert report["aside"]["path"] == "/bin/aside"


def test_detect_points_at_the_setup_skills_config_tool(tmp_path):
    from pathlib import Path

    report = f.detect(tmp_path, which_fn=_which(set()))
    path = report["config_tool"]
    assert path is not None
    assert Path(path).is_absolute()
    assert Path(path).name == "config_tool.py"
    assert Path(path).exists()


def test_detect_reports_config_tool_as_null_when_the_setup_skill_is_absent(tmp_path):
    report = f.detect(tmp_path, which_fn=_which(set()), config_tool_fn=lambda: None)
    assert report["config_tool"] is None


def test_detect_reads_watch_from_the_config(tmp_path):
    config = _workspace(tmp_path)
    config["modules"]["reference"]["watch"] = True
    h.save_config(tmp_path, config)
    assert f.detect(tmp_path, which_fn=_which(set()))["watch_installed"] is True


def test_detect_keeps_a_broken_config_in_workspace_mode(tmp_path):
    (tmp_path / "harness.config.json").write_text("{망가진", encoding="utf-8")
    report = f.detect(tmp_path, which_fn=_which(set()))
    assert report["mode"] == "workspace"
    assert report["channels"] == []
    assert report["config_error"]


# --- brief ---


def test_brief_carries_the_platforms_format_and_count():
    text = f.build_brief(ANSWERS)
    assert "유튜브" in text and "틱톡" in text
    assert "인스타그램" not in text
    assert "9:16" in text
    assert "8개" in text


def test_brief_count_is_overridable():
    assert "3개" in f.build_brief(ANSWERS, count=3)


def test_brief_lists_every_field_each_candidate_must_come_back_with():
    text = f.build_brief(ANSWERS)
    for key in ("url", "what", "why_fit", "caution", "numbers_seen_on_page"):
        assert f"`{key}`" in text, key


def test_brief_carries_the_read_only_rules():
    text = f.build_brief(ANSWERS)
    assert "보기만 한다" in text
    for banned in ("구독", "좋아요", "댓글", "팔로우", "메시지", "저장"):
        assert banned in text, banned
    assert "로그인" in text
    assert "내려받지 않는다" in text
    assert "지어내지 않는다" in text


def test_brief_tells_the_browser_agent_to_stop_at_a_login_wall():
    text = f.build_brief(ANSWERS)
    assert "로그인 화면이 나오면" in text
    assert "건너뛰고" in text


def test_brief_asks_for_a_json_array_and_nothing_else():
    text = f.build_brief(ANSWERS)
    assert "JSON 배열" in text
    assert "다른 말을 쓰지 않는다" in text


def test_brief_is_deterministic():
    assert f.build_brief(ANSWERS) == f.build_brief(dict(ANSWERS))


def test_brief_includes_the_optional_answers_only_when_given():
    plain = f.build_brief(ANSWERS)
    assert "피하고 싶은 것" not in plain
    assert "비슷한 곳" not in plain

    rich = f.build_brief({**ANSWERS, "avoid": "자극적인 썸네일", "similar_to": ["https://example.com/c"]})
    assert "자극적인 썸네일" in rich
    assert "https://example.com/c" in rich


def test_validate_answers_accepts_a_good_answer_sheet():
    assert f.validate_answers(ANSWERS) == []


def test_validate_answers_rejects_bad_values():
    assert f.validate_answers({**ANSWERS, "format": "4:3"})
    assert f.validate_answers({**ANSWERS, "platforms": ["youtube", "네이버"]})
    assert f.validate_answers({**ANSWERS, "platforms": []})
    assert f.validate_answers({**ANSWERS, "focus": ["색감"]})
    assert f.validate_answers({k: v for k, v in ANSWERS.items() if k != "field"})
    assert f.validate_answers({**ANSWERS, "audience": "   "})


def test_validate_answers_messages_are_korean():
    errors = f.validate_answers({**ANSWERS, "format": "4:3"})
    assert any("포맷" in e for e in errors), errors


# --- 주소 다듬기와 중복 합치기 ---


def test_normalise_url_folds_the_three_youtube_shapes():
    canonical = f.normalise_url("https://www.youtube.com/watch?v=abc12345678")
    assert f.normalise_url("https://youtu.be/abc12345678") == canonical
    assert f.normalise_url("https://www.youtube.com/shorts/abc12345678") == canonical
    assert f.normalise_url("https://m.youtube.com/watch?v=abc12345678&si=xxxx") == canonical


def test_normalise_url_strips_tracking_slashes_and_host_case():
    assert f.normalise_url("HTTPS://WWW.TikTok.com/@someone/?utm_source=x") == "https://www.tiktok.com/@someone"


def test_classify_reads_the_host_and_the_path():
    assert f.classify("https://www.youtube.com/watch?v=abc12345678") == "youtube-video"
    assert f.classify("https://www.youtube.com/@handle") == "youtube-page"
    assert f.classify("https://www.tiktok.com/@someone") == "tiktok"
    assert f.classify("https://www.instagram.com/reel/abc/") == "instagram"
    assert f.classify("https://example.com/video") == "other"


# --- verify ---

YT_OK = json.dumps({"title": "진짜 제목", "author_name": "진짜 채널"})
TT_OK = json.dumps({"title": "틱톡 제목", "author_name": "틱톡 사람"})


def _fetch(table, seen=None):
    """가짜 네트워크. 주소별로 (상태 코드, 본문)을 돌려준다. 표에 없으면 404."""

    def fetch(url):
        if seen is not None:
            seen.append(url)
        for fragment, response in table.items():
            if fragment in url:
                return response
        return 404, ""

    return fetch


def test_verify_confirms_a_youtube_video_and_overwrites_title_and_author():
    result = f.verify_candidates(
        [{"url": "https://youtu.be/abc12345678", "what": "지어낸 제목", "title": "지어낸 제목"}],
        fetch=_fetch({"oembed": (200, YT_OK)}),
    )
    candidate = result["candidates"][0]
    assert candidate["status"] == "확인됨"
    assert candidate["title"] == "진짜 제목"
    assert candidate["author"] == "진짜 채널"


def test_verify_drops_a_youtube_video_the_endpoint_refuses():
    """실제 유튜브 oEmbed는 없는 영상에 404가 아니라 400을 준다."""
    result = f.verify_candidates(
        [{"url": "https://www.youtube.com/watch?v=zzzzzzzzzzz"}],
        fetch=_fetch({"oembed": (400, "Bad Request")}),
    )
    assert result["candidates"] == []
    assert result["dropped"][0]["status"] == "없는 주소"


def test_verify_checks_a_youtube_channel_with_a_page_request():
    seen = []
    result = f.verify_candidates(
        [{"url": "https://www.youtube.com/@handle"}],
        fetch=_fetch({"youtube.com/@handle": (200, "<title>어떤 채널 - YouTube</title>")}, seen),
    )
    assert result["candidates"][0]["status"] == "확인됨"
    assert result["candidates"][0]["title"] == "어떤 채널"
    assert not any("oembed" in url for url in seen)


def test_verify_drops_a_missing_youtube_channel():
    result = f.verify_candidates(
        [{"url": "https://www.youtube.com/@nosuchhandle"}], fetch=_fetch({})
    )
    assert result["candidates"] == []
    assert result["dropped"][0]["status"] == "없는 주소"


def test_verify_confirms_a_tiktok_profile():
    result = f.verify_candidates(
        [{"url": "https://www.tiktok.com/@someone"}], fetch=_fetch({"oembed": (200, TT_OK)})
    )
    assert result["candidates"][0]["status"] == "확인됨"
    assert result["candidates"][0]["author"] == "틱톡 사람"


def test_verify_drops_a_tiktok_url_the_endpoint_refuses():
    result = f.verify_candidates(
        [{"url": "https://www.tiktok.com/@nobody"}], fetch=_fetch({"oembed": (400, "")})
    )
    assert result["candidates"] == []


def test_verify_never_claims_an_instagram_link_and_never_requests_it():
    seen = []
    result = f.verify_candidates(
        [{"url": "https://www.instagram.com/reel/abc/"}], fetch=_fetch({}, seen)
    )
    assert result["candidates"][0]["status"] == "직접 확인 필요"
    assert seen == []


def test_verify_marks_an_unknown_host_as_needing_a_human():
    result = f.verify_candidates([{"url": "https://example.com/x"}], fetch=_fetch({}))
    assert result["candidates"][0]["status"] == "직접 확인 필요"


def test_verify_keeps_a_candidate_when_the_network_fails():
    def fetch(url):
        return None, "연결할 수 없습니다"

    result = f.verify_candidates([{"url": "https://youtu.be/abc12345678"}], fetch=fetch)
    assert result["candidates"][0]["status"] == "확인 실패"
    assert result["dropped"] == []


def test_verify_treats_a_server_error_as_unverified_not_as_missing():
    result = f.verify_candidates(
        [{"url": "https://youtu.be/abc12345678"}], fetch=_fetch({"oembed": (503, "")})
    )
    assert result["candidates"][0]["status"] == "확인 실패"


def test_verify_merges_duplicates_before_asking_the_network():
    seen = []
    result = f.verify_candidates(
        [
            {"url": "https://youtu.be/abc12345678", "why_fit": "자막이 크다"},
            {"url": "https://www.youtube.com/shorts/abc12345678", "caution": "광고가 많다"},
        ],
        fetch=_fetch({"oembed": (200, YT_OK)}, seen),
    )
    assert len(result["candidates"]) == 1
    assert result["candidates"][0]["why_fit"] == "자막이 크다"
    assert result["candidates"][0]["caution"] == "광고가 많다"
    assert len(seen) == 1


def test_verify_summary_counts_every_status():
    result = f.verify_candidates(
        [
            {"url": "https://youtu.be/abc12345678"},
            {"url": "https://www.instagram.com/reel/abc/"},
            {"url": "https://www.youtube.com/@nosuchhandle"},
        ],
        fetch=_fetch({"oembed": (200, YT_OK)}),
    )
    assert result["summary"]["확인됨"] == 1
    assert result["summary"]["직접 확인 필요"] == 1
    assert result["summary"]["없는 주소"] == 1


def test_parse_candidates_reads_a_json_array():
    raw = json.dumps([{"url": "https://youtu.be/abc12345678", "what": "쇼츠"}])
    assert f.parse_candidates(raw)[0]["what"] == "쇼츠"


def test_parse_candidates_pulls_urls_out_of_prose_and_marks_them():
    raw = "찾아봤습니다. https://youtu.be/abc12345678 과 https://www.tiktok.com/@someone 이 좋아 보입니다."
    candidates = f.parse_candidates(raw)
    assert [c["url"] for c in candidates] == [
        "https://youtu.be/abc12345678",
        "https://www.tiktok.com/@someone",
    ]
    assert all(c["what"] == "설명 없음" for c in candidates)


def test_parse_candidates_drops_trailing_punctuation():
    assert f.parse_candidates("(https://youtu.be/abc12345678).")[0]["url"] == "https://youtu.be/abc12345678"


def test_render_table_shows_the_columns_the_user_picks_from():
    result = f.verify_candidates(
        [{"url": "https://youtu.be/abc12345678", "what": "쇼츠", "why_fit": "자막", "caution": "없음"}],
        fetch=_fetch({"oembed": (200, YT_OK)}),
    )
    table = f.render_table(result)
    for header in ("주소", "무엇인지", "왜 맞는지", "주의점", "확인 상태"):
        assert header in table, header
    assert "확인됨" in table


def test_render_table_shows_the_real_name_next_to_the_claimed_one():
    """에이전트가 적어 온 제목이 지어낸 것일 때 사용자가 알아볼 수 있어야 한다."""
    result = f.verify_candidates(
        [{"url": "https://youtu.be/abc12345678", "what": "지어낸 제목"}],
        fetch=_fetch({"oembed": (200, YT_OK)}),
    )
    row = [line for line in f.render_table(result).splitlines() if "youtube.com" in line][0]
    assert "지어낸 제목" in row
    assert "실제: 진짜 제목 / 진짜 채널" in row


def test_render_table_escapes_pipes_so_the_table_does_not_break():
    result = {"candidates": [{"url": "https://example.com/a", "what": "가|나", "status": "직접 확인 필요"}], "dropped": [], "summary": {}}
    row = [line for line in f.render_table(result).splitlines() if "example.com" in line][0]
    assert "가\\|나" in row
    # 칸을 가르는 `|`는 여섯 칸 표의 일곱 개뿐이다. 값 안의 `|`는 이스케이프되어 세지 않는다.
    assert len(re.findall(r"(?<!\\)\|", row)) == 7


# --- record (단독 모드) ---


def test_record_creates_the_candidate_file(tmp_path):
    result = f.record_standalone(
        tmp_path, [{"url": "https://youtu.be/abc12345678", "what": "쇼츠", "likes": "자막이 크다", "status": "확인됨"}]
    )
    text = (tmp_path / "레퍼런스_후보.md").read_text(encoding="utf-8")
    assert result["created"] is True
    assert "https://youtu.be/abc12345678" in text
    assert "자막이 크다" in text
    assert "확인됨" in text
    assert "분석용" in text


def test_record_appends_without_touching_what_the_user_wrote(tmp_path):
    f.record_standalone(tmp_path, [{"url": "https://youtu.be/abc12345678", "likes": "자막"}])
    path = tmp_path / "레퍼런스_후보.md"
    path.write_text(path.read_text(encoding="utf-8") + "\n내가 적은 메모\n", encoding="utf-8")

    result = f.record_standalone(tmp_path, [{"url": "https://www.tiktok.com/@someone", "likes": "컷 템포"}])

    text = path.read_text(encoding="utf-8")
    assert result["created"] is False
    assert "내가 적은 메모" in text
    assert "자막" in text and "컷 템포" in text
    assert "| 2 |" in text


def test_record_skips_a_url_already_in_the_file(tmp_path):
    f.record_standalone(tmp_path, [{"url": "https://youtu.be/abc12345678", "likes": "자막"}])
    result = f.record_standalone(tmp_path, [{"url": "https://www.youtube.com/watch?v=abc12345678", "likes": "다시"}])
    text = (tmp_path / "레퍼런스_후보.md").read_text(encoding="utf-8")
    assert result["added"] == []
    assert result["skipped"] == ["https://www.youtube.com/watch?v=abc12345678"]
    assert "다시" not in text


# --- CLI ---


def test_cli_detect_prints_json(tmp_path, capsys):
    assert f.main(["detect", str(tmp_path)]) == 0
    assert json.loads(capsys.readouterr().out)["mode"] == "standalone"


def test_cli_brief_reads_the_answer_file(tmp_path, capsys):
    answers = tmp_path / "answers.json"
    answers.write_text(json.dumps(ANSWERS, ensure_ascii=False), encoding="utf-8")
    assert f.main(["brief", "--answers", str(answers)]) == 0
    assert "유튜브" in capsys.readouterr().out


def test_cli_brief_refuses_a_bad_answer_file_with_exit_2(tmp_path, capsys):
    answers = tmp_path / "answers.json"
    answers.write_text(json.dumps({**ANSWERS, "format": "4:3"}, ensure_ascii=False), encoding="utf-8")
    assert f.main(["brief", "--answers", str(answers)]) == 2
    assert "포맷" in capsys.readouterr().err


def test_cli_brief_refuses_a_missing_file_with_exit_2(tmp_path, capsys):
    assert f.main(["brief", "--answers", str(tmp_path / "없는파일.json")]) == 2
    assert capsys.readouterr().err


def test_cli_verify_exits_zero_even_when_nothing_could_be_checked(tmp_path, capsys, monkeypatch):
    monkeypatch.setattr(f, "http_get", lambda url: (None, "연결 실패"))
    candidates = tmp_path / "candidates.json"
    candidates.write_text(json.dumps([{"url": "https://youtu.be/abc12345678"}]), encoding="utf-8")

    assert f.main(["verify", str(candidates)]) == 0
    assert json.loads(capsys.readouterr().out)["candidates"][0]["status"] == "확인 실패"


def test_cli_verify_table_flag(tmp_path, capsys, monkeypatch):
    monkeypatch.setattr(f, "http_get", lambda url: (200, YT_OK))
    candidates = tmp_path / "candidates.json"
    candidates.write_text(json.dumps([{"url": "https://youtu.be/abc12345678"}]), encoding="utf-8")

    assert f.main(["verify", str(candidates), "--table"]) == 0
    assert "확인 상태" in capsys.readouterr().out


def test_cli_record_standalone(tmp_path, capsys):
    picked = tmp_path / "picked.json"
    picked.write_text(json.dumps([{"url": "https://youtu.be/abc12345678", "likes": "자막"}]), encoding="utf-8")

    assert f.main(["record", "--standalone", str(tmp_path), "--picked", str(picked)]) == 0
    assert json.loads(capsys.readouterr().out)["added"]
    assert (tmp_path / "레퍼런스_후보.md").is_file()


def test_the_tool_only_uses_the_standard_library():
    from pathlib import Path
    import re as _re

    source = Path(f.__file__).read_text(encoding="utf-8")
    imported = set(_re.findall(r"^(?:import|from)\s+([a-zA-Z_][\w.]*)", source, _re.M))
    allowed = {
        "__future__", "argparse", "html", "json", "re", "shutil", "sys", "urllib",
        "urllib.error", "urllib.parse", "urllib.request", "pathlib", "typing",
    }
    assert imported <= allowed, imported - allowed
