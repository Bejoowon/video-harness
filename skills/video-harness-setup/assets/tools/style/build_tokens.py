#!/usr/bin/env python3
"""frame.md의 머리말(YAML frontmatter)에서 tokens.css / theme.ts를 생성한다.

이 도구는 작업 공간 `도구/style/`에 복사되어 도구 가상환경(PyYAML 포함) 안에서
실행된다. 이 스킬 안에서 서드파티 패키지(`yaml`)를 쓰는 유일한 곳이다.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import yaml

GENERATED_CSS_HEADER = "/* 이 파일은 frame.md에서 자동 생성됩니다. 직접 수정하지 마세요. */"


def load_frame(path: Path) -> dict:
    """frame.md 파일에서 첫 두 `---` 사이의 YAML 머리말만 파싱한다."""
    path = Path(path)
    text = path.read_text(encoding="utf-8")
    lines = text.splitlines()

    if not lines or lines[0].strip() != "---":
        raise ValueError(f"{path}: YAML 머리말(frontmatter)이 없습니다.")

    end_idx = None
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            end_idx = i
            break
    if end_idx is None:
        raise ValueError(f"{path}: YAML 머리말(frontmatter)이 닫히지 않았습니다.")

    frontmatter_text = "\n".join(lines[1:end_idx])
    data = yaml.safe_load(frontmatter_text)
    if not isinstance(data, dict):
        raise ValueError(f"{path}: YAML 머리말이 올바른 매핑이 아닙니다.")
    return data


def _font_stack(family: str) -> str:
    return f'"{family}", "Apple SD Gothic Neo", "Malgun Gothic", sans-serif'


def to_css(frame: dict) -> str:
    """frame 머리말을 `:root { ... }` 하나짜리 CSS 변수 블록으로 변환한다."""
    colors = frame["colors"]
    typo = frame["typography"]
    layout = frame["layout"]
    stroke = frame["stroke"]
    motion = frame["motion"]

    lines = [
        f"--c-bg: {colors['bg']};",
        f"--c-fg: {colors['fg']};",
        f"--c-accent: {colors['accent']};",
        f"--f-caption: {_font_stack(typo['caption']['family'])};",
        f"--f-caption-w: {typo['caption']['weight']};",
        f"--f-caption-size: {typo['caption']['size']}px;",
        f"--f-title: {_font_stack(typo['title']['family'])};",
        f"--f-title-w: {typo['title']['weight']};",
        f"--f-title-size: {typo['title']['size']}px;",
        f"--f-note: {_font_stack(typo['note']['family'])};",
        f"--f-note-w: {typo['note']['weight']};",
        f"--f-note-size: {typo['note']['size']}px;",
        f"--l-title-top: {layout['title_top']}px;",
        f"--l-caption-bottom: {layout['caption_bottom']}px;",
        f"--l-source-bottom: {layout.get('source_bottom', 96)}px;",
        f"--l-safe-side: {layout['safe_side']}px;",
        f"--s-caption-outline: {stroke['caption_outline']}px;",
        f"--s-shadow: {stroke['shadow']};",
        f"--m-in-dur: {motion['in']['duration']};",
        f"--m-in-ease: {motion['in']['ease']};",
        f"--m-out-dur: {motion['out']['duration']};",
        f"--m-out-ease: {motion['out']['ease']};",
        f"--m-stagger: {motion['stagger']};",
    ]
    body = "\n".join(f"  {line}" for line in lines)
    return f"{GENERATED_CSS_HEADER}\n:root {{\n{body}\n}}\n"


def _ts_value(value) -> str:
    if isinstance(value, str):
        return f'"{value}"'
    if isinstance(value, bool):
        return "true" if value else "false"
    return str(value)


def _serialize_ts_object(obj: dict, indent: int) -> str:
    pad = "  " * indent
    closing_pad = "  " * (indent - 1)
    lines = ["{"]
    for key, value in obj.items():
        if isinstance(value, dict):
            lines.append(f"{pad}{key}: {_serialize_ts_object(value, indent + 1)},")
        else:
            lines.append(f"{pad}{key}: {_ts_value(value)},")
    lines.append(f"{closing_pad}}}")
    return "\n".join(lines)


def to_theme_ts(frame: dict) -> str:
    """frame 머리말을 같은 값을 camelCase로 담은 Remotion용 `theme` 객체로 변환한다."""
    colors = frame["colors"]
    typo = frame["typography"]
    layout = frame["layout"]
    stroke = frame["stroke"]
    motion = frame["motion"]
    canvas = frame["canvas"]

    theme = {
        "colors": {
            "bg": colors["bg"],
            "fg": colors["fg"],
            "accent": colors["accent"],
        },
        "typography": {
            "captionFamily": typo["caption"]["family"],
            "captionWeight": typo["caption"]["weight"],
            "captionSize": typo["caption"]["size"],
            "titleFamily": typo["title"]["family"],
            "titleWeight": typo["title"]["weight"],
            "titleSize": typo["title"]["size"],
            "noteFamily": typo["note"]["family"],
            "noteWeight": typo["note"]["weight"],
            "noteSize": typo["note"]["size"],
        },
        "layout": {
            "titleTop": layout["title_top"],
            "captionBottom": layout["caption_bottom"],
            "sourceBottom": layout.get("source_bottom", 96),
            "safeSide": layout["safe_side"],
        },
        "stroke": {
            "captionOutline": stroke["caption_outline"],
            "shadow": stroke["shadow"],
        },
        "motion": {
            "inDuration": motion["in"]["duration"],
            "inEase": motion["in"]["ease"],
            "outDuration": motion["out"]["duration"],
            "outEase": motion["out"]["ease"],
            "stagger": motion["stagger"],
        },
        "canvas": {
            "width": canvas["width"],
            "height": canvas["height"],
            "fps": canvas["fps"],
        },
    }
    body = _serialize_ts_object(theme, indent=1)
    return f"export const theme = {body} as const;\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="frame.md에서 tokens.css / theme.ts를 생성한다.")
    parser.add_argument("frame", type=Path, help="frame.md 경로")
    parser.add_argument("--css", type=Path, required=True, help="tokens.css 출력 경로")
    parser.add_argument("--ts", type=Path, help="theme.ts 출력 경로 (Remotion 채널만 필요)")
    args = parser.parse_args(argv)

    frame = load_frame(args.frame)

    args.css.parent.mkdir(parents=True, exist_ok=True)
    args.css.write_text(to_css(frame), encoding="utf-8")

    if args.ts:
        args.ts.parent.mkdir(parents=True, exist_ok=True)
        args.ts.write_text(to_theme_ts(frame), encoding="utf-8")

    return 0


if __name__ == "__main__":
    sys.exit(main())
