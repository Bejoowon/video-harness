#!/usr/bin/env python3
"""편집기 넘기기 공용 헬퍼: 컷 목록 로드/검증, 프레임 변환, SRT 생성.

표준 라이브러리만 쓴다. 이 도구는 작업 공간 `도구/export/`에 복사되어 실행된다.
`to_premiere_xml.py`·`to_capcut.py`가 공통으로 임포트한다.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

_RANGE_KEYS = ("video", "audio", "overlays")
_REQUIRED_KEYS = ("name", "width", "height", "fps", "video")


def _bad_name_errors(name) -> list[str]:
    """`name`은 두 내보내기 도구가 그대로 파일 이름으로 쓴다.

    구분자나 `..`가 들어오면 `out_dir` 바깥에 파일을 쓰게 되므로 여기서 막는다.
    """
    if not isinstance(name, str) or not name.strip():
        return ["name: 비어 있지 않은 문자열이어야 합니다"]
    if "/" in name or "\\" in name:
        return [f"name: 경로 구분자를 쓸 수 없습니다: {name}"]
    if name.strip(".") == "":
        return [f"name: 파일 이름으로 쓸 수 없습니다: {name}"]
    return []


class CutlistError(Exception):
    """컷 목록을 불러오거나 검증하는 중 문제가 있을 때 던진다.

    메시지는 그대로 사용자에게 보여줄 한국어 문장이다. 두 CLI(`to_premiere_xml.py`,
    `to_capcut.py`)가 이 예외 하나만 잡아서 `fail()`로 출력하면 된다.
    """


def frames(seconds: float, fps: int) -> int:
    """초를 프레임 수로 반올림한다."""
    return round(seconds * fps)


def _resolve_src(src: str, workspace: Path) -> Path:
    p = Path(src)
    if not p.is_absolute():
        p = workspace / p
    return p


def load_cutlist(path: Path, workspace: Path) -> dict:
    """컷 목록 JSON을 읽고 각 항목의 `src`를 작업 공간 기준 절대경로로 바꾼다.

    참조된 미디어 파일이 하나라도 없으면 `FileNotFoundError`를 던지며, 메시지에
    빠진 파일 목록을 담는다 (경로는 이미 절대경로이므로 그대로 보여준다).
    """
    path = Path(path)
    workspace = Path(workspace)
    cutlist = json.loads(path.read_text(encoding="utf-8"))

    missing: list[str] = []
    for key in _RANGE_KEYS:
        for item in cutlist.get(key, []):
            resolved = _resolve_src(item["src"], workspace)
            item["src"] = str(resolved)
            if not resolved.exists():
                missing.append(str(resolved))

    if missing:
        raise FileNotFoundError(f"미디어 파일을 찾을 수 없습니다: {', '.join(missing)}")

    return cutlist


def _bad_range_errors(key: str, items: list[dict]) -> list[str]:
    """개별 항목의 음수 시간·역전된 구간을 검사한다.

    `out < in`(엄밀히 역전된 구간)은 "음수 시간" 오류와 "out<=in" 오류를 함께
    낸다 — 둘은 서로 다른 문제를 가리킨다: 전자는 계산된 구간 길이 자체가
    음수라는 뜻이고, 후자는 in/out 순서가 잘못됐다는 뜻이다. `out == in`(길이
    0)은 순서 오류만 낸다.
    """
    errors: list[str] = []
    for i, item in enumerate(items):
        start = item.get("start", 0)
        in_ = item.get("in", 0)
        out = item.get("out", 0)
        if start < 0 or in_ < 0 or out < 0:
            errors.append(f"{key}[{i}]: 시간 값은 음수일 수 없습니다")
        if out < in_:
            errors.append(f"{key}[{i}]: 구간 길이가 음수입니다 (in={in_}, out={out})")
        if out <= in_:
            errors.append(f"{key}[{i}]: out은 in보다 커야 합니다 (in={in_}, out={out})")
    return errors


def _overlap_errors(key: str, items: list[dict]) -> list[str]:
    """같은 트랙(같은 리스트) 안에서 구간이 겹치는지 검사한다.

    `out<=in`으로 이미 오류가 난 항목은 구간을 계산할 수 없으므로 겹침 검사에서
    제외한다(중복 보고를 피한다).
    """
    ranges = [
        (item.get("start", 0), item.get("start", 0) + (item.get("out", 0) - item.get("in", 0)))
        for item in items
        if item.get("out", 0) > item.get("in", 0)
    ]
    for i in range(len(ranges)):
        s1, e1 = ranges[i]
        for j in range(i + 1, len(ranges)):
            s2, e2 = ranges[j]
            if s1 < e2 and s2 < e1:
                return [f"{key}: 같은 트랙에서 구간이 겹칩니다"]
    return []


def validate_cutlist(c: dict) -> list[str]:
    """컷 목록을 검증해 오류 메시지 목록을 돌려준다. 빈 목록이면 통과.

    검사 항목: 필수 항목(`name, width, height, fps, video`)이 모두 있는지,
    fps/width/height는 0보다 커야 함, 각 항목의 음수 시간과 `out<=in`, 같은
    트랙(video/overlays/오디오 트랙 이름별) 안의 구간 겹침. `audio`·`captions`·
    `overlays`는 선택 항목이라 없으면 빈 목록으로 본다.

    필수 항목이 하나라도 없으면 그 사실만 보고하고 나머지 검사는 건너뛴다 —
    이후 검사들이 `c[key]`가 아니라 `c.get(key)`만 쓰더라도, 값이 아예 없다는
    사실 자체를 가리는 대신 명확히 알려주기 위해서다. 이렇게 해야 CLI가 이
    함수만 통과하면 `cutlist["name"]`처럼 직접 접근해도 `KeyError`가 나지
    않는다.
    """
    missing = [key for key in _REQUIRED_KEYS if key not in c]
    if missing:
        return [f"다음 항목이 없습니다: {', '.join(missing)}"]

    errors: list[str] = []
    errors += _bad_name_errors(c.get("name"))

    fps = c.get("fps")
    if not isinstance(fps, (int, float)) or isinstance(fps, bool) or fps <= 0:
        errors.append(f"fps는 0보다 커야 합니다: {fps}")

    for dim in ("width", "height"):
        value = c.get(dim)
        if not isinstance(value, (int, float)) or isinstance(value, bool) or value <= 0:
            errors.append(f"{dim}는 0보다 커야 합니다: {value}")

    video = c.get("video", [])
    overlays = c.get("overlays", [])
    errors += _bad_range_errors("video", video)
    errors += _overlap_errors("video", video)
    errors += _bad_range_errors("overlays", overlays)
    errors += _overlap_errors("overlays", overlays)

    audio_by_track: dict[str, list[dict]] = {}
    for item in c.get("audio", []):
        audio_by_track.setdefault(item.get("track", ""), []).append(item)
    for track_name, items in audio_by_track.items():
        label = f"audio[{track_name}]"
        errors += _bad_range_errors(label, items)
        errors += _overlap_errors(label, items)

    for i, cap in enumerate(c.get("captions", [])):
        start = cap.get("start", 0)
        end = cap.get("end", 0)
        if start < 0 or end < 0:
            errors.append(f"captions[{i}]: 시간 값은 음수일 수 없습니다")
        if end < start:
            errors.append(f"captions[{i}]: 구간 길이가 음수입니다 (start={start}, end={end})")
        if end <= start:
            errors.append(f"captions[{i}]: end는 start보다 커야 합니다 (start={start}, end={end})")

    return errors


def _srt_time(seconds: float) -> str:
    total_ms = round(seconds * 1000)
    hours, rem = divmod(total_ms, 3600000)
    minutes, rem = divmod(rem, 60000)
    secs, ms = divmod(rem, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{ms:03d}"


def captions_to_srt(captions: list[dict]) -> str:
    """자막 목록을 SRT 문자열로 만든다."""
    lines: list[str] = []
    for i, cap in enumerate(captions, start=1):
        lines.append(str(i))
        lines.append(f"{_srt_time(cap['start'])} --> {_srt_time(cap['end'])}")
        lines.append(cap["text"])
        lines.append("")
    return "\n".join(lines)


def load_and_validate(path: Path, workspace: Path) -> dict:
    """`load_cutlist` + `validate_cutlist`를 한 번에 하고, 문제가 있으면 `CutlistError`로
    감싸 던진다. 두 CLI의 `main()`이 공유하는 진입점이다.
    """
    try:
        cutlist = load_cutlist(path, workspace)
    except FileNotFoundError as e:
        raise CutlistError(str(e)) from None
    except (json.JSONDecodeError, KeyError) as e:
        raise CutlistError(f"컷 목록을 읽을 수 없습니다: {e}") from None

    errors = validate_cutlist(cutlist)
    if errors:
        raise CutlistError("컷 목록이 올바르지 않습니다:\n" + "\n".join(errors))

    return cutlist


def fail(message: str) -> int:
    """한국어 오류 메시지를 stderr에 출력한다(트레이스백 없음). 종료 코드 1을 돌려준다."""
    print(message, file=sys.stderr)
    return 1
