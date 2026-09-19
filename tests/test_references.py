# tests/test_references.py
import re
from pathlib import Path

import module_registry as m

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills/video-harness-setup"
R = SKILL / "references"
BANNED = ["AskUserQuestion", "Bash tool", "Read tool", "/Users/", "/opt/homebrew", "/opt/miniconda3"]


def test_every_module_has_reference():
    names = {p.stem for p in R.glob("module-*.md")}
    for mod in m.MODULES:
        if mod in ("tools-venv", "fonts"):
            continue
        assert f"module-{mod}" in names, mod


def test_sections_and_no_banned_strings():
    for p in R.glob("*.md"):
        text = p.read_text(encoding="utf-8")
        for b in BANNED:
            assert b not in text, (p.name, b)
        if p.name.startswith("module-"):
            for sec in ["## 무엇을 설치하나", "## 사용자에게 알릴 것", "## 설치 뒤 확인", "## 자주 막히는 곳"]:
                assert sec in text, (p.name, sec)


def test_pitfalls_cover_known_incidents():
    text = (R / "pitfalls.md").read_text(encoding="utf-8")
    for must in ["Navigation timeout", "HF_HUB_DISABLE_XET", "chrome-headless-shell", "작업 공간 루트", "청취"]:
        assert must in text, must


# --- 아래는 브리프의 모호성 해소 항목("Extend tests/test_references.py beyond the brief")에
# 대한 추가 커버리지다. ---


def test_module_references_stay_under_100_lines():
    for p in R.glob("module-*.md"):
        line_count = len(p.read_text(encoding="utf-8").splitlines())
        assert line_count <= 100, (p.name, line_count)


def test_no_todo_or_tbd_markers():
    for p in R.glob("*.md"):
        text = p.read_text(encoding="utf-8")
        assert "TODO" not in text, p.name
        assert "TBD" not in text, p.name


_PY_NAME_RE = re.compile(r"`([^`]*\.py)`")


def _existing_py_filenames() -> set[str]:
    names = {p.name for p in (SKILL / "scripts").glob("*.py")}
    names |= {p.name for p in (SKILL / "assets" / "tools").rglob("*.py")}
    return names


def test_mentioned_py_filenames_actually_exist():
    known = _existing_py_filenames()
    for p in R.glob("*.md"):
        text = p.read_text(encoding="utf-8")
        for match in _PY_NAME_RE.finditer(text):
            name = Path(match.group(1)).name
            assert name in known, (p.name, match.group(1))


# --- 아래는 최종 리뷰 M10·I9·M2에 대한 커버리지다. ---


def test_references_use_only_the_documented_placeholder():
    """`<skill>`은 SKILL.md의 명령 규칙에 없다. `${SKILL_DIR}`만 쓴다 (M10)."""
    for p in list(R.glob("*.md")) + list((SKILL / "assets" / "templates").glob("*")):
        if not p.is_file():
            continue
        text = p.read_text(encoding="utf-8")
        assert "<skill>" not in text, p.name


def test_transcribe_reference_tells_the_agent_to_pass_the_recorded_values():
    """설정에 기록만 되고 아무도 읽지 않는 값이 되지 않게 한다 (I9)."""
    text = (R / "module-transcribe.md").read_text(encoding="utf-8")
    assert "modules.transcribe.model" in text
    assert "modules.transcribe.engine" in text
    assert "--model" in text and "--engine" in text


def test_remotion_reference_documents_the_repeated_npm_install():
    """스모크는 복사본에서 매번 npm install을 돌린다 — 시간과 네트워크가 든다 (M2)."""
    text = (R / "module-remotion.md").read_text(encoding="utf-8")
    assert "node_modules" in text and "npm install" in text
    assert "인터넷" in text or "네트워크" in text


_CODE_SPAN_RE = re.compile(r"`([^`\n]+)`")
_FENCE_RE = re.compile(r"```.*?\n(.*?)```", re.S)
# 인자를 받는 스크립트 호출만 명령으로 본다. `<workspace>/도구/stock/search.py`처럼
# 파일을 가리키기만 하는 산문 조각은 명령이 아니라 경로 언급이다.
_COMMAND_RE = re.compile(r"\.py[\"']?\s+\S")


def _command_chunks(text: str) -> list[str]:
    chunks = _CODE_SPAN_RE.findall(text)
    for block in _FENCE_RE.findall(text):
        chunks.extend(block.replace("\\\n", " ").splitlines())
    return [c for c in chunks if _COMMAND_RE.search(c)]


def test_workspace_argument_is_quoted_in_runnable_reference_commands():
    """SKILL.md의 따옴표 규칙은 references의 실행 가능한 예시에도 적용된다."""
    for p in sorted(R.glob("*.md")):
        for chunk in _command_chunks(p.read_text(encoding="utf-8")):
            for placeholder in ("<workspace>", "<ws>"):
                if placeholder not in chunk:
                    continue
                unquoted = re.search(rf'(?<!"){re.escape(placeholder)}', chunk)
                assert not unquoted, (p.name, chunk.strip())


# --- 출발점(workflow) 참고 문서 ---


def test_workflows_reference_covers_both_flows_and_the_middle_case():
    text = (R / "workflows.md").read_text(encoding="utf-8")
    for value in ("footage-first", "script-first", "per-episode"):
        assert value in text, value
    # 초보자에게 설명할 말과, 애매한 중간 사례(찍은 영상 + 새 내레이션)까지 적혀 있어야 한다.
    assert "보충 내레이션" in text
    assert "자막" in text


# --- 대본 운율(script_rhythm) 참고 문서 ---


def test_script_rhythm_reference_carries_the_rule_grades_examples_and_fixes():
    text = (R / "script-rhythm.md").read_text(encoding="utf-8")
    assert "뜻이 먼저다" in text
    for grade in ("맞음", "허용", "벗어남"):
        assert grade in text, grade
    for example in (
        "오늘은 / 우리 동네 / 숨은 맛집 / 가 볼게",
        "냉장고에 / 남은 재료 / 이것만은 / 꼭 넣어",
        "딱 하나만 / 기억하세요",
    ):
        assert example in text, example
    assert "check_rhythm.py" in text and "--strip" in text
    # 고치는 법과 하지 말 것이 둘 다 있어야 한다.
    assert "## 벗어남" in text and "## 하지 않을 것" in text
    assert "전사" in text


def test_workflows_reference_points_at_the_rhythm_rule():
    text = (R / "workflows.md").read_text(encoding="utf-8")
    assert "script-rhythm.md" in text
    assert "운율" in text


# --- 방향 파악(1부)과 조사(2부) 참고 문서 ---


def test_discovery_reference_covers_the_interview_the_research_and_the_no_web_case():
    text = (R / "discovery.md").read_text(encoding="utf-8")
    for field in ("audience", "scope", "expertise", "tone", "platforms", "evidence", "topics"):
        assert field in text, field
    # 막연한 답에는 추측 대신 구체적인 예를 두세 개 들어 준다.
    assert "추측" in text and "예" in text
    # 조사 결과의 정직성 규칙.
    assert "지어내지 않는다" in text
    assert "출처 미확인" in text
    assert "찾아본 척하지 않는다" in text
    assert "조사하지 않은 아이디어" in text
    # 민감 분야.
    assert "strict" in text


def test_discovery_reference_keeps_references_analysis_only():
    text = (R / "discovery.md").read_text(encoding="utf-8")
    assert "분석용" in text
