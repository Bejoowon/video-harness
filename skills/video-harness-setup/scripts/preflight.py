#!/usr/bin/env python3
"""환경 점검: 도구·편집기·오디오 장치·디스크 여유 공간을 점검하고 JSON으로 보고한다.

표준 라이브러리만 사용한다 (global-constraints.md).
"""

from __future__ import annotations

import argparse
import json
import re
import shutil
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
import harness_lib as h

REQUIRED = ["python", "ffmpeg", "ffprobe", "node", "npx", "git"]
OPTIONAL = ["uv", "yt-dlp", "brew", "winget", "aside"]

# 있는지만 보고 **실행하지 않는** 도구. `aside`는 사용자의 로그인된 브라우저를 움직이는
# CLI라, 버전을 물어보려고라도 점검이 실행해서는 안 된다. 선택 도구이므로 없어도
# `can_proceed`에는 영향이 없다(그 값은 REQUIRED만 본다).
PATH_ONLY = {"aside"}

# 편집기 탐지 경로 상수 (탐지 대상이므로 절대경로 금지 규칙의 예외, global-constraints.md).
# 모든 항목은 루트 + 상대 이름/글롭으로 구성한다. `detect_editors`는 이 표에서만 경로를
# 조립하며, 함수 본문에는 어떤 경로 리터럴도 두지 않는다.
# - apps_root: 사용자 영역 앱 설치 루트 (macOS는 Premiere/CapCut 공용, Windows는 `home` 기준
#   상대 경로로 `%LOCALAPPDATA%`에 해당하며 CapCut 전용)
# - system_apps_root: 시스템 영역 앱 설치 루트 (Windows Premiere 전용)
# - capcut_drafts: macOS는 `home` 기준, Windows는 `apps_root` 기준 상대 경로
EDITOR_PATHS = {
    "darwin": {
        "apps_root": "/Applications",
        "capcut_app": "CapCut.app",
        "premiere_app_glob": "Adobe Premiere Pro *",
        "capcut_drafts": "Movies/CapCut/User Data/Projects/com.lveditor.draft",
    },
    "windows": {
        "apps_root": "AppData/Local",
        "capcut_app": "CapCut",
        "system_apps_root": "C:/Program Files/Adobe",
        "premiere_app_glob": "Adobe Premiere Pro *",
        "capcut_drafts": "CapCut/User Data/Projects/com.lveditor.draft",
    },
}


def _extract_version(text: str) -> str | None:
    match = re.search(r"(\d+)\.(\d+)(?:\.(\d+))?", text or "")
    if not match:
        return None
    return match.group(0)


def check_tools(which_fn=h.which, run_fn=h.run) -> dict:
    """REQUIRED + OPTIONAL 도구를 점검한다."""
    tools: dict[str, dict] = {}

    py_version = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    py_ok = (sys.version_info.major, sys.version_info.minor) >= (3, 10)
    tools["python"] = {
        "found": True,
        "path": sys.executable,
        "version": py_version,
        "ok": py_ok,
        "note": "" if py_ok else "Python 3.10 이상이 필요합니다",
    }

    for tool in REQUIRED + OPTIONAL:
        if tool == "python":
            continue
        path = which_fn(tool)
        if path is None:
            tools[tool] = {
                "found": False,
                "path": None,
                "version": None,
                "ok": False,
                "note": "설치되지 않았습니다",
            }
            continue

        if tool in PATH_ONLY:
            tools[tool] = {
                "found": True,
                "path": path,
                "version": None,
                "ok": True,
                "note": "설치되어 있습니다 (버전을 확인하려고 실행하지는 않습니다)",
            }
            continue

        version_flag = "-version" if tool in ("ffmpeg", "ffprobe") else "--version"
        code, out = run_fn([path, version_flag])
        version = _extract_version(out) if code == 0 else None

        ok = code == 0
        note = ""
        if tool == "node":
            # 버전을 못 읽으면 `< 22` 관문이 통째로 건너뛰어져 ok가 참으로 남는다.
            # 확인하지 못한 것을 통과로 보고하지 않는다.
            if version is None:
                ok = False
                note = "Node.js 버전을 읽지 못했습니다 (22 이상이 필요합니다)"
            elif int(version.split(".")[0]) < 22:
                ok = False
                note = "Node.js 22 이상이 필요합니다"
        elif not ok:
            note = "버전 확인에 실패했습니다"

        tools[tool] = {
            "found": True,
            "path": path,
            "version": version,
            "ok": ok,
            "note": note,
        }

    return tools


def install_hint(tool: str, platform: dict) -> str:
    """도구별 설치 안내 명령을 플랫폼에 맞게 돌려준다."""
    os_name = platform.get("os")

    # ffprobe/npx/npm은 독립 패키지가 아니라 다른 도구에 딸려 온다.
    # 실제로 설치해야 할 상위 패키지의 안내로 매핑한다 (모든 플랫폼 공통).
    if tool == "ffprobe":
        tool = "ffmpeg"
    elif tool in ("npx", "npm"):
        tool = "node"

    if tool == "node":
        if os_name == "darwin":
            return "brew install node@22"
        if os_name == "windows":
            return "winget install OpenJS.NodeJS.LTS"
        return "https://nodejs.org 에서 Node.js 22 이상을 설치하세요"

    if tool == "uv":
        if os_name == "darwin":
            return "brew install uv"
        if os_name == "windows":
            return "winget install astral-sh.uv"
        return "curl -LsSf https://astral.sh/uv/install.sh | sh"

    if os_name == "darwin":
        return f"brew install {tool}"
    if os_name == "windows":
        winget_ids = {"ffmpeg": "Gyan.FFmpeg"}
        return f"winget install {winget_ids.get(tool, tool)}"
    return f"sudo apt install {tool}"


def _mac_app_version(app_path: Path, run_fn=h.run) -> str | None:
    plist_target = f"{app_path}/Contents/Info.plist"
    code, out = run_fn(["defaults", "read", plist_target, "CFBundleShortVersionString"])
    if code != 0:
        return None
    return out.strip() or None


def detect_editors(
    platform: dict,
    home: Path,
    apps_root: Path | None = None,
    system_apps_root: Path | None = None,
    run_fn=h.run,
) -> dict:
    """CapCut / Premiere Pro 설치 및 초안 폴더를 탐지한다.

    경로는 전부 `EDITOR_PATHS`에서만 조립한다 (경로 리터럴을 여기 두지 않는다).

    `apps_root`: 사용자 영역 앱 설치 루트를 덮어쓴다. 기본값은 `EDITOR_PATHS`의
    macOS `/Applications`, Windows `<home>/AppData/Local`. `system_apps_root`:
    Windows의 시스템 영역 Premiere 설치 루트를 덮어쓴다 (기본값 `C:/Program Files/Adobe`).
    macOS는 Premiere도 `apps_root`를 공유하므로 쓰이지 않는다.
    """
    home = Path(home)
    os_name = platform.get("os")
    paths = EDITOR_PATHS.get(os_name, {})
    capcut = {"installed": False, "version": None, "drafts_dir": None}
    premiere = {"installed": False, "version": None}

    if os_name == "darwin":
        resolved_apps_root = Path(apps_root) if apps_root is not None else Path(paths["apps_root"])

        capcut_app = resolved_apps_root / paths["capcut_app"]
        if capcut_app.exists():
            capcut["installed"] = True
            capcut["version"] = _mac_app_version(capcut_app, run_fn)

        premiere_matches = sorted(resolved_apps_root.glob(paths["premiere_app_glob"]))
        if premiere_matches:
            premiere["installed"] = True
            premiere["version"] = _mac_app_version(premiere_matches[-1], run_fn)

        drafts_dir = home / paths["capcut_drafts"]
        if drafts_dir.exists():
            capcut["drafts_dir"] = str(drafts_dir)

    elif os_name == "windows":
        resolved_apps_root = Path(apps_root) if apps_root is not None else home / paths["apps_root"]
        resolved_system_root = (
            Path(system_apps_root) if system_apps_root is not None else Path(paths["system_apps_root"])
        )

        capcut_dir = resolved_apps_root / paths["capcut_app"]
        if capcut_dir.exists():
            capcut["installed"] = True

        premiere_matches = sorted(resolved_system_root.glob(paths["premiere_app_glob"]))
        if premiere_matches:
            premiere["installed"] = True

        drafts_dir = resolved_apps_root / paths["capcut_drafts"]
        if drafts_dir.exists():
            capcut["drafts_dir"] = str(drafts_dir)

    return {"capcut": capcut, "premiere": premiere}


def audio_output_warning(platform: dict, run_fn=h.run) -> str | None:
    """macOS에서 기본 출력 장치가 마이크류이면 경고 문장을 돌려준다."""
    if platform.get("os") != "darwin":
        return None

    code, out = run_fn(["system_profiler", "SPAudioDataType"])
    if code != 0 or not out:
        return None

    blocks: list[list[str]] = []
    current: list[str] | None = None
    for raw_line in out.splitlines():
        line = raw_line.strip()
        if not line:
            continue
        if line.endswith(":"):
            current = [line[:-1]]
            blocks.append(current)
        elif current is not None:
            current.append(line)

    for block in blocks:
        name = block[0]
        body = "\n".join(block[1:])
        if "Default Output Device: Yes" in body:
            if "microphone" in name.lower() or "mic" in name.lower():
                return f"기본 출력 장치가 '{name}'입니다. 마이크가 스피커로 잡혀 있을 수 있으니 확인하세요."
            return None

    return None


def disk_free_gb(path: Path) -> float:
    path = Path(path)
    check_path = path if path.exists() else path.parent
    if not check_path.exists():
        check_path = Path(check_path.anchor or ".")
    usage = shutil.disk_usage(check_path)
    return round(usage.free / (1024 ** 3), 2)


def _looks_like_existing_workspace(workspace: Path) -> bool:
    if (workspace / "AGENTS.md").exists():
        return True
    if not workspace.exists():
        return False
    for child in workspace.iterdir():
        if child.is_dir() and (child / "01_원본영상").exists():
            return True
    return False


def build_report(workspace: Path) -> dict:
    workspace = Path(workspace)
    platform = h.platform_info()
    tools = check_tools()
    missing_required = [t for t in REQUIRED if not tools[t]["ok"]]
    hints = {t: install_hint(t, platform) for t in missing_required}
    editors = detect_editors(platform, Path.home())
    audio_warning = audio_output_warning(platform)
    disk_free = disk_free_gb(workspace if workspace.exists() else workspace.parent)
    existing_config = h.load_config(workspace) is not None
    looks_like_existing = not existing_config and _looks_like_existing_workspace(workspace)

    return {
        "platform": platform,
        "tools": tools,
        "missing_required": missing_required,
        "hints": hints,
        "editors": editors,
        "audio_warning": audio_warning,
        "disk_free_gb": disk_free,
        "existing_config": existing_config,
        "looks_like_existing_workspace": looks_like_existing,
        "can_proceed": not missing_required,
    }


def _print_human(report: dict) -> None:
    platform = report["platform"]
    print(f"플랫폼: {platform['os']} ({platform['arch']})")
    print()
    print("도구:")
    for tool, info in report["tools"].items():
        mark = "OK" if info["ok"] else "!!"
        version = info["version"] or "-"
        print(f"  [{mark}] {tool:<8} {version}")
        if not info["ok"] and tool in report["hints"]:
            print(f"        설치 안내: {report['hints'][tool]}")

    print()
    editors = report["editors"]
    capcut = editors["capcut"]
    premiere = editors["premiere"]
    print("편집기:")
    print(f"  CapCut: {'설치됨 ' + (capcut['version'] or '') if capcut['installed'] else '미설치'}")
    if capcut["drafts_dir"]:
        print(f"    초안 폴더: {capcut['drafts_dir']}")
    print(f"  Premiere Pro: {'설치됨 ' + (premiere['version'] or '') if premiere['installed'] else '미설치'}")

    if report["audio_warning"]:
        print()
        print(f"경고: {report['audio_warning']}")

    print()
    print(f"디스크 여유 공간: {report['disk_free_gb']} GB")

    if report["existing_config"]:
        print("기존 harness.config.json 발견됨")
    elif report["looks_like_existing_workspace"]:
        print("기존 작업 공간 구조가 감지되었습니다 (설정 파일 없음)")

    print()
    print(f"진행 가능: {'예' if report['can_proceed'] else '아니오'}")
    if not report["can_proceed"]:
        print(f"필수 도구 누락: {', '.join(report['missing_required'])}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="video-harness-setup 환경 점검")
    parser.add_argument("workspace", type=Path, help="작업 공간 경로")
    parser.add_argument("--json", action="store_true", help="JSON으로 출력")
    args = parser.parse_args(argv)

    report = build_report(args.workspace)

    if args.json:
        print(json.dumps(report, ensure_ascii=False, indent=2))
    else:
        _print_human(report)

    return 0


if __name__ == "__main__":
    sys.exit(main())
