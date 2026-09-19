#!/usr/bin/env python3
"""작업 공간·채널 생성, 도구 복사, 기존 작업 공간 채택.

표준 라이브러리만 사용한다 (global-constraints.md).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import harness_lib as h

WORKSPACE_DIRS = [
    "스타일_라이브러리/06_참고영상/_양식/캡처",
    "스타일_라이브러리/01_폰트",
    "스타일_라이브러리/02_효과음",
    "스타일_라이브러리/03_BGM",
    "스타일_라이브러리/04_프리셋",
    "스타일_라이브러리/05_색보정",
    "스타일_라이브러리/06_참고영상",
    "99.레퍼런스",
    "도구/logs",
]

CHANNEL_DIRS = [
    "01_원본영상",
    "02_기획과자막/스타일레퍼런스",
    "03_편집프로젝트/_채널공용/부품",
    "03_편집프로젝트/_채널공용/회차템플릿",
    "03_편집프로젝트/_채널공용/기준프레임",
    "03_편집프로젝트/_채널공용/효과음",
    "04_완성영상",
]

RENDER_ENGINE_LABELS = {
    "hyperframes": "HyperFrames",
    "remotion": "Remotion",
    "both": "HyperFrames와 Remotion",
}
VOICE_MODE_LABELS = {
    "local-mlx": "로컬 목소리 복제(TTS)",
    "cloud": "클라우드 TTS",
    "record": "직접 녹음·원음",
}
HANDOFF_EDITOR_LABELS = {
    "none": "사용 안 함(Studio만)",
    "capcut": "CapCut",
    "premiere": "Premiere Pro",
}
VERSIONING_LABELS = {
    "vN-then-final": "작업 중에는 _vN으로 올리고, 확정되면 최종본만 남기고 삭제기록을 쓴다",
    "keep-all": "모든 버전을 보존한다",
}
SCRIPT_RHYTHM_LABELS = {"meter": "3·4조 네 마디 (기본)", "free": "자유"}
DEFAULT_SCRIPT_RHYTHM = "meter"

# 대본 운율 규칙의 단일 원본. AGENTS.md의 "대본 쓰기" 절이 이 문장 그대로 렌더된다.
# 참고 문서(`references/script-rhythm.md`)와 채널의 대본 양식도 같은 말을 쓴다.
METER_RULE = """- 내레이션 대본은 읽었을 때 운율이 느껴지게 쓴다. 한 줄을 **마디**(한 호흡에 읽는 덩어리, 보통 한두 어절)로 나누고, 마디는 **3~4음절이 기본, 5음절까지 허용**한다.
- 한 줄은 **네 마디가 기본**이다(`3/4/4/3`, `4/4/4/3`, `3/4/3/4`, `4/4/4/4` …). 짧게 끊을 때는 **두 마디**(`3/4`, `4/4`, `4/5`)도 좋다. 세 마디도 허용한다.
- **뜻이 먼저다.** 운율을 맞추려고 말이 어색해지거나 사실이 바뀌면 안 된다. 고유명사·숫자·인용 때문에 안 맞는 줄은 그대로 둔다. 목표는 "대부분의 줄"이지 "모든 줄"이 아니다.
- 대본 파일에서는 마디 경계를 ` / `로 표시한다. TTS 입력·자막으로 넘길 때는 ` / `를 뺀다.
- 숫자·영문·기호는 **읽는 소리대로 한글로** 쓴다(`3개` → `세 개`, `AI` → `에이아이`). 음절을 셀 수 있고 TTS도 정확히 읽는다.
- 적용 범위: 에이전트가 **새로 쓰는** 내레이션·보충 내레이션·자막 문구. 사람이 실제로 말한 촬영본의 전사 결과는 운율에 맞추려고 고쳐 쓰지 않는다.
- 채널의 `채널기준.md`에 다른 말투·운율 규칙이 적혀 있으면 그쪽을 따른다.

예) `오늘은 / 우리 동네 / 숨은 맛집 / 가 볼게`는 3/4/4/3, `딱 하나만 / 기억하세요`는 4/5다.

파이썬으로 `도구/script/check_rhythm.py <대본 파일>`을 돌리면 줄마다 마디와 음절을 세어 보여 준다. 합격·불합격을 가르는 검사가 아니라 운율이 처지는 줄을 찾아 주는 보조 도구다 — 비율이 낮아도 뜻이 먼저다. `도구/script/check_rhythm.py <대본 파일> --strip`은 마디 표시 ` / `를 뺀 대본만 내놓는다. TTS 원고와 자막에는 그것을 쓴다. 파일에 `## 대본` 제목이 있으면 그 아래 글만 세고 내놓는다(안내문·예시·메모는 건드리지 않는다). 제목이 없으면 파일 전체를 대본으로 본다."""
FREE_RULE = "이 작업 공간은 대본에 운율 규칙을 적용하지 않는다. 자연스럽게 쓴다."
SCRIPT_RHYTHM_RULES = {"meter": METER_RULE, "free": FREE_RULE}

# 채널의 `대본_양식.md`에 들어가는 짧은 판. 운율을 쓰지 않는 작업 공간에서는 빈
# 문자열이라 양식이 그냥 빈 대본 틀로 남는다.
METER_FORM_BLOCK = """## 운율

- 한 줄을 **마디**(한 호흡에 읽는 덩어리, 보통 한두 어절)로 나누고, 마디는 **3~4음절이 기본, 5음절까지 허용**한다.
- 한 줄은 **네 마디가 기본**이다. 짧게 끊을 때는 **두 마디**도 좋다.
- **뜻이 먼저다.** 운율을 맞추려고 말이 어색해지거나 사실이 바뀌면 안 된다. 안 맞는 줄은 그대로 둔다.
- 마디 경계는 ` / `로 표시하고, TTS·자막으로 넘길 때 뺀다.
- 숫자·영문은 읽는 소리대로 한글로 쓴다(`3개` → `세 개`, `AI` → `에이아이`).

```
오늘은 / 우리 동네 / 숨은 맛집 / 가 볼게     3/4/4/3
냉장고에 / 남은 재료 / 이것만은 / 꼭 넣어     4/4/4/3
딱 하나만 / 기억하세요                       4/5
```

작업 공간 루트에서 세어 보고, 넘길 때는 마디 표시를 뺀다. 두 명령 모두 아래 `## 대본` 제목 밑에 쓴 글만 본다 — 이 안내문은 세지도, TTS 원고로 내보내지도 않는다.

```
python3 도구/script/check_rhythm.py <대본 파일>
python3 도구/script/check_rhythm.py <대본 파일> --strip
```

"""
SCRIPT_RHYTHM_FORM_BLOCKS = {"meter": METER_FORM_BLOCK, "free": ""}

STATUS_LABELS = {"pending": "미분석", "done": "분석 완료"}
KIND_LABELS = {
    "narration-shorts": "내레이션 쇼츠",
    "footage-shorts": "촬영본 중심 쇼츠",
    "longform-vlog": "롱폼 브이로그",
}
WORKFLOW_LABELS = {
    "script-first": "대본 먼저",
    "footage-first": "찍은 영상 먼저",
    "per-episode": "회차마다 정함",
}
NOT_SET_LABEL = "(아직 정하지 않음)"
NO_WORKFLOW_LABEL = NOT_SET_LABEL
STYLE_START_LABELS = {
    "reference": "레퍼런스 영상에서 뽑기",
    "preset": "기성 프리셋에서 고르기",
    "manual": "직접 입력",
    "later": "나중에 정함",
}
CONSISTENCY_LABELS = {
    "fixed": "포맷 고정형(모든 회차가 같은 틀)",
    "variation": "회차 변주형(틀은 같고 정해진 범위만 회차마다 바꿈)",
    "decide-later": "만들면서 정함",
}
DEFAULT_STYLE_START = "later"
DEFAULT_CONSISTENCY = "decide-later"

# 채널의 `근거 규칙` 절. 인터뷰 1부에서 "틀린 말이 사람을 다치게 할 수 있는 분야"로
# 확인되면 `strict`가 기록되고, 그 채널만 규칙이 세진다. 값이 없으면 `normal`이다.
DEFAULT_EVIDENCE = "normal"
NORMAL_EVIDENCE_RULE = (
    "외부 자료는 출처를 기록하고 라이선스를 확인한다. 확인하지 않은 주장을 사실처럼 쓰지 않는다."
)
STRICT_EVIDENCE_RULE = """이 채널은 틀린 말이 사람을 다치게 할 수 있는 분야다. 아래를 지킨다.

- 모든 사실·수치에 공신력 있는 출처를 `02_기획과자막/_양식/출처와제작기록.md`에 남긴다.
- 출처를 못 찾은 내용은 대본에 쓰지 않는다.
- 진단·치료·투자 지시처럼 들리는 단정 표현을 쓰지 않는다.
- 필요한 경우 "전문가와 상담하라"는 안내를 넣는다."""
EVIDENCE_RULES = {"normal": NORMAL_EVIDENCE_RULE, "strict": STRICT_EVIDENCE_RULE}

# 인터뷰 2부에서 고른 주제 후보. `조사함`은 출처를 실제로 열어 본 것, `아이디어`는
# 함께 떠올리기만 한 것이다(`harness_lib.TOPIC_STATUSES`와 같은 값).
TOPIC_STATUS_LABELS = {"researched": "조사함", "idea": "아이디어"}
TOPIC_EMPTY_NOTE = (
    "아직 고른 주제가 없다. 에이전트에게 방향에 맞는 주제를 찾아 달라고 하면 후보를 모아 보여 준다. "
    "그중 사용자가 고른 것만 이 표에 들어간다."
)

# 출발점(workflow)별 "작업 순서". `{sample}`에는 `rules.sample_seconds`가 들어간다 —
# AGENTS.md가 읽는 값과 같은 자리(`_agents_values`)에서 가져와 두 문서가 어긋나지 않게 한다.
FOOTAGE_FIRST_ORDER = (
    "촬영본 확인(길이·화질·소리) → 전사 → 쓸 구간 고르기 → 구성안 → "
    "자막(전사 결과가 원본)·필요하면 보충 내레이션 → {sample}초 샘플 → "
    "본편 편집(필요하면 편집기로 넘기기) → 검수 → 버전 저장"
)
SCRIPT_FIRST_ORDER = (
    "주제 정하기 → 레퍼런스 분석 → 대본(대본이 자막의 원본) → 목소리(TTS·녹음) → "
    "대본에 맞는 소재 찾기·생성(출처 기록) → {sample}초 샘플 → 본편 편집 → 검수 → 버전 저장"
)
# 출발점이 없는 채널(예전 설정·채택한 작업 공간)이 쓰는 공통 순서. AGENTS.md의 폴백과 같은 문장이다.
GENERIC_ORDER = "원본 확인 → 레퍼런스 분석 → 기획·대본 → 음성과 {sample}초 샘플 → 본편 편집 → 검수 → 버전 저장."
PER_EPISODE_INTRO = (
    '회차를 시작할 때 "촬영본이 있는가"를 먼저 확인해 아래 두 순서 중 하나를 고르고, 고른 쪽을 회차 기록에 적는다.'
)

LATER_NOTE = "나중에 가져오기: 위 기준을 보고 레퍼런스를 고른 뒤 이 표에 추가한다. 자세한 방법은 `레퍼런스_모으는_법.md`를 참고한다."


_IGNORED_DIRS = {"__pycache__", "node_modules"}
_IGNORED_FILES = {".DS_Store"}
_IGNORED_SUFFIXES = {".pyc"}

_CANVAS_BY_FORMAT = {"9:16": (1080, 1920), "16:9": (1920, 1080)}
_CANVAS_LINE_RE = re.compile(r"^canvas:\s*\{[^}]*\}\s*$", re.MULTILINE)


def _canvas_of(channel_format: str | None) -> tuple[int, int]:
    return _CANVAS_BY_FORMAT.get(channel_format, _CANVAS_BY_FORMAT["9:16"])


# 복사한 회차 템플릿을 채널 캔버스에 맞출 때 쓰는 자리들.
_HTML_VIEWPORT_RE = re.compile(r'content="width=\d+,\s*height=\d+"')
_HTML_ROOT_SIZE_RE = re.compile(r'data-width="\d+"\s+data-height="\d+"')
_THEME_CANVAS_RE = re.compile(r"(canvas:\s*\{\s*width:\s*)\d+(\s*,\s*height:\s*)\d+")


def _sub_exactly_once(pattern: re.Pattern, repl, text: str, what: str) -> str:
    """정확히 한 번 치환한다. 못 찾거나 두 번 이상 나오면 멈춘다.

    이 치환들은 전부 이 스킬이 함께 배포하는 템플릿을 대상으로 한다. 빗나갔다는
    것은 템플릿과 코드가 어긋났다는 뜻이므로, 값이 사라진 파일을 만들어 놓고
    성공을 보고하는 대신 여기서 실패한다.
    """
    new_text, count = pattern.subn(repl, text)
    if count != 1:
        raise ValueError(f"{what}: 바꿀 자리를 찾지 못했습니다")
    return new_text


# 머리말의 `consistency:` 블록 전체(머리 줄 + 뒤따르는 들여쓴 줄들).
_CONSISTENCY_BLOCK_RE = re.compile(r"^consistency:\n(?:[ \t]+.*\n)+", re.MULTILINE)
# 3-2에서 "포맷 고정형"을 골랐을 때의 블록: 전환과 강조색까지 회차 간 고정하고,
# 삽화 색도 자유 목록에서 뺀다 — 검사기가 아니라 이 선언이 규칙을 정한다.
_FIXED_CONSISTENCY_BLOCK = (
    "consistency:\n"
    '  locked: [typography, layout, stroke, "motion.in", "motion.out", '
    '"motion.transitions", "colors.accent"]\n'
    "  choose: {}\n"
    '  free: ["footage"]\n'
)


def _set_frame_canvas(frame_text: str, channel_format: str | None) -> str:
    """frame.md 머리말의 canvas 줄을 채널 포맷에 맞는 해상도로 다시 쓴다(fps는 30 고정).

    `frame.md.tmpl` 자체는 9:16 기본값을 담은 유효한 YAML로 그대로 두고 렌더링된
    텍스트에만 적용한다 — 플레이스홀더를 넣지 않으므로 `{{channel_name}}`만 치환해
    쓰는 다른 소비자(`tests/test_style.py` 등)에는 영향이 없다.
    """
    width, height = _canvas_of(channel_format)
    return _sub_exactly_once(
        _CANVAS_LINE_RE, f"canvas: {{width: {width}, height: {height}, fps: 30}}", frame_text, "frame.md의 canvas 줄"
    )


def _set_frame_consistency(frame_text: str, channel: dict) -> str:
    """인터뷰 3-1(스타일 시작점)과 3-2(일관성 수준) 답을 렌더링된 frame.md에 반영한다.

    `_set_frame_canvas`와 같은 방식이다 — `frame.md.tmpl` 자체에는 플레이스홀더를
    넣지 않고 렌더링된 텍스트만 고친다. 답을 머리말에 늘 기록하고(`style_start`,
    `consistency_level`), "포맷 고정형"일 때만 `consistency` 블록을 더 좁게 바꾼다.
    """
    style_start = channel.get("style_start") or DEFAULT_STYLE_START
    consistency = channel.get("consistency") or DEFAULT_CONSISTENCY

    record = f"style_start: {style_start}\nconsistency_level: {consistency}\n"
    frame_text = _sub_exactly_once(
        _CANVAS_LINE_RE,
        lambda m: m.group(0) + "\n" + record.rstrip("\n"),
        frame_text,
        "frame.md 머리말의 인터뷰 답 기록 자리",
    )

    if consistency == "fixed":
        frame_text = _sub_exactly_once(
            _CONSISTENCY_BLOCK_RE, _FIXED_CONSISTENCY_BLOCK, frame_text, "frame.md의 consistency 블록"
        )
    return frame_text


def _retarget_hyperframes_template(dest: Path, created: list[str], channel_format: str | None) -> None:
    """복사한 HyperFrames 회차템플릿의 캔버스를 채널 포맷에 맞춘다.

    템플릿 파일 자체는 9:16 기본값으로 배포되므로, 16:9 채널이 그대로 복사받으면
    첫 회차부터 세로 루트를 쓰게 된다(`tokens.css`는 `frame.md`에서 다시 만들지만
    `index.html`의 캔버스는 아무도 고쳐 주지 않는다). 이번 복사에서 **새로 만든**
    파일만 고친다 — 사용자가 이미 손댄 파일은 절대 건드리지 않는다.
    """
    index_path = dest / "index.html"
    if str(index_path) not in created:
        return
    width, height = _canvas_of(channel_format)
    text = index_path.read_text(encoding="utf-8")
    text = _sub_exactly_once(
        _HTML_VIEWPORT_RE, f'content="width={width}, height={height}"', text, "index.html의 viewport meta"
    )
    text = _sub_exactly_once(
        _HTML_ROOT_SIZE_RE, f'data-width="{width}" data-height="{height}"', text, "index.html의 루트 캔버스"
    )
    index_path.write_text(text, encoding="utf-8")


def _retarget_remotion_template(dest: Path, created: list[str], channel_format: str | None) -> None:
    """복사한 Remotion 회차템플릿의 `theme.ts` canvas를 채널 포맷에 맞춘다.

    `_retarget_hyperframes_template`과 같은 이유·같은 규칙이다(새로 만든 파일만).
    """
    theme_path = dest / "src" / "theme.ts"
    if str(theme_path) not in created:
        return
    width, height = _canvas_of(channel_format)
    text = theme_path.read_text(encoding="utf-8")
    text = _sub_exactly_once(
        _THEME_CANVAS_RE, lambda mo: f"{mo.group(1)}{width}{mo.group(2)}{height}", text, "theme.ts의 canvas"
    )
    theme_path.write_text(text, encoding="utf-8")


def _templates_dir() -> Path:
    return h.skill_root() / "assets" / "templates"


def write_if_absent(path: Path, text: str, report: dict) -> None:
    """`path`가 없으면 `text`를 쓰고 report["created"]에, 있으면 손대지 않고 report["skipped"]에 남긴다."""
    path = Path(path)
    if path.exists():
        report["skipped"].append(str(path))
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    report["created"].append(str(path))


def write_bytes_if_absent(path: Path, data: bytes, report: dict) -> None:
    """`write_if_absent`의 바이너리 판. 폰트·이미지·gsap.min.js 때문에 필요하다."""
    path = Path(path)
    if path.exists():
        report["skipped"].append(str(path))
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(data)
    report["created"].append(str(path))


def _copy_asset_dir(src: Path, dest: Path, report: dict) -> list[str]:
    """디렉터리를 **파일 단위로** 복사한다. 이미 있는 파일은 절대 덮지 않는다.

    예전에는 대상 디렉터리가 비어 있지 않으면 통째로 건너뛰었다. 그래서 `도구/style/`
    안의 파일 하나만 지워진 경우 doctor가 "scaffold.py를 다시 실행하면 없는 도구만
    복사합니다"라고 안내해도 실제로는 아무것도 복원되지 않았다(리뷰 I5). 파일 단위로
    바꿔서 그 안내가 말 그대로 참이 되게 하고, 나중에 스킬이 도구 디렉터리에 파일을
    하나 더 추가해도 기존 작업 공간이 그것을 받을 수 있게 한다.

    새로 만든 파일의 경로 목록을 돌려준다(캔버스 재조정처럼 "방금 만든 것만" 고쳐야
    하는 후속 처리를 위해서다).
    """
    src = Path(src)
    dest = Path(dest)
    if not src.exists():
        report["skipped"].append(f"{dest} (소스 없음)")
        return []

    before = len(report["created"])
    dest.mkdir(parents=True, exist_ok=True)
    for path in sorted(src.rglob("*")):
        if not path.is_file():
            continue
        rel = path.relative_to(src)
        if set(rel.parts) & _IGNORED_DIRS:
            continue
        if path.name in _IGNORED_FILES or path.suffix in _IGNORED_SUFFIXES:
            continue
        write_bytes_if_absent(dest / rel, path.read_bytes(), report)
    return report["created"][before:]


def script_rhythm_of(config: dict) -> str:
    """설정의 대본 운율. 이 키가 없는 예전 설정은 기본값 `meter`로 본다."""
    value = config.get("rules", {}).get("script_rhythm")
    return value if value in SCRIPT_RHYTHM_LABELS else DEFAULT_SCRIPT_RHYTHM


def _agents_values(config: dict) -> dict:
    modules = config.get("modules", {})
    rules = config.get("rules", {})
    engine = modules.get("render", {}).get("engine")
    voice_mode = modules.get("voice", {}).get("mode")
    handoff_editor = modules.get("handoff", {}).get("editor")
    versioning = rules.get("versioning")
    script_rhythm = script_rhythm_of(config)
    return {
        "workspace_name": config.get("workspace", {}).get("name", ""),
        "render_engine": RENDER_ENGINE_LABELS.get(engine, engine or ""),
        "voice_mode": VOICE_MODE_LABELS.get(voice_mode, voice_mode or ""),
        "handoff_editor": HANDOFF_EDITOR_LABELS.get(handoff_editor, handoff_editor or ""),
        "sample_seconds": rules.get("sample_seconds", ""),
        "versioning_rule": VERSIONING_LABELS.get(versioning, versioning or ""),
        "script_rhythm_label": SCRIPT_RHYTHM_LABELS[script_rhythm],
        "script_rhythm_rule": SCRIPT_RHYTHM_RULES[script_rhythm],
    }


def workflow_steps(workflow: str | None, sample_seconds) -> str:
    """출발점에 맞는 "작업 순서" 문단을 만든다. 출발점이 없으면 공통 순서를 쓴다."""
    footage = FOOTAGE_FIRST_ORDER.format(sample=sample_seconds)
    script = SCRIPT_FIRST_ORDER.format(sample=sample_seconds)
    if workflow == "footage-first":
        return footage
    if workflow == "script-first":
        return script
    if workflow == "per-episode":
        lines = [
            PER_EPISODE_INTRO,
            "",
            f"- {WORKFLOW_LABELS['footage-first']}: {footage}",
            f"- {WORKFLOW_LABELS['script-first']}: {script}",
        ]
        return "\n".join(lines)
    return GENERIC_ORDER.format(sample=sample_seconds)


def _channel_values(config: dict, channel: dict) -> dict:
    values = _agents_values(config)
    workflow = channel.get("workflow")
    values.update(
        {
            "channel_name": channel.get("name", ""),
            "format": channel.get("format", ""),
            "kind": KIND_LABELS.get(channel.get("kind"), channel.get("kind", "")),
            "workflow": WORKFLOW_LABELS.get(workflow, NO_WORKFLOW_LABEL),
            "workflow_steps": workflow_steps(workflow, values["sample_seconds"]),
            "target_seconds": channel.get("target_seconds", ""),
            "language": channel.get("language", ""),
            "concept": channel.get("concept", NOT_SET_LABEL),
            "opening": channel.get("opening", ""),
            # 1부(방향 파악)의 답. 아직 묻지 않은 것은 빈칸이 아니라 "정하지 않음"으로 남긴다.
            **{field: channel.get(field) or NOT_SET_LABEL for field in h.DIRECTION_FIELDS},
            "evidence_rules": EVIDENCE_RULES[channel.get("evidence") or DEFAULT_EVIDENCE],
            "style_start": STYLE_START_LABELS[channel.get("style_start") or DEFAULT_STYLE_START],
            "consistency": CONSISTENCY_LABELS[channel.get("consistency") or DEFAULT_CONSISTENCY],
        }
    )
    return values


def _reference_rows(references: list[dict]) -> str:
    rows = []
    for i, ref in enumerate(references, start=1):
        location = ref.get("url") or ref.get("path", "")
        likes = ref.get("likes", "")
        status_raw = ref.get("status", "")
        status = STATUS_LABELS.get(status_raw, status_raw)
        rows.append(f"| {i} | {location} | {likes} | {status} |")
    return "\n".join(rows)


def _topic_rows(topics: list[dict]) -> str:
    """`_reference_rows`와 같은 방식으로 주제 후보 표의 줄들을 만든다."""
    rows = []
    for i, topic in enumerate(topics, start=1):
        status_raw = topic.get("status", "")
        status = TOPIC_STATUS_LABELS.get(status_raw, status_raw)
        rows.append(f"| {i} | {topic.get('title', '')} | {topic.get('basis', '')} | {status} |")
    return "\n".join(rows)


def scaffold_workspace(workspace: Path, config: dict) -> dict:
    """작업 공간 루트 문서와 WORKSPACE_DIRS를 만든다. {"created": [...], "skipped": [...]}."""
    workspace = Path(workspace)
    report: dict = {"created": [], "skipped": []}
    templates = _templates_dir()
    values = _agents_values(config)

    for rel in WORKSPACE_DIRS:
        (workspace / rel).mkdir(parents=True, exist_ok=True)

    agents_text = h.render_template((templates / "AGENTS.md.tmpl").read_text(encoding="utf-8"), values)
    write_if_absent(workspace / "AGENTS.md", agents_text, report)

    if "claude" in config.get("agents", []):
        claude_text = (templates / "CLAUDE.md.tmpl").read_text(encoding="utf-8")
        write_if_absent(workspace / "CLAUDE.md", claude_text, report)

    env_text = (templates / "env.example").read_text(encoding="utf-8")
    write_if_absent(workspace / ".env.example", env_text, report)

    gitignore_text = (templates / "gitignore").read_text(encoding="utf-8")
    write_if_absent(workspace / ".gitignore", gitignore_text, report)

    library_guide = h.render_template((templates / "넣는_방법.md.tmpl").read_text(encoding="utf-8"), values)
    write_if_absent(workspace / "스타일_라이브러리/넣는_방법.md", library_guide, report)

    font_rules = h.render_template((templates / "폰트_사용규칙.md.tmpl").read_text(encoding="utf-8"), values)
    write_if_absent(workspace / "스타일_라이브러리/01_폰트/폰트_사용규칙.md", font_rules, report)

    forms_src = templates / "참고영상_양식"
    forms_dest = workspace / "스타일_라이브러리/06_참고영상/_양식"
    for name in ("원본정보.md", "구조분석.md", "스타일분석.md", "적용규칙.md", "metadata.json"):
        text = (forms_src / name).read_text(encoding="utf-8")
        write_if_absent(forms_dest / name, text, report)

    voice_mode = config.get("modules", {}).get("voice", {}).get("mode")
    if voice_mode in ("local-mlx", "record"):
        recording_guide = (templates / "녹음가이드.md.tmpl").read_text(encoding="utf-8")
        write_if_absent(workspace / "도구/tts/녹음가이드.md", recording_guide, report)
    if voice_mode == "local-mlx":
        (workspace / "도구/tts/녹음").mkdir(parents=True, exist_ok=True)

    return report


def scaffold_channel(workspace: Path, config: dict, channel: dict) -> dict:
    """`<채널명>/` 아래 CHANNEL_DIRS와 채널 문서를 만든다. {"created": [...], "skipped": [...]}."""
    workspace = Path(workspace)
    report: dict = {"created": [], "skipped": []}
    templates = _templates_dir()
    base = workspace / channel["name"]

    for rel in CHANNEL_DIRS:
        (base / rel).mkdir(parents=True, exist_ok=True)

    values = _channel_values(config, channel)

    guide = h.render_template((templates / "채널기준.md.tmpl").read_text(encoding="utf-8"), values)
    write_if_absent(base / "채널기준.md", guide, report)

    put_guide = h.render_template((templates / "채널_넣는_방법.md.tmpl").read_text(encoding="utf-8"), values)
    write_if_absent(base / "넣는_방법.md", put_guide, report)

    worklist = h.render_template((templates / "작업목록.md.tmpl").read_text(encoding="utf-8"), values)
    write_if_absent(base / "02_기획과자막/작업목록.md", worklist, report)

    topics = channel.get("topics", [])
    topic_values = dict(values)
    topic_values["topic_rows"] = _topic_rows(topics)
    topic_values["topic_empty_note"] = "" if topics else TOPIC_EMPTY_NOTE
    topic_list = h.render_template((templates / "주제_후보.md.tmpl").read_text(encoding="utf-8"), topic_values)
    write_if_absent(base / "02_기획과자막/주제_후보.md", topic_list, report)

    provenance_note = (templates / "출처와제작기록.md.tmpl").read_text(encoding="utf-8")
    write_if_absent(base / "02_기획과자막/_양식/출처와제작기록.md", provenance_note, report)

    provenance_json = (templates / "provenance.json").read_text(encoding="utf-8")
    write_if_absent(base / "02_기획과자막/_양식/provenance.json", provenance_json, report)

    form_values = dict(values)
    form_values["script_rhythm_block"] = SCRIPT_RHYTHM_FORM_BLOCKS[script_rhythm_of(config)]
    script_form = h.render_template((templates / "대본_양식.md.tmpl").read_text(encoding="utf-8"), form_values)
    write_if_absent(base / "02_기획과자막/_양식/대본_양식.md", script_form, report)

    references = channel.get("references", [])
    ref_values = dict(values)
    ref_values["reference_rows"] = _reference_rows(references)
    ref_values["later_note"] = "" if references else LATER_NOTE
    ref_list = h.render_template((templates / "레퍼런스_목록.md.tmpl").read_text(encoding="utf-8"), ref_values)
    write_if_absent(base / "02_기획과자막/스타일레퍼런스/레퍼런스_목록.md", ref_list, report)

    gathering = h.render_template((templates / "레퍼런스_모으는_법.md.tmpl").read_text(encoding="utf-8"), values)
    write_if_absent(base / "02_기획과자막/스타일레퍼런스/레퍼런스_모으는_법.md", gathering, report)

    video_list = h.render_template((templates / "영상목록.md.tmpl").read_text(encoding="utf-8"), values)
    write_if_absent(base / "04_완성영상/영상목록.md", video_list, report)

    frame = h.render_template((templates / "frame.md.tmpl").read_text(encoding="utf-8"), values)
    frame = _set_frame_canvas(frame, channel.get("format"))
    frame = _set_frame_consistency(frame, channel)
    write_if_absent(base / "03_편집프로젝트/_채널공용/frame.md", frame, report)

    engine = config.get("modules", {}).get("render", {}).get("engine")
    channel_format = channel.get("format")
    if engine in ("hyperframes", "both"):
        dest = base / "03_편집프로젝트/_채널공용/회차템플릿"
        created = _copy_asset_dir(
            h.skill_root() / "assets" / "episode-template-hyperframes", dest, report
        )
        _retarget_hyperframes_template(dest, created, channel_format)
    if engine in ("remotion", "both"):
        dest = base / "03_편집프로젝트/_채널공용/회차템플릿-remotion"
        created = _copy_asset_dir(
            h.skill_root() / "assets" / "episode-template-remotion", dest, report
        )
        _retarget_remotion_template(dest, created, channel_format)

    return report


def copy_tools(workspace: Path, config: dict) -> dict:
    """config의 모듈에 맞는 assets/tools/*만 `도구/`로 복사한다. {"created": [...], "skipped": [...]}."""
    workspace = Path(workspace)
    report: dict = {"created": [], "skipped": []}
    tools_src = h.skill_root() / "assets" / "tools"
    dest_root = workspace / "도구"

    modules = config.get("modules", {})
    engine = modules.get("render", {}).get("engine")
    voice_mode = modules.get("voice", {}).get("mode")
    sources = modules.get("sources", [])
    handoff_editor = modules.get("handoff", {}).get("editor")

    # `script`(대본 운율 검사기)와 `style`은 모듈 선택과 무관하게 늘 복사한다.
    dir_items = ["script", "style"]
    if "stock" in sources:
        dir_items.append("stock")
    dir_items.append("transcribe")
    if handoff_editor != "none":
        dir_items.append("export")

    for name in dir_items:
        _copy_asset_dir(tools_src / name, dest_root / name, report)

    file_items = []
    if engine in ("hyperframes", "both"):
        file_items.append("chrome-noaudio.py")
    if voice_mode == "local-mlx":
        file_items += ["tts/generate_local_mlx.py", "tts/postprocess.py"]
    elif voice_mode == "cloud":
        file_items += ["tts/generate_cloud.py", "tts/postprocess.py"]

    for rel in file_items:
        src = tools_src / rel
        dest = dest_root / rel
        if not src.exists():
            report["skipped"].append(f"{dest} (소스 없음)")
            continue
        write_if_absent(dest, src.read_text(encoding="utf-8"), report)

    return report


def adopt_existing(workspace: Path, config: dict) -> list[dict]:
    """이미 있는 채널 폴더(하위에 01_원본영상이 있는 폴더)를 찾는다. 파일은 아무것도 고치지 않는다."""
    workspace = Path(workspace)
    found: list[dict] = []
    if not workspace.exists():
        return found

    for child in sorted(workspace.iterdir()):
        if not child.is_dir():
            continue
        if not (child / "01_원본영상").is_dir():
            continue
        found.append(
            {
                "id": h.slugify_channel(child.name),
                "name": child.name,
                "format": "9:16",
                "kind": "narration-shorts",
                "target_seconds": 60,
                "language": "ko",
                "adopted": True,
            }
        )

    return found


def _fail(message: str) -> int:
    print(json.dumps({"error": message}, ensure_ascii=False), file=sys.stderr)
    return 1


def _missing_config_error(workspace: Path) -> str:
    config_tool = Path(__file__).resolve().parent / "config_tool.py"
    return (
        "harness.config.json이 없습니다. 먼저 "
        f'{h.python_cmd()} "{config_tool}" init "{workspace}" --name "<작업 공간 이름>" --agents <에이전트>'
        "를 실행하세요."
    )


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="video-harness-setup 작업 공간·채널 생성")
    parser.add_argument("workspace", type=Path, help="작업 공간 경로")
    parser.add_argument("--channel", help="이 채널만 생성한다 (channel id)")
    parser.add_argument("--adopt", action="store_true", help="기존 작업 공간을 채택한다")
    args = parser.parse_args(argv)

    workspace = args.workspace

    if args.adopt:
        # `--adopt`는 채널(인터뷰 답)을 설정에 넣는다. 설정을 지어내면 그 뒤의
        # `config_tool.py init`이 "이미 있습니다"로 막혀 이름 없는 작업 공간에서
        # 빠져나올 길이 없어진다. 없으면 만들지 말고 멈춘다 (리뷰 I4).
        config = h.load_config(workspace)
        if config is None:
            return _fail(_missing_config_error(workspace))

        errors = h.validate_config(config)
        if errors:
            return _fail("harness.config.json이 올바르지 않습니다: " + "; ".join(errors))

        found = adopt_existing(workspace, config)
        existing_names = {c.get("name") for c in config.get("channels", [])}
        added = [c for c in found if c["name"] not in existing_names]
        already = [c["name"] for c in found if c["name"] in existing_names]
        config.setdefault("channels", []).extend(added)

        # 기록은 언제나 validate_config를 지나간다 (design §7, 단일 관문).
        errors = h.save_validated(workspace, config)
        if errors:
            return _fail("채택한 채널을 저장하지 못했습니다: " + "; ".join(errors))

        print(json.dumps({"adopted": added, "already_registered": already}, ensure_ascii=False, indent=2))
        return 0

    config = h.load_config(workspace)
    if config is None:
        return _fail(_missing_config_error(workspace))

    if args.channel:
        channel = next((c for c in config.get("channels", []) if c.get("id") == args.channel), None)
        if channel is None:
            print(json.dumps({"error": f"채널을 찾을 수 없습니다: {args.channel}"}, ensure_ascii=False), file=sys.stderr)
            return 1
        result = scaffold_channel(workspace, config, channel)
        print(json.dumps(result, ensure_ascii=False, indent=2))
        return 0

    result = {
        "workspace": scaffold_workspace(workspace, config),
        "tools": copy_tools(workspace, config),
        "channels": {
            channel.get("id", channel.get("name")): scaffold_channel(workspace, config, channel)
            for channel in config.get("channels", [])
        },
    }
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
