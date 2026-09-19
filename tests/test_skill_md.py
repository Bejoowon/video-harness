# tests/test_skill_md.py
import re
from pathlib import Path

import pytest

S = Path(__file__).resolve().parents[1] / "skills/video-harness-setup"


def text():
    return (S / "SKILL.md").read_text(encoding="utf-8")


def test_frontmatter_only_name_and_description():
    fm = re.match(r"^---\n(.*?)\n---\n", text(), re.S).group(1)
    keys = [l.split(":")[0] for l in fm.splitlines() if re.match(r"^[a-z_]+:", l)]
    assert keys == ["name", "description"]
    assert "name: video-harness-setup" in fm
    for trig in ["채널", "HyperFrames", "Remotion", "점검"]:
        assert trig in fm, trig


def test_length_and_neutral_wording():
    t = text()
    assert len(t.splitlines()) <= 500
    for banned in ["AskUserQuestion", "Bash tool", "Read tool", "/Users/"]:
        assert banned not in t


def test_references_all_scripts_and_modes():
    t = text()
    for s in ["preflight.py", "scaffold.py", "install_module.py", "smoke_test.py", "doctor.py", "--adopt", "--channel"]:
        assert s in t, s
    for mode in ["채널 추가", "기존 작업 공간", "미확인"]:
        assert mode in t, mode


# 걸러 낼 이름 목록은 저장소에 넣지 않는다(목록 자체가 그 이름을 드러내므로).
# 스킬을 손보는 사람이 `tests/author_blocklist.local.txt`에 한 줄에 하나씩 적어 두면 검사한다.
BLOCKLIST_FILE = Path(__file__).resolve().parent / "author_blocklist.local.txt"


def author_specific_names() -> list[str]:
    if not BLOCKLIST_FILE.exists():
        return []
    lines = BLOCKLIST_FILE.read_text(encoding="utf-8").splitlines()
    return [line.strip() for line in lines if line.strip() and not line.startswith("#")]


def test_no_author_specific_names_anywhere_in_the_skill():
    """배포되는 스킬 폴더에는 이 스킬을 만든 사람의 실제 채널 이름이 남으면 안 된다."""
    names = author_specific_names()
    if not names:
        pytest.skip("tests/author_blocklist.local.txt가 없어 건너뜀")
    for path in sorted(S.rglob("*")):
        if not path.is_file() or path.suffix in {".pyc", ".png", ".jpg", ".otf", ".ttf"}:
            continue
        if "__pycache__" in path.parts or "node_modules" in path.parts:
            continue
        try:
            body = path.read_text(encoding="utf-8")
        except UnicodeDecodeError:
            continue
        for name in names:
            assert name not in body, (path.relative_to(S).as_posix(), name)


def test_every_reference_file_is_linked():
    t = text()
    for p in (S / "references").glob("*.md"):
        assert p.name in t, p.name


# --- 아래는 컨트롤러가 브리프에 덧붙인 항목에 대한 추가 커버리지다. ---


def test_config_tool_records_the_answers():
    t = text()
    assert "config_tool.py" in t
    for sub in ["init", "set", "add-channel", "remove-channel", "show", "validate"]:
        assert re.search(rf'config_tool\.py"? {sub}\b', t), sub


def test_every_interview_step_id_appears_in_the_table():
    t = text()
    steps = ["0", "1", "2", "3", "3-1", "3-1a", "3-2", "4", "4-1", "5", "6", "7", "8", "9", "10"]
    for step in steps:
        assert f"| {step} |" in t, step


_CODE_SPAN_RE = re.compile(r"`([^`\n]+)`")
_FENCE_RE = re.compile(r"```.*?\n(.*?)```", re.S)
_SCRIPT_RE = re.compile(r"scripts/([A-Za-z0-9_]+\.py)")
_FLAG_RE = re.compile(r"--[a-z][a-z0-9-]*")
_ADD_ARGUMENT_RE = re.compile(r"add_argument\(\s*\"(--[a-z0-9-]+)\"")


def _command_chunks() -> list[str]:
    """SKILL.md에서 명령이 될 수 있는 조각(인라인 코드, 코드블록의 명령 한 줄)을 모은다.

    코드블록에서 `\\`로 이어지는 줄은 한 명령으로 합친다 — 그래야 다음 줄에 쓴
    옵션도 앞줄의 스크립트에 붙은 것으로 검사된다.
    """
    t = text()
    chunks = _CODE_SPAN_RE.findall(t)
    for block in _FENCE_RE.findall(t):
        joined = block.replace("\\\n", " ")
        chunks.extend(joined.splitlines())
    return chunks


def test_named_scripts_exist():
    named = {name for chunk in _command_chunks() for name in _SCRIPT_RE.findall(chunk)}
    named |= set(_SCRIPT_RE.findall(text()))
    assert named, "SKILL.md가 스크립트를 하나도 부르지 않는다"
    for name in named:
        assert (S / "scripts" / name).exists(), name


def _declared_flags(script: str) -> set[str]:
    source = (S / "scripts" / script).read_text(encoding="utf-8")
    return set(_ADD_ARGUMENT_RE.findall(source))


def test_workspace_placeholder_is_always_quoted_in_commands():
    """경로에 공백이 있을 수 있으므로 명령 예시의 `<ws>`는 언제나 따옴표 안에 있어야 한다."""
    for chunk in _command_chunks():
        if ".py" not in chunk or "<ws>" not in chunk:
            continue
        assert '"<ws>"' in chunk, chunk.strip()
        assert not re.search(r'(?<!")<ws>(?!")', chunk), chunk.strip()


def test_branch_table_declares_first_match_wins():
    """1절 분기 표는 위에서부터 처음 맞는 조건 하나만 적용해야 한다(Codex 관찰 4번)."""
    assert "위에서부터 처음 맞는 조건 하나만 적용한다" in text()


def test_no_unresolvable_skill_placeholder():
    """`${SKILL_DIR}`만 쓴다. `<skill>`은 어떤 명령 규칙에도 정의되어 있지 않다."""
    assert "<skill>" not in text()


def test_flags_used_on_our_scripts_exist_in_their_parsers():
    for chunk in _command_chunks():
        scripts = _SCRIPT_RE.findall(chunk)
        if not scripts:
            continue
        allowed: set[str] = set()
        for script in scripts:
            allowed |= _declared_flags(script)
        for flag in _FLAG_RE.findall(chunk):
            assert flag in allowed, (chunk.strip(), flag, sorted(allowed))


# --- 출발점(workflow)은 인터뷰의 첫 질문이다 ---

WORKFLOW_QUESTION = "직접 찍은 촬영본으로 만드시나요?"


def test_the_workflow_question_comes_before_the_workspace_name_question():
    t = text()
    assert WORKFLOW_QUESTION in t
    assert t.index(WORKFLOW_QUESTION) < t.index("작업 공간 경로와 이름")


def test_all_three_workflow_values_appear():
    t = text()
    for value in ("footage-first", "script-first", "per-episode"):
        assert f"`{value}`" in t, value


def test_the_kind_flag_is_gone_from_example_commands():
    """유형(`kind`)은 묻지 않고 출발점과 포맷에서 자동으로 정해진다."""
    for chunk in _command_chunks():
        assert "--kind" not in chunk, chunk.strip()


def test_add_channel_example_passes_the_workflow():
    assert any("add-channel" in chunk and "--workflow" in chunk for chunk in _command_chunks())


def test_the_skill_says_kind_is_derived_and_not_asked():
    assert "영상 유형(`kind`)은 묻지 않는다" in text()


# --- 대본 운율(script_rhythm)은 9단계 작업 규칙의 세 번째 값이다 ---


def test_step_nine_offers_both_rhythm_values_with_a_runnable_command():
    t = text()
    assert "rules.script_rhythm" in t
    for value in ("`meter`", "`free`"):
        assert value in t, value
    assert any("rules.script_rhythm" in chunk and '"meter"' in chunk for chunk in _command_chunks())


def test_the_rhythm_is_explained_in_plain_words_with_one_example():
    t = text()
    assert "오늘은 / 우리 동네 / 숨은 맛집 / 가 볼게" in t
    # 사용자에게 음수율·음보를 강의하지 않는다.
    assert "음수율" not in t and "음보" not in t


def test_the_summary_step_lists_the_rhythm():
    t = text()
    assert "대본 운율" in t
