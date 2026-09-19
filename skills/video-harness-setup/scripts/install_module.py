#!/usr/bin/env python3
"""모듈 설치 계획(plan)과 실행(run).

표준 라이브러리만 사용한다 (global-constraints.md).
"""

from __future__ import annotations

import argparse
import io
import json
import re
import shutil
import sys
import urllib.request
import zipfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import harness_lib as h
import module_registry as m

PRETENDARD_RELEASE_API = "https://api.github.com/repos/orioncactus/pretendard/releases/latest"
PRETENDARD_ZIP_NAME_RE = re.compile(r"^Pretendard-[0-9][0-9.]*\.zip$")
PRETENDARD_FONT_FILES = ("Pretendard-Bold.otf", "Pretendard-Medium.otf")


# Node가 깔아 주는 명령. 계획(plan)은 사람이 읽는 것이라 짧은 이름 그대로 두고,
# 실행 직전에만 `which`로 푼다 — Windows의 `npx.cmd`/`npm.cmd`는 bare argv[0]로는
# 실행되지 않는다(harness_lib.node_cmd 참고).
_NODE_COMMANDS = ("npx", "npm")


def _runnable(cmd: list[str]) -> list[str]:
    if cmd and cmd[0] in _NODE_COMMANDS:
        return [h.node_cmd(cmd[0]), *cmd[1:]]
    return cmd


def _pick_pretendard_asset(assets: list[dict]) -> dict | None:
    for asset in assets:
        if PRETENDARD_ZIP_NAME_RE.match(asset.get("name", "")):
            return asset
    return None


def download_pretendard(dest: Path, opener=urllib.request.urlopen) -> list[Path]:
    """Pretendard 최신 릴리스 zip에서 Bold/Medium otf만 dest에 푼다.

    이미 있는 파일은 덮어쓰지 않는다.
    """
    dest = Path(dest)
    dest.mkdir(parents=True, exist_ok=True)

    existing = {name: (dest / name) for name in PRETENDARD_FONT_FILES if (dest / name).exists()}
    if len(existing) == len(PRETENDARD_FONT_FILES):
        return list(existing.values())

    with opener(PRETENDARD_RELEASE_API) as resp:
        release = json.loads(resp.read().decode("utf-8"))

    asset = _pick_pretendard_asset(release.get("assets", []))
    if asset is None:
        raise RuntimeError("Pretendard 릴리스에서 zip 에셋을 찾을 수 없습니다")

    with opener(asset["browser_download_url"]) as resp:
        zip_bytes = resp.read()

    extracted: list[Path] = []
    with zipfile.ZipFile(io.BytesIO(zip_bytes)) as zf:
        for info in zf.infolist():
            name = Path(info.filename).name
            if name not in PRETENDARD_FONT_FILES:
                continue
            target = dest / name
            if not target.exists():
                with zf.open(info) as src, target.open("wb") as out:
                    shutil.copyfileobj(src, out)
            extracted.append(target)

    return extracted


def _handle_hyperframes_browser_path(workspace: Path, config: dict, output: str, module: str) -> list[str] | None:
    lines = [line.strip() for line in output.splitlines() if line.strip()]
    if not lines:
        return None
    chrome_path = lines[-1]
    tools_dir = workspace / "도구"
    tools_dir.mkdir(parents=True, exist_ok=True)
    (tools_dir / "chrome-path.txt").write_text(chrome_path + "\n", encoding="utf-8")
    config.setdefault("paths", {})["chrome"] = chrome_path
    return None


def _handle_voice_model_download(workspace: Path, config: dict, output: str, module: str) -> list[str] | None:
    model_dir = workspace / m.VOICE_MODEL_REL_DIR
    config.setdefault("modules", {}).setdefault("voice", {})["model_path"] = str(model_dir)
    return None


def _handle_handoff_editor_detect(workspace: Path, config: dict, output: str, module: str) -> list[str] | None:
    """CapCut/Premiere 감지 결과를 config에 기록하고, 지금 실행 중인 handoff 모듈의
    편집기가 설치돼 있지 않으면 안내 문구를 반환한다 (plan 시점이 아니라 방금 감지한
    결과로 판단하므로 정확하다).
    """
    try:
        report = json.loads(output)
    except (json.JSONDecodeError, ValueError):
        return None
    editors = report.get("editors", {})
    handoff = config.setdefault("modules", {}).setdefault("handoff", {})
    if "capcut" in editors:
        handoff["capcut"] = editors["capcut"]
    if "premiere" in editors:
        handoff["premiere"] = editors["premiere"]

    reminders: list[str] = []
    if module == "handoff-capcut" and not editors.get("capcut", {}).get("installed"):
        reminders.append("CapCut 데스크톱을 설치한 뒤 doctor를 다시 실행")
    if module == "handoff-premiere" and not editors.get("premiere", {}).get("installed"):
        reminders.append("Premiere Pro가 설치되어 있지 않습니다. 설치한 뒤 doctor를 다시 실행하세요.")
    return reminders


_POST_STEP_HANDLERS = {
    m.HYPERFRAMES_BROWSER_PATH_TITLE: _handle_hyperframes_browser_path,
    m.VOICE_MODEL_DOWNLOAD_TITLE: _handle_voice_model_download,
    m.HANDOFF_EDITOR_DETECT_TITLE: _handle_handoff_editor_detect,
}


def _load_and_validate_config(workspace: Path) -> tuple[dict | None, str | None]:
    """config를 읽고 검증한다. 문제가 있으면 (None, 한국어 오류 메시지)를 돌려준다."""
    config = h.load_config(workspace)
    if config is None:
        return None, "harness.config.json이 없습니다. 먼저 인터뷰를 진행하세요."
    errors = h.validate_config(config)
    if errors:
        return None, "harness.config.json이 올바르지 않습니다: " + "; ".join(errors)
    return config, None


def run_module(workspace: Path, module: str, run_fn=h.run) -> dict:
    """모듈을 계획대로 실행하고 config를 갱신한다."""
    workspace = Path(workspace)
    config, error = _load_and_validate_config(workspace)
    if error:
        return {"error": error}

    if module not in m.MODULES:
        return {"error": f"알 수 없는 모듈: {module}"}

    steps = m.plan(module, workspace, config)
    log_path = workspace / "도구" / "logs" / f"install-{module}.log"

    ran: list[str] = []
    manual: list[str] = []
    failed_step: str | None = None
    ok = True

    for st in steps:
        if st["cmd"] is None:
            if st["manual"]:
                manual.append(st["manual"])
            continue

        code, output = run_fn(_runnable(st["cmd"]), cwd=st["cwd"], env=st["env"] or None, log=log_path)
        if code != 0:
            ok = False
            failed_step = st["title"]
            break

        ran.append(st["title"])
        handler = _POST_STEP_HANDLERS.get(st["title"])
        if handler is not None:
            manual.extend(handler(workspace, config, output, module) or [])

    status = config.setdefault("status", {})
    kept_failures = [f for f in status.get("failed", []) if f.get("module") != module]
    if ok:
        installed = status.setdefault("installed", [])
        if module not in installed:
            installed.append(module)
        status["failed"] = kept_failures
    else:
        # 같은 모듈을 여러 번 재시도해도 마지막 실패 한 줄만 남긴다 — 아니면
        # doctor가 똑같은 `fail` 행을 재시도 횟수만큼 찍는다.
        status["failed"] = kept_failures + [{"module": module, "step": failed_step, "log": str(log_path)}]

    h.save_config(workspace, config)

    return {
        "module": module,
        "ok": ok,
        "ran": ran,
        "manual": manual,
        "failed_step": failed_step,
        "log": str(log_path),
    }


def _plan_result(workspace: Path, config: dict, module: str) -> dict:
    return {"module": module, "steps": m.plan(module, workspace, config)}


def cmd_plan(args: argparse.Namespace) -> int:
    workspace = args.workspace
    config, error = _load_and_validate_config(workspace)
    if error:
        print(json.dumps({"error": error}, ensure_ascii=False), file=sys.stderr)
        return 1

    if args.all and args.module:
        print(json.dumps({"error": "모듈과 --all을 동시에 줄 수 없습니다."}, ensure_ascii=False), file=sys.stderr)
        return 1

    if args.all:
        result = {"modules": [_plan_result(workspace, config, name) for name in m.modules_for(config)]}
    else:
        if not args.module:
            print(json.dumps({"error": "모듈 이름 또는 --all이 필요합니다."}, ensure_ascii=False), file=sys.stderr)
            return 1
        if args.module not in m.MODULES:
            print(json.dumps({"error": f"알 수 없는 모듈: {args.module}"}, ensure_ascii=False), file=sys.stderr)
            return 1
        result = _plan_result(workspace, config, args.module)

    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    result = run_module(args.workspace, args.module)
    if "error" in result:
        print(json.dumps(result, ensure_ascii=False), file=sys.stderr)
        return 1
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["ok"] else 1


def cmd_fonts(args: argparse.Namespace) -> int:
    workspace = Path(args.workspace)
    dest = workspace / "스타일_라이브러리" / "01_폰트"
    try:
        extracted = download_pretendard(dest)
    except Exception as error:
        print(json.dumps({"error": str(error)}, ensure_ascii=False), file=sys.stderr)
        return 1
    print(json.dumps({"extracted": [str(p) for p in extracted]}, ensure_ascii=False))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="video-harness-setup 모듈 설치 계획/실행")
    sub = parser.add_subparsers(dest="command", required=True)

    plan_parser = sub.add_parser("plan", help="설치 계획을 JSON으로 보여준다")
    plan_parser.add_argument("workspace", type=Path)
    plan_parser.add_argument("module", nargs="?", default=None)
    plan_parser.add_argument("--all", action="store_true")

    run_parser = sub.add_parser("run", help="모듈을 실제로 설치한다")
    run_parser.add_argument("workspace", type=Path)
    run_parser.add_argument("module")

    fonts_parser = sub.add_parser("_fonts", help=argparse.SUPPRESS)
    fonts_parser.add_argument("workspace", type=Path)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "plan":
        return cmd_plan(args)
    if args.command == "run":
        return cmd_run(args)
    if args.command == "_fonts":
        return cmd_fonts(args)

    parser.error("알 수 없는 명령입니다")
    return 2


if __name__ == "__main__":
    sys.exit(main())
