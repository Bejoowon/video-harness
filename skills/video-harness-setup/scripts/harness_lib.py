"""공용 헬퍼: config 입출력, 플랫폼 감지, 명령 실행, 템플릿 치환.

표준 라이브러리만 사용한다 (global-constraints.md).
"""

from __future__ import annotations

import hashlib
import json
import os
import platform
import re
import shutil
import subprocess
from pathlib import Path

CONFIG_NAME = "harness.config.json"
CONFIG_VERSION = 1


def skill_root() -> Path:
    """scripts/ 의 부모 디렉터리 (skills/video-harness-setup)."""
    return Path(__file__).resolve().parent.parent


def scripts_dir() -> Path:
    return skill_root() / "scripts"


def script_fix(script: str, *args: str) -> str:
    """사용자가 그대로 복사해 실행할 수 있는 세팅 스크립트 명령 문자열을 만든다.

    스킬 설치 위치는 사람마다 다르므로 `skill_root()`가 `__file__`에서 푼 실제
    경로를 쓰고, 경로에 공백이 있을 수 있으니 큰따옴표로 감싼다. 인터프리터 이름도
    플랫폼을 따른다(Windows는 `python`).

    `args`는 이미 따옴표까지 붙여서 넘긴다 — 경로 인자는 `f'"{workspace}"'`처럼,
    값 인자(모듈 이름·채널 id)는 그대로.
    """
    return " ".join([python_cmd(), f'"{scripts_dir() / script}"', *args])


def load_config(workspace: Path) -> dict | None:
    """작업 공간에서 config를 읽는다. 없으면 None."""
    path = Path(workspace) / CONFIG_NAME
    if not path.exists():
        return None
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def save_config(workspace: Path, config: dict) -> Path:
    """config를 임시 파일에 쓰고 os.replace로 원자적으로 반영한다."""
    workspace = Path(workspace)
    workspace.mkdir(parents=True, exist_ok=True)
    path = workspace / CONFIG_NAME
    tmp_path = workspace / f".{CONFIG_NAME}.tmp"
    with tmp_path.open("w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=2)
    os.replace(tmp_path, path)
    return path


def save_validated(workspace: Path, config: dict) -> list[str]:
    """`validate_config`를 통과할 때만 저장한다. 오류 목록을 돌려주고, 비었으면 저장된 것이다.

    설정을 쓰는 곳은 전부 이 함수를 지나간다 — `validate_config`가 단일 관문이라는
    설계(design §7)를 코드 한 군데에서 지키기 위해서다. 검증에 걸리면 파일을
    건드리지 않는다.
    """
    errors = validate_config(config)
    if errors:
        return errors
    save_config(workspace, config)
    return []


def default_config() -> dict:
    return {
        "version": CONFIG_VERSION,
        "created": "",
        "platform": platform_info(),
        "agents": ["claude"],
        "workspace": {"name": "", "path": "."},
        "channels": [],
        "modules": {
            "render": {"engine": "hyperframes", "hyperframes_version": "0.8.43"},
            "handoff": {"editor": "none"},
            "voice": {"mode": "record"},
            "transcribe": {"engine": "auto", "model": "large-v3-turbo"},
            "sources": ["own-footage"],
            "higgsfield": {"auth": "none"},
            "reference": {"watch": False},
        },
        "rules": {"versioning": "vN-then-final", "sample_seconds": 12},
        "paths": {},
        "status": {"installed": [], "failed": [], "smoke_test": "not-run", "handoff_verified_by_user": False},
    }


def validate_config(config: dict) -> list[str]:
    """config를 검증하고 오류 메시지 목록을 돌려준다. 빈 목록이면 통과."""
    errors: list[str] = []

    render_engines = {"hyperframes", "remotion", "both"}
    editors = {"none", "capcut", "premiere"}
    voice_modes = {"local-mlx", "cloud", "record"}
    transcribe_engines = {"auto", "mlx-whisper", "faster-whisper"}
    valid_sources = {"own-footage", "stock", "higgsfield"}
    higgsfield_auths = {"none", "account", "api-key"}
    valid_agents = {"claude", "codex"}
    versioning_values = {"vN-then-final", "keep-all"}
    formats = {"9:16", "16:9"}
    kinds = {"narration-shorts", "footage-shorts", "longform-vlog"}
    style_starts = {"reference", "preset", "manual", "later"}
    consistency_levels = {"fixed", "variation", "decide-later"}

    modules = config.get("modules", {})

    render_engine = modules.get("render", {}).get("engine")
    if render_engine not in render_engines:
        errors.append(f"modules.render.engine: 알 수 없는 값 '{render_engine}' (허용: {sorted(render_engines)})")

    handoff_editor = modules.get("handoff", {}).get("editor")
    if handoff_editor not in editors:
        errors.append(f"modules.handoff.editor: 알 수 없는 값 '{handoff_editor}' (허용: {sorted(editors)})")

    voice_mode = modules.get("voice", {}).get("mode")
    if voice_mode not in voice_modes:
        errors.append(f"modules.voice.mode: 알 수 없는 값 '{voice_mode}' (허용: {sorted(voice_modes)})")

    transcribe_engine = modules.get("transcribe", {}).get("engine")
    if transcribe_engine not in transcribe_engines:
        errors.append(f"modules.transcribe.engine: 알 수 없는 값 '{transcribe_engine}' (허용: {sorted(transcribe_engines)})")

    sources = modules.get("sources", [])
    for source in sources:
        if source not in valid_sources:
            errors.append(f"modules.sources: 알 수 없는 값 '{source}' (허용: {sorted(valid_sources)})")

    higgsfield_auth = modules.get("higgsfield", {}).get("auth")
    if higgsfield_auth not in higgsfield_auths:
        errors.append(f"modules.higgsfield.auth: 알 수 없는 값 '{higgsfield_auth}' (허용: {sorted(higgsfield_auths)})")

    agents = config.get("agents", [])
    for agent in agents:
        if agent not in valid_agents:
            errors.append(f"agents: 알 수 없는 값 '{agent}' (허용: {sorted(valid_agents)})")

    rules = config.get("rules", {})
    versioning = rules.get("versioning")
    if versioning not in versioning_values:
        errors.append(f"rules.versioning: 알 수 없는 값 '{versioning}' (허용: {sorted(versioning_values)})")

    # 문자열 "12"가 들어오면 AGENTS.md에 `"12"초`로 조용히 렌더된다. 숫자만 받는다.
    # `bool`은 파이썬에서 `int`의 하위 타입이라 따로 빼지 않으면 `True초`가 렌더된다
    # (handoff_common.validate_cutlist가 fps에 쓰는 것과 같은 제외다).
    sample_seconds = rules.get("sample_seconds")
    if "sample_seconds" in rules and (not isinstance(sample_seconds, int) or isinstance(sample_seconds, bool)):
        errors.append("rules.sample_seconds: 정수가 아닙니다")

    apple_silicon = config.get("platform", {}).get("apple_silicon")
    if voice_mode == "local-mlx" and not apple_silicon:
        errors.append("modules.voice.mode: 'local-mlx'는 Apple Silicon에서만 사용할 수 있습니다")

    for channel in config.get("channels", []):
        required = ("id", "name", "format", "kind", "target_seconds", "language")
        for key in required:
            if key not in channel:
                errors.append(f"channels[{channel.get('id', '?')}].{key}: 필수 항목이 없습니다")
        if "format" in channel and channel["format"] not in formats:
            errors.append(f"channels[{channel.get('id', '?')}].format: 알 수 없는 값 '{channel['format']}' (허용: {sorted(formats)})")
        if "kind" in channel and channel["kind"] not in kinds:
            errors.append(f"channels[{channel.get('id', '?')}].kind: 알 수 없는 값 '{channel['kind']}' (허용: {sorted(kinds)})")
        if "target_seconds" in channel and not isinstance(channel["target_seconds"], int):
            errors.append(f"channels[{channel.get('id', '?')}].target_seconds: 정수가 아닙니다")
        # style_start(3-1 스타일 시작점)·consistency(3-2 일관성 수준)는 둘 다 선택 항목이다.
        if "style_start" in channel and channel["style_start"] not in style_starts:
            errors.append(
                f"channels[{channel.get('id', '?')}].style_start: 알 수 없는 값 "
                f"'{channel['style_start']}' (허용: {sorted(style_starts)})"
            )
        if "consistency" in channel and channel["consistency"] not in consistency_levels:
            errors.append(
                f"channels[{channel.get('id', '?')}].consistency: 알 수 없는 값 "
                f"'{channel['consistency']}' (허용: {sorted(consistency_levels)})"
            )

    return errors


def platform_info() -> dict:
    system = platform.system().lower()
    if system.startswith("darwin"):
        os_name = "darwin"
    elif system.startswith("windows"):
        os_name = "windows"
    else:
        os_name = "linux"
    machine = platform.machine()
    apple_silicon = os_name == "darwin" and machine == "arm64"
    return {"os": os_name, "arch": machine, "apple_silicon": apple_silicon}


def which(name: str) -> str | None:
    return shutil.which(name)


def node_cmd(name: str) -> str:
    """`npx`·`npm`처럼 Node가 깔아 주는 명령을 실행 가능한 형태로 돌려준다.

    `run()`은 `shell=False`로 `subprocess.run`을 부르고, Windows의 `CreateProcess`는
    `PATHEXT`를 보지 않고 `.exe`만 붙여 본다. 그래서 Node가 Windows에 설치하는
    `npx.cmd`/`npm.cmd`는 bare `"npx"`로는 실행되지 않는다(`FileNotFoundError` → 127).
    `shutil.which`는 `PATHEXT`를 보므로 미리 풀어서 넘긴다. 못 찾으면 이름 그대로
    돌려주어, 실패 메시지가 지금과 같게 남는다.
    """
    return which(name) or name


def run(
    cmd: list[str],
    cwd: Path | None = None,
    env: dict | None = None,
    log: Path | None = None,
    timeout: int | None = None,
) -> tuple[int, str]:
    """명령을 실행하고 (returncode, 합쳐진 stdout+stderr)을 돌려준다.

    비정상 종료 코드에서 예외를 던지지 않는다. FileNotFoundError는 127,
    타임아웃은 124로 변환한다.

    작업 공간의 `도구/` 아래 파이썬 스크립트(`check_style.py`가 `build_tokens`를
    불러오는 것처럼 서로를 import하는 것들)를 이 함수로 실행하면 평소라면
    `__pycache__`가 남는다. 파이썬이 아닌 명령에는 영향이 없으므로 항상
    `PYTHONDONTWRITEBYTECODE=1`을 넣어 이 흔적을 막는다.
    """
    run_env = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}
    if env is not None:
        run_env = {**run_env, **env}

    output = ""
    returncode: int
    try:
        result = subprocess.run(
            cmd,
            cwd=str(cwd) if cwd is not None else None,
            env=run_env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=timeout,
            encoding="utf-8",
            errors="replace",
        )
        returncode = result.returncode
        output = result.stdout or ""
    except FileNotFoundError as error:
        returncode = 127
        output = str(error)
    except subprocess.TimeoutExpired as error:
        returncode = 124
        partial = error.output or ""
        if isinstance(partial, bytes):
            partial = partial.decode("utf-8", errors="replace")
        output = partial

    if log is not None:
        log = Path(log)
        log.parent.mkdir(parents=True, exist_ok=True)
        with log.open("a", encoding="utf-8") as f:
            f.write(output)
            if not output.endswith("\n"):
                f.write("\n")

    return returncode, output


def render_template(text: str, values: dict) -> str:
    """{{키}} 를 values로 치환한다. 없는 키는 KeyError."""

    def replace(match: re.Match) -> str:
        key = match.group(1)
        if key not in values:
            raise KeyError(key)
        return str(values[key])

    return re.sub(r"\{\{(.+?)\}\}", replace, text)


def slugify_channel(name: str) -> str:
    """영문·숫자만 남겨 슬러그를 만든다. 결과가 비면 channel-<8자리 해시>."""
    lowered = name.lower()
    slug = re.sub(r"[^a-z0-9]+", "-", lowered).strip("-")
    if not slug:
        digest = hashlib.sha256(name.encode("utf-8")).hexdigest()[:8]
        return f"channel-{digest}"
    return slug


def python_cmd() -> str:
    return "python" if platform.system().lower().startswith("windows") else "python3"
