# 영상 하네스 세팅 (video-harness-setup)

쇼츠·릴스·유튜브 영상을 자동화로 만들기 위한 작업 공간을 인터뷰로 처음 세팅하는 Claude Code / Codex 스킬 저장소다. 사용자가 고른 모듈만 설치하고(렌더 엔진, 편집기 넘기기, 목소리, 전사, 소재 수급), 채널 폴더와 채널별 스타일 명세(`frame.md`)를 만든 뒤, 10초 영상을 실제로 렌더해서 세팅이 정말로 도는지 증명한다. 영상을 처음 만들어 보는 사람도 쉬운 말로 한 번에 하나씩 물어보며 진행할 수 있게 만들어졌다.

## 저장소 구조

```
video-harness/
├── skills/video-harness-setup/   에이전트가 읽는 스킬 본체 (SKILL.md, scripts, references, assets)
├── install.sh                    한 줄 설치 (macOS · Linux)
├── install.ps1                   한 줄 설치 (Windows PowerShell)
├── tests/                        pytest 테스트
└── dist/                         패키징 결과물 (.skill 파일, git에 커밋하지 않음)
```

## 무엇을 설치하나

인터뷰에서 고른 답에 따라 아래 모듈만 골라서 설치한다. 고르지 않은 모듈은 아무것도 설치하지 않는다.

| 구분 | 선택지 | 비고 |
|---|---|---|
| 렌더 엔진 | HyperFrames(기본) / Remotion / 둘 다 | HyperFrames는 설치가 가볍다. Remotion은 React를 아는 사람에게 편하고 회사 규모에 따라 유료 라이선스가 필요할 수 있다 |
| 편집기 넘기기 | 안 씀 / CapCut / Premiere Pro | 자막(SRT)·컷 목록·가져오기 안내가 항상 함께 나온다 |
| 목소리 | 직접 녹음·원음(기본) / 클라우드 TTS(ElevenLabs) / 로컬 목소리 복제(Apple Silicon 전용) | 로컬 목소리 복제는 참고 녹음 하나로 그 목소리를 흉내 낸다 |
| 전사(말→자막) | mlx-whisper(Apple Silicon) / faster-whisper(그 외) | 기본 모델은 `large-v3-turbo` |
| 소재 수급 | 직접 촬영(기본) / 무료 스톡(Pexels·Wikimedia) / Higgsfield(AI 생성) | 복수 선택 가능 |
| 레퍼런스 분석 | 설치 / 안 함 | 닮고 싶은 영상을 채널 스타일에 반영할 때 쓴다 |

그 밖에 폰트(Pretendard 자동 설치, Paperlogy는 안내만)와 채널마다 하나씩 만들어지는 스타일 명세(`frame.md`)는 항상 함께 만들어진다.

## 요구 사항

- macOS, Windows, 또는 Linux
- Python 3.10 이상
- Node.js 22 이상 (npx 포함)
- ffmpeg / ffprobe
- git
- (선택) uv — 있으면 가상환경을 더 빠르게 만든다
- 로컬 목소리 복제를 쓰려면 Apple Silicon Mac이 필요하다

`preflight.py`가 이 도구들의 설치 여부를 점검하고, 없는 도구는 설치 명령만 보여 준다(자동으로 설치하지 않는다).

## 설치

### 한 줄 설치 (권장)

터미널에 아래 한 줄을 붙여 넣는다. 스킬 폴더 하나를 복사할 뿐, 다른 프로그램은 설치하지 않는다. Claude Code와 Codex 중 이 컴퓨터에 있는 쪽을 찾아서 넣고, 이미 설치돼 있으면 예전 것을 `skills-backup` 폴더로 옮긴 뒤 새로 넣는다(업데이트도 같은 명령이다).

macOS · Linux:

```bash
curl -fsSL https://raw.githubusercontent.com/Bejoowon/video-harness/main/install.sh | bash
```

Windows (PowerShell):

```powershell
irm https://raw.githubusercontent.com/Bejoowon/video-harness/main/install.ps1 | iex
```

설치 위치를 직접 고르려면:

| | macOS · Linux | Windows |
|---|---|---|
| Claude Code에만 | `… \| bash -s -- --claude` | 실행 전에 `$env:VIDEO_HARNESS_TARGET = "claude"` |
| Codex에만 | `… \| bash -s -- --codex` | `$env:VIDEO_HARNESS_TARGET = "codex"` |
| 둘 다 | `… \| bash -s -- --both` | `$env:VIDEO_HARNESS_TARGET = "both"` |

설치한 뒤에는 Claude Code나 Codex를 새로 열어야 스킬이 보인다.

> `install.ps1`은 아직 실제 Windows 기기에서 돌려 보지 못했다. 막히면 아래 "직접 복사"로 설치한다.

### 직접 복사

저장소를 받아서 `skills/video-harness-setup/` 폴더를 그대로 복사한다.

- Claude Code: `~/.claude/skills/video-harness-setup/`(개인용) 또는 프로젝트의 `.claude/skills/video-harness-setup/`(프로젝트용)
- Codex: `~/.codex/skills/video-harness-setup/`

### 배포용 패키지

파일 하나로 옮기고 싶으면 `dist/video-harness-setup.skill`(zip 형식)을 만들어 전달한다. 만드는 방법은 스킬 개발 도구를 참고한다: `package_skill.py skills/video-harness-setup dist`.

## 시작하는 법

Claude Code나 Codex에서 다음 문장을 그대로 말한다.

```
영상 하네스 세팅을 시작해줘
```

에이전트가 지금 폴더를 점검하고, 부족한 게 있으면 알려 주고, 없으면 바로 인터뷰를 시작한다.

## 다시 실행하면 무엇을 할 수 있나

이미 세팅된 작업 공간에서 같은 문장을 다시 말하면(또는 스킬을 다시 부르면) 아래 네 가지 중 하나를 고를 수 있다.

- **채널 추가** — 기존 채널은 하나도 건드리지 않고 새 채널 폴더와 스타일 명세를 만든다.
- **모듈 추가·변경** — 목소리·편집기·소재 수급 등 한 가지 모듈만 다시 묻고 그 모듈만 설치한다.
- **재점검(doctor)** — 도구·설정·설치 흔적·`.env` 키·채널 상태를 다시 확인해 표로 보여 준다.
- **스모크 테스트 다시** — 10초 영상을 다시 렌더해 세팅이 여전히 도는지 확인한다.

설정 파일이 없지만 채널 폴더(`01_원본영상` 등)나 `AGENTS.md`가 이미 있는 폴더에서 시작하면, 기존 파일을 하나도 고치지 않고 채널만 등록하는 "기존 작업 공간 채택" 경로로 안내한다.

## 검증 범위 (정확히 무엇을 확인했고 무엇을 확인하지 못했나)

- **실제로 돌려서 확인한 환경**: macOS(Apple Silicon)에서 Claude Code로 새 작업 공간 만들기, 채널 추가, 기존 작업 공간 채택, HyperFrames·Remotion 렌더, 로컬 목소리 복제(mlx-audio)까지 전부 실행하고 결과 영상(해상도·길이·오디오)을 ffprobe로 검증했다.
- **Codex에서 확인한 범위**: 점검 명령(`preflight.py`·`doctor.py`)까지만 실행해 봤고, 전체 흐름은 Claude Code로 확인했다. Codex에서 인터뷰부터 스모크 테스트까지 이어서 돌려 본 적은 없다.
- **코드는 있지만 실제로 돌려 보지 않은 것**: Windows·Linux·Intel Mac 경로(도구 탐지, 편집기 경로, `venv` 생성 등)는 코드로는 갈라져 있지만 이 환경에서 실행해 본 적이 없다.
- **공식 문서만 보고 구현했고 실제로 호출해 본 적이 없는 것**: ElevenLabs(클라우드 TTS)와 Pexels(무료 스톡) API 호출. 처음 쓸 때 결과를 직접 확인해야 한다.
- **사람이 직접 확인해야 하는 것**: CapCut·Premiere Pro로 넘긴 결과가 실제 편집기 앱에서 열리는지는 이 하네스가 확인하지 않는다(파일 구조까지만 검증한다). 화면을 볼 수 있는 도구가 있는 에이전트라면 열어 볼 수 있지만, `status.handoff_verified_by_user`는 사용자의 확인으로만 기록한다. 특히 macOS에서 생성된 CapCut 초안은 사람이 한 번 열어 봐 줘야 한다.
- **에이전트가 판단할 수 없는 것**: 생성된 목소리나 음악이 실제로 자연스럽게 들리는지, 원래 목소리와 얼마나 닮았는지 같은 오디오 품질은 에이전트가 소리를 들을 수 없으므로 전혀 검증하지 못한다. 반드시 사람이 직접 들어 봐야 한다.

세팅이 통과했다는 말은 `smoke_test.py`가 `passed: true`를 돌려준 경우만을 뜻하고, 위에서 "미확인"이라고 적은 부분은 통과 여부와 별개로 늘 사람의 확인이 필요하다.

## 테스트 실행

```
python3 -m venv .venv
.venv/bin/pip install pytest pyyaml
.venv/bin/python -m pytest tests -q
```

테스트는 파일 시스템만으로 동작하는 단위 테스트다. 실제 렌더·네트워크·GPU가 필요한 확인(HyperFrames/Remotion 렌더, 로컬 목소리 복제, 클라우드 API 호출)은 pytest가 아니라 위 "검증 범위"에 적은 것처럼 사람이 실제 작업 공간에서 스크립트를 직접 실행해 확인한다.
