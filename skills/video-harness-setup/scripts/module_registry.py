"""모듈별 설치 계획: config → Step 목록. 부작용 없는 순수 함수.

표준 라이브러리만 사용한다 (global-constraints.md).
"""

from __future__ import annotations

from pathlib import Path
from typing import Callable

import harness_lib as h
import preflight as pf

# install_module.py가 특정 단계의 실행 결과를 config에 반영할 때 제목으로 찾는 상수.
# (Step의 공개 키는 그대로 두고, 제목으로만 연결한다.)
HYPERFRAMES_BROWSER_PATH_TITLE = "HyperFrames 브라우저 경로 확인"
VOICE_MODEL_DOWNLOAD_TITLE = "Qwen3-TTS 모델 다운로드"
HANDOFF_EDITOR_DETECT_TITLE = "편집기(CapCut/Premiere) 설치 감지"

DEFAULT_HYPERFRAMES_VERSION = "0.8.43"
VOICE_MODEL_ID = "mlx-community/Qwen3-TTS-12Hz-1.7B-Base-8bit"
VOICE_MODEL_REL_DIR = "도구/tts/models/Qwen3-TTS-12Hz-1.7B-Base-8bit"
# to_capcut.py의 JSON 후처리(fix_text_style_ranges, fix_text_refs)가 이 버전을 대상으로
# 작성되고 검증되었으므로 고정한다(리뷰 반영: 이전에는 버전 없이 pycapcut을 설치했다).
PYCAPCUT_VERSION = "0.0.3"


def step(
    title: str,
    cmd: list[str] | None = None,
    cwd: str | None = None,
    env: dict | None = None,
    manual: str | None = None,
    needs_network: bool = False,
    background: bool = False,
) -> dict:
    """모든 키를 갖춘 Step을 만든다."""
    return {
        "title": title,
        "cmd": cmd,
        "cwd": cwd,
        "env": dict(env) if env else {},
        "manual": manual,
        "needs_network": needs_network,
        "background": background,
    }


def _venv_python(venv: Path, platform: dict) -> Path:
    venv = Path(venv)
    if platform.get("os") == "windows":
        return venv / "Scripts" / "python.exe"
    return venv / "bin" / "python"


def venv_steps(venv: Path, packages: list[str], uv_available: bool, platform: dict) -> list[dict]:
    """가상환경 생성 + (있으면) 패키지 설치 Step들을 만든다."""
    venv = Path(venv)
    venv_python = _venv_python(venv, platform)
    steps: list[dict] = []

    if uv_available:
        steps.append(step(title=f"{venv} 가상환경 만들기 (uv)", cmd=["uv", "venv", "--python", "3.12", str(venv)]))
        if packages:
            steps.append(
                step(
                    title=f"{venv}에 패키지 설치",
                    cmd=["uv", "pip", "install", "--python", str(venv_python), *packages],
                    needs_network=True,
                )
            )
    else:
        steps.append(step(title=f"{venv} 가상환경 만들기", cmd=[h.python_cmd(), "-m", "venv", str(venv)]))
        if packages:
            steps.append(
                step(
                    title=f"{venv}에 패키지 설치",
                    cmd=[str(venv_python), "-m", "pip", "install", *packages],
                    needs_network=True,
                )
            )

    return steps


def _scripts_dir() -> Path:
    return Path(__file__).resolve().parent


def _platform_of(config: dict) -> dict:
    return config.get("platform") or h.platform_info()


def _plan_tools_venv(workspace: Path, config: dict, which_fn=h.which) -> list[dict]:
    platform = _platform_of(config)
    handoff_editor = config.get("modules", {}).get("handoff", {}).get("editor")
    packages = ["pyyaml"]
    if handoff_editor == "capcut":
        packages.append(f"pycapcut=={PYCAPCUT_VERSION}")
    uv_available = which_fn("uv") is not None
    return venv_steps(workspace / "도구" / ".venv", packages, uv_available, platform)


def _plan_hyperframes(workspace: Path, config: dict, which_fn=h.which) -> list[dict]:
    version = config.get("modules", {}).get("render", {}).get("hyperframes_version", DEFAULT_HYPERFRAMES_VERSION)
    pkg = f"hyperframes@{version}"
    return [
        step(title="HyperFrames 브라우저 준비", cmd=["npx", "--yes", pkg, "browser", "ensure"], needs_network=True),
        step(
            title=HYPERFRAMES_BROWSER_PATH_TITLE,
            cmd=["npx", "--yes", pkg, "browser", "path"],
        ),
        step(title="HyperFrames doctor", cmd=["npx", "--yes", pkg, "doctor", "--json"]),
        step(
            title="HyperFrames 스킬 설치 안내",
            manual=f"HyperFrames 스킬 설치: `npx --yes {pkg} skills` (에이전트 스킬 폴더를 바꾸므로 확인 후 실행)",
        ),
    ]


def _plan_remotion(workspace: Path, config: dict, which_fn=h.which) -> list[dict]:
    steps: list[dict] = []
    for channel in config.get("channels", []):
        base = workspace / channel["name"] / "03_편집프로젝트/_채널공용/회차템플릿-remotion"
        steps.append(
            step(
                title=f"{channel['name']} Remotion 템플릿 npm install",
                cmd=["npm", "install", "--no-audit", "--no-fund"],
                cwd=str(base),
                needs_network=True,
            )
        )
    steps.append(step(title="Remotion 스킬 설치 안내", manual="Remotion 스킬 설치: `npx skills add remotion-dev/skills`"))
    return steps


def _plan_voice_local_mlx(workspace: Path, config: dict, which_fn=h.which) -> list[dict]:
    platform = _platform_of(config)
    uv_available = which_fn("uv") is not None
    venv = workspace / "도구" / "tts" / ".venv"
    steps = venv_steps(venv, ["mlx-audio==0.5.3", "numpy"], uv_available, platform)

    model_path = config.get("modules", {}).get("voice", {}).get("model_path")
    if not model_path:
        venv_python = _venv_python(venv, platform)
        code = (
            "from huggingface_hub import snapshot_download; "
            f"snapshot_download('{VOICE_MODEL_ID}', local_dir='{VOICE_MODEL_REL_DIR}')"
        )
        steps.append(
            step(
                title=VOICE_MODEL_DOWNLOAD_TITLE,
                cmd=[str(venv_python), "-c", code],
                cwd=str(workspace),
                env={"HF_HUB_DISABLE_XET": "1"},
                needs_network=True,
                background=True,
            )
        )

    steps.append(
        step(
            title="참고 녹음 준비 안내",
            manual="참고 녹음 10~20초와 정확한 대본을 `도구/tts/녹음/`에 넣기 (녹음가이드.md)",
        )
    )
    return steps


def _plan_voice_cloud(workspace: Path, config: dict, which_fn=h.which) -> list[dict]:
    platform = _platform_of(config)
    uv_available = which_fn("uv") is not None
    steps = venv_steps(workspace / "도구" / "tts" / ".venv", [], uv_available, platform)
    steps.append(step(title="ElevenLabs 키 안내", manual="`.env`에 `ELEVENLABS_API_KEY`를 직접 채우기"))
    return steps


def _plan_voice_record(workspace: Path, config: dict, which_fn=h.which) -> list[dict]:
    return [
        step(
            title="녹음 안내",
            manual="녹음가이드.md를 읽고 원본 녹음을 `01_원본영상/<작업명>/`에 넣기",
        )
    ]


def _plan_transcribe(workspace: Path, config: dict, which_fn=h.which) -> list[dict]:
    platform = _platform_of(config)
    packages = ["mlx-whisper"] if platform.get("apple_silicon") else ["faster-whisper"]
    uv_available = which_fn("uv") is not None
    return venv_steps(workspace / "도구" / "transcribe" / ".venv", packages, uv_available, platform)


def _plan_stock(workspace: Path, config: dict, which_fn=h.which) -> list[dict]:
    return [step(title="Pexels 키 안내", manual="`.env`에 `PEXELS_API_KEY`(선택). 없으면 Wikimedia만 검색")]


def _plan_higgsfield(workspace: Path, config: dict, which_fn=h.which) -> list[dict]:
    platform = _platform_of(config)
    auth = config.get("modules", {}).get("higgsfield", {}).get("auth")
    steps: list[dict] = []

    if auth == "account":
        steps.append(step(title="Higgsfield 스킬 설치 안내", manual="`npx skills add higgsfield-ai/skills`"))
        steps.append(step(title="Higgsfield CLI 설치 안내", manual="`npm install -g @higgsfield/cli`"))
        steps.append(step(title="Higgsfield 로그인 안내", manual="`higgsfield auth login`"))
    elif auth == "api-key":
        uv_available = which_fn("uv") is not None
        steps.extend(venv_steps(workspace / "도구" / ".venv", ["higgsfield-client"], uv_available, platform))
        steps.append(
            step(
                title="Higgsfield 키 안내",
                manual="`.env`에 `HF_KEY`를 `KEY_ID:KEY_SECRET` 형식으로 직접 채우기",
            )
        )
    else:
        steps.append(step(title="Higgsfield 인증 방식 선택 안내", manual="Higgsfield 인증 방식을 선택하세요 (account 또는 api-key)"))

    steps.append(
        step(
            title="Higgsfield 크레딧 안내",
            manual="Unlimited 구독 혜택은 CLI·MCP·API에 적용되지 않고 항상 크레딧이 차감됩니다",
        )
    )
    return steps


def _plan_watch(workspace: Path, config: dict, which_fn=h.which) -> list[dict]:
    platform = _platform_of(config)
    steps = [
        step(
            title="영상 저장 스킬 설치 안내",
            manual="`npx skills add bradautomates/claude-video -g` 후 첫 실행 때 `setup.py --json` 점검을 따른다",
        )
    ]
    if which_fn("yt-dlp") is None:
        steps.append(
            step(
                title="yt-dlp 설치 안내",
                manual=f"yt-dlp가 설치되어 있지 않습니다: {pf.install_hint('yt-dlp', platform)}",
            )
        )
    return steps


def _plan_fonts(workspace: Path, config: dict, which_fn=h.which) -> list[dict]:
    scripts_dir = _scripts_dir()
    return [
        step(
            title="Pretendard 폰트 설치",
            cmd=[h.python_cmd(), "install_module.py", "_fonts", str(workspace)],
            cwd=str(scripts_dir),
            needs_network=True,
        ),
        step(
            title="Paperlogy 설치 안내",
            manual="Paperlogy는 https://freesentation.blog/paperlogyfont 에서 받아 같은 폴더에 넣기",
        ),
    ]


def _handoff_editor_detect_step(workspace: Path) -> dict:
    """CapCut/Premiere 감지 Step. 두 handoff 모듈이 동일하게 쓴다.

    설치 여부는 실행(run) 시점에 preflight.py로 감지하기 전까지 알 수 없으므로,
    plan() 단계에서는 "설치 안내" manual을 조건부로 넣지 않는다 (감지 전에는 항상
    틀릴 수 있는 판단이 되기 때문). 설치 안내는 install_module.py의 post-step
    핸들러가 감지 결과를 보고 run() 결과의 manual 목록에 동적으로 추가한다.
    """
    scripts_dir = _scripts_dir()
    return step(
        title=HANDOFF_EDITOR_DETECT_TITLE,
        cmd=[h.python_cmd(), "preflight.py", str(workspace), "--json"],
        cwd=str(scripts_dir),
    )


def _plan_handoff_capcut(workspace: Path, config: dict, which_fn=h.which) -> list[dict]:
    return [_handoff_editor_detect_step(workspace)]


def _plan_handoff_premiere(workspace: Path, config: dict, which_fn=h.which) -> list[dict]:
    return [_handoff_editor_detect_step(workspace)]


MODULES: dict[str, Callable[..., list[dict]]] = {
    "tools-venv": _plan_tools_venv,
    "hyperframes": _plan_hyperframes,
    "remotion": _plan_remotion,
    "voice-local-mlx": _plan_voice_local_mlx,
    "voice-cloud": _plan_voice_cloud,
    "voice-record": _plan_voice_record,
    "transcribe": _plan_transcribe,
    "stock": _plan_stock,
    "higgsfield": _plan_higgsfield,
    "watch": _plan_watch,
    "fonts": _plan_fonts,
    "handoff-capcut": _plan_handoff_capcut,
    "handoff-premiere": _plan_handoff_premiere,
}

_MODULE_ORDER = [
    "tools-venv",
    "hyperframes",
    "remotion",
    "voice-local-mlx",
    "voice-cloud",
    "voice-record",
    "transcribe",
    "stock",
    "higgsfield",
    "watch",
    "handoff-capcut",
    "handoff-premiere",
    "fonts",
]


def plan(module: str, workspace: Path, config: dict, which_fn=h.which) -> list[dict]:
    """모듈 하나의 설치 계획을 만든다."""
    fn = MODULES.get(module)
    if fn is None:
        raise ValueError(f"알 수 없는 모듈: {module}")
    return fn(Path(workspace), config, which_fn=which_fn)


def modules_for(config: dict) -> list[str]:
    """config에서 설치할 모듈 순서. 항상 tools-venv가 맨 앞, fonts가 맨 뒤."""
    modules = config.get("modules", {})
    render_engine = modules.get("render", {}).get("engine")
    voice_mode = modules.get("voice", {}).get("mode")
    handoff_editor = modules.get("handoff", {}).get("editor")
    sources = modules.get("sources", [])
    watch = modules.get("reference", {}).get("watch")

    selected = {
        "tools-venv": True,
        "hyperframes": render_engine in ("hyperframes", "both"),
        "remotion": render_engine in ("remotion", "both"),
        "voice-local-mlx": voice_mode == "local-mlx",
        "voice-cloud": voice_mode == "cloud",
        "voice-record": voice_mode == "record",
        "transcribe": True,
        "stock": "stock" in sources,
        "higgsfield": "higgsfield" in sources,
        "watch": bool(watch),
        "handoff-capcut": handoff_editor == "capcut",
        "handoff-premiere": handoff_editor == "premiere",
        "fonts": True,
    }
    return [name for name in _MODULE_ORDER if selected.get(name)]
