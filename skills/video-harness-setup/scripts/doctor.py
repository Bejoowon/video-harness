#!/usr/bin/env python3
"""건강 검진: 도구·config·모듈 설치 흔적·.env 키·채널 스타일 명세·스모크 테스트 상태를
다시 점검해 한국어 표 또는 JSON으로 보여준다.

표준 라이브러리만 사용한다 (global-constraints.md). frame.md의 status는 PyYAML 없이
정규식으로만 읽는다.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import harness_lib as h
import module_registry as m
import preflight as pf

# 이 하네스에서 검증된 CapCut 버전. Task 11에서 실제 값을 채운다.
VERIFIED_CAPCUT: str | None = None

_STATUS_RE = re.compile(r"^status:\s*(\S+)", re.MULTILINE)

_STATE_LABELS = {"ok": "정상", "warn": "주의", "fail": "문제"}


def _item(item: str, state: str, detail: str = "", fix: str | None = None) -> dict:
    return {"item": item, "state": state, "detail": detail, "fix": fix}


def check_env_keys(env_path: Path, needed: list[str]) -> dict[str, bool]:
    """`.env`에서 각 키가 채워져 있는지만 확인한다. 값 자체는 돌려주지 않는다.

    `.env`가 없으면 모든 키가 False다. 주석(`#`)과 빈 줄은 무시한다.
    """
    env_path = Path(env_path)
    present: dict[str, str] = {}
    if env_path.exists():
        for raw_line in env_path.read_text(encoding="utf-8").splitlines():
            line = raw_line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, _, value = line.partition("=")
            present[key.strip()] = value.strip()
    return {key: bool(present.get(key)) for key in needed}


def needed_keys(config: dict) -> list[str]:
    """config에서 실제로 필요한 `.env` 키 목록. `PEXELS_API_KEY`는 선택이라 포함하지 않는다."""
    keys: list[str] = []
    modules = config.get("modules", {})
    if modules.get("voice", {}).get("mode") == "cloud":
        keys.append("ELEVENLABS_API_KEY")
    if modules.get("higgsfield", {}).get("auth") == "api-key":
        keys.append("HF_KEY")
    return keys


# 조치 문장은 사용자가 그대로 복사해 실행한다. 만드는 일은 `harness_lib.script_fix`가
# 하나로 맡는다(smoke_test.py의 오류 문장도 같은 함수를 쓴다).
def _install_fix(workspace: Path, module: str) -> str:
    return h.script_fix("install_module.py", "run", f'"{workspace}"', module)


def _scaffold_fix(workspace: Path) -> str:
    return h.script_fix("scaffold.py", f'"{workspace}"')


_SCAFFOLD_FIX_DETAIL = "scaffold.py를 다시 실행하면 없는 도구만 복사합니다(있는 파일은 덮지 않습니다)."


def _tool_items(config: dict, report: dict) -> list[dict]:
    """필수 도구 점검 항목. report에 항목이 없고 missing_required에도 없으면 건너뛴다."""
    items: list[dict] = []
    platform = config.get("platform") or h.platform_info()
    tools = report.get("tools", {}) or {}
    missing = set(report.get("missing_required", []) or [])
    hints = report.get("hints", {}) or {}

    for tool in pf.REQUIRED:
        entry = tools.get(tool)
        if entry is None and tool not in missing:
            continue
        if tool in missing:
            fix = hints.get(tool) or pf.install_hint(tool, platform)
            detail = (entry or {}).get("note") or "설치되지 않았거나 버전 조건을 만족하지 않습니다"
            items.append(_item(tool, "fail", detail, fix))
        else:
            detail = (entry or {}).get("version") or ""
            items.append(_item(tool, "ok", detail))
    return items


def _config_item(config: dict) -> dict:
    errors = h.validate_config(config)
    if errors:
        return _item("설정 파일", "fail", "; ".join(errors), "harness.config.json 값을 오류 내용에 맞게 수정하세요")
    return _item("설정 파일", "ok")


def _module_trace(module: str, workspace: Path, config: dict) -> tuple[str, bool] | None:
    """`install_module.py run`으로 실제로 만들어지는 모듈별 설치 흔적을 확인한다.

    `도구/stock/search.py`, `도구/export/` 같은 흔적은 install_module.py가 아니라
    scaffold.py의 copy_tools가 config를 보고 복사하므로 `_scaffold_trace_items`에서
    따로 확인한다 (리뷰 반영: install_module 실행으로는 만들어지지 않는 흔적에 그
    명령을 fix로 안내하면 사용자가 같은 문제를 다시 보게 된다).

    안내만 있고 디스크에 남는 흔적이 없는 모듈(voice-record, remotion, higgsfield,
    watch)은 판단할 근거가 없으므로 None을 돌려주어 항목을 만들지 않는다.
    """
    if module == "tools-venv":
        return "도구/.venv", (workspace / "도구" / ".venv").exists()
    if module == "hyperframes":
        return "도구/chrome-path.txt", (workspace / "도구" / "chrome-path.txt").exists()
    if module == "voice-cloud":
        return "도구/tts/.venv", (workspace / "도구" / "tts" / ".venv").exists()
    if module == "voice-local-mlx":
        venv_ok = (workspace / "도구" / "tts" / ".venv").exists()
        model_path = config.get("modules", {}).get("voice", {}).get("model_path")
        model_dir = Path(model_path) if model_path else workspace / m.VOICE_MODEL_REL_DIR
        return "도구/tts/.venv", venv_ok and model_dir.exists()
    if module == "transcribe":
        return "도구/transcribe/.venv", (workspace / "도구" / "transcribe" / ".venv").exists()
    if module == "fonts":
        path = workspace / "스타일_라이브러리" / "01_폰트" / "Pretendard-Bold.otf"
        return "스타일_라이브러리/01_폰트/Pretendard-Bold.otf", path.exists()
    return None


def _module_trace_items(workspace: Path, config: dict) -> list[dict]:
    items: list[dict] = []
    for module in m.modules_for(config):
        trace = _module_trace(module, workspace, config)
        if trace is None:
            continue
        label, ok = trace
        if ok:
            items.append(_item(label, "ok"))
        else:
            detail = f"{module} 설치 흔적이 없습니다"
            items.append(_item(label, "fail", detail, _install_fix(workspace, module)))
    return items


def _scaffold_trace_item(workspace: Path, label: str, path: Path) -> dict:
    if path.exists():
        return _item(label, "ok")
    return _item(label, "fail", _SCAFFOLD_FIX_DETAIL, _scaffold_fix(workspace))


def _scaffold_trace_items(workspace: Path, config: dict) -> list[dict]:
    """`scaffold.py`의 `copy_tools`가 config를 보고 `도구/`에 복사하는 흔적들을 확인한다.

    조건은 `scaffold.copy_tools`의 로직을 그대로 따른다: `style`·`script`와
    `transcribe/transcribe.py`는 모듈 선택과 무관하게 항상 복사되고, 나머지는 각
    config 값이 선택됐을 때만 복사된다.
    """
    items: list[dict] = []
    modules = config.get("modules", {})
    engine = modules.get("render", {}).get("engine")
    voice_mode = modules.get("voice", {}).get("mode")
    sources = modules.get("sources", [])
    handoff_editor = modules.get("handoff", {}).get("editor")

    items.append(
        _scaffold_trace_item(workspace, "도구/style/check_style.py", workspace / "도구" / "style" / "check_style.py")
    )
    items.append(
        _scaffold_trace_item(
            workspace, "도구/script/check_rhythm.py", workspace / "도구" / "script" / "check_rhythm.py"
        )
    )
    items.append(
        _scaffold_trace_item(
            workspace, "도구/transcribe/transcribe.py", workspace / "도구" / "transcribe" / "transcribe.py"
        )
    )

    if "stock" in sources:
        items.append(
            _scaffold_trace_item(workspace, "도구/stock/search.py", workspace / "도구" / "stock" / "search.py")
        )

    if handoff_editor != "none":
        items.append(_scaffold_trace_item(workspace, "도구/export/", workspace / "도구" / "export"))

    if engine in ("hyperframes", "both"):
        items.append(
            _scaffold_trace_item(workspace, "도구/chrome-noaudio.py", workspace / "도구" / "chrome-noaudio.py")
        )

    if voice_mode == "local-mlx":
        label = "도구/tts/generate_local_mlx.py"
        ok = (workspace / "도구" / "tts" / "generate_local_mlx.py").exists() and (
            workspace / "도구" / "tts" / "postprocess.py"
        ).exists()
        items.append(_item(label, "ok") if ok else _item(label, "fail", _SCAFFOLD_FIX_DETAIL, _scaffold_fix(workspace)))
    elif voice_mode == "cloud":
        label = "도구/tts/generate_cloud.py"
        ok = (workspace / "도구" / "tts" / "generate_cloud.py").exists() and (
            workspace / "도구" / "tts" / "postprocess.py"
        ).exists()
        items.append(_item(label, "ok") if ok else _item(label, "fail", _SCAFFOLD_FIX_DETAIL, _scaffold_fix(workspace)))

    return items


def _handoff_detection_item(workspace: Path, config: dict) -> dict | None:
    """편집기 감지 결과가 config에 기록됐는지 확인한다.

    `도구/export/` 흔적(스캐폴드 복사)과는 별개다. install_module.py의 handoff-capcut/
    handoff-premiere 단계가 실행되면 preflight로 capcut/premiere를 동시에 감지해
    `config["modules"]["handoff"]["capcut"]`/`["premiere"]`에 기록한다
    (install_module.py의 `_handle_handoff_editor_detect` 참고). 그 기록이 아직 없으면
    handoff 설치 단계를 한 번도 실행하지 않았다는 뜻이므로 warn으로 안내한다.
    """
    handoff_editor = config.get("modules", {}).get("handoff", {}).get("editor")
    if handoff_editor not in ("capcut", "premiere"):
        return None

    detected = config.get("modules", {}).get("handoff", {}).get(handoff_editor)
    label = f"handoff.{handoff_editor} 감지"
    if detected is not None:
        return _item(label, "ok")
    module = f"handoff-{handoff_editor}"
    return _item(label, "warn", "편집기 감지를 아직 실행하지 않았습니다", _install_fix(workspace, module))


def _env_items(workspace: Path, config: dict) -> list[dict]:
    needed = needed_keys(config)
    if not needed:
        return []
    present = check_env_keys(workspace / ".env", needed)
    items: list[dict] = []
    for key in needed:
        if present.get(key):
            items.append(_item(key, "ok"))
        else:
            items.append(_item(key, "warn", "값이 비어 있거나 없습니다", f".env에 {key} 값을 직접 채우세요"))
    return items


def _workflow_item(workspace: Path, index: int, name: str) -> dict:
    """출발점(workflow)이 비어 있는 채널을 `주의`로 알린다.

    출발점이 없으면 `채널기준.md`의 "작업 순서"가 공통 순서로 남는다. 세팅을 막을
    일은 아니므로 `fail`이 아니라 `warn`이다. 조치 문장은 목록 번호(0부터)를 그대로
    짚어 복사해 실행할 수 있게 한다.
    """
    fix = h.script_fix("config_tool.py", "set", f'"{workspace}"', f"channels.{index}.workflow", "footage-first")
    # 조치 명령은 그대로 실행되도록 값 하나(footage-first)를 넣어 두었다. 고르지 않은 값이
    # 들어가지 않게, 맞는 값으로 바꿔 실행하라고 함께 알린다.
    detail = (
        "출발점이 정해지지 않았습니다 — 조치 명령 끝의 footage-first를 "
        "footage-first(찍은 영상 먼저) · script-first(대본 먼저) · per-episode(회차마다 정함) 중 맞는 값으로 바꿔 실행하세요"
    )
    return _item(f"{name} 출발점", "warn", detail, fix)


def _direction_item(name: str) -> dict:
    """방향(시청자·범위)이 하나도 기록되지 않은 채널을 `주의`로 알린다.

    방향은 사용자만 답할 수 있다. 그래서 조치가 복사해 실행할 명령이 아니라 "다시
    물어보라"는 안내다 — 값이 미리 박힌 명령을 주면 에이전트가 그것을 그대로 실행해
    사용자 대신 방향을 정해 버린다(이번 인터뷰 개편이 막으려는 바로 그 일이다).
    """
    detail = "채널 방향이 기록되지 않았습니다 — 시청자와 다루는 범위가 둘 다 비어 있습니다"
    fix = '재실행 메뉴의 "채널 방향 다시 잡기"로 방향 질문(1부)을 사용자에게 다시 하세요'
    return _item(f"{name} 방향", "warn", detail, fix)


def _channel_items(workspace: Path, config: dict) -> list[dict]:
    items: list[dict] = []
    for index, channel in enumerate(config.get("channels", [])):
        name = channel.get("name", "")
        if not channel.get("workflow"):
            items.append(_workflow_item(workspace, index, name))
        if not channel.get("audience") and not channel.get("scope"):
            items.append(_direction_item(name))
        label = f"{name} frame.md"
        frame_path = workspace / name / "03_편집프로젝트" / "_채널공용" / "frame.md"

        if not frame_path.exists():
            ref = channel.get("id") or name
            fix = h.script_fix("scaffold.py", f'"{workspace}"', "--channel", ref)
            items.append(_item(label, "fail", "frame.md가 없습니다", fix))
            continue

        text = frame_path.read_text(encoding="utf-8")
        match = _STATUS_RE.search(text)
        status = match.group(1) if match else None

        if status == "approved":
            items.append(_item(label, "ok"))
        elif status == "draft":
            items.append(_item(label, "warn", "초안(draft)"))
        else:
            items.append(_item(label, "warn", f"status 값을 확인할 수 없습니다: {status}"))
    return items


def _capcut_item(config: dict, report: dict) -> dict | None:
    if config.get("modules", {}).get("handoff", {}).get("editor") != "capcut":
        return None

    if VERIFIED_CAPCUT is None:
        return _item("CapCut 버전", "warn", "이 하네스에서 검증된 CapCut 버전이 아직 없습니다")

    detected = (report.get("editors", {}).get("capcut", {}) or {}).get("version")
    if detected != VERIFIED_CAPCUT:
        detail = f"감지된 버전 '{detected}'이 검증된 버전 '{VERIFIED_CAPCUT}'과 다릅니다"
        return _item("CapCut 버전", "warn", detail)
    return _item("CapCut 버전", "ok", detected or "")


def _failed_install_items(workspace: Path, config: dict) -> list[dict]:
    items: list[dict] = []
    for entry in config.get("status", {}).get("failed", []):
        module = entry.get("module", "?")
        step = entry.get("step") or "-"
        log = entry.get("log") or "-"
        items.append(_item(f"{module} 설치", "fail", f"{step} ({log})", _install_fix(workspace, module)))
    return items


def _smoke_item(workspace: Path, config: dict) -> dict:
    status = config.get("status", {}).get("smoke_test", "not-run")
    fix = h.script_fix("smoke_test.py", f'"{workspace}"')
    if status == "passed":
        return _item("스모크 테스트", "ok")
    if status == "failed":
        return _item("스모크 테스트", "fail", "마지막 스모크 테스트가 실패했습니다", fix)
    return _item("스모크 테스트", "warn", "스모크 테스트를 아직 실행하지 않았습니다", fix)


def diagnose(workspace: Path, config: dict, preflight_report: dict) -> list[dict]:
    """모든 점검 항목을 모은다. `{"item", "state": "ok|warn|fail", "detail", "fix"}` 목록."""
    workspace = Path(workspace)
    items: list[dict] = []
    items.extend(_tool_items(config, preflight_report))
    items.append(_config_item(config))
    items.extend(_module_trace_items(workspace, config))
    items.extend(_scaffold_trace_items(workspace, config))

    handoff_item = _handoff_detection_item(workspace, config)
    if handoff_item is not None:
        items.append(handoff_item)

    items.extend(_env_items(workspace, config))
    items.extend(_channel_items(workspace, config))

    capcut_item = _capcut_item(config, preflight_report)
    if capcut_item is not None:
        items.append(capcut_item)

    items.extend(_failed_install_items(workspace, config))
    items.append(_smoke_item(workspace, config))
    return items


def _print_human(items: list[dict]) -> None:
    label_width = max((len(it["item"]) for it in items), default=0)
    for it in items:
        state_label = _STATE_LABELS.get(it["state"], it["state"])
        detail = f"  {it['detail']}" if it.get("detail") else ""
        print(f"[{state_label}] {it['item']:<{label_width}}{detail}")

    fixes = [it for it in items if it["state"] != "ok" and it.get("fix")]
    if fixes:
        print()
        print("조치:")
        for it in fixes:
            print(f"  {it['item']}: {it['fix']}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="video-harness-setup 상태 점검")
    parser.add_argument("workspace", type=Path, help="작업 공간 경로")
    parser.add_argument("--json", action="store_true", help="JSON으로 출력")
    args = parser.parse_args(argv)

    workspace = args.workspace
    config = h.load_config(workspace)
    if config is None:
        error = "harness.config.json이 없습니다. 먼저 인터뷰를 진행하세요."
        if args.json:
            print(json.dumps({"error": error}, ensure_ascii=False), file=sys.stderr)
        else:
            print(error, file=sys.stderr)
        return 1

    report = pf.build_report(workspace)
    items = diagnose(workspace, config, report)
    ok = not any(it["state"] == "fail" for it in items)

    if args.json:
        print(json.dumps({"ok": ok, "items": items}, ensure_ascii=False, indent=2))
    else:
        _print_human(items)
        print()
        print(f"전체 상태: {'정상' if ok else '문제 있음'}")

    return 0 if ok else 1


if __name__ == "__main__":
    sys.exit(main())
