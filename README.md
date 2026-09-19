# 영상 하네스 세팅 (video-harness-setup)

쇼츠·릴스·유튜브 영상을 AI 에이전트와 함께 만들기 위한 **작업 공간을 처음 세팅해 주는 스킬**입니다. Claude Code와 Codex에서 쓸 수 있고, macOS와 Windows를 지원합니다.

에이전트가 쉬운 말로 한 번에 하나씩 물어보고, 고른 것만 설치한 뒤, 10초짜리 영상을 실제로 만들어 보여서 세팅이 정말 되는지 확인합니다. 영상을 처음 만들어 보는 사람도 따라올 수 있게 만들었습니다.

## 에이전트에게 이렇게 말하세요

**① 설치** — Claude Code나 Codex 채팅창에 그대로 붙여 넣습니다. 쓰는 컴퓨터에 맞는 쪽을 고릅니다.

Mac:

```
아래 명령을 실행해서 영상 하네스 세팅 스킬을 설치해줘.
curl -fsSL https://raw.githubusercontent.com/Bejoowon/video-harness/main/install.sh | bash
```

Windows:

```
아래 명령을 Windows PowerShell에서 실행해서 영상 하네스 세팅 스킬을 설치해줘.
irm https://raw.githubusercontent.com/Bejoowon/video-harness/main/install.ps1 | iex
```

에이전트가 "인터넷에서 받은 스크립트를 실행해도 되나요?"라고 물으면 허용하면 됩니다. 스킬 폴더 하나를 복사할 뿐, 다른 프로그램은 설치하지 않습니다.

**② 껐다 켜기** — 설치가 끝나면 Claude Code(또는 Codex)를 닫았다가, 영상 작업에 쓸 **빈 폴더**에서 다시 엽니다. 새로 열어야 스킬이 보입니다.

**③ 실행** — 이렇게 말합니다.

```
영상 하네스 세팅을 시작해줘
```

첫 질문은 "어떤 채널을 만들고 싶으세요?"입니다. 에이전트가 먼저 어떤 채널을 만들고 싶은지 대화로 파악하고, 참고할 채널과 주제 후보를 찾아 보여 드린 뒤에 세팅을 시작합니다. 혼자 알아서 세팅해 버리지 않습니다.

## 설치

에이전트 없이 직접 설치하려면 터미널에 아래 한 줄을 붙여 넣습니다.

**macOS · Linux**

```bash
curl -fsSL https://raw.githubusercontent.com/Bejoowon/video-harness/main/install.sh | bash
```

**Windows (PowerShell)**

```powershell
irm https://raw.githubusercontent.com/Bejoowon/video-harness/main/install.ps1 | iex
```

이 한 줄이 하는 일은 스킬 폴더 하나를 복사하는 것뿐입니다. 다른 프로그램은 설치하지 않습니다.

- Claude Code와 Codex 중 이 컴퓨터에 있는 쪽을 찾아서 넣습니다.
- 이미 설치돼 있으면 예전 것을 지우지 않고 `skills-backup` 폴더로 옮긴 뒤 새로 넣습니다. **업데이트도 같은 명령**입니다.
- 설치한 뒤에는 Claude Code나 Codex를 **새로 열어야** 스킬이 보입니다.

> `install.ps1`은 아직 실제 Windows 기기에서 돌려 보지 못했습니다. 막히면 아래 "직접 복사"로 설치해 주세요.

<details>
<summary>설치 위치를 직접 고르기 · 직접 복사하기</summary>

| | macOS · Linux | Windows |
|---|---|---|
| Claude Code에만 | `… \| bash -s -- --claude` | 실행 전에 `$env:VIDEO_HARNESS_TARGET = "claude"` |
| Codex에만 | `… \| bash -s -- --codex` | `$env:VIDEO_HARNESS_TARGET = "codex"` |
| 둘 다 | `… \| bash -s -- --both` | `$env:VIDEO_HARNESS_TARGET = "both"` |

**직접 복사:** 이 저장소를 받아서 `skills/video-harness-setup/` 폴더를 그대로 복사합니다.

- Claude Code: `~/.claude/skills/video-harness-setup/` (개인용) 또는 프로젝트의 `.claude/skills/video-harness-setup/` (프로젝트용)
- Codex: `~/.codex/skills/video-harness-setup/`

</details>

## 시작하기

1. 영상 작업에 쓸 **빈 폴더**를 하나 만듭니다.
2. 그 폴더에서 Claude Code(또는 Codex)를 엽니다.
3. 이렇게 말합니다.

```
영상 하네스 세팅을 시작해줘
```

에이전트가 컴퓨터를 점검하고, 부족한 프로그램이 있으면 설치 방법을 알려 주고, 준비가 됐으면 질문을 시작합니다. 순서는 이렇습니다.

1. **어떤 채널을 만들고 싶은지 먼저 이야기합니다.** 첫 질문은 "어떤 채널을 만들고 싶으세요?"입니다. 이어서 직접 찍은 촬영본으로 만드는지, 누가 보면 좋겠는지, 무엇은 다루지 않을 건지, 어떤 느낌이면 좋겠는지를 하나씩 묻습니다. 건강·금융·법률처럼 틀린 말이 사람을 다치게 할 수 있는 분야면 작업 공간에 엄격한 근거 규칙을 넣겠다고 알려 줍니다.
2. **그 방향으로 레퍼런스 채널과 주제 후보를 찾아서 보여 줍니다.** 닮고 싶은 채널·영상 몇 개와, 그 시청자가 실제로 궁금해하는 주제 후보를 모아 옵니다. **그중에서 고르는 것은 사용자입니다.** 에이전트가 웹을 볼 수 없는 환경이면 찾아본 척하지 않고 그렇다고 말한 뒤 함께 떠올립니다.
3. **그다음에야 세팅을 시작합니다.** 포맷·길이 같은 값은 앞에서 들은 이야기에서 제안하고 "괜찮으세요?"를 묻습니다.

에이전트는 질문을 하면 답을 기다립니다. 추천(★)은 제안일 뿐이라 대신 골라서 넘어가지 않습니다. "알아서 해 주세요"라고 하면 설치 관련 항목만 추천값으로 채우고, 방향과 주제는 그래도 함께 정합니다.

### 미리 있으면 좋은 프로그램

| 프로그램 | 버전 |
|---|---|
| Python | 3.10 이상 |
| Node.js | 22 이상 (npx 포함) |
| ffmpeg / ffprobe | — |
| git | — |
| uv (선택) | 있으면 설치가 더 빠릅니다 |

없어도 괜찮습니다. 스킬이 무엇이 없는지 찾아서 설치 명령을 알려 줍니다. 다만 **대신 설치해 주지는 않습니다.**

### API 키는 직접 넣습니다

ElevenLabs·Pexels·Higgsfield 같은 서비스를 고르면 키가 필요합니다. 키는 작업 공간의 `.env` 파일에 **직접** 적습니다. 에이전트는 키가 있는지만 확인하고, 값을 묻거나 화면에 출력하지 않습니다.

## 무엇을 고를 수 있나

고른 것만 설치합니다. 고르지 않은 것은 아무것도 설치하지 않습니다.

| 구분 | 선택지 | 비고 |
|---|---|---|
| 만드는 방식 | 찍은 영상 먼저 / 대본 먼저 / 회차마다 정함 | 방향을 이야기할 때 함께 묻습니다. 이후 질문의 추천이 이 답에 맞춰 달라집니다 |
| 렌더 엔진 | HyperFrames(기본) / Remotion / 둘 다 | HyperFrames는 설치가 가볍습니다. Remotion은 React를 아는 사람에게 편하고, 회사 규모에 따라 유료 라이선스가 필요할 수 있습니다 |
| 사람이 직접 편집하기 | 안 씀 / CapCut / Premiere Pro | 컷 목록·자막(SRT)·가져오기 안내가 함께 나옵니다 |
| 목소리 | 직접 녹음·원음(기본) / 클라우드 TTS(ElevenLabs) / 로컬 목소리 복제 | 로컬 목소리 복제는 Apple Silicon Mac 전용입니다 |
| 말 → 자막 | mlx-whisper(Apple Silicon) / faster-whisper(그 외) | 기본 모델 `large-v3-turbo` |
| 소재 | 직접 촬영(기본) / 무료 스톡(Pexels·Wikimedia) / Higgsfield(AI 생성) | 여러 개 고를 수 있습니다 |
| 레퍼런스 분석 | 설치 / 안 함 | 닮고 싶은 영상을 채널 스타일에 반영할 때 씁니다 |
| 대본 운율 | 3·4조 네 마디(기본) / 자유 | 에이전트가 쓰는 내레이션이 읽을 때 리듬이 느껴지게 나옵니다. 글자 수를 세어 보여 주는 도구가 함께 들어갑니다 |

폰트(Pretendard)와 채널별 스타일 명세(`frame.md`)는 항상 함께 만들어집니다. `frame.md`는 색·글꼴·자막 위치·움직임을 한곳에 정해 두어, 회차가 바뀌어도 모션그래픽이 같은 모양을 유지하게 합니다.

## 세팅이 끝나면 생기는 것

- 채널별 폴더 (`01_원본영상`, `02_기획과자막`, `03_편집프로젝트`, `04_완성영상`)와 스타일 명세
- 이야기한 방향과 근거 규칙이 적힌 `채널기준.md`, 함께 고른 주제가 적힌 `02_기획과자막/주제_후보.md`
- 공용 폴더 (`스타일_라이브러리`, `도구`, `99.레퍼런스`)
- 에이전트가 지킬 작업 규칙 (`AGENTS.md`, Claude Code용 `CLAUDE.md`)
- 채널별 대본 양식과 대본의 마디·음절을 세어 보여 주는 도구 (`도구/script/check_rhythm.py`)
- 설정 파일 `harness.config.json`과 키를 적을 `.env` 양식
- 실제로 렌더한 10초 확인 영상

## 다시 실행하면

이미 세팅된 폴더에서 같은 말을 다시 하면 아래 중 하나를 고를 수 있습니다.

- **채널 추가** — 기존 채널은 건드리지 않고 새 채널 폴더와 스타일 명세를 만듭니다. 새 채널도 방향부터 다시 이야기합니다.
- **채널 방향 다시 잡기** — 시청자·범위·말투를 다시 묻고, 원하면 레퍼런스와 주제도 다시 찾아 줍니다.
- **모듈 추가·변경** — 목소리·편집기·소재 중 하나만 다시 묻고 그것만 설치합니다.
- **재점검** — 도구·설정·설치 상태·키·채널 상태를 표로 보여 줍니다.
- **확인 영상 다시 만들기** — 10초 영상을 다시 렌더해 여전히 되는지 봅니다.

세팅 파일은 없지만 이미 영상 폴더를 쓰고 있던 곳이라면, 기존 파일을 하나도 고치지 않고 채널만 등록하는 "기존 작업 공간 채택"으로 안내합니다.

## 어디까지 확인했나

솔직하게 적습니다.

- **실제로 돌려서 확인한 것** — macOS(Apple Silicon) + Claude Code에서 새 작업 공간 만들기, 채널 추가, 기존 작업 공간 채택, HyperFrames·Remotion 렌더. 결과 영상의 해상도·길이·오디오를 ffprobe로 검증했습니다. 한 줄 설치(`install.sh`)도 macOS에서 실제로 내려받아 설치해 봤습니다.
- **일부만 확인한 것**
  - *Codex*: 점검 명령(`preflight.py`·`doctor.py`)까지만 실행했습니다. 인터뷰부터 끝까지 이어서 돌려 본 적은 없습니다.
  - *로컬 목소리 복제*: 음성 생성 도구는 이미 설치돼 있던 환경과 모델로 실행해 음성이 만들어지는 것을 확인했습니다. 이 스킬의 **설치 단계**(가상환경 만들기, 수 GB 모델 내려받기)는 돌려 보지 않았습니다.
  - *무료 스톡*: Wikimedia 검색은 실제로 호출해 봤습니다. Pexels는 호출해 보지 않았습니다.
- **코드는 있지만 돌려 보지 않은 것** — Windows·Linux·Intel Mac 경로 전부, `install.ps1`, ElevenLabs(클라우드 TTS) 호출.
- **사람이 직접 봐야 하는 것** — CapCut·Premiere Pro로 넘긴 결과가 앱에서 실제로 열리는지는 이 스킬이 확인하지 않습니다(파일 구조까지만 검증). 특히 macOS의 CapCut 초안은 한 번 직접 열어 봐 주세요.
- **에이전트가 판단할 수 없는 것** — 만들어진 목소리가 자연스러운지, 원래 목소리와 닮았는지. 에이전트는 소리를 들을 수 없으니 반드시 직접 들어 보세요.

"세팅이 통과했다"는 말은 확인 영상 렌더(`smoke_test.py`)가 `passed: true`를 돌려준 경우만을 뜻합니다.

## 개발자용

```
video-harness/
├── skills/video-harness-setup/   스킬 본체 (SKILL.md, scripts, references, assets)
├── install.sh / install.ps1      한 줄 설치
└── tests/                        pytest 테스트
```

스킬의 스크립트는 파이썬 표준 라이브러리만 씁니다. 테스트는 이렇게 돌립니다.

```bash
python3 -m venv .venv
.venv/bin/pip install pytest pyyaml
.venv/bin/python -m pytest tests -q
```

테스트는 파일 시스템만으로 도는 단위 테스트입니다. 실제 렌더·네트워크·GPU가 필요한 확인은 위 "어디까지 확인했나"에 적은 대로 실제 작업 공간에서 직접 돌려서 합니다.

## 라이선스

[MIT](LICENSE). 함께 들어 있는 GSAP(`skills/video-harness-setup/assets/episode-template-hyperframes/assets/gsap.min.js`)은 GSAP의 자체 라이선스를 따르며, 같은 폴더의 `gsap-LICENSE.txt`에 있습니다. 설치 중에 내려받는 도구와 모델(HyperFrames, Remotion, Pretendard, Whisper·Qwen3-TTS 모델 등)은 각자의 라이선스를 따릅니다.
