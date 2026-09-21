# tests/test_finder_skill_md.py
import re
from pathlib import Path

S = Path(__file__).resolve().parents[1] / "skills/video-reference-finder"
SETUP = Path(__file__).resolve().parents[1] / "skills/video-harness-setup"
R = S / "references"

# 하네스 중립: 특정 에이전트의 도구 이름을 쓰지 않는다. "웹을 검색하거나 페이지를 열 수
# 있는 수단"처럼 말한다. Aside는 도구가 아니라 바깥 CLI라서 이 목록에 없다.
BANNED = [
    "AskUserQuestion", "WebSearch", "WebFetch", "Bash tool", "Read tool",
    "/Users/", "/opt/homebrew", "/opt/miniconda3",
]

PATH_PLACEHOLDERS = ("<폴더>", "<ws>", "<답 파일>", "<후보 파일>", "<고른 목록 파일>", "<config_tool 경로>")


def text():
    return (S / "SKILL.md").read_text(encoding="utf-8")


_CODE_SPAN_RE = re.compile(r"`([^`\n]+)`")
_FENCE_RE = re.compile(r"```.*?\n(.*?)```", re.S)
_SCRIPT_RE = re.compile(r"scripts/([A-Za-z0-9_]+\.py)")
_FLAG_RE = re.compile(r"--[a-z][a-z0-9-]*")
_ADD_ARGUMENT_RE = re.compile(r"add_argument\(\s*\"(--[a-z0-9-]+)\"")


def _command_chunks(body: str | None = None) -> list[str]:
    body = text() if body is None else body
    chunks = _CODE_SPAN_RE.findall(body)
    for block in _FENCE_RE.findall(body):
        chunks.extend(block.replace("\\\n", " ").splitlines())
    return chunks


# --- 앞머리와 길이 ---


def test_frontmatter_only_name_and_description():
    fm = re.match(r"^---\n(.*?)\n---\n", text(), re.S).group(1)
    keys = [line.split(":")[0] for line in fm.splitlines() if re.match(r"^[a-z_]+:", line)]
    assert keys == ["name", "description"]
    assert "name: video-reference-finder" in fm


def test_description_lists_the_korean_trigger_phrases():
    fm = re.match(r"^---\n(.*?)\n---\n", text(), re.S).group(1)
    for trigger in ["레퍼런스 찾아줘", "참고할 채널 찾아줘", "비슷한 채널 더 찾아줘", "벤치마킹할 영상 찾아줘"]:
        assert trigger in fm, trigger


def test_length_and_neutral_wording():
    body = text()
    assert len(body.splitlines()) <= 200
    for banned in BANNED:
        assert banned not in body, banned


def test_the_skill_never_names_a_harness_tool_for_the_web():
    assert "웹을 검색하거나 페이지를 열 수 있는 수단" in text()


def test_no_unresolvable_skill_placeholder():
    assert "<skill>" not in text()


# --- 대화 규칙이 맨 위에 있다 ---


def test_the_conversation_rules_come_before_anything_else():
    body = text()
    assert body.index("## 대화 규칙") < body.index("## 명령 규칙")
    assert body.index("## 대화 규칙") < body.index("## 1.")


def _rules_block() -> str:
    body = text()
    return body[body.index("## 대화 규칙"): body.index("## 명령 규칙")]


def test_the_rules_are_short_and_absolute():
    block = _rules_block()
    assert "질문을 하면 거기서 멈추고 사용자의 답을 기다린다" in block
    assert "대신 답하거나 대신 고르지 않는다" in block
    assert "추측해서 채우지 않는다" in block
    assert "물을 수 없는 환경" in block
    assert len(block.splitlines()) <= 20


def test_a_run_that_cannot_ask_stops_with_the_question_list():
    block = _rules_block()
    assert "질문 목록만 내놓고 멈춘다" in block


def test_the_user_is_the_one_who_picks():
    body = text()
    assert "사용자가 고른다" in body or "고르는 사람은 사용자다" in body


# --- 흐름과 명령 ---


def test_every_step_of_the_flow_is_present():
    body = text()
    for step in ["detect", "brief", "verify", "record"]:
        assert re.search(rf'finder_tool\.py"? {step}\b', body), step


def test_named_scripts_exist():
    named = set(_SCRIPT_RE.findall(text()))
    assert named
    for name in named:
        assert (S / "scripts" / name).exists(), name


def _declared_flags(script: str) -> set[str]:
    source = (S / "scripts" / script).read_text(encoding="utf-8")
    return set(_ADD_ARGUMENT_RE.findall(source))


def test_flags_used_on_our_script_exist_in_its_parser():
    for chunk in _command_chunks():
        scripts = _SCRIPT_RE.findall(chunk)
        if not scripts:
            continue
        allowed: set[str] = set()
        for script in scripts:
            allowed |= _declared_flags(script)
        for flag in _FLAG_RE.findall(chunk):
            assert flag in allowed, (chunk.strip(), flag, sorted(allowed))


def _runnable(chunks: list[str]) -> list[str]:
    """실행할 수 있는 명령 조각만 고른다. `<폴더>`처럼 자리표시자만 가리키는 조각은 명령이 아니다."""
    return [c for c in chunks if re.search(r"\bpython3? |^aside\b", c.strip())]


def test_path_placeholders_are_always_quoted():
    for chunk in _runnable(_command_chunks()):
        for placeholder in PATH_PLACEHOLDERS:
            if placeholder not in chunk:
                continue
            assert not re.search(rf'(?<!"){re.escape(placeholder)}', chunk), (chunk.strip(), placeholder)


def test_the_default_candidate_count_and_the_focus_question_are_stated():
    body = text()
    assert "8개" in body
    assert "특히 보고 싶은" in body


def test_the_four_verification_statuses_appear_with_their_exact_labels():
    body = text()
    for status in ["확인됨", "없는 주소", "직접 확인 필요", "확인 실패"]:
        assert status in body, status


def test_workspace_recording_goes_through_the_setup_skills_config_tool():
    body = text()
    assert "add-reference" in body
    assert "config_tool.py" in body
    assert "레퍼런스_목록.md" in body


def test_the_add_reference_flags_exist_in_the_setup_skills_parser():
    source = (SETUP / "scripts" / "config_tool.py").read_text(encoding="utf-8")
    declared = set(_ADD_ARGUMENT_RE.findall(source))
    for flag in ("--channel", "--reference"):
        assert flag in declared, flag


def test_standalone_mode_writes_the_candidate_file():
    assert "레퍼런스_후보.md" in text()


def test_too_few_candidates_asks_before_widening():
    assert "3개 미만" in text()


# --- Aside ---


def test_aside_is_documented_with_its_real_commands():
    body = text()
    assert 'aside exec "' in body
    assert "aside session stop" in body
    assert "60초" in body
    assert "10분" in body


def test_aside_permission_is_never_raised():
    body = text()
    assert "`--permission full-access`는 쓰지 않는다" in body
    for chunk in _command_chunks():
        if chunk.strip().startswith("aside"):
            assert "--permission" not in chunk, chunk.strip()


def test_the_agent_tells_the_user_the_cost_before_starting_aside():
    body = text()
    assert "몇 분" in body
    assert "사용량" in body


def test_aside_failure_is_reported_not_swallowed():
    body = text()
    assert "조용히 넘어가지 않는다" in body


# --- 안전 규칙 ---


def test_the_safety_rules_are_all_there():
    body = text()
    assert "보기만 한다" in body
    for banned in ("구독", "좋아요", "댓글", "팔로우", "메시지", "저장"):
        assert banned in body, banned
    assert "로그인" in body
    assert "내려받" in body
    assert "지어내지 않는다" in body
    assert "분석용" in body


# --- 참고 문서 ---


def test_every_reference_file_is_linked():
    body = text()
    files = list(R.glob("*.md"))
    assert files
    for path in files:
        assert path.name in body, path.name


def test_reference_files_stay_neutral_and_finished():
    for path in R.glob("*.md"):
        body = path.read_text(encoding="utf-8")
        for banned in BANNED:
            assert banned not in body, (path.name, banned)
        assert "TODO" not in body, path.name
        assert "TBD" not in body, path.name
        assert "<skill>" not in body, path.name


def test_reference_commands_quote_their_path_arguments():
    for path in R.glob("*.md"):
        for chunk in _runnable(_command_chunks(path.read_text(encoding="utf-8"))):
            for placeholder in PATH_PLACEHOLDERS:
                if placeholder not in chunk:
                    continue
                assert not re.search(rf'(?<!"){re.escape(placeholder)}', chunk), (path.name, chunk.strip())


def test_the_judging_reference_covers_the_criteria_and_how_to_show_candidates():
    body = (R / "judging.md").read_text(encoding="utf-8")
    assert "포맷" in body
    assert "1~3개" in body
    assert "분석용" in body
    assert "사용자" in body


def test_the_aside_reference_covers_handing_off_reporting_stopping_and_failing():
    body = (R / "aside.md").read_text(encoding="utf-8")
    assert 'aside exec "' in body
    assert "aside session resume" in body
    assert "aside session stop" in body
    assert "60초" in body
    assert "실패" in body


# --- 에이전트 표시 이름 ---


def test_openai_agent_file_mirrors_the_setup_skill():
    body = (S / "agents" / "openai.yaml").read_text(encoding="utf-8")
    assert "레퍼런스 찾기" in body
    assert "레퍼런스 찾아줘" in body
    for key in ("display_name", "short_description", "default_prompt"):
        assert key in body, key


def test_the_skill_uses_no_pictographic_emoji():
    """저장소의 다른 스킬과 같은 표기를 쓴다 (기호는 `★`뿐이다)."""
    body = text() + "".join(p.read_text(encoding="utf-8") for p in R.glob("*.md"))
    found = re.findall(r"[\U0001F300-\U0001FAFF☀-➿]", body)
    assert not found, found


def test_the_stop_before_recording_is_spelled_out():
    body = text()
    assert "여기서 멈춘다" in body
    assert "답이 오기 전에는 8절로 넘어가지 않는다" in body
