#!/usr/bin/env python3
"""frame.md의 규범 값(locked/choose/free)과 어긋나는 소스 파일의 스타일 값을 찾는다.

이 도구는 작업 공간 `도구/style/`에 복사되어 도구 가상환경(PyYAML 포함) 안에서
실행된다.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

from build_tokens import load_frame

HEX_RE = re.compile(r"#[0-9a-fA-F]{6}\b")
FONT_FAMILY_RE = re.compile(r'font-family\s*:\s*("[^"]*"|\'[^\']*\'|[^;}"\']*)')
FONT_SIZE_RE = re.compile(r"font-size\s*:\s*(\d+)px")
EASE_RE = re.compile(r'eas(?:e|ing)\s*:\s*["\']([^"\']+)["\']')

# JSX/TS 스타일 객체 표기(`fontFamily:`/`fontSize:`)용 — CSS 표기와 달리 값이 문자열/
# 템플릿 리터럴로 "바로" 시작해야만 매치한다. `theme.typography.caption.family`처럼
# 식별자·멤버 표현식으로 시작하면 애초에 매치되지 않아 자연스럽게 무시된다.
JS_SUFFIXES = {".tsx", ".ts", ".jsx", ".js"}
JS_FONT_FAMILY_RE = re.compile(r'fontFamily\s*:\s*(`[^`]*`|"[^"]*"|\'[^\']*\')')
JS_FONT_SIZE_RE = re.compile(r"fontSize\s*:\s*(\d+)\b")

GENERIC_FONT_FALLBACKS = {
    "sans-serif",
    "serif",
    "monospace",
    "system-ui",
    "Apple SD Gothic Neo",
    "Malgun Gothic",
}

SKIP_NAMES = {"tokens.css", "theme.ts"}
SCAN_SUFFIXES = {".html", ".css", ".tsx", ".ts", ".jsx", ".js"}


def _first_family_from_js_value(raw: str) -> str | None:
    """JS/TS `fontFamily` 값(따옴표/백틱 안 내용)에서 첫 패밀리 이름만 뽑는다.

    `${...}` 보간으로 시작하면(예: 백틱 템플릿 리터럴로 theme 값을 참조하는 경우)
    하드코딩된 리터럴이 아니라고 보고 None을 돌려준다 — CSS 쪽의 `var(...)` 무시와
    같은 취급이다.
    """
    if raw.startswith("${"):
        return None
    first = raw.split(",")[0].strip().strip("'\"")
    if not first or first.startswith("${") or first.startswith("var("):
        return None
    return first


def extract_values(source_text: str, suffix: str | None = None) -> dict:
    """소스 텍스트에서 색상·폰트·글자 크기·이징 값을 뽑아낸다.

    `suffix`가 JS/TS 계열(`.tsx/.ts/.jsx/.js`)이면 `fontFamily:`/`fontSize:` 같은
    JSX 스타일 객체 표기도 추가로 본다.
    """
    colors = {m.group(0).lower() for m in HEX_RE.finditer(source_text)}

    fonts: set[str] = set()
    for m in FONT_FAMILY_RE.finditer(source_text):
        raw = m.group(1).strip()
        if not raw or raw.startswith("var("):
            continue
        first = raw.split(",")[0].strip().strip("'\"")
        if first and not first.startswith("var("):
            fonts.add(first)

    font_sizes = {int(m.group(1)) for m in FONT_SIZE_RE.finditer(source_text)}
    eases = {m.group(1) for m in EASE_RE.finditer(source_text)}

    if suffix in JS_SUFFIXES:
        for m in JS_FONT_FAMILY_RE.finditer(source_text):
            family = _first_family_from_js_value(m.group(1)[1:-1])
            if family:
                fonts.add(family)
        font_sizes |= {int(m.group(1)) for m in JS_FONT_SIZE_RE.finditer(source_text)}

    return {"colors": colors, "fonts": fonts, "font_sizes": font_sizes, "eases": eases}


def _flatten_accent_sets(accent_sets) -> set[str]:
    colors: set[str] = set()
    for group in accent_sets or []:
        for c in group:
            colors.add(str(c).lower())
    return colors


def check(frame: dict, sources: list[Path]) -> dict:
    """소스 파일들을 frame의 locked/choose/free 규칙에 대조한다.

    `tokens.css`/`theme.ts`는 `frame.md`에서 생성된 파일이라 검사 대상에서 빠지고
    (`SKIP_NAMES`), 그 값은 이미 `frame.md` 머리말에 있으므로 따로 읽지 않는다.
    """
    errors: list[str] = []
    warnings: list[str] = []
    free_notes: list[str] = []

    consistency = frame.get("consistency", {})
    locked = set(consistency.get("locked", []))
    choose = consistency.get("choose") or {}
    free = set(consistency.get("free", []))

    typography_locked = "typography" in locked
    motion_locked = "motion.in" in locked or "motion.out" in locked
    # 검사기는 frame.md가 선언한 것만 따른다. "포맷 고정형" 채널이 삽화 색까지
    # 묶고 싶으면 `free`에서 `illustration_colors`를 빼서 선언하면 된다.
    illustration_free = "illustration_colors" in free

    typo = frame.get("typography", {})
    known_fonts = {entry["family"] for entry in typo.values()}
    known_sizes = {entry["size"] for entry in typo.values()}

    motion = frame.get("motion", {})
    known_eases = {motion.get("in", {}).get("ease"), motion.get("out", {}).get("ease")}
    known_eases.discard(None)

    colors = frame.get("colors", {})
    known_colors = {str(colors.get(k, "")).lower() for k in ("bg", "fg", "accent")}
    # `accent_sets`는 `choose`의 후보 목록이다. `choose`가 강조색을 고를 수 있다고
    # 선언했을 때만 후보가 후보 노릇을 한다 — "포맷 고정형"은 `choose`가 비어 있으므로
    # 강조색이 `frame.md`의 `colors.accent` 하나로 고정된다. 여기서도 검사기가 아니라
    # 선언이 규칙을 정한다.
    if "colors.accent" in choose:
        known_colors |= _flatten_accent_sets(colors.get("accent_sets"))

    for src in sources:
        text = Path(src).read_text(encoding="utf-8")
        values = extract_values(text, suffix=Path(src).suffix)

        if typography_locked:
            for f in values["fonts"]:
                if f in GENERIC_FONT_FALLBACKS or f in known_fonts:
                    continue
                errors.append(f"{src}: 알 수 없는 폰트 '{f}' (typography는 locked)")
            for s in values["font_sizes"]:
                if s in known_sizes:
                    continue
                errors.append(f"{src}: 알 수 없는 글자 크기 {s}px (typography는 locked)")

        if motion_locked:
            for e in values["eases"]:
                if e in known_eases:
                    continue
                warnings.append(f"{src}: 토큰에 없는 ease '{e}' (설명 그래픽 고유 모션이면 무시해도 됨)")

        for c in values["colors"]:
            if c in known_colors:
                continue
            if illustration_free:
                free_notes.append(f"{src}: 자유 색상 {c} (illustration_colors)")
            else:
                errors.append(f"{src}: 알 수 없는 색상 {c}")

    return {"errors": errors, "warnings": warnings, "free_notes": free_notes}


def _iter_source_files(project_dir: Path):
    for path in sorted(project_dir.rglob("*")):
        if not path.is_file() or path.suffix not in SCAN_SUFFIXES:
            continue
        if path.name in SKIP_NAMES:
            continue
        rel = path.relative_to(project_dir)
        if "node_modules" in rel.parts:
            continue
        if rel.as_posix().endswith("assets/gsap.min.js"):
            continue
        yield path


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="frame.md 규범 값과 어긋나는 스타일을 찾는다.")
    parser.add_argument("frame", type=Path, help="frame.md 경로")
    parser.add_argument("project_dir", type=Path, help="검사할 회차 프로젝트 디렉터리")
    parser.add_argument("--json", action="store_true", help="결과를 JSON으로 출력한다")
    args = parser.parse_args(argv)

    frame = load_frame(args.frame)
    sources = list(_iter_source_files(args.project_dir))
    result = check(frame, sources)

    if args.json:
        print(json.dumps(result, ensure_ascii=False))
    else:
        print(f"검사한 파일: {len(sources)}개")
        print(f"오류: {len(result['errors'])}개")
        for e in result["errors"]:
            print(f"  - {e}")
        print(f"경고: {len(result['warnings'])}개")
        for w in result["warnings"]:
            print(f"  - {w}")
        if result["free_notes"]:
            print(f"자유 기록: {len(result['free_notes'])}개")
            for n in result["free_notes"]:
                print(f"  - {n}")

    return 1 if result["errors"] else 0


if __name__ == "__main__":
    sys.exit(main())
