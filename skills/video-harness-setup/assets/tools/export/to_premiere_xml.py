#!/usr/bin/env python3
"""Premiere Pro(FCP7 XML)로 넘기기: xmeml 시퀀스 + SRT + 가져오는 방법 안내.

표준 라이브러리만 쓴다. 이 도구는 작업 공간 `도구/export/`에 복사되어 실행된다.
handoff는 한 방향이다 — Premiere에서 고친 내용은 코드로 돌아오지 않는다.
"""

from __future__ import annotations

import argparse
import json
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import handoff_common as hc

_IMPORT_GUIDE = """# {name} 가져오는 방법

이 폴더는 하네스가 컷 목록에서 한 번 만들어 낸 결과물입니다. Premiere Pro에서
고친 내용은 다시 코드나 컷 목록으로 돌아오지 않습니다(한 방향 넘기기).

1. Premiere Pro에서 `파일 > 가져오기`로 `{xml_name}`을 가져옵니다.
2. `{srt_name}`도 같은 방법으로 가져온 뒤, 프로젝트 패널에서 시퀀스 위로
   끌어다 놓아 캡션 트랙으로 붙입니다.
3. 원본 영상 파일 경로가 바뀌었다면 Premiere가 "미디어 찾기(Locate File)"
   대화상자를 띄웁니다. 원본 파일이 있는 위치를 지정해 주세요.
"""


def _sub(parent: ET.Element, tag: str, text: str | None = None) -> ET.Element:
    el = ET.SubElement(parent, tag)
    if text is not None:
        el.text = text
    return el


def _file_element(parent: ET.Element, src: str, fps: int, registry: dict[str, str], counters: dict[str, int]) -> None:
    """`<file>`을 만든다. 이미 등장한 src면 id만 있는 참조 태그를 만든다."""
    if src in registry:
        ET.SubElement(parent, "file", {"id": registry[src]})
        return

    counters["file"] += 1
    file_id = f"file-{counters['file']}"
    registry[src] = file_id

    file_el = ET.SubElement(parent, "file", {"id": file_id})
    _sub(file_el, "name", Path(src).name)
    _sub(file_el, "pathurl", Path(src).as_uri())
    rate_el = ET.SubElement(file_el, "rate")
    _sub(rate_el, "timebase", str(fps))
    _sub(rate_el, "ntsc", "FALSE")


def _clip_element(
    track: ET.Element, item: dict, fps: int, registry: dict[str, str], counters: dict[str, int]
) -> int:
    """`<clipitem>`을 track에 추가하고 이 클립의 타임라인 종료 프레임을 돌려준다."""
    start = hc.frames(item["start"], fps)
    in_f = hc.frames(item["in"], fps)
    out_f = hc.frames(item["out"], fps)
    end = start + (out_f - in_f)

    counters["clip"] += 1
    clip = ET.SubElement(track, "clipitem", {"id": f"clipitem-{counters['clip']}"})
    _sub(clip, "name", Path(item["src"]).name)
    _sub(clip, "start", str(start))
    _sub(clip, "end", str(end))
    _sub(clip, "in", str(in_f))
    _sub(clip, "out", str(out_f))
    _file_element(clip, item["src"], fps, registry, counters)

    return end


def build_xmeml(cutlist: dict) -> str:
    """컷 목록을 FCP7 XML(xmeml) 문자열로 만든다.

    시퀀스 1개, 비디오 트랙 V1(컷)·V2(오버레이, 있을 때만), 오디오 트랙은
    `track` 이름별로 하나씩. 같은 파일은 첫 등장에만 전체 `<file>`을 쓰고
    이후는 `<file id="..."/>` 참조만 남긴다.
    """
    fps = cutlist["fps"]
    registry: dict[str, str] = {}
    counters = {"file": 0, "clip": 0}

    xmeml = ET.Element("xmeml", {"version": "5"})
    project = ET.SubElement(xmeml, "project")
    _sub(project, "name", cutlist["name"])
    children = ET.SubElement(project, "children")
    sequence = ET.SubElement(children, "sequence")
    _sub(sequence, "name", cutlist["name"])
    duration_el = _sub(sequence, "duration", "0")

    rate = ET.SubElement(sequence, "rate")
    _sub(rate, "timebase", str(fps))
    _sub(rate, "ntsc", "FALSE")

    media = ET.SubElement(sequence, "media")
    video = ET.SubElement(media, "video")
    video_format = ET.SubElement(video, "format")
    samplechar = ET.SubElement(video_format, "samplecharacteristics")
    _sub(samplechar, "width", str(cutlist["width"]))
    _sub(samplechar, "height", str(cutlist["height"]))

    end_frames: list[int] = []

    v1 = ET.SubElement(video, "track")
    for item in cutlist.get("video", []):
        end_frames.append(_clip_element(v1, item, fps, registry, counters))

    overlays = cutlist.get("overlays", [])
    if overlays:
        v2 = ET.SubElement(video, "track")
        for item in overlays:
            end_frames.append(_clip_element(v2, item, fps, registry, counters))

    audio = ET.SubElement(media, "audio")
    audio_tracks: dict[str, ET.Element] = {}
    for item in cutlist.get("audio", []):
        track_name = item.get("track", "")
        if track_name not in audio_tracks:
            audio_tracks[track_name] = ET.SubElement(audio, "track")
        end_frames.append(_clip_element(audio_tracks[track_name], item, fps, registry, counters))

    # 시퀀스 길이는 video/overlays/audio 중 가장 늦게 끝나는 클립을 기준으로 한다 —
    # 내레이션이 마지막 영상 컷보다 길게 남는 경우가 흔하다.
    duration_el.text = str(max(end_frames) if end_frames else 0)

    xml_body = ET.tostring(xmeml, encoding="unicode")
    return f'<?xml version="1.0" encoding="UTF-8"?>\n<!DOCTYPE xmeml>\n{xml_body}'


def export_premiere(cutlist: dict, out_dir: Path) -> dict:
    """`<name>.xml`·`<name>.srt`·`가져오는_방법.md`를 out_dir에 쓰고 파일 목록을 돌려준다."""
    out_dir = Path(out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    name = cutlist["name"]
    xml_path = out_dir / f"{name}.xml"
    srt_path = out_dir / f"{name}.srt"
    guide_path = out_dir / "가져오는_방법.md"

    xml_path.write_text(build_xmeml(cutlist), encoding="utf-8")
    srt_path.write_text(hc.captions_to_srt(cutlist.get("captions", [])), encoding="utf-8")
    guide_path.write_text(
        _IMPORT_GUIDE.format(name=name, xml_name=xml_path.name, srt_name=srt_path.name),
        encoding="utf-8",
    )

    return {"files": [str(xml_path), str(srt_path), str(guide_path)]}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="컷 목록을 Premiere Pro(FCP7 XML)로 내보낸다.")
    parser.add_argument("cutlist", type=Path, help="컷 목록 JSON 경로")
    parser.add_argument("--workspace", type=Path, required=True, help="작업 공간 경로")
    parser.add_argument("--out", type=Path, required=True, help="xml/srt/안내문을 쓸 폴더")
    args = parser.parse_args(argv)

    try:
        cutlist = hc.load_and_validate(args.cutlist, args.workspace)
    except hc.CutlistError as e:
        return hc.fail(str(e))

    result = export_premiere(cutlist, args.out)
    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
