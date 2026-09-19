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
