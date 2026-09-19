import xml.etree.ElementTree as ET
import pytest
import handoff_common as hc
import to_premiere_xml as px


def cutlist(tmp_path):
    a = tmp_path / "01_원본영상" / "한글 폴더" / "a.mp4"
    a.parent.mkdir(parents=True)
    a.write_bytes(b"0")
    n = tmp_path / "n.wav"
    n.write_bytes(b"0")
    return {"name": "미니", "width": 1080, "height": 1920, "fps": 30,
            "video": [{"src": str(a), "in": 1.0, "out": 3.0, "start": 0.0}, {"src": str(a), "in": 5.0, "out": 6.5, "start": 2.0}],
            "audio": [{"src": str(n), "in": 0, "out": 3.5, "start": 0, "track": "내레이션"}],
            "captions": [{"text": "첫 자막", "start": 0.0, "end": 1.8}], "overlays": []}


def test_frames_rounding():
    assert hc.frames(1.0, 30) == 30 and hc.frames(0.0166, 30) == 0 and hc.frames(0.0167, 30) == 1


def test_validate_detects_overlap_and_bad_range(tmp_path):
    c = cutlist(tmp_path)
    assert hc.validate_cutlist(c) == []
    c["video"][1]["start"] = 1.0
    c["video"][0]["out"] = 0.5
    errs = hc.validate_cutlist(c)
    assert len(errs) == 2


def test_missing_media_raises(tmp_path):
    c = cutlist(tmp_path)
    c["video"][0]["src"] = str(tmp_path / "없음.mp4")
    import json
    p = tmp_path / "c.json"
    p.write_text(json.dumps(c, ensure_ascii=False), encoding="utf-8")
    with pytest.raises(FileNotFoundError):
        hc.load_cutlist(p, tmp_path)


def test_xmeml_structure(tmp_path):
    root = ET.fromstring(px.build_xmeml(cutlist(tmp_path)).split("<!DOCTYPE xmeml>")[-1])
    assert root.tag == "xmeml" and root.get("version") == "5"
    seq = root.find("./project/children/sequence")
    assert seq.findtext("rate/timebase") == "30"
    assert seq.findtext("media/video/format/samplecharacteristics/width") == "1080"
    clips = seq.findall("media/video/track/clipitem")
    assert [(c.findtext("start"), c.findtext("end"), c.findtext("in"), c.findtext("out")) for c in clips] == [("0", "60", "30", "90"), ("60", "105", "150", "195")]
    assert "%ED%95%9C%EA%B8%80" in clips[0].findtext("file/pathurl")     # 한글 경로 인코딩
    assert clips[1].find("file").get("id") == clips[0].find("file").get("id") and clips[1].find("file/pathurl") is None
    assert len(seq.findall("media/audio/track/clipitem")) == 1


def test_captions_to_srt():
    assert hc.captions_to_srt([{"text": "첫 자막", "start": 0.0, "end": 1.8}]) == "1\n00:00:00,000 --> 00:00:01,800\n첫 자막\n"


# --- 아래는 브리프의 모호성 해소 항목들(validate_cutlist 확장, load_cutlist 상대경로,
# 오버레이/다중 오디오 트랙, CapCut 초안·수동 묶음·CLI)에 대한 추가 커버리지다.
# 위 5개(cutlist 픽스처 포함)는 브리프의 "전문" 블록 그대로다. ---

import json
import shutil
import subprocess
from pathlib import Path

import to_capcut as tc


def test_validate_rejects_non_positive_fps_and_dims(tmp_path):
    c = cutlist(tmp_path)
    c["fps"] = 0
    c["width"] = -1
    c["height"] = 0
    errs = hc.validate_cutlist(c)
    assert len(errs) == 3


def test_validate_rejects_in_greater_equal_out_phrasing(tmp_path):
    # 해소 항목 표현: "in >= out"도 거부한다 (out <= in과 동치).
    c = cutlist(tmp_path)
    c["video"][0]["in"] = c["video"][0]["out"]
    errs = hc.validate_cutlist(c)
    assert any("out" in e for e in errs)


def test_validate_reports_missing_required_keys_instead_of_keyerror(tmp_path):
    c = cutlist(tmp_path)
    del c["name"]
    errs = hc.validate_cutlist(c)
    assert len(errs) == 1
    assert "name" in errs[0]


def test_validate_treats_audio_captions_overlays_as_optional(tmp_path):
    c = cutlist(tmp_path)
    del c["audio"]
    del c["captions"]
    del c["overlays"]
    assert hc.validate_cutlist(c) == []


def test_load_cutlist_resolves_relative_paths(tmp_path):
    (tmp_path / "01_원본영상").mkdir()
    video_path = tmp_path / "01_원본영상" / "a.mp4"
    video_path.write_bytes(b"0")
    c = {
        "name": "t", "width": 1080, "height": 1920, "fps": 30,
        "video": [{"src": "01_원본영상/a.mp4", "in": 0.0, "out": 1.0, "start": 0.0}],
        "audio": [], "captions": [], "overlays": [],
    }
    p = tmp_path / "c.json"
    p.write_text(json.dumps(c, ensure_ascii=False), encoding="utf-8")

    loaded = hc.load_cutlist(p, tmp_path)
    assert Path(loaded["video"][0]["src"]) == video_path
    assert Path(loaded["video"][0]["src"]).is_absolute()


def test_xmeml_overlays_go_to_second_video_track_and_audio_tracks_split_by_name(tmp_path):
    c = cutlist(tmp_path)
    b = tmp_path / "b.mp4"
    b.write_bytes(b"0")
    c["overlays"] = [{"src": str(b), "in": 0.0, "out": 1.0, "start": 0.0}]
    m = tmp_path / "m.wav"
    m.write_bytes(b"0")
    c["audio"].append({"src": str(m), "in": 0.0, "out": 1.0, "start": 0.0, "track": "음악"})

    root = ET.fromstring(px.build_xmeml(c).split("<!DOCTYPE xmeml>")[-1])
    seq = root.find("./project/children/sequence")

    video_tracks = seq.findall("media/video/track")
    assert len(video_tracks) == 2
    assert len(video_tracks[0].findall("clipitem")) == 2
    assert len(video_tracks[1].findall("clipitem")) == 1

    audio_tracks = seq.findall("media/audio/track")
    assert len(audio_tracks) == 2


def test_xmeml_duration_accounts_for_audio_extending_past_last_video_clip(tmp_path):
    c = cutlist(tmp_path)
    # 원래 video의 마지막 clip end frame은 105(60+45)다. 내레이션을 그보다 길게 늘린다.
    c["audio"][0]["in"] = 0.0
    c["audio"][0]["out"] = 10.0  # start=0이므로 end frame = frames(10.0,30) = 300

    root = ET.fromstring(px.build_xmeml(c).split("<!DOCTYPE xmeml>")[-1])
    seq = root.find("./project/children/sequence")
    audio_clip = seq.find("media/audio/track/clipitem")

    assert audio_clip.findtext("end") == "300"
    assert seq.findtext("duration") == "300"


def test_premiere_cli_writes_files_and_prints_json(tmp_path, capsys):
    c = cutlist(tmp_path)
    p = tmp_path / "c.json"
    p.write_text(json.dumps(c, ensure_ascii=False), encoding="utf-8")
    out_dir = tmp_path / "out"

    exit_code = px.main([str(p), "--workspace", str(tmp_path), "--out", str(out_dir)])
    captured = capsys.readouterr()

    assert exit_code == 0
    result = json.loads(captured.out)
    assert len(result["files"]) == 3
    assert (out_dir / "미니.xml").is_file()
    assert (out_dir / "미니.srt").is_file()
    assert (out_dir / "가져오는_방법.md").is_file()
    assert "한 방향" in (out_dir / "가져오는_방법.md").read_text(encoding="utf-8")


def test_premiere_cli_missing_media_exits_1_korean_no_traceback(tmp_path, capsys):
    c = cutlist(tmp_path)
    c["video"][0]["src"] = str(tmp_path / "없음.mp4")
    p = tmp_path / "c.json"
    p.write_text(json.dumps(c, ensure_ascii=False), encoding="utf-8")

    exit_code = px.main([str(p), "--workspace", str(tmp_path), "--out", str(tmp_path / "out")])
    captured = capsys.readouterr()

    assert exit_code == 1
    assert captured.out == ""
    assert "찾을 수 없습니다" in captured.err
    assert "Traceback" not in captured.err


def test_premiere_cli_missing_required_key_exits_1_no_keyerror(tmp_path, capsys):
    c = cutlist(tmp_path)
    del c["name"]
    p = tmp_path / "c.json"
    p.write_text(json.dumps(c, ensure_ascii=False), encoding="utf-8")

    exit_code = px.main([str(p), "--workspace", str(tmp_path), "--out", str(tmp_path / "out")])
    captured = capsys.readouterr()

    assert exit_code == 1
    assert captured.out == ""
    assert "name" in captured.err
    assert "Traceback" not in captured.err
    assert "KeyError" not in captured.err


def test_premiere_cli_invalid_cutlist_exits_1_no_traceback(tmp_path, capsys):
    c = cutlist(tmp_path)
    c["fps"] = 0
    p = tmp_path / "c.json"
    p.write_text(json.dumps(c, ensure_ascii=False), encoding="utf-8")

    exit_code = px.main([str(p), "--workspace", str(tmp_path), "--out", str(tmp_path / "out")])
    captured = capsys.readouterr()

    assert exit_code == 1
    assert "fps" in captured.err
    assert "Traceback" not in captured.err


# --- to_capcut: 순수 보정 함수 (pycapcut 없이도 동작) ---


def test_fix_text_style_ranges_aligns_consecutive_and_last_to_text_length():
    doc = {
        "materials": {
            "texts": [
                {
                    "id": "t1",
                    "content": json.dumps(
                        {"text": "안녕하세요", "styles": [{"range": [0, 2]}, {"range": [2, 999]}]},
                        ensure_ascii=False,
                    ),
                }
            ]
        }
    }
    tc.fix_text_style_ranges(doc)
    content = json.loads(doc["materials"]["texts"][0]["content"])
    assert content["styles"][0]["range"] == [0, 2]
    assert content["styles"][1]["range"] == [2, 5]  # len("안녕하세요") == 5


def test_fix_text_style_ranges_single_style_matches_text_length():
    doc = {
        "materials": {
            "texts": [{"id": "t1", "content": json.dumps({"text": "abc", "styles": [{"range": [0, 999]}]})}]
        }
    }
    tc.fix_text_style_ranges(doc)
    content = json.loads(doc["materials"]["texts"][0]["content"])
    assert content["styles"][0]["range"] == [0, 3]


def test_fix_text_refs_drops_dangling_ids_keeps_valid():
    doc = {
        "materials": {"speeds": [{"id": "speed-1"}], "texts": [{"id": "text-1"}]},
        "tracks": [{"type": "text", "segments": [{"extra_material_refs": ["speed-1", "ghost-id"]}]}],
    }
    tc.fix_text_refs(doc)
    assert doc["tracks"][0]["segments"][0]["extra_material_refs"] == ["speed-1"]


# --- to_capcut: 수동 묶음 대안 (pycapcut 불필요) ---


def test_fallback_bundle_writes_four_files(tmp_path):
    c = cutlist(tmp_path)
    out_dir = tc.fallback_bundle(c, tmp_path / "bundle")
    assert (out_dir / "미니.srt").is_file()
    assert (out_dir / "컷목록.md").is_file()
    assert (out_dir / "오버레이_파일_목록.md").is_file()
    assert (out_dir / "가져오는_방법.md").is_file()
    assert "한 방향" in (out_dir / "가져오는_방법.md").read_text(encoding="utf-8")


def test_capcut_bundle_cli_writes_files_and_prints_json(tmp_path, capsys):
    c = cutlist(tmp_path)
    p = tmp_path / "c.json"
    p.write_text(json.dumps(c, ensure_ascii=False), encoding="utf-8")
    out_dir = tmp_path / "bundle"

    exit_code = tc.main([str(p), "--workspace", str(tmp_path), "--bundle-out", str(out_dir)])
    captured = capsys.readouterr()

    assert exit_code == 0
    result = json.loads(captured.out)
    assert len(result["files"]) == 4
    assert (out_dir / "미니.srt").is_file()


def test_capcut_cli_missing_media_exits_1_korean_no_traceback(tmp_path, capsys):
    c = cutlist(tmp_path)
    c["video"][0]["src"] = str(tmp_path / "없음.mp4")
    p = tmp_path / "c.json"
    p.write_text(json.dumps(c, ensure_ascii=False), encoding="utf-8")

    exit_code = tc.main([str(p), "--workspace", str(tmp_path), "--bundle-out", str(tmp_path / "out")])
    captured = capsys.readouterr()

    assert exit_code == 1
    assert captured.out == ""
    assert "찾을 수 없습니다" in captured.err
    assert "Traceback" not in captured.err


def test_capcut_cli_missing_required_key_exits_1_no_keyerror(tmp_path, capsys):
    c = cutlist(tmp_path)
    del c["width"]
    p = tmp_path / "c.json"
    p.write_text(json.dumps(c, ensure_ascii=False), encoding="utf-8")

    exit_code = tc.main([str(p), "--workspace", str(tmp_path), "--bundle-out", str(tmp_path / "out")])
    captured = capsys.readouterr()

    assert exit_code == 1
    assert captured.out == ""
    assert "width" in captured.err
    assert "Traceback" not in captured.err
    assert "KeyError" not in captured.err


def test_capcut_cli_requires_drafts_dir_or_bundle_out(tmp_path):
    c = cutlist(tmp_path)
    p = tmp_path / "c.json"
    p.write_text(json.dumps(c, ensure_ascii=False), encoding="utf-8")

    with pytest.raises(SystemExit):
        tc.main([str(p), "--workspace", str(tmp_path)])


# --- to_capcut: 실제 pycapcut 초안 생성 (ffmpeg로 만든 실제 미디어 필요) ---


def _ffmpeg_available() -> bool:
    return shutil.which("ffmpeg") is not None


@pytest.fixture
def real_media(tmp_path):
    if not _ffmpeg_available():
        pytest.skip("ffmpeg가 없어 건너뜁니다")
    video = tmp_path / "clip.mp4"
    audio = tmp_path / "clip.wav"
    subprocess.run(
        [
            "ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi",
            "-i", "testsrc=size=320x568:duration=2:rate=30", "-pix_fmt", "yuv420p", str(video),
        ],
        check=True,
    )
    subprocess.run(
        ["ffmpeg", "-y", "-loglevel", "error", "-f", "lavfi", "-i", "sine=frequency=440:duration=2",
         "-ar", "48000", str(audio)],
        check=True,
    )
    return video, audio


def _real_cutlist(video: Path, audio: Path) -> dict:
    return {
        "name": "테스트컷",
        "width": 1080,
        "height": 1920,
        "fps": 30,
        "video": [
            {"src": str(video), "in": 0.0, "out": 1.0, "start": 0.0},
            {"src": str(video), "in": 1.0, "out": 1.9, "start": 1.0},
        ],
        "audio": [{"src": str(audio), "in": 0.0, "out": 1.9, "start": 0.0, "track": "내레이션"}],
        "captions": [{"text": "첫 자막", "start": 0.0, "end": 1.0}],
        "overlays": [],
    }


def test_build_draft_creates_expected_track_structure(tmp_path, real_media):
    pytest.importorskip("pycapcut")
    video, audio = real_media
    drafts_dir = tmp_path / "drafts"
    c = _real_cutlist(video, audio)

    draft_path = tc.build_draft(c, drafts_dir)

    assert draft_path == drafts_dir / "테스트컷"
    doc = json.loads((draft_path / "draft_content.json").read_text(encoding="utf-8"))
    tracks = {t["type"]: t for t in doc["tracks"]}
    assert len(tracks["video"]["segments"]) == 2
    assert len(tracks["audio"]["segments"]) == 1
    assert len(tracks["text"]["segments"]) == 1

    valid_ids = {
        entry["id"]
        for value in doc["materials"].values()
        if isinstance(value, list)
        for entry in value
        if isinstance(entry, dict) and "id" in entry
    }
    for track in doc["tracks"]:
        for seg in track["segments"]:
            for ref in seg.get("extra_material_refs", []):
                assert ref in valid_ids, f"매달린 참조: {ref}"

    assert (draft_path / "draft_meta_info.json").is_file()


def test_build_draft_creates_overlay_track_when_overlays_present(tmp_path, real_media):
    pytest.importorskip("pycapcut")
    video, audio = real_media
    drafts_dir = tmp_path / "drafts"
    c = _real_cutlist(video, audio)
    c["overlays"] = [{"src": str(video), "in": 0.0, "out": 0.5, "start": 0.0}]

    draft_path = tc.build_draft(c, drafts_dir)

    doc = json.loads((draft_path / "draft_content.json").read_text(encoding="utf-8"))
    video_tracks = [t for t in doc["tracks"] if t["type"] == "video"]
    assert len(video_tracks) == 2
    overlay_track = next(t for t in video_tracks if t["name"] == "오버레이")
    assert len(overlay_track["segments"]) == 1


def test_build_draft_never_overwrites_existing_draft(tmp_path, real_media):
    pytest.importorskip("pycapcut")
    video, audio = real_media
    drafts_dir = tmp_path / "drafts"
    c = _real_cutlist(video, audio)

    first = tc.build_draft(c, drafts_dir)
    (first / "MARKER.txt").write_text("do-not-touch", encoding="utf-8")

    second = tc.build_draft(c, drafts_dir)

    assert second == drafts_dir / "테스트컷_2"
    assert (first / "MARKER.txt").read_text(encoding="utf-8") == "do-not-touch"


def test_capcut_drafts_dir_cli_end_to_end(tmp_path, real_media, capsys):
    pytest.importorskip("pycapcut")
    video, audio = real_media
    c = _real_cutlist(video, audio)
    p = tmp_path / "c.json"
    p.write_text(json.dumps(c, ensure_ascii=False), encoding="utf-8")
    drafts_dir = tmp_path / "drafts"

    exit_code = tc.main([str(p), "--workspace", str(tmp_path), "--drafts-dir", str(drafts_dir)])
    captured = capsys.readouterr()

    assert exit_code == 0
    result = json.loads(captured.out)
    assert result["draft"] == str(drafts_dir / "테스트컷")
    assert (drafts_dir / "테스트컷" / "draft_content.json").is_file()


def test_validate_rejects_cutlist_names_that_escape_the_output_dir(tmp_path):
    """이름은 그대로 파일 이름이 된다. 구분자가 들어오면 out_dir 밖에 쓰게 된다 (M7)."""
    c = cutlist(tmp_path)
    for bad in ("../탈출", "위/아래", "뒤\\슬래시", "..", "."):
        c["name"] = bad
        errors = hc.validate_cutlist(c)
        assert any("name" in e for e in errors), (bad, errors)


def test_validate_accepts_an_ordinary_korean_name(tmp_path):
    c = cutlist(tmp_path)
    c["name"] = "001_동네한바퀴"
    assert hc.validate_cutlist(c) == []
