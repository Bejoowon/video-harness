#!/usr/bin/env python3
"""대본 한 줄의 마디와 음절을 세어 보여 준다. 합격·불합격을 가르는 관문이 아니다.

이 도구는 작업 공간 `도구/script/`에 복사되어 실행된다. 표준 라이브러리만 쓰고
다른 도구를 부르지 않으므로 별도 가상환경 없이 시스템 파이썬으로 바로 돌아간다.

무엇을 하나 — 대본 파일을 읽어 줄마다 마디(` / `로 나눈 덩어리)의 음절 수를 세고,
`3/4/4/3`처럼 보여 준다. 운율에서 벗어난 줄을 눈에 띄게 해 주는 것이 전부다.
**뜻이 먼저다.** 고유명사·숫자·인용 때문에 안 맞는 줄은 그대로 두면 된다. 그래서
기본 종료 코드는 비율과 상관없이 언제나 0이다(`--min-rate`를 준 사람만 관문으로 쓴다).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import unicodedata
from pathlib import Path

# 한글 음절 영역. 자모(ㄱ, ㅏ)와 한자·숫자·영문은 세지 않는다.
HANGUL_FIRST = 0xAC00
HANGUL_LAST = 0xD7A3

GRADE_OK = "맞음"
GRADE_TOLERATED = "허용"
GRADE_OFF = "벗어남"
GRADE_UNMARKED = "마디 표시 없음"
GRADE_SPELL_OUT = "읽는 대로 한글로 풀어 쓰세요"

DEFAULT_CORE_MIN = 3
DEFAULT_CORE_MAX = 4
DEFAULT_MAX = 5
DEFAULT_MIN_GROUPS = 2
DEFAULT_MAX_GROUPS = 4

NO_PATTERN = "-"

# 줄 앞머리의 목록 기호와 화자 이름표. 이름표는 공백·콜론·슬래시가 없는 짧은 토큰일
# 때만 뗀다 — 본문을 잘못 잘라 내지 않으려고 좁게 잡았다(`http://…`도 걸리지 않는다).
_LIST_MARKER_RE = re.compile(r"^[-*]\s+")
_SPEAKER_RE = re.compile(r"^[^\s:/]{1,10}:\s+")
_ASCII_WORD_RE = re.compile(r"[0-9A-Za-z]")
_MARK_RE = re.compile(r"\s*/\s*")
_HEADING_RE = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")
_FENCE_RE = re.compile(r"^(```|~~~)")

# 대본 양식을 복사해 쓴 파일은 안내문·예시·명령어가 함께 들어 있다. 제목이 이 이름인
# 구역이 있으면 그 아래만 대본으로 본다 — 안내문이 표에 섞이거나 TTS 원고로 나가면 안 된다.
SCRIPT_HEADING = "대본"
PLACEHOLDER = "(여기에 쓴다)"
SCOPE_SECTION = "section"
SCOPE_WHOLE = "whole-file"


def syllables(text: str) -> int:
    """한글 음절 글자 수. 공백·문장부호는 세지 않는다."""
    return sum(1 for ch in text if HANGUL_FIRST <= ord(ch) <= HANGUL_LAST)


def is_skipped(line: str) -> bool:
    """빈 줄과 `#`으로 시작하는 줄(메모·마크다운 제목)은 아예 보지 않는다."""
    stripped = line.strip()
    return not stripped or stripped.startswith("#")


def script_lines(text: str) -> tuple[list[tuple[int, str]], str]:
    """대본에 해당하는 줄만 (원래 줄 번호, 내용)으로 돌려준다. 둘째 값은 본 범위다.

    `## 대본` 같은 제목이 있으면 그 아래부터 같은 수준(또는 더 높은 수준)의 다음 제목
    전까지만 대본이다. 없으면 파일 전체가 대본이다. 어느 쪽이든 제목·`#` 메모·코드
    블록·빈 양식 자리표시는 뺀다. 빈 줄은 문단 나눔으로 쓰이므로 내용이 빈 채로 남긴다.
    """
    lines = text.splitlines()
    has_section = any(
        (m := _HEADING_RE.match(line.strip())) and m.group(2) == SCRIPT_HEADING for line in lines
    )

    picked: list[tuple[int, str]] = []
    inside = not has_section
    section_level = 0
    fence: str | None = None

    for number, raw in enumerate(lines, start=1):
        stripped = raw.strip()

        if fence is not None:
            if stripped.startswith(fence):
                fence = None
            continue
        fence_match = _FENCE_RE.match(stripped)
        if fence_match:
            fence = fence_match.group(1)
            continue

        heading = _HEADING_RE.match(stripped)
        if heading:
            level = len(heading.group(1))
            if has_section:
                if heading.group(2) == SCRIPT_HEADING:
                    inside, section_level = True, level
                elif inside and level <= section_level:
                    inside = False
            continue

        if not inside or stripped.startswith("#") or stripped == PLACEHOLDER:
            continue
        picked.append((number, raw))

    return picked, (SCOPE_SECTION if has_section else SCOPE_WHOLE)


def strip_prefix(line: str) -> str:
    """줄 앞의 목록 기호(`- `)와 화자 이름표(`이름: `)를 뗀다."""
    body = _LIST_MARKER_RE.sub("", line.strip(), count=1)
    return _SPEAKER_RE.sub("", body, count=1)


def split_groups(body: str) -> list[str]:
    """`/`로 마디를 나눈다. 빈 조각(줄 끝의 `/` 등)은 버린다."""
    return [part.strip() for part in body.split("/") if part.strip()]


def grade(
    counts: list[int],
    core_min: int = DEFAULT_CORE_MIN,
    core_max: int = DEFAULT_CORE_MAX,
    max_syllables: int = DEFAULT_MAX,
    min_groups: int = DEFAULT_MIN_GROUPS,
    max_groups: int = DEFAULT_MAX_GROUPS,
) -> str:
    """마디별 음절 수 목록을 `맞음`·`허용`·`벗어남`으로 판정한다."""
    if not min_groups <= len(counts) <= max_groups:
        return GRADE_OFF
    if all(core_min <= c <= core_max for c in counts):
        return GRADE_OK
    if all(core_min <= c <= max_syllables for c in counts):
        return GRADE_TOLERATED
    return GRADE_OFF


def analyze(
    text: str,
    core_min: int = DEFAULT_CORE_MIN,
    core_max: int = DEFAULT_CORE_MAX,
    max_syllables: int = DEFAULT_MAX,
    min_groups: int = DEFAULT_MIN_GROUPS,
    max_groups: int = DEFAULT_MAX_GROUPS,
) -> dict:
    """대본 전체를 줄 단위로 본다.

    센 줄(`counted`)은 마디가 표시되어 있고 음절을 제대로 셀 수 있는 줄뿐이다.
    표시가 없는 줄과 숫자·영문이 섞인 줄은 목록에는 남기되 비율에서 뺀다 — 셀 수
    없는 줄을 틀린 줄로 세면 비율이 거짓말을 한다.
    """
    rows: list[dict] = []
    tally = {GRADE_OK: 0, GRADE_TOLERATED: 0, GRADE_OFF: 0, GRADE_UNMARKED: 0, GRADE_SPELL_OUT: 0}

    picked, scope = script_lines(text)
    for number, raw in picked:
        if is_skipped(raw):
            continue
        shown = raw.strip()
        body = strip_prefix(raw)

        if "/" not in body:
            verdict = GRADE_UNMARKED
            counts: list[int] = []
        else:
            groups = split_groups(body)
            if any(_ASCII_WORD_RE.search(group) for group in groups):
                verdict = GRADE_SPELL_OUT
                counts = []
            else:
                counts = [syllables(group) for group in groups]
                verdict = grade(counts, core_min, core_max, max_syllables, min_groups, max_groups)

        tally[verdict] += 1
        rows.append(
            {
                "line": number,
                "pattern": "/".join(str(c) for c in counts) if counts else NO_PATTERN,
                "counts": counts,
                "grade": verdict,
                "text": shown,
            }
        )

    counted = tally[GRADE_OK] + tally[GRADE_TOLERATED] + tally[GRADE_OFF]
    rate = (tally[GRADE_OK] + tally[GRADE_TOLERATED]) / counted if counted else None
    return {
        "lines": rows,
        "counted": counted,
        "hit": tally[GRADE_OK],
        "tolerated": tally[GRADE_TOLERATED],
        "off": tally[GRADE_OFF],
        "unmarked": tally[GRADE_UNMARKED],
        "spell_out": tally[GRADE_SPELL_OUT],
        "rate": rate,
        "scope": scope,
    }


def strip_marks(text: str) -> str:
    """대본 줄만 골라 마디 경계 ` / `를 빼고 한 칸 띄어쓰기로 되돌린다.

    TTS 원고와 자막으로 넘길 때 쓴다. 제목·메모·코드 블록·대본 구역 밖의 글은 내보내지
    않는다(읽히면 안 되는 글이다). 목록 기호도 뗀다. 빈 줄은 문단 나눔으로 하나만 남긴다.
    """
    picked, _scope = script_lines(text)
    out: list[str] = []
    for _number, raw in picked:
        if not raw.strip():
            if out and out[-1] != "":
                out.append("")
            continue
        cleaned = _MARK_RE.sub(" ", _LIST_MARKER_RE.sub("", raw.strip(), count=1))
        out.append(re.sub(r"[ \t]{2,}", " ", cleaned).strip())
    while out and out[-1] == "":
        out.pop()
    return "\n".join(out) + ("\n" if out else "")


def _percent(rate: float | None) -> str:
    return "-" if rate is None else f"{round(rate * 100)}%"


def _width(text: str) -> int:
    """터미널에서 차지하는 칸 수. 한글·전각 글자는 두 칸이다."""
    return sum(2 if unicodedata.east_asian_width(ch) in "WF" else 1 for ch in text)


def _pad(text: str, width: int) -> str:
    return text + " " * max(0, width - _width(text))


def print_report(result: dict, path: Path) -> None:
    rows = result["lines"]
    print(f"{path} — 줄마다 마디와 음절을 세어 봤습니다.")
    if result.get("scope") == SCOPE_SECTION:
        print(f'"## {SCRIPT_HEADING}" 아래만 셌습니다.')
    else:
        print("파일 전체를 셌습니다.")
    print()
    if not rows:
        print("볼 줄이 없습니다.")
        return

    pattern_width = max(_width("마디"), *(_width(row["pattern"]) for row in rows))
    grade_width = max(_width("판정"), *(_width(row["grade"]) for row in rows))
    print(f"{'줄':>4}  {_pad('마디', pattern_width)}  {_pad('판정', grade_width)}  내용")
    for row in rows:
        pattern = _pad(row["pattern"], pattern_width)
        verdict = _pad(row["grade"], grade_width)
        print(f"{row['line']:>4}  {pattern}  {verdict}  {row['text']}")

    print()
    print(
        f"센 줄 {result['counted']} · {GRADE_OK} {result['hit']} · {GRADE_TOLERATED} {result['tolerated']}"
        f" · {GRADE_OFF} {result['off']} · 비율 {_percent(result['rate'])}"
    )
    if result["unmarked"] or result["spell_out"]:
        print(
            f"{GRADE_UNMARKED} {result['unmarked']}줄, 숫자·영문이 섞인 줄 {result['spell_out']}줄은 비율에서 뺐습니다."
        )
    print("뜻이 먼저다 — 비율은 합격선이 아니라 운율이 처지는 줄을 찾아 주는 눈금이다.")


def _read(path: Path) -> tuple[str | None, str | None]:
    """대본을 UTF-8로 읽는다. (내용, 오류 메시지) 중 하나만 채워서 돌려준다."""
    try:
        return path.read_text(encoding="utf-8"), None
    except FileNotFoundError:
        return None, f"파일이 없습니다: {path}"
    except IsADirectoryError:
        return None, f"파일이 아니라 폴더입니다: {path}"
    except UnicodeDecodeError:
        return None, f"UTF-8로 읽을 수 없습니다. 대본을 UTF-8로 저장한 뒤 다시 실행하세요: {path}"
    except OSError as error:
        return None, f"파일을 읽지 못했습니다: {path} ({error})"


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="대본의 마디와 음절을 세어 보여 준다 (합격 판정이 아니다)")
    parser.add_argument("script", type=Path, help="대본 파일 (UTF-8)")
    parser.add_argument("--json", action="store_true", help="표 대신 JSON 하나로 출력")
    parser.add_argument("--strip", action="store_true", help="마디 표시 ` / `를 뺀 대본만 출력 (TTS·자막용)")
    parser.add_argument("--min-rate", type=float, help="이 비율보다 낮으면 종료 코드 1 (관문으로 쓰고 싶을 때만)")
    parser.add_argument("--core-min", type=int, default=DEFAULT_CORE_MIN, help=f"기본 마디 최소 음절 (기본 {DEFAULT_CORE_MIN})")
    parser.add_argument("--core-max", type=int, default=DEFAULT_CORE_MAX, help=f"기본 마디 최대 음절 (기본 {DEFAULT_CORE_MAX})")
    parser.add_argument("--max", type=int, default=DEFAULT_MAX, help=f"허용할 최대 음절 (기본 {DEFAULT_MAX})")
    parser.add_argument("--min-groups", type=int, default=DEFAULT_MIN_GROUPS, help=f"한 줄의 최소 마디 수 (기본 {DEFAULT_MIN_GROUPS})")
    parser.add_argument("--max-groups", type=int, default=DEFAULT_MAX_GROUPS, help=f"한 줄의 최대 마디 수 (기본 {DEFAULT_MAX_GROUPS})")
    return parser


def main(argv: list[str] | None = None) -> int:
    # Windows 콘솔의 기본 인코딩이 UTF-8이 아니면 한국어 출력이 깨진다. 읽고 쓰는
    # 인코딩을 여기서 못박는다.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8")

    args = build_parser().parse_args(argv)

    text, error = _read(args.script)
    if error is not None:
        print(error, file=sys.stderr)
        return 2

    if args.strip:
        sys.stdout.write(strip_marks(text))
        return 0

    result = analyze(
        text,
        core_min=args.core_min,
        core_max=args.core_max,
        max_syllables=args.max,
        min_groups=args.min_groups,
        max_groups=args.max_groups,
    )

    if args.json:
        print(json.dumps({"file": str(args.script), **result}, ensure_ascii=False, indent=2))
    else:
        print_report(result, args.script)

    # 기본은 언제나 0이다. 관문은 `--min-rate`를 준 사람만 쓴다. 셀 수 있는 줄이
    # 하나도 없으면 판단할 근거가 없으므로 실패로 보지 않는다.
    if args.min_rate is not None and result["rate"] is not None and result["rate"] < args.min_rate:
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
