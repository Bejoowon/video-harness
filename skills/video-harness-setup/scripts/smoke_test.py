#!/usr/bin/env python3
"""스모크 테스트: 회차 템플릿을 복사해 실제로 렌더까지 되는지 증명한다.

채널의 회차템플릿을 복사하고, frame.md로 tokens.css를 재생성하고, 짧은 내레이션을
채워 넣은 뒤 hyperframes check/render를 돌리고 결과 mp4를 검증한다. 마지막으로
모아보기(contact sheet)를 만들고 스타일 검사를 실행한다.

표준 라이브러리만 사용한다 (global-constraints.md).
"""

from __future__ import annotations

import argparse
import html
import json
import re
import shutil
import sys
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import harness_lib as h
import module_registry as m

NARRATION_TEXT = "세팅이 끝났습니다."
SMOKE_TITLE = "세팅 확인"
SMOKE_CAPTION = "자막이 보이면 성공"
SMOKE_SOURCE = "테스트"

FONT_FILES = {
    "Pretendard": "Pretendard-Bold.otf",
    "Paperlogy": "Paperlogy-Black.ttf",
}

FORMAT_DIMENSIONS = {"9:16": (1080, 1920), "16:9": (1920, 1080)}

_TEMPLATE_COPY_IGNORE = shutil.ignore_patterns("__pycache__", "*.pyc", ".DS_Store", "node_modules")


def _format_duration(value: float) -> str:
    """길이를 소수점 없는 정수("12") 또는 최대 3자리 소수("11.6")로 만든다."""
    rounded = round(float(value), 3)
    if rounded == int(rounded):
        return str(int(rounded))
    text = f"{rounded:.3f}".rstrip("0").rstrip(".")
    return text


def fill_template(
    index_html: str,
    title: str,
    caption: str,
    source: str,
    duration: float,
    width: int | None = None,
    height: int | None = None,
) -> str:
    """`#title-text` · `#caption-text` · `#source-text`와 루트·각 clip의 data-duration을 채운다.

    캡션 clip은 `duration - 0.4`가 된다. width/height를 주면 루트의
    data-width/data-height도 바꾼다(16:9 채널용). 다른 속성은 건드리지 않는다.
    """
    out = index_html

    out = re.sub(
        r'(<h1 id="title-text">).*?(</h1>)',
        lambda mo: mo.group(1) + html.escape(title) + mo.group(2),
        out,
        count=1,
        flags=re.S,
    )
    out = re.sub(
        r'(<p id="caption-text">).*?(</p>)',
        lambda mo: mo.group(1) + html.escape(caption) + mo.group(2),
        out,
        count=1,
        flags=re.S,
    )
    out = re.sub(
        r'(<p id="source-text">).*?(</p>)',
        lambda mo: mo.group(1) + html.escape(source) + mo.group(2),
        out,
        count=1,
        flags=re.S,
    )

    duration_text = _format_duration(duration)
    caption_duration_text = _format_duration(duration - 0.4)

    out = out.replace('data-duration="10"', f'data-duration="{duration_text}"')
    out = out.replace('data-duration="9.6"', f'data-duration="{caption_duration_text}"')

    if width is not None:
        out = out.replace('data-width="1080"', f'data-width="{width}"')
    if height is not None:
        out = out.replace('data-height="1920"', f'data-height="{height}"')

    return out


def wire_fonts(index_html: str, available: dict) -> str:
    """`available`에 있는 폰트 패밀리의 `@font-face` src 맨 앞에 `url(...)`을 끼워 넣는다.

    다른 패밀리는 건드리지 않는다.
    """
    out = index_html
    for family, path in available.items():
        pattern = re.compile(
            r'(@font-face\s*\{[^}]*?font-family:\s*"' + re.escape(family) + r'"[^}]*?src:\s*)(local\()'
        )
        out = pattern.sub(lambda mo, p=path: mo.group(1) + f'url("{p}"), ' + mo.group(2), out, count=1)
    return out


def probe(path: Path, run_fn=h.run) -> dict:
    """ffprobe로 `{"width","height","duration","has_audio"}`를 얻는다."""
    code, output = run_fn(
        ["ffprobe", "-v", "error", "-print_format", "json", "-show_streams", "-show_format", str(path)]
    )
    data = {}
    if code == 0 and output.strip():
        try:
            data = json.loads(output)
        except (json.JSONDecodeError, ValueError):
            data = {}

    width = height = None
    has_audio = False
    for stream in data.get("streams", []):
        if stream.get("codec_type") == "video" and width is None:
            width = stream.get("width")
            height = stream.get("height")
        elif stream.get("codec_type") == "audio":
            has_audio = True

    duration_raw = data.get("format", {}).get("duration")
    duration = float(duration_raw) if duration_raw is not None else 0.0

    return {"width": width, "height": height, "duration": duration, "has_audio": has_audio}


def verify(probe: dict, expect_w: int, expect_h: int, min_dur: float) -> list[str]:
    """probe 결과를 기대값과 비교해 문제 목록을 돌려준다."""
    problems: list[str] = []
    if probe.get("width") != expect_w or probe.get("height") != expect_h:
        problems.append(f"해상도가 {expect_w}x{expect_h}가 아닙니다: {probe.get('width')}x{probe.get('height')}")
    if (probe.get("duration") or 0) < min_dur:
        problems.append(f"길이가 {min_dur}초보다 짧습니다: {probe.get('duration')}")
    if not probe.get("has_audio"):
        problems.append("오디오 트랙이 없습니다")
    return problems


def render_env(workspace: Path, config: dict, use_wrapper: bool) -> dict:
    """래퍼를 켤 때만 필요한 추가 환경변수를 돌려준다. 아니면 빈 dict."""
    if not use_wrapper:
        return {}
    workspace = Path(workspace)
    chrome = config.get("paths", {}).get("chrome")
    if not chrome:
        chrome_path_file = workspace / "도구" / "chrome-path.txt"
        if chrome_path_file.exists():
            chrome = chrome_path_file.read_text(encoding="utf-8").strip()
    return {
        "HYPERFRAMES_BROWSER_PATH": str(workspace / "도구" / "chrome-noaudio.py"),
        "HARNESS_CHROME": chrome or "",
    }


def _parse_json_object(text: str) -> dict | None:
    """텍스트 어디에 있든(로그 줄 뒤에도) 실제 최상위 JSON 객체를 찾아 돌려준다.

    앞쪽 로그 줄뿐 아니라, 객체 안에 중첩된 객체(`_meta` 등)도 그 자리에서 유효한
    JSON으로 파싱된다. 그래서 "성공하는 마지막 파싱"이 아니라 "텍스트 끝까지
    소비하는 첫 파싱"을 진짜 최상위 객체로 본다. 끝까지 소비하는 후보가 없으면
    마지막으로 성공한 파싱으로 대체한다.
    """
    decoder = json.JSONDecoder()
    fallback = None
    idx = text.find("{")
    while idx != -1:
        try:
            obj, end = decoder.raw_decode(text, idx)
        except json.JSONDecodeError:
            idx = text.find("{", idx + 1)
            continue
        if isinstance(obj, dict):
            if not text[end:].strip():
                return obj
            fallback = obj
        idx = text.find("{", idx + 1)
    return fallback


def _findings_summary(check_json: dict) -> dict:
    return {k: v for k, v in check_json.items() if k not in ("ok", "snapshots")}


def _run_hyperframes_step(
    cmd: list[str],
    workspace: Path,
    config: dict,
    run_fn,
    log: Path,
    use_wrapper: bool,
) -> tuple[int, str, bool]:
    """명령을 실행하고, "Navigation timeout"이면 macOS에서 크롬 래퍼로 한 번 재시도한다."""
    env = render_env(workspace, config, use_wrapper)
    code, output = run_fn(cmd, env=env or None, log=log)

    platform_os = (config.get("platform") or {}).get("os") or h.platform_info().get("os")
    if code != 0 and not use_wrapper and platform_os == "darwin" and "Navigation timeout" in output:
        env2 = render_env(workspace, config, True)
        code2, output2 = run_fn(cmd, env=env2 or None, log=log)
        if code2 == 0:
            return code2, output2, True
        return code2, output2, use_wrapper

    return code, output, use_wrapper


_REFERENCE_AUDIO_EXTS = {".wav", ".m4a", ".mp3", ".flac", ".aac", ".ogg", ".mov", ".mp4"}


def _find_reference_recording(rec_dir: Path) -> tuple[Path, Path] | None:
    """녹음 폴더에서 (참고 음성, 대본 txt) 쌍을 찾는다.

    `.DS_Store` 같은 점파일과 오디오가 아닌 확장자는 무시한다(허용 목록 기반).
    대본은 음성과 이름(stem)이 같은 .txt를 우선하고, 없으면 첫 .txt를 쓴다.
    """
    audio_candidates = sorted(
        p
        for p in rec_dir.iterdir()
        if p.is_file() and not p.name.startswith(".") and p.suffix.lower() in _REFERENCE_AUDIO_EXTS
    )
    if not audio_candidates:
        return None
    ref_audio = audio_candidates[0]

    same_stem = rec_dir / f"{ref_audio.stem}.txt"
    if same_stem.is_file():
        return ref_audio, same_stem

    txt_candidates = sorted(
        p for p in rec_dir.iterdir() if p.is_file() and not p.name.startswith(".") and p.suffix.lower() == ".txt"
    )
    if not txt_candidates:
        return None
    return ref_audio, txt_candidates[0]


def _local_tts_ready(workspace: Path, config: dict, platform: dict) -> dict | None:
    """로컬 TTS에 필요한 4가지 조건을 모두 만족하면 필요한 경로들을 돌려준다. 아니면 None."""
    voice = config.get("modules", {}).get("voice", {})
    if voice.get("mode") != "local-mlx":
        return None

    model_path = voice.get("model_path") or str(workspace / m.VOICE_MODEL_REL_DIR)
    model_dir = Path(model_path)
    if not model_dir.exists():
        return None

    venv_python = m._venv_python(workspace / "도구" / "tts" / ".venv", platform)
    if not venv_python.exists():
        return None

    rec_dir = workspace / "도구" / "tts" / "녹음"
    if not rec_dir.is_dir():
        return None

    found = _find_reference_recording(rec_dir)
    if found is None:
        return None
    ref_audio, ref_text = found

    return {"model_dir": model_dir, "venv_python": venv_python, "ref_audio": ref_audio, "ref_text": ref_text}


def _generate_sine(path: Path, run_fn, log: Path) -> Path:
    run_fn(
        ["ffmpeg", "-y", "-f", "lavfi", "-i", "sine=frequency=440:duration=3", "-ar", "48000", str(path)],
        log=log,
    )
    return path


def _generate_narration(workspace: Path, config: dict, run_dir: Path, run_fn, log: Path) -> dict:
    """로컬 TTS 준비가 됐으면 시도하고, 아니면(또는 실패하면) 신호음으로 대체한다."""
    platform = config.get("platform") or h.platform_info()
    narration_wav = run_dir / "narration.wav"

    ready = _local_tts_ready(workspace, config, platform)
    if ready is None:
        return {"narration": "sine", "path": _generate_sine(narration_wav, run_fn, log)}

    text_path = run_dir / "narration_text.txt"
    text_path.write_text(NARRATION_TEXT, encoding="utf-8")
    raw_path = run_dir / "narration_raw.wav"

    code, output = run_fn(
        [
            str(ready["venv_python"]),
            str(workspace / "도구" / "tts" / "generate_local_mlx.py"),
            "--model", str(ready["model_dir"]),
            "--ref-audio", str(ready["ref_audio"]),
            "--ref-text", str(ready["ref_text"]),
            "--text", str(text_path),
            "--output", str(raw_path),
        ],
        log=log,
    )
    if code != 0:
        return {
            "narration": "sine",
            "path": _generate_sine(narration_wav, run_fn, log),
            "tts_error": output[:300],
        }

    conv_code, conv_output = run_fn(
        ["ffmpeg", "-y", "-i", str(raw_path), "-ar", "48000", str(narration_wav)],
        log=log,
    )
    if conv_code != 0:
        return {
            "narration": "sine",
            "path": _generate_sine(narration_wav, run_fn, log),
            "tts_error": conv_output[:300],
        }

    return {"narration": "local-tts", "path": narration_wav}


HANDOFF_CAPTION_TEXT = "자막이 보이면 성공"


def _build_handoff_cutlist(
    mp4_path: Path, narration_path: Path, narration_seconds: float, width: int, height: int
) -> dict:
    """스모크 결과로 만드는 최소 컷 목록: smoke.mp4를 0~4초·5~9초로 잘라 이어붙이고,
    내레이션 1트랙과 자막 1줄을 더한다."""
    caption_end = min(1.8, narration_seconds) if narration_seconds > 0 else 1.8
    return {
        "name": "스모크",
        "width": width,
        "height": height,
        "fps": 30,
        "video": [
            {"src": str(mp4_path), "in": 0.0, "out": 4.0, "start": 0.0},
            {"src": str(mp4_path), "in": 5.0, "out": 9.0, "start": 4.0},
        ],
        "audio": [
            {"src": str(narration_path), "in": 0.0, "out": narration_seconds, "start": 0.0, "track": "내레이션"}
        ],
        "captions": [{"text": HANDOFF_CAPTION_TEXT, "start": 0.0, "end": caption_end}],
        "overlays": [],
    }


def _handoff_ask_user(editor: str) -> str:
    label = "Premiere Pro" if editor == "premiere" else "CapCut"
    return f"{label}에서 도구/logs/smoke/<시각>/handoff/ 결과를 열어 컷과 자막이 맞는지 확인해 주세요."


def _files_exist(paths: list[str]) -> bool:
    return bool(paths) and all(Path(p).exists() for p in paths)


def _run_premiere_handoff(workspace: Path, cutlist_path: Path, handoff_dir: Path, run_fn, log: Path) -> dict:
    code, output = run_fn(
        [
            h.python_cmd(), str(workspace / "도구" / "export" / "to_premiere_xml.py"),
            str(cutlist_path), "--workspace", str(workspace), "--out", str(handoff_dir),
        ],
        log=log,
    )
    parsed = _parse_json_object(output) or {}
    files = list(parsed.get("files", []))
    return {"editor": "premiere", "files": files, "structure_ok": code == 0 and _files_exist(files)}


def _run_capcut_handoff(workspace: Path, config: dict, cutlist_path: Path, handoff_dir: Path, run_fn, log: Path) -> dict:
    """항상 수동 묶음을 만들고, `도구/.venv`에서 pycapcut을 쓸 수 있으면 추가로 초안도 만든다.

    초안은 실제 CapCut 초안 폴더가 아니라 `handoff_dir/capcut-draft/`에만 만든다.
    """
    platform = config.get("platform") or h.platform_info()
    venv_python = m._venv_python(workspace / "도구" / ".venv", platform)

    bundle_code, bundle_output = run_fn(
        [
            str(venv_python), str(workspace / "도구" / "export" / "to_capcut.py"),
            str(cutlist_path), "--workspace", str(workspace), "--bundle-out", str(handoff_dir),
        ],
        log=log,
    )
    bundle_result = _parse_json_object(bundle_output) or {}
    files = list(bundle_result.get("files", []))
    structure_ok = bundle_code == 0 and _files_exist(files)

    probe_code, _ = run_fn([str(venv_python), "-c", "import pycapcut"], log=log)
    if probe_code == 0:
        draft_code, draft_output = run_fn(
            [
                str(venv_python), str(workspace / "도구" / "export" / "to_capcut.py"),
                str(cutlist_path), "--workspace", str(workspace), "--drafts-dir", str(handoff_dir),
            ],
            log=log,
        )
        draft_result = _parse_json_object(draft_output) or {}
        draft_path = draft_result.get("draft")
        final_draft_path = handoff_dir / "capcut-draft"
        if draft_code == 0 and draft_path and Path(draft_path).exists():
            if not final_draft_path.exists():
                shutil.move(draft_path, final_draft_path)
            files.append(str(final_draft_path))
            structure_ok = structure_ok and final_draft_path.exists()
        else:
            structure_ok = False

    return {"editor": "capcut", "files": files, "structure_ok": structure_ok}


def run_handoff_export(
    workspace: Path,
    config: dict,
    mp4_path: Path,
    narration_path: Path,
    narration_seconds: float,
    width: int,
    height: int,
    run_dir: Path,
    run_fn,
    log: Path,
) -> dict:
    """`modules.handoff.editor`에 맞춰 스모크 결과를 편집기 도구로 넘긴다.

    `editor`가 "premiere"가 아니면 CapCut 경로(수동 묶음 + 가능하면 초안)를 탄다.
    호출 쪽(`run_smoke_test`)에서 `editor != "none"`일 때만 부른다.
    """
    handoff_editor = config.get("modules", {}).get("handoff", {}).get("editor")
    handoff_dir = run_dir / "handoff"
    handoff_dir.mkdir(parents=True, exist_ok=True)

    cutlist = _build_handoff_cutlist(mp4_path, narration_path, narration_seconds, width, height)
    cutlist_path = run_dir / "handoff_cutlist.json"
    cutlist_path.write_text(json.dumps(cutlist, ensure_ascii=False), encoding="utf-8")

    if handoff_editor == "premiere":
        result = _run_premiere_handoff(workspace, cutlist_path, handoff_dir, run_fn, log)
    else:
        result = _run_capcut_handoff(workspace, config, cutlist_path, handoff_dir, run_fn, log)

    result["ask_user"] = _handoff_ask_user(handoff_editor)
    return result


def _resolve_channel(config: dict, channel_id: str | None) -> dict | None:
    channels = config.get("channels", [])
    if channel_id:
        return next((c for c in channels if c.get("id") == channel_id), None)
    if len(channels) == 1:
        return channels[0]
    return None


def _wire_project_fonts(workspace: Path, project_dir: Path) -> dict:
    """작업 공간 폰트가 있으면 프로젝트로 복사하고 wire_fonts로 연결한다."""
    font_dir = workspace / "스타일_라이브러리" / "01_폰트"
    available: dict[str, str] = {}
    for family, filename in FONT_FILES.items():
        src = font_dir / filename
        if not src.exists():
            continue
        dest_dir = project_dir / "assets" / "fonts"
        dest_dir.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(src, dest_dir / filename)
        available[family] = f"assets/fonts/{filename}"
    return available


def _make_contact_sheet(mp4_path: Path, run_dir: Path, run_fn, log: Path) -> str | None:
    """5장 썸네일을 한 줄로 이어붙인 모아보기(jpg)를 만든다. 실패하면 None. 두 엔진이 공유한다."""
    contact_path = run_dir / "contact.jpg"
    contact_cmd = [
        "ffmpeg", "-y", "-i", str(mp4_path),
        "-vf", "fps=1/2,scale=270:-1,tile=5x1", "-frames:v", "1", str(contact_path),
    ]
    contact_code, _ = run_fn(contact_cmd, log=log)
    return str(contact_path) if contact_code == 0 else None


def _run_style_check(
    venv_python: Path, workspace: Path, frame_path: Path, project_dir: Path, run_fn, log: Path
) -> dict | None:
    """check_style.py를 돌려 파싱한 결과를 돌려준다. 두 엔진이 공유한다(대상 파일 확장자로 구분)."""
    style_cmd = [
        str(venv_python), str(workspace / "도구" / "style" / "check_style.py"),
        str(frame_path), str(project_dir), "--json",
    ]
    _, style_output = run_fn(style_cmd, log=log)
    return _parse_json_object(style_output)


def _fail_result(result: dict, reason: str, run_dir: Path, workspace: Path, config: dict) -> dict:
    """공통 실패 처리: result에 에러를 채우고 config 상태를 갱신한 뒤 result.json을 쓴다.

    두 엔진의 `_fail` 클로저가 이 함수 하나에 위임한다.
    """
    result["error"] = reason
    config.setdefault("status", {})["smoke_test"] = "failed"
    h.save_config(workspace, config)
    (run_dir / "result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


def _prepare_project(
    workspace: Path, config: dict, channel: dict, template_src: Path, project_dir: Path, template_label: str
) -> dict:
    """공통 준비 단계: 회차템플릿을 `project_dir`로 복사하고 도구 venv 파이썬을 확인한다.

    실패하면 `{"ok": False, "error": "..."}`, 성공하면 `{"ok": True, "venv_python": Path}`.
    `template_label`은 오류 메시지에 넣을 템플릿 이름("회차템플릿"/"Remotion 회차템플릿").
    두 엔진이 공유한다.
    """
    # 조치 명령은 doctor와 같은 `harness_lib.script_fix`로 만든다 — 실제 스크립트 경로와
    # 플랫폼 인터프리터가 들어가고 경로가 따옴표로 감싸여 그대로 복사해 실행할 수 있다.
    # (따옴표는 f-string 식 밖에서 미리 붙인다 — 식 안의 백슬래시는 3.12 이전에서 못 쓴다.)
    quoted_workspace = f'"{workspace}"'

    if not template_src.is_dir():
        channel_ref = channel.get("id") or channel["name"]
        scaffold_cmd = h.script_fix("scaffold.py", quoted_workspace, "--channel", channel_ref)
        return {
            "ok": False,
            "error": (
                f"채널 '{channel['name']}'의 {template_label}이 없습니다. 먼저 "
                f"`{scaffold_cmd}`를 실행하세요."
            ),
        }

    # 같은 초에 두 번 돌면 `%Y%m%d-%H%M%S` run 디렉터리가 겹친다. 날 FileExistsError로
    # 죽는 대신 덮어 쓰며 잇는다(둘 다 스크래치 폴더라 잃을 것이 없다).
    shutil.copytree(template_src, project_dir, dirs_exist_ok=True, ignore=_TEMPLATE_COPY_IGNORE)

    platform = config.get("platform") or h.platform_info()
    venv_python = m._venv_python(workspace / "도구" / ".venv", platform)
    if not venv_python.exists():
        install_cmd = h.script_fix("install_module.py", "run", quoted_workspace, "tools-venv")
        return {
            "ok": False,
            "error": f"도구/.venv가 없습니다. 먼저 `{install_cmd}`를 실행하세요.",
        }

    return {"ok": True, "venv_python": venv_python}


def _prepare_narration(
    workspace: Path, config: dict, run_dir: Path, project_dir: Path, dest_rel: str, run_fn, log_path: Path
) -> dict:
    """내레이션을 만들어 프로젝트 안 `dest_rel`(엔진마다 다른 상대경로)에 복사하고,
    길이를 재서 스모크 duration까지 계산한다. 두 엔진이 공유한다.

    반환: `narration`/`tts_error`(있으면)/`project_narration`/`narration_seconds`/`duration`.
    """
    narration_info = _generate_narration(workspace, config, run_dir, run_fn, log_path)

    project_narration = project_dir / dest_rel
    project_narration.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(narration_info["path"], project_narration)

    narration_probe = probe(project_narration, run_fn=run_fn)
    narration_seconds = narration_probe.get("duration") or 3.0
    duration = max(10.0, narration_seconds + 1)

    prepared = {
        "narration": narration_info["narration"],
        "project_narration": project_narration,
        "narration_seconds": narration_seconds,
        "duration": duration,
    }
    if "tts_error" in narration_info:
        prepared["tts_error"] = narration_info["tts_error"]
    return prepared


_CANVAS_RE = re.compile(r"canvas:\s*\{\s*width:\s*(\d+)\s*,\s*height:\s*(\d+)")


def _read_frame_canvas(frame_path: Path) -> tuple[int, int] | None:
    """frame.md 머리말에서 canvas의 width/height만 정규식으로 읽는다(PyYAML 없이).

    smoke_test.py는 표준 라이브러리만 쓰므로(global-constraints.md) 이 정도 가벼운
    파싱만 한다 — frame.md의 나머지 구조는 신경 쓰지 않는다. 못 찾으면 None.
    """
    if not frame_path.is_file():
        return None
    match = _CANVAS_RE.search(frame_path.read_text(encoding="utf-8"))
    if not match:
        return None
    return int(match.group(1)), int(match.group(2))


def _canvas_mismatch_error(frame_path: Path, channel_format: str | None) -> str | None:
    """frame.md의 canvas가 채널 포맷과 어긋나면 한국어 오류 메시지를 돌려준다.

    맞거나 canvas를 못 읽으면(그 뒤 단계에서 걸러지도록) None을 돌려준다. 두 엔진이
    공유한다 — HyperFrames는 canvas 값을 직접 쓰진 않지만, frame.md가 채널 포맷과
    어긋나 있으면 나중에 Remotion으로 바꿀 때도 안전하도록 같은 시점에 검증한다.
    """
    expect_w, expect_h = FORMAT_DIMENSIONS.get(channel_format, FORMAT_DIMENSIONS["9:16"])
    actual = _read_frame_canvas(frame_path)
    if actual is None or actual == (expect_w, expect_h):
        return None
    actual_w, actual_h = actual
    return (
        f"frame.md의 canvas({actual_w}x{actual_h})가 채널 포맷 '{channel_format or '9:16'}'의 "
        f"해상도({expect_w}x{expect_h})와 다릅니다. frame.md의 canvas 값을 고치세요."
    )


def _run_hyperframes_smoke_test(
    workspace: Path,
    channel: dict,
    config: dict,
    run_dir: Path,
    project_dir: Path,
    log_path: Path,
    run_fn,
) -> dict:
    """HyperFrames 회차템플릿으로 스모크 테스트를 돌린다."""
    version = config.get("modules", {}).get("render", {}).get("hyperframes_version", m.DEFAULT_HYPERFRAMES_VERSION)

    channel_base = workspace / channel["name"]
    template_src = channel_base / "03_편집프로젝트" / "_채널공용" / "회차템플릿"
    frame_path = channel_base / "03_편집프로젝트" / "_채널공용" / "frame.md"

    result: dict = {
        "passed": False,
        "engine": "hyperframes",
        "video": None,
        "contact_sheet": None,
        "narration": None,
        "check_ok": False,
        "verify_problems": [],
        "style": None,
        "used_chrome_wrapper": bool(config.get("paths", {}).get("use_chrome_wrapper")),
        "studio_hint": f"npx --yes hyperframes@{version} preview {project_dir}",
    }

    def _fail(reason: str) -> dict:
        return _fail_result(result, reason, run_dir, workspace, config)

    prep = _prepare_project(workspace, config, channel, template_src, project_dir, "회차템플릿")
    if not prep["ok"]:
        return _fail(prep["error"])
    venv_python = prep["venv_python"]

    canvas_error = _canvas_mismatch_error(frame_path, channel.get("format"))
    if canvas_error:
        return _fail(canvas_error)

    tokens_css = project_dir / "tokens.css"
    tokens_code, tokens_output = run_fn(
        [str(venv_python), str(workspace / "도구" / "style" / "build_tokens.py"), str(frame_path), "--css", str(tokens_css)],
        log=log_path,
    )
    if tokens_code != 0:
        return _fail(f"tokens.css 생성에 실패했습니다: {tokens_output[:300]}")

    narration_prepared = _prepare_narration(
        workspace, config, run_dir, project_dir, "assets/narration.wav", run_fn, log_path
    )
    result["narration"] = narration_prepared["narration"]
    if "tts_error" in narration_prepared:
        result["tts_error"] = narration_prepared["tts_error"]
    project_narration = narration_prepared["project_narration"]
    narration_seconds = narration_prepared["narration_seconds"]
    duration = narration_prepared["duration"]

    index_path = project_dir / "index.html"
    index_text = index_path.read_text(encoding="utf-8")

    available_fonts = _wire_project_fonts(workspace, project_dir)
    if available_fonts:
        index_text = wire_fonts(index_text, available_fonts)

    width = height = None
    if channel.get("format") == "16:9":
        width, height = FORMAT_DIMENSIONS["16:9"]

    index_text = fill_template(index_text, SMOKE_TITLE, SMOKE_CAPTION, SMOKE_SOURCE, duration, width=width, height=height)
    index_path.write_text(index_text, encoding="utf-8")

    use_wrapper = bool(config.get("paths", {}).get("use_chrome_wrapper"))

    check_cmd = [h.node_cmd("npx"), "--yes", f"hyperframes@{version}", "check", str(project_dir), "--json"]
    check_code, check_output, use_wrapper = _run_hyperframes_step(
        check_cmd, workspace, config, run_fn, log_path, use_wrapper
    )
    if use_wrapper:
        config.setdefault("paths", {})["use_chrome_wrapper"] = True
    result["used_chrome_wrapper"] = use_wrapper

    check_json = _parse_json_object(check_output) or {}
    check_ok = bool(check_json.get("ok"))
    result["check_ok"] = check_ok

    if not check_ok:
        result["findings"] = _findings_summary(check_json)
        return _fail("hyperframes check가 통과하지 못했습니다.")

    mp4_path = run_dir / "smoke.mp4"
    render_cmd = [
        h.node_cmd("npx"), "--yes", f"hyperframes@{version}", "render", str(project_dir),
        "--output", str(mp4_path), "--quality", "draft",
    ]
    render_code, render_output, use_wrapper = _run_hyperframes_step(
        render_cmd, workspace, config, run_fn, log_path, use_wrapper
    )
    if use_wrapper:
        config.setdefault("paths", {})["use_chrome_wrapper"] = True
    result["used_chrome_wrapper"] = use_wrapper

    if render_code != 0:
        return _fail(f"렌더에 실패했습니다: {render_output[:300]}")

    result["video"] = str(mp4_path)

    expect_w, expect_h = FORMAT_DIMENSIONS.get(channel.get("format"), FORMAT_DIMENSIONS["9:16"])
    video_probe = probe(mp4_path, run_fn=run_fn)
    verify_problems = verify(video_probe, expect_w, expect_h, duration - 0.5)
    result["verify_problems"] = verify_problems

    handoff_editor = config.get("modules", {}).get("handoff", {}).get("editor", "none")
    if handoff_editor != "none":
        result["handoff"] = run_handoff_export(
            workspace, config, mp4_path, project_narration, narration_seconds,
            expect_w, expect_h, run_dir, run_fn, log_path,
        )

    result["contact_sheet"] = _make_contact_sheet(mp4_path, run_dir, run_fn, log_path)

    style_result = _run_style_check(venv_python, workspace, frame_path, project_dir, run_fn, log_path)
    result["style"] = style_result
    style_errors = bool(style_result and style_result.get("errors"))

    # 렌더 실패는 이미 위에서 돌아갔으므로 여기서 render_code를 다시 보지 않는다.
    passed = check_ok and not verify_problems and not style_errors
    result["passed"] = passed

    config.setdefault("status", {})["smoke_test"] = "passed" if passed else "failed"
    h.save_config(workspace, config)

    (run_dir / "result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


def _run_remotion_smoke_test(
    workspace: Path,
    channel: dict,
    config: dict,
    run_dir: Path,
    project_dir: Path,
    log_path: Path,
    run_fn,
) -> dict:
    """Remotion 회차템플릿으로 스모크 테스트를 돌린다.

    probe/verify/모아보기/스타일 검사는 HyperFrames 경로와 같은 헬퍼를 그대로 쓴다.
    `hyperframes check` 같은 별도 정적 검증 단계는 없고, 렌더 성공 여부로 대신한다.
    """
    channel_base = workspace / channel["name"]
    template_src = channel_base / "03_편집프로젝트" / "_채널공용" / "회차템플릿-remotion"
    frame_path = channel_base / "03_편집프로젝트" / "_채널공용" / "frame.md"

    result: dict = {
        "passed": False,
        "engine": "remotion",
        "video": None,
        "contact_sheet": None,
        "narration": None,
        "verify_problems": [],
        "style": None,
        "npm_install_ran": False,
        "studio_hint": f"cd {project_dir} && npx remotion studio",
    }

    def _fail(reason: str) -> dict:
        return _fail_result(result, reason, run_dir, workspace, config)

    prep = _prepare_project(workspace, config, channel, template_src, project_dir, "Remotion 회차템플릿")
    if not prep["ok"]:
        return _fail(prep["error"])
    venv_python = prep["venv_python"]

    canvas_error = _canvas_mismatch_error(frame_path, channel.get("format"))
    if canvas_error:
        return _fail(canvas_error)

    scratch_css = run_dir / "tokens.css"
    theme_ts = project_dir / "src" / "theme.ts"
    tokens_code, tokens_output = run_fn(
        [
            str(venv_python), str(workspace / "도구" / "style" / "build_tokens.py"),
            str(frame_path), "--css", str(scratch_css), "--ts", str(theme_ts),
        ],
        log=log_path,
    )
    if tokens_code != 0:
        return _fail(f"theme.ts 생성에 실패했습니다: {tokens_output[:300]}")

    if not (project_dir / "node_modules").is_dir():
        install_code, install_output = run_fn(
            [h.node_cmd("npm"), "install", "--no-audit", "--no-fund"], cwd=project_dir, log=log_path,
        )
        result["npm_install_ran"] = True
        if install_code != 0:
            return _fail(f"npm install에 실패했습니다: {install_output[:300]}")

    narration_prepared = _prepare_narration(
        workspace, config, run_dir, project_dir, "public/narration.wav", run_fn, log_path
    )
    result["narration"] = narration_prepared["narration"]
    if "tts_error" in narration_prepared:
        result["tts_error"] = narration_prepared["tts_error"]
    project_narration = narration_prepared["project_narration"]
    narration_seconds = narration_prepared["narration_seconds"]
    duration = narration_prepared["duration"]

    props = {
        "title": SMOKE_TITLE,
        "caption": SMOKE_CAPTION,
        "source": SMOKE_SOURCE,
        "narration": "narration.wav",
        "durationInSeconds": duration,
    }
    props_path = run_dir / "props.json"
    props_path.write_text(json.dumps(props, ensure_ascii=False), encoding="utf-8")

    mp4_path = run_dir / "smoke.mp4"
    render_cmd = [
        h.node_cmd("npx"), "remotion", "render", "src/index.ts", "Episode", str(mp4_path),
        f"--props={props_path}",
    ]
    render_code, render_output = run_fn(render_cmd, cwd=project_dir, log=log_path)
    if render_code != 0:
        return _fail(f"렌더에 실패했습니다: {render_output[:300]}")

    result["video"] = str(mp4_path)

    expect_w, expect_h = FORMAT_DIMENSIONS.get(channel.get("format"), FORMAT_DIMENSIONS["9:16"])
    video_probe = probe(mp4_path, run_fn=run_fn)
    verify_problems = verify(video_probe, expect_w, expect_h, duration - 0.5)
    result["verify_problems"] = verify_problems

    handoff_editor = config.get("modules", {}).get("handoff", {}).get("editor", "none")
    if handoff_editor != "none":
        result["handoff"] = run_handoff_export(
            workspace, config, mp4_path, project_narration, narration_seconds,
            expect_w, expect_h, run_dir, run_fn, log_path,
        )

    result["contact_sheet"] = _make_contact_sheet(mp4_path, run_dir, run_fn, log_path)

    style_result = _run_style_check(venv_python, workspace, frame_path, project_dir, run_fn, log_path)
    result["style"] = style_result
    style_errors = bool(style_result and style_result.get("errors"))

    # 렌더 실패는 이미 위에서 돌아갔다.
    passed = not verify_problems and not style_errors
    result["passed"] = passed

    config.setdefault("status", {})["smoke_test"] = "passed" if passed else "failed"
    h.save_config(workspace, config)

    (run_dir / "result.json").write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")
    return result


def run_smoke_test(
    workspace: Path,
    channel_id: str | None = None,
    engine: str | None = None,
    run_fn=h.run,
) -> dict:
    """스모크 테스트 전체 흐름. `run_fn`을 주입할 수 있어 가짜로 단위 테스트한다.

    엔진 판정만 하고 실제 작업은 `_run_hyperframes_smoke_test`/`_run_remotion_smoke_test`에
    맡긴다. `engine`이 "both"인 채널에서 `--engine`을 주지 않으면 HyperFrames를 기본으로 쓴다.
    """
    workspace = Path(workspace)
    config = h.load_config(workspace)
    if config is None:
        return {"passed": False, "error": "harness.config.json이 없습니다. 먼저 인터뷰를 진행하세요."}

    resolved_engine = engine or config.get("modules", {}).get("render", {}).get("engine", "hyperframes")

    channel = _resolve_channel(config, channel_id)
    if channel is None:
        return {"passed": False, "error": "채널을 찾지 못했습니다. --channel로 채널 id를 지정하세요."}

    timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    run_dir = workspace / "도구" / "logs" / "smoke" / timestamp
    project_dir = run_dir / "project"
    log_path = run_dir / "render.log"
    run_dir.mkdir(parents=True, exist_ok=True)

    if resolved_engine == "remotion":
        return _run_remotion_smoke_test(workspace, channel, config, run_dir, project_dir, log_path, run_fn)

    return _run_hyperframes_smoke_test(workspace, channel, config, run_dir, project_dir, log_path, run_fn)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="video-harness-setup 스모크 테스트")
    parser.add_argument("workspace", type=Path, help="작업 공간 경로")
    parser.add_argument("--channel", dest="channel_id", help="채널 id")
    parser.add_argument("--engine", choices=["hyperframes", "remotion"], help="렌더 엔진 (기본은 config 값)")
    args = parser.parse_args(argv)

    result = run_smoke_test(args.workspace, channel_id=args.channel_id, engine=args.engine)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result.get("passed") else 1


if __name__ == "__main__":
    sys.exit(main())
