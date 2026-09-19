#!/usr/bin/env python3
"""CapCut으로 넘기기: pyCapCut 초안 생성, 안 되면 수동 묶음 대안.

`build_draft`는 `pycapcut`이 필요하다. `pycapcut`은 작업 공간의 `도구/.venv`에만
설치되므로(module_registry.py), 이 스크립트는 그 가상환경 파이썬으로 실행해야
한다. `fallback_bundle`과 두 보정 함수는 표준 라이브러리만으로 동작한다.

handoff는 한 방향이다 — CapCut에서 고친 내용은 코드나 컷 목록으로 돌아오지 않는다.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import handoff_common as hc

_IMPORT_GUIDE_BUNDLE = """# {name} 가져오는 방법 (수동 묶음)

이 컷 목록은 CapCut 초안으로 자동 변환되지 않았습니다. 아래 파일을 CapCut에서
손으로 가져와 주세요. 이 하네스가 한 번 만들어 낸 결과이며, 되돌아오지 않는
한 방향 넘기기입니다.

1. CapCut에서 새 프로젝트를 만들고 화면비를 {width}x{height}, {fps}fps로 맞춥니다.
2. `컷목록.md`의 표를 보고 원본 파일을 순서대로 타임라인에 자릅니다.
3. `{srt_name}`을 자막으로 가져옵니다("자막 가져오기").
4. `오버레이_파일_목록.md`에 파일이 있다면 두 번째 비디오 트랙에 겹쳐 올립니다.
"""


def fix_text_style_ranges(doc: dict) -> dict:
    """`materials.texts[].content`(JSON 문자열) 안 styles의 range를 이어붙인다.

    각 `styles[i].range[1]`을 다음 스타일의 시작으로, 마지막 스타일은 글자 수로
    맞춘다. pycapcut 0.0.3에서 발견된 문제를 보정한다.
    """
    texts = doc.get("materials", {}).get("texts", [])
    for text_mat in texts:
        content_raw = text_mat.get("content")
        if not content_raw:
            continue
        try:
            content = json.loads(content_raw)
        except (json.JSONDecodeError, TypeError):
            continue

        styles = content.get("styles")
        text = content.get("text", "")
        if not styles:
            continue

        for i in range(len(styles) - 1):
            styles[i]["range"][1] = styles[i + 1]["range"][0]
        styles[-1]["range"][1] = len(text)

        text_mat["content"] = json.dumps(content, ensure_ascii=False)

    return doc


def fix_text_refs(doc: dict) -> dict:
    """트랙 세그먼트의 `extra_material_refs`에서 materials에 없는 id를 없앤다.

    pycapcut 0.0.3은 텍스트 세그먼트를 만들 때 speed 참조를 남기지만, 텍스트
    세그먼트를 추가할 때는 그 speed를 materials.speeds에 등록하지 않아 매달린
    참조가 생긴다.
    """
    materials = doc.get("materials", {})
    valid_ids: set[str] = set()
    for value in materials.values():
        if not isinstance(value, list):
            continue
        for entry in value:
            if isinstance(entry, dict) and "id" in entry:
                valid_ids.add(entry["id"])

    for track in doc.get("tracks", []):
        for segment in track.get("segments", []):
            refs = segment.get("extra_material_refs")
            if refs:
                segment["extra_material_refs"] = [r for r in refs if r in valid_ids]

    return doc


def _unique_draft_name(drafts_dir: Path, name: str) -> str:
    """`name`이 이미 있으면 `_2`, `_3`... 을 붙여 비어 있는 이름을 찾는다."""
    if not (drafts_dir / name).exists():
        return name
    i = 2
    while (drafts_dir / f"{name}_{i}").exists():
        i += 1
    return f"{name}_{i}"


def _post_process_draft(draft_path: Path) -> None:
    for filename in ("draft_content.json", "draft_info.json"):
        path = draft_path / filename
        if not path.exists():
            continue
        doc = json.loads(path.read_text(encoding="utf-8"))
        fix_text_style_ranges(doc)
        fix_text_refs(doc)
        path.write_text(json.dumps(doc, ensure_ascii=False, indent=4), encoding="utf-8")


def build_draft(cutlist: dict, drafts_dir: Path):
    """컷 목록으로 CapCut 초안을 만든다. 기존 초안은 절대 건드리지 않는다.

    이름이 이미 있으면 `_2`, `_3`을 붙인다. 저장한 뒤 `fix_text_style_ranges`·
    `fix_text_refs`로 draft_content.json(있으면 draft_info.json도)을 보정한다.
    만들어진 초안 폴더 경로를 돌려준다.
    """
    import pycapcut as cc

    drafts_dir = Path(drafts_dir)
    drafts_dir.mkdir(parents=True, exist_ok=True)

    name = _unique_draft_name(drafts_dir, cutlist["name"])
    folder = cc.DraftFolder(str(drafts_dir))
    script = folder.create_draft(name, cutlist["width"], cutlist["height"], fps=cutlist["fps"])

    def us(seconds: float) -> int:
        return round(seconds * cc.SEC)

    video_items = cutlist.get("video", [])
    overlay_items = cutlist.get("overlays", [])
    audio_items = cutlist.get("audio", [])
    caption_items = cutlist.get("captions", [])

    if video_items:
        script.add_track(cc.TrackType.video, "비디오")
    if overlay_items:
        script.add_track(cc.TrackType.video, "오버레이", relative_index=1)

    video_materials: dict[str, "cc.VideoMaterial"] = {}
    audio_materials: dict[str, "cc.AudioMaterial"] = {}

    def video_material(src: str):
        if src not in video_materials:
            video_materials[src] = cc.VideoMaterial(src)
        return video_materials[src]

    def audio_material(src: str):
        if src not in audio_materials:
            audio_materials[src] = cc.AudioMaterial(src)
        return audio_materials[src]

    def video_segment(item: dict) -> "cc.VideoSegment":
        duration = us(item["out"] - item["in"])
        return cc.VideoSegment(
            video_material(item["src"]),
            cc.Timerange(us(item["start"]), duration),
            source_timerange=cc.Timerange(us(item["in"]), duration),
        )

    for item in video_items:
        script.add_segment(video_segment(item), "비디오")
    for item in overlay_items:
        script.add_segment(video_segment(item), "오버레이")

    audio_track_names: list[str] = []
    for item in audio_items:
        track_name = item.get("track") or "오디오"
        if track_name not in audio_track_names:
            audio_track_names.append(track_name)
            script.add_track(cc.TrackType.audio, track_name)
        duration = us(item["out"] - item["in"])
        seg = cc.AudioSegment(
            audio_material(item["src"]),
            cc.Timerange(us(item["start"]), duration),
            source_timerange=cc.Timerange(us(item["in"]), duration),
        )
        script.add_segment(seg, track_name)

    if caption_items:
        script.add_track(cc.TrackType.text, "자막")
        for cap in caption_items:
            seg = cc.TextSegment(
                cap["text"],
                cc.Timerange(us(cap["start"]), us(cap["end"] - cap["start"])),
                style=cc.TextStyle(size=8.0, align=1, auto_wrapping=True),
                clip_settings=cc.ClipSettings(transform_y=-0.8),
            )
            script.add_segment(seg, "자막")

    script.save()

    draft_path = drafts_dir / name
    _post_process_draft(draft_path)
    return draft_path


def _table_row(item: dict, extra: str = "") -> str:
    duration = round(item.get("out", 0) - item.get("in", 0), 3)
    row = f"| {Path(item['src']).name} | {item.get('in')} | {item.get('out')} | {item.get('start')} | {duration} |"
    if extra:
        row += f" {extra} |"
    return row


def fallback_bundle(cutlist: dict, out_dir: Path) -> Path:
    """초안 자동 생성이 안 될 때의 대안: srt·컷목록·오버레이 목록·안내문을 만든다."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    name = cutlist["name"]
    srt_path = out_dir / f"{name}.srt"
    srt_path.write_text(hc.captions_to_srt(cutlist.get("captions", [])), encoding="utf-8")

    lines = [
        "# 컷 목록",
        "",
        "## 비디오",
        "",
        "| 파일 | in | out | start | 길이(초) |",
        "| --- | --- | --- | --- | --- |",
    ]
    for item in cutlist.get("video", []):
        lines.append(_table_row(item))
    lines += [
        "",
        "## 오디오",
        "",
        "| 파일 | in | out | start | 길이(초) | 트랙 |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    for item in cutlist.get("audio", []):
        lines.append(_table_row(item, item.get("track", "")))
    (out_dir / "컷목록.md").write_text("\n".join(lines) + "\n", encoding="utf-8")

    overlays = cutlist.get("overlays", [])
    overlay_lines = ["# 오버레이 파일 목록", ""]
    if overlays:
        for item in overlays:
            overlay_lines.append(
                f"- {Path(item['src']).name} (in={item.get('in')}, out={item.get('out')}, start={item.get('start')})"
            )
    else:
        overlay_lines.append("(오버레이 없음)")
    (out_dir / "오버레이_파일_목록.md").write_text("\n".join(overlay_lines) + "\n", encoding="utf-8")

    (out_dir / "가져오는_방법.md").write_text(
        _IMPORT_GUIDE_BUNDLE.format(
            name=name,
            width=cutlist["width"],
            height=cutlist["height"],
            fps=cutlist["fps"],
            srt_name=srt_path.name,
        ),
        encoding="utf-8",
    )

    return out_dir


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="컷 목록을 CapCut으로 내보낸다.")
    parser.add_argument("cutlist", type=Path, help="컷 목록 JSON 경로")
    parser.add_argument("--workspace", type=Path, required=True, help="작업 공간 경로")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--drafts-dir", type=Path, help="CapCut 초안을 만들 폴더")
    group.add_argument("--bundle-out", type=Path, help="수동 묶음을 쓸 폴더")
    args = parser.parse_args(argv)

    try:
        cutlist = hc.load_and_validate(args.cutlist, args.workspace)
    except hc.CutlistError as e:
        return hc.fail(str(e))

    if args.drafts_dir is not None:
        try:
            draft_path = build_draft(cutlist, args.drafts_dir)
        except ImportError:
            return hc.fail("pycapcut을 찾을 수 없습니다. 도구/.venv에 설치되어 있는지 확인하세요.")
        except Exception as e:  # pycapcut의 다양한 예외를 한국어 메시지로 감싼다
            return hc.fail(f"CapCut 초안을 만들지 못했습니다: {e}")

        files = [str(draft_path)]
        for filename in ("draft_content.json", "draft_meta_info.json"):
            candidate = draft_path / filename
            if candidate.exists():
                files.append(str(candidate))
        result = {"draft": str(draft_path), "files": files}
    else:
        bundle_dir = fallback_bundle(cutlist, args.bundle_out)
        result = {
            "files": [
                str(bundle_dir / f"{cutlist['name']}.srt"),
                str(bundle_dir / "컷목록.md"),
                str(bundle_dir / "오버레이_파일_목록.md"),
                str(bundle_dir / "가져오는_방법.md"),
            ]
        }

    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
