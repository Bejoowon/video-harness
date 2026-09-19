---
name: video-harness-setup
description: 쇼츠·릴스·영상 자동화 작업 공간을 인터뷰로 처음 세팅한다. 사용자가 고른 모듈만 설치하고(HyperFrames·Remotion 렌더 엔진, CapCut·Premiere 편집기 넘기기, 음성·전사, 무료 스톡·Higgsfield 소재, 레퍼런스 분석), 채널 폴더와 채널별 스타일 명세를 만들고, 10초 렌더로 세팅이 실제로 도는지 증명한다. 쓰는 때 — 영상 하네스 세팅, 쇼츠 제작 환경 만들어줘, 릴스 만드는 환경 세팅, 새 채널 추가, 모듈 추가(TTS·스톡·Higgsfield·편집기), 세팅 점검·doctor, HyperFrames와 Remotion 중 고르기.
---

# 영상 하네스 세팅

영상을 처음 만들어 보는 사람과 대화하며 작업 공간을 세팅한다. 상대는 전문가가 아니다. 한국어로, 쉬운 말로, 한 번에 하나씩 묻는다. 마지막에 10초 영상을 실제로 렌더해서 세팅이 도는 것을 보여 준다.

이 스킬은 초기세팅만 한다. 매 편 제작 절차를 맡을 2단계 제작 절차 스킬(`video-harness-workflow`)은 아직 만들어지지 않았다. 그때까지는 이 스킬이 세팅까지만 하고, 레퍼런스 분석은 `watch` 모듈이 설치됐을 때만 세팅 끝에 이어서 한다.

## 명령 규칙

- `SKILL_DIR` — 지금 읽고 있는 이 SKILL.md가 들어 있는 폴더의 절대경로다. 설치 위치는 사람마다 다르므로(에이전트별 스킬 폴더) 이 파일을 읽은 경로에서 파일 이름만 뺀 값을 쓴다.
- `<ws>` — 작업 공간의 절대경로. 하위 명령이 없는 스크립트(`preflight.py`·`scaffold.py`·`smoke_test.py`·`doctor.py`)는 첫 인자, 하위 명령이 있는 스크립트(`config_tool.py`·`install_module.py`)는 하위 명령 바로 다음 인자다. 현재 폴더에 의존하지 않으니 어디서 실행해도 된다.
- 아래 예시의 `${SKILL_DIR}`와 `<ws>`는 셸 변수로 두지 말고 실제 절대경로로 바꿔서 실행한다. 경로에 공백이 있을 수 있으니 `"<ws>"`처럼 항상 따옴표로 감싼다.
- 실행 형태: `python3 "${SKILL_DIR}/scripts/preflight.py" "<ws>" --json`. Windows에서는 `python3` 대신 `python`을 쓴다.
- Windows PowerShell에서는 작은따옴표 안의 JSON이 그대로 전달되지 않을 수 있고 줄 끝 `\`도 통하지 않는다. 확실하지 않으면 명령을 한 줄로 쓰고 JSON 값의 큰따옴표를 이스케이프한다(`'\"hyperframes\"'`). 어떤 셸인지 먼저 확인한다.
- 스크립트는 전부 JSON이나 한국어 표로 답한다. 그 결과를 사용자에게 그대로 쏟지 말고, 필요한 줄만 골라 옮긴다.

## 1. 시작

아직 작업 공간을 묻기 전이다. 지금 대화가 열려 있는 폴더를 `<ws>`로 삼아 점검을 돌린다.

```
python3 "${SKILL_DIR}/scripts/preflight.py" "<ws>" --json
```

결과를 보고 갈 길을 정한다. 위에서부터 처음 맞는 조건 하나만 적용한다.

| 조건 | 할 일 |
|---|---|
| `can_proceed`가 거짓 | 아래 "필수 도구가 없을 때"로 간다 |
| `existing_config`가 참 | 8절 "재실행 메뉴" |
| `looks_like_existing_workspace`가 참 | 7절 "기존 작업 공간 채택" |
| 그 밖 | 2절 인터뷰 |

그 밖에 읽을 값: `platform.apple_silicon`(선택지 걸러내기), `editors`(CapCut·Premiere 설치 여부), `disk_free_gb`, `audio_warning`.

**경로가 바뀌면 분기를 다시 한다.** 인터뷰 1단계에서 작업 공간 경로를 확인하는데, 사용자가 지금 폴더가 아닌 다른 경로를 대면 그 경로로 `preflight.py`를 **다시 돌리고 위 표로 돌아가 분기부터 다시 정한다**. `config_tool.py init`은 그다음이다. 이미 설정 파일이 있는 폴더는 `init`이 아니라 8절 재실행 메뉴로 가야 하고, 기존 채널 폴더가 있는 곳은 7절 채택으로 가야 한다.

`audio_warning`이 비어 있지 않으면 그대로 전한다. macOS에서 기본 소리 출력 장치가 마이크류로 잡혀 있다는 뜻이고, 그대로 두면 렌더가 "Navigation timeout"으로 멈출 수 있다. 세팅을 막지는 않지만 스모크 테스트 전에 소리 출력 장치를 바꾸라고 알린다(`pitfalls.md` 1번).

### 필수 도구가 없을 때

`missing_required`에 빠진 도구가, `hints`에 도구별 설치 명령이 들어 있다. 설치 명령을 그대로 보여 주고 둘 중 하나를 고르게 한다.

- 대신 실행해 달라 → 동의를 받은 뒤에만 실행한다. 시스템 도구는 묻지 않고 설치하지 않는다.
- 직접 설치하겠다 → 설치가 끝나면 알려 달라고 한다.

어느 쪽이든 끝나면 `preflight.py`를 다시 돌려 `can_proceed`가 참이 된 것을 확인하고 진행한다.

## 2. 인터뷰

### 규칙

- 한 번에 한 가지만 묻는다. 여러 질문을 한 번에 쏟지 않는다. 표의 한 행이 한 질문이다. 3단계처럼 한 행에 값이 여러 개면 값마다 나눠 묻되, 기록은 행 단위로 한 번에 한다.
- 질문마다 선택지를 모두 보여 주고, 추천 하나에 ★를 붙이고, 추천하는 이유를 한 줄 덧붙인다. 0단계(출발점)만 예외다 — 취향이 아니라 사실을 묻는 질문이라 추천을 붙이지 않는다.
- 점검 결과로 걸러진 선택지는 아예 보여 주지 않는다. `platform.apple_silicon`이 거짓이면 로컬 목소리 복제를 선택지에서 뺀다.
- 답을 받으면 그 줄의 기록 명령을 바로 실행한다. 도중에 끊겨도 다음 실행 때 이어서 한다.
- "모르겠어요", "아무거나"라고 하면 추천값으로 정하고 더 캐묻지 않는다. 무엇으로 정했는지 한 줄로만 알린다.
- API 키·비밀번호 같은 비밀값은 채팅으로 받지 않는다. `.env.example`을 보고 본인이 `.env`에 직접 채우게 하고, 나중에 doctor가 "채워졌는지"만 확인한다.
- 채널 질문(0 · 3 · 3-1 · 3-1a · 3-2)은 답을 모았다가 `add-channel` 한 번으로 기록한다. 채널은 통째로 만들어야 해서다. 그 앞뒤 단계는 답마다 바로 기록한다.

### 0단계 — 출발점

인터뷰의 **첫 질문**이다. 작업 공간 이름보다 먼저 묻는다. 영상을 만드는 방식이 두 갈래로 갈라지고, 그 갈래가 뒤에 오는 질문들의 추천을 바꾸기 때문이다.

> 직접 찍은 촬영본으로 만드시나요?
> ① 네, 찍어 둔 영상으로 만들어요 (`footage-first`)
> ② 아니요, 대본부터 쓰고 영상은 찾거나 생성해요 (`script-first`)
> ③ 회차마다 달라요 (`per-episode`)

이 질문에는 ★ 추천을 붙이지 않는다. 취향이 아니라 사용자가 이미 하고 있는 방식을 묻는 것이라 대신 골라 줄 수 없다. 사용자가 헷갈려 하면 두 흐름을 각각 한두 문장으로 풀어 주고 다시 묻는다 — 찍은 영상 먼저는 찍어 둔 촬영본을 먼저 보고 쓸 구간을 골라 이야기를 만드는 방식이고, 대본 먼저는 할 말을 먼저 쓴 다음 거기에 맞는 화면을 찾거나 만드는 방식이다. 더 풀어서 설명할 말은 `workflows.md`에 있다.

답은 채널을 만들 때 `add-channel`의 `--workflow`로 함께 기록된다. 그 전까지는 설정 파일 어디에도 남지 않는다. 그래서 이어서 할 때 `channels`가 비어 있으면 이 질문부터 다시 한다.

영상 유형(`kind`)은 묻지 않는다. 출발점과 포맷에서 자동으로 정해진다 — `script-first`면 내레이션 쇼츠, 그 밖에는 세로면 촬영본 중심 쇼츠·가로면 롱폼 브이로그다. 설정에는 그대로 기록되므로 다르면 나중에 `channels.<번호>.kind`로 고친다.

#### 출발점에 따른 추천

뒤 단계에서 어느 선택지에 ★를 붙일지 이 표를 보고 정한다. 선택지 자체는 그대로 다 보여 준다.

| 단계 | `footage-first` | `script-first` | `per-episode` |
|---|---|---|---|
| 편집기 넘기기 (4-1) | 쓰기를 권함 — 촬영본은 손으로 다듬는 단계가 생긴다 | `none` | 쓰기를 권함 |
| 목소리 (5) | `record` — 원음·직접 녹음 | TTS — Apple Silicon이면 `local-mlx`도 안내하고, 아니면 `cloud` | 둘 다 설명하고 고르게 함 |
| 전사 (6) | 필수로 안내 — 전사 결과가 자막의 원본이다 | 설치 권함 — 자막 타이밍을 맞추는 데 쓴다 | 필수로 안내 |
| 소재 (7) | `own-footage` | `stock`(무료 스톡)과 `higgsfield` 중에서 | 복수 선택 안내 |
| 레퍼런스 분석 (8) | 선택 | 권함 — 다른 채널 영상을 보고 구성을 잡는 흐름이다 | 권함 |

### 단계

답은 `config_tool.py`로만 기록한다. 설정 파일을 직접 편집하지 않는다. 이 도구가 값을 검증하고, 검증에 걸리면 파일을 건드리지 않은 채 무엇이 틀렸는지 알려 준다. 지금까지의 답을 다시 보려면 `config_tool.py show "<ws>"`, 설정이 온전한지만 보려면 `config_tool.py validate "<ws>"`를 쓴다.

기록 명령은 모두 `python3 "${SKILL_DIR}/scripts/config_tool.py" …` 형태다. 아래 표에서는 앞부분을 줄여 적었다.

| 단계 | 묻는 것 | 선택지 (★ 추천 — 이유) | 기록 명령 | 고르면 읽을 문서 |
|---|---|---|---|---|
| 0 | 출발점 — 위 "0단계"의 질문을 그대로 묻는다 | 찍은 영상 먼저 `footage-first` / 대본 먼저 `script-first` / 회차마다 정함 `per-episode`. ★ 없음 — 사실을 묻는 질문이다 | (3-2까지 모아서 아래 `add-channel` 한 번) | `workflows.md` |
| 1 | 작업 공간 경로와 이름 | 지금 폴더 ★ — 이미 여기서 일하고 있다 / 다른 경로(고르면 그 경로로 `preflight.py`부터 다시) | `config_tool.py init "<ws>" --name "내작업실"` | — |
| 2 | 어느 에이전트에서 쓸지 | 지금 이 에이전트만 ★ — 나중에 늘릴 수 있다 / Claude Code(`claude`) / Codex(`codex`) / 둘 다(`claude`,`codex` — 규칙 파일이 양쪽 형식으로 놓인다) | `config_tool.py set "<ws>" agents '["claude","codex"]'`. 1·2단계 답을 함께 알면 `config_tool.py init "<ws>" --name "내작업실" --agents claude,codex`로 한 번에 기록해도 된다 | — |
| 3 | 채널 이름, 포맷, 목표 길이, 언어, 한 줄 콘셉트, 고정 오프닝(선택) | 포맷 세로 쇼츠 `9:16` ★ — 쇼츠·릴스 기본 / 가로 `16:9`. 길이 60초 ★. 영상 유형은 0단계 답과 포맷에서 자동으로 정해지므로 묻지 않는다 | (3-2까지 모아서 아래 `add-channel` 한 번) | — |
| 3-1 | 스타일 시작점 | 레퍼런스에서 뽑기 `reference` ★ — 닮고 싶은 영상이 있으면 가장 빠르다(레퍼런스 분석 모듈 필요) / 기성 프리셋 `preset` / 직접 입력 `manual` / 나중에 정함 `later` | `add-channel`의 `--style-start reference`. `frame.md` 머리말에 `style_start: reference`로 남는다 | `module-watch.md`, `style-system.md` |
| 3-1a | (3-1이 `reference`일 때) 닮고 싶은 영상 1~3개와 각각 마음에 드는 점 | 지금 있는 것만 ★ — 없으면 "나중에 가져오기"로 넘긴다 | `add-channel`의 `--reference "URL::자막이 크고 가운데에 겹친다"`(여러 번). 채널의 `레퍼런스_목록.md`에 "미분석"으로 들어간다 | `module-watch.md` |
| 3-2 | 일관성 수준 | 만들면서 정함 `decide-later` ★ — 첫 채널은 대개 여기서 시작한다 / 포맷 고정형 `fixed` / 회차 변주형 `variation` | `add-channel`의 `--consistency decide-later`. `frame.md` 머리말에 `consistency_level`로 남고, `fixed`를 고르면 `consistency` 블록이 좁아진다(아래 설명) | `style-system.md` |
| 4 | 렌더 엔진 | HyperFrames `hyperframes` ★ — 설치가 가볍고 이 하네스의 기본 / Remotion `remotion` / 둘 다 `both` | `config_tool.py set "<ws>" modules.render.engine '"hyperframes"'` | `module-hyperframes.md`, `module-remotion.md` |
| 4-1 | 손으로 편집할 편집기 | 안 씀 `none` / CapCut `capcut` / Premiere Pro `premiere`. 추천 규칙은 아래 "단계별로 더 알아야 할 것"을 따른다 — 이미 쓰는 편집기가 있으면 그것을 추천한다 | `config_tool.py set "<ws>" modules.handoff.editor '"capcut"'` | `module-handoff-capcut.md`, `module-handoff-premiere.md` |
| 5 | 목소리 | 직접 녹음·원음 `record` ★ — 설치할 게 없고 품질이 확실하다 / 클라우드 TTS `cloud` / 로컬 목소리 복제 `local-mlx`(Apple Silicon에서만 보여 준다) | `config_tool.py set "<ws>" modules.voice.mode '"record"'` | `module-voice-record.md`, `module-voice-cloud.md`, `module-voice-local-mlx.md` |
| 6 | 전사(말→자막) 모델 | `large-v3-turbo` ★ — 빠르면서 정확하고, 이 하네스에서 검증한 이름은 이것뿐이다 / 다른 모델 이름 직접 지정(미확인) | `config_tool.py set "<ws>" modules.transcribe.model '"large-v3-turbo"'` | `module-transcribe.md` |
| 7 | 소재 수급 (복수 선택) | 직접 촬영 `own-footage` ★ / 무료 스톡 `stock` / Higgsfield(AI 생성) `higgsfield`. Higgsfield를 고르면 인증 방식도 묻는다 — 구독 계정 로그인 `account` 또는 API 키 `api-key`(안 고르면 `none`) | `config_tool.py set "<ws>" modules.sources '["own-footage","stock"]'` 그리고 `config_tool.py set "<ws>" modules.higgsfield.auth '"api-key"'` | `module-stock.md`, `module-higgsfield.md` |
| 8 | 레퍼런스 분석 스킬 | 설치 ★(3-1에서 레퍼런스를 골랐다면) — 없으면 레퍼런스를 자동으로 분석할 수 없다 / 안 함 | `config_tool.py set "<ws>" modules.reference.watch true` | `module-watch.md` |
| 9 | 작업 규칙 | 버전은 `vN-then-final` ★(작업 중에는 _v2, _v3로 올리고 확정되면 최종본만 남긴다) 또는 `keep-all`. 샘플 길이 12초 ★. 대본 운율은 `meter` ★ — 읽을 때 리듬이 살아 쇼츠 내레이션이 귀에 잘 붙는다 / `free`(운율 규칙 없이 자연스럽게). 셋 다 기본값 그대로 두면 통과. 이 값은 앞으로의 작업 규칙으로 기록만 된다. 세팅 단계에서는 어떤 파일도 지우지 않는다. 실제 정리는 2단계에서 사용자 승인을 받고 한다 | `config_tool.py set "<ws>" rules.versioning '"vN-then-final"'` 그리고 `config_tool.py set "<ws>" rules.sample_seconds 12` 그리고 `config_tool.py set "<ws>" rules.script_rhythm '"meter"'` | `script-rhythm.md` |
| 10 | 요약을 보여 주고 확인 | — | 기록 없음. 3절로 간다 | — |

채널 기록(0 · 3 · 3-1 · 3-1a · 3-2를 한 번에):

```
python3 "${SKILL_DIR}/scripts/config_tool.py" add-channel "<ws>" \
  --name "동네한바퀴" --format 9:16 --workflow script-first \
  --target-seconds 60 --language ko --concept "우리 동네 가게를 1분에 소개한다" \
  --opening "오늘은 여기입니다" --style-start reference --consistency decide-later \
  --reference "https://example.com/shorts/1::자막이 크고 화면 가운데에 겹친다"
```

출력에 새 채널의 `id`가 들어 있다. 이후 `--channel`에 쓸 값이니 기억한다. 한글 이름은 `channel-6ad0f42f` 같은 임의 id가 되므로 짐작하지 말고 출력값을 그대로 쓴다. 채널 폴더 이름은 `--name` 값 그대로다.

이미 만든 채널의 값을 고쳐야 하면 목록 번호(0부터)로 짚는다: `config_tool.py set "<ws>" channels.0.format '"16:9"'`.

0단계의 답은 채널의 `채널기준.md`에 들어간다 — 머리의 "출발점" 한 줄과 "작업 순서" 절이 그 답에서 만들어진다. 출발점을 고르지 않은 채 채널을 만들면 작업 순서가 공통 순서로 남고, 나중 점검에서 `주의`로 뜬다.

3-1과 3-2의 답은 채널의 `frame.md`(스타일 단일 원본)에 그대로 들어간다.

- 머리말에 `style_start`와 `consistency_level` 두 줄이 항상 적힌다. 나중에 "이 스타일을 어디서 가져왔더라"를 문서만 보고 알 수 있게 하기 위해서다.
- 3-2가 `fixed`면 `consistency` 블록이 좁아진다: 전환(`motion.transitions`)과 강조색(`colors.accent`)까지 `locked`로 올라가고 `choose`가 비고 `free`에서 `illustration_colors`가 빠진다. 포맷 고정형은 삽화 색까지 `frame.md`의 색으로 제한하니, 이야기별 삽화 색을 자유롭게 쓰려면 회차 변주형을 고른다.
- `variation`과 `decide-later`는 기본 블록 그대로다. 정해 둔 후보 안에서 회차마다 고를 수 있다.
- `채널기준.md`에도 두 답이 한국어로 적힌다.

### 단계별로 더 알아야 할 것

- **4 (렌더 엔진)** — 솔직하게 비교해 준다. HyperFrames는 컷·자막·그래픽 자동화에 강하고, 속도 램프·피사체 추적·멀티캠은 못 한다. 그런 편집이 필요하면 4-1에서 편집기를 고르면 된다. Remotion은 React를 아는 사람에게 편하고, 영리 법인 규모에 따라 유료 라이선스가 필요할 수 있다(`module-remotion.md`).
- **4-1 (편집기)** — 출발점이 `footage-first`나 `per-episode`면 편집기를 쓰라고 권한다. 촬영본에서 시작하는 영상은 손으로 다듬는 단계가 반드시 생긴다. 어느 편집기인지는 이 순서로 정한다. ① **이미 쓰는 편집기가 있으면 그것을 추천한다** — 점검 결과의 `editors`로 CapCut·Premiere Pro 설치 여부를 보고, 설치된 쪽을 먼저 물어본다. ② 둘 다 안 쓰면 무료인 CapCut을 권하되, **CapCut 초안을 앱에서 실제로 여는 것은 아직 미확인**이라고 말한다(사람이 한 번 확인해 줘야 한다). Premiere Pro 쪽은 오래된 교환 형식인 FCP7 XML을 쓴다. ③ 어느 쪽이든 넘기기가 잘 안 되면 자막(SRT)·컷 목록·가져오기 안내가 든 묶음이 항상 함께 나오므로 손으로 가져올 수 있다. `script-first`면 `none`으로 충분하고 나중에 모듈만 추가할 수 있다.
- **5 (목소리)** — 로컬 목소리 복제(`local-mlx`)는 Apple Silicon에서 실제로 돌려 봤다. 두 문단을 만들어 후처리하고 다시 전사했더니 글자는 입력과 정확히 같았다. 다만 **어떻게 들리는지(자연스러움, 원래 목소리와 닮은 정도)는 미확인이다** — 에이전트는 소리를 들을 수 없으니 사람이 들어 봐야 한다. 클라우드 TTS(`cloud`)는 공식 문서만 보고 구현했고 **실제로 호출해 본 적이 없다**(키가 없었다). 고르면 그대로 알린다. 남의 목소리를 복제하려면 그 사람의 동의가 필요하다.
- **7 (Higgsfield)** — 구독의 무제한 혜택은 CLI·API에 적용되지 않고 항상 크레딧이 깎인다. 고르기 전에 알린다.
- **9 (대본 운율)** — 용어를 설명하지 말고 예를 하나만 보여 준다. "에이전트가 내레이션을 쓸 때 읽으면 리듬이 느껴지게 끊어 씁니다 — `오늘은 / 우리 동네 / 숨은 맛집 / 가 볼게`처럼요. 글자 수를 세어 보여 주는 도구도 함께 들어갑니다." 기본값이므로 사용자가 다른 말을 하지 않으면 그대로 두고 넘어간다. "운율은 필요 없다"고 하면 `free`로 기록한다. 이 규칙은 에이전트가 새로 쓰는 글에만 적용되고, 사람이 실제로 한 말을 받아 적은 전사 결과는 고치지 않는다는 점도 한 줄로 알린다.

### 3-1a 레퍼런스 고르는 기준

질문과 함께 이 네 가지를 보여 준다.

1. 만들려는 것과 포맷이 같은 영상(세로 쇼츠면 세로 쇼츠).
2. 영상 유형이 같은 영상(내레이션형이면 내레이션형).
3. 자막·제목·컷 템포 중 하나라도 "이렇게 하고 싶다"가 분명한 영상.
4. 1~3개면 충분하다. 많을수록 좋은 게 아니라 방향이 한쪽으로 모이는 게 중요하다. 고른 영상들의 스타일이 서로 다르면 어느 쪽이 기준인지 묻는다.

영상마다 "어디가 마음에 드는지"를 한 줄로 받는다. 자막 / 제목 / 컷 템포 / 색감 / 효과음·BGM / 구성 중에서 고르게 하면 대답하기 쉽다. 지금 가진 게 없으면 "나중에 가져오기"로 넘어가고, 채널 폴더의 `레퍼런스_모으는_법.md`를 나중에 읽으라고 알린다.

같이 알릴 것: 레퍼런스는 분석용이다. 레퍼런스 영상의 화면·소리를 내 영상에 가져다 쓰지 않는다. 채널 스타일 명세(`frame.md`)는 레퍼런스가 분석되고 첫 샘플이 승인될 때까지 `draft` 상태로 남는다.

## 3. 요약과 확인

설치를 시작하기 전에 한 화면으로 정리해 보여 주고 확인을 받는다.

- 작업 공간 이름과 경로, 만들 채널(이름·출발점·포맷·유형·길이)
- 고른 모듈 목록과 각각이 하는 일 한 줄
- 작업 규칙: 버전 규칙, 샘플 길이, 대본 운율
- 오래 걸릴 수 있는 것(모델 다운로드, npm 설치)과 대략의 소요
- 나중에 사용자가 직접 해야 하는 일이 생긴다는 예고

확인을 받기 전에는 아무것도 설치하지 않는다. 바꾸고 싶다는 답이 오면 해당 단계만 다시 묻고 `set`으로 덮어쓴다. 채널을 잘못 넣었으면 되돌리는 길이 따로 있다.

```
python3 "${SKILL_DIR}/scripts/config_tool.py" remove-channel "<ws>" <채널 id>
```

설정에서만 뺀다. 이미 만들어진 폴더와 파일은 하나도 지우지 않으니, 필요 없으면 사용자가 직접 지우게 안내한다.

## 4. 만들기

### 4-1. 폴더와 문서

```
python3 "${SKILL_DIR}/scripts/scaffold.py" "<ws>"
```

작업 공간 폴더, 채널 폴더, 규칙 문서, 회차 템플릿, `도구/`의 스크립트를 한 번에 만든다. 멱등이라 이미 있는 파일은 건드리지 않고 `skipped`로만 보고한다. 결과에서 `created` 개수와 주요 경로만 전한다.

### 4-2. 설치 계획 보여 주기

```
python3 "${SKILL_DIR}/scripts/install_module.py" plan "<ws>" --all
```

모듈 순서와 단계 제목이 나온다. 사람이 읽을 수 있게 옮긴다: 모듈 이름, 각 단계가 무엇을 하는지, 인터넷이 필요한 단계(`needs_network`), 오래 걸리는 단계(`background`), 사람이 직접 해야 하는 항목(`manual`).

### 4-3. 모듈 설치

계획에 나온 순서 그대로, 모듈마다 한 번씩 실행한다.

```
python3 "${SKILL_DIR}/scripts/install_module.py" run "<ws>" hyperframes
```

- `install_module.py run`은 단계를 순서대로 동기 실행한다. 따라서 `background`가 참인 단계가 있는 모듈(로컬 목소리 복제의 모델 다운로드)은 단계 하나가 아니라 **명령 전체**를 백그라운드로 돌리고, 로그 경로 `<ws>/도구/logs/install-<모듈>.log`를 알려 준 뒤 다음 모듈로 넘어간다.
- `manual` 항목은 기본적으로 사용자에게 체크리스트로 넘긴다. 모아 두었다가 마지막에 한 번에 건넨다. 사용자가 대신 실행해 달라고 하면 명령을 그대로 보여 주고 따로 확인을 받은 뒤에만 실행한다.
- 에이전트의 스킬 폴더를 바꾸는 명령(`npx --yes hyperframes@0.8.43 skills`, `npx skills add remotion-dev/skills`, `npx skills add higgsfield-ai/skills`, `npx skills add bradautomates/claude-video -g`)은 `manual`로 나온다. `npx skills add …`가 어느 스킬 폴더에 설치되는지는 그 CLI와 `-g` 여부가 정하므로, 실행 전에 설치 위치를 사용자에게 확인받는다.
- 결과의 `ok`가 거짓이어도 멈추지 않는다. `failed_step`과 로그 경로를 적어 두고 다음 모듈을 계속한다. 실패는 설정의 `status.failed`에 남는다. 마지막에 실패 목록과 재시도 명령(`install_module.py run "<ws>" <모듈>`)을 함께 보여 준다.

## 5. 마무리: 실제로 도는지 증명

백그라운드로 돌린 모듈이 있으면 먼저 끝났는지 확인한다 — `config_tool.py show "<ws>"`의 `status.installed`에 그 모듈이 들어왔거나 `status.failed`에 기록됐을 때가 끝난 때다. 스모크 테스트는 로컬 목소리 복제 모델을 실제로 쓰므로 다운로드가 끝나기 전에 돌리면 신호음으로 대체된다.

```
python3 "${SKILL_DIR}/scripts/smoke_test.py" "<ws>"
```

채널이 여럿이면 `--channel <채널 id>`로 방금 만든 채널을 짚어 돌린다. 엔진을 둘 다 골랐으면 `--engine hyperframes`와 `--engine remotion`을 각각 한 번씩 돌린다. 돌린 조합이 모두 `passed: true`일 때만 완료다. 회차 템플릿을 복사해 10초 영상을 실제로 렌더하고, 해상도·길이·오디오를 확인하고, 모아보기 이미지를 만들고, 스타일 검사까지 돌린다.

Remotion으로 돌리면 복사한 프로젝트에 `node_modules`가 없으므로 스모크 테스트가 매번 `npm install`을 다시 한다(수백 MB를 복사하지 않으려고 일부러 그렇게 뒀다). 그래서 Remotion 스모크는 몇 분이 걸릴 수 있고 인터넷이 필요하다. 미리 알린다.

1. 세팅 완료 = 스모크 테스트가 `passed: true`이고 doctor에 `문제` 항목이 없는 것. `주의`만 남은 것은 완료로 본다(예: `frame.md` 초안, 검증된 CapCut 버전 없음, `.env` 선택 키 미입력). `passed`가 거짓이면 아직 완료가 아니다.
2. 통과하면 `contact_sheet` 경로(10초 영상을 다섯 장으로 펼친 모아보기 jpg)를 열어 보라고 알리고, `studio_hint`에 담긴 미리보기 명령을 그대로 전한다.
3. 실패하면 `verify_problems`와 `style`, 그리고 `<ws>/도구/logs/smoke/<시각>/render.log`를 보고 원인을 찾는다. 증상별 해결은 `pitfalls.md`에 있다. macOS에서 "Navigation timeout"이면 기본 소리 출력 장치를 먼저 확인한다.
4. 편집기를 골랐으면 결과의 `handoff.ask_user` 문장을 그대로 물어본다. 파일 구조는 스크립트가 검증했지만 앱에서 실제로 열리는지는 이 하네스가 확인하지 않는다. 화면을 볼 수 있는 도구가 있는 에이전트라면 열어 볼 수 있지만, `status.handoff_verified_by_user`는 사용자의 확인으로만 기록한다. 답을 기록한다.

```
python3 "${SKILL_DIR}/scripts/config_tool.py" set "<ws>" status.handoff_verified_by_user true
```

열어 보지 않았거나 열리지 않았으면 `true`로 적지 않는다. 그대로 두고 "편집기에서 열리는지는 미확인"이라고 말한다.

5. 마지막 점검을 돌려 표를 보여 주고, "주의"·"문제" 항목의 조치 문장을 전한다.

```
python3 "${SKILL_DIR}/scripts/doctor.py" "<ws>"
```

6. 모아 둔 `manual` 체크리스트를 건넨다. `.env`에 채울 키가 있으면 여기서 알린다(값은 받지 않는다).
7. 3-1에서 "레퍼런스에서 뽑기"를 골랐고 레퍼런스 분석 스킬이 실제로 설치되었으면, 지금 이어서 레퍼런스를 분석할지 묻는다. 원하지 않거나 스킬이 없으면 레퍼런스는 "미분석"으로 남는다. 2단계 제작 절차 스킬은 아직 없으므로, 그 스킬이 나오기 전까지는 `watch` 모듈을 설치한 뒤 이 스킬을 다시 돌려 여기서 분석하는 것이 유일한 길이라고 알린다.

## 6. 채널 추가

이미 세팅된 작업 공간에 채널을 더할 때. 채널 질문(0 · 3 · 3-1 · 3-1a · 3-2)만 다시 묻는다. 모듈·규칙은 묻지 않는다. 여기서도 출발점을 **가장 먼저** 묻는다 — 채널마다 다를 수 있고, 이미 있는 채널의 답을 물려받지 않는다.

```
python3 "${SKILL_DIR}/scripts/config_tool.py" add-channel "<ws>" --name "새채널" --format 9:16 --workflow footage-first --target-seconds 45 --language ko
python3 "${SKILL_DIR}/scripts/scaffold.py" "<ws>" --channel <새 채널 id>
python3 "${SKILL_DIR}/scripts/smoke_test.py" "<ws>" --channel <새 채널 id>
```

기존 채널의 파일은 건드리지 않는다. 새 채널의 출발점이 `footage-first`나 `per-episode`인데 편집기 모듈이 없으면, 편집기를 추가할지 한 번 묻는다.

## 7. 기존 작업 공간 채택

설정 파일은 없는데 채널 폴더(`01_원본영상`이 들어 있는 폴더)나 `AGENTS.md`가 이미 있는 경우다. 하네스로 만들지 않은 작업 공간에도 새 채널을 추가할 수 있게 하기 위한 길이다.

먼저 무슨 일이 일어나는지 정확히 설명하고 동의를 받는다.

- 지금 있는 파일은 **하나도 고치지 않고 지우지도 않는다**. 찾은 채널 폴더를 설정에 등록만 한다.
- 다만 그다음 폴더 만들기 단계에서 **기존 채널 폴더 안에 새 문서와 폴더가 더해진다** — `채널기준.md`, `넣는_방법.md`, `03_편집프로젝트/_채널공용/`(`frame.md`와 회차 템플릿), `02_기획과자막/스타일레퍼런스/`(레퍼런스 목록), `04_완성영상/영상목록.md` 등이다. 같은 이름의 파일이 이미 있으면 건드리지 않고 넘어간다(덮어쓰지 않는다).
- 새로 더해지는 파일이 마음에 들지 않으면 지우면 된다. 기존 작업에는 영향이 없다.

채택 경로에서도 인터뷰 1·2단계(작업 공간 이름, 에이전트)를 먼저 묻는다. 에이전트를 묻지 않고 넘어가면 기본값(`claude`)이 그대로 들어가, Codex만 쓰는 사람의 작업 공간에도 `CLAUDE.md`가 놓인다.

```
python3 "${SKILL_DIR}/scripts/config_tool.py" init "<ws>" --name "내작업실" --agents <고른 값>
python3 "${SKILL_DIR}/scripts/scaffold.py" "<ws>" --adopt
```

`--adopt`는 등록만 한다. 설정 파일이 없으면 `--adopt`는 아무것도 만들지 않고 오류로 멈추므로 `init`을 반드시 먼저 실행한다. 폴더와 문서는 4절의 `scaffold.py "<ws>"`가 만든다. 멱등이라 이미 있는 파일은 그대로 두고 빠진 것만 채운다.

채택 결과에 등록된 채널 목록이 나온다. 출발점은 아예 비어 있고 포맷·유형·길이는 기본값(9:16 세로, 내레이션 쇼츠, 60초)으로 들어간다. 채널마다 0단계 질문을 하고, 포맷·길이도 맞는지 확인해 다르면 목록 번호로 고친다.

```
python3 "${SKILL_DIR}/scripts/config_tool.py" set "<ws>" channels.0.workflow footage-first
python3 "${SKILL_DIR}/scripts/config_tool.py" set "<ws>" channels.0.format '"16:9"'
python3 "${SKILL_DIR}/scripts/config_tool.py" set "<ws>" channels.0.kind '"longform-vlog"'
```

그다음 인터뷰의 4~9단계 중 **비어 있는 모듈만** 묻고, 4절의 설치와 5절의 스모크 테스트로 이어 간다. "비어 있는 모듈"은 설정값이 기본값 그대로인 모듈이다(렌더 엔진 `hyperframes`, 편집기 `none`, 목소리 `record`, 소재 `["own-footage"]`, Higgsfield 인증 `none`, 레퍼런스 분석 `false`). 9단계는 모듈이 아니라 작업 규칙이므로 항상 한 번 확인한다. 물어본 뒤에는 3절 요약·확인을 반드시 다시 거친다.

## 8. 재실행 메뉴

설정 파일이 이미 있으면 처음부터 묻지 않는다. 여섯 가지 중 하나를 고르게 한다.

| 고른 것 | 할 일 |
|---|---|
| 채널 추가 | 6절 |
| 채널 출발점 바꾸기 | 0단계 질문을 다시 하고 `config_tool.py set "<ws>" channels.N.workflow '"footage-first"'`로 덮어쓴다(`N`은 목록 번호). `채널기준.md`는 이미 만들어진 파일이라 스캐폴드가 덮어쓰지 않으므로, 그 파일의 "작업 순서" 절은 새 출발점에 맞게 손으로 고쳐 준다 |
| 모듈 추가·변경 | 해당 단계만 다시 묻고 `config_tool.py set`으로 덮어쓴 뒤, 그 모듈만 `install_module.py run`. 편집기를 바꾸면 이전 확인값이 자동으로 지워지므로 새 편집기로 다시 확인받는다 |
| 인터뷰 이어서 하기 | `config_tool.py show "<ws>"`로 지금까지의 답을 읽는다. `channels`가 비었으면 0단계(출발점)부터, 모듈 값이 기본값 그대로면 그 단계부터 다시 묻는다. 기본값을 의도적으로 고른 경우와 구분할 수 없으므로, 이어 가기 전에 지금 값을 한 화면으로 보여 주고 "이대로 둘지"를 먼저 확인한다 |
| 재점검 | `doctor.py "<ws>"`를 돌리고 표와 조치를 전한다 |
| 스모크 테스트 다시 | `smoke_test.py "<ws>"`(필요하면 `--channel`) |

"Higgsfield 추가" 같은 요청은 인터뷰 7단계(소재 수급)만 다시 타면 된다. 모듈을 바꾼 뒤에는 `scaffold.py "<ws>"`를 한 번 더 돌려 새 모듈의 도구를 `도구/`에 배치한다. 멱등이라 기존 파일을 덮어쓰지 않으므로 다시 돌려도 안전하다.

## 9. 말하는 법

- 한국어로, 쉬운 말로 쓴다. 전문 용어는 꼭 필요할 때만 쓰고 쓸 때는 한 줄 설명을 붙인다.
- 통과하지 않은 것을 완료라고 하지 않는다. "세팅 완료"의 기준은 5절 1번에 한 번만 정의해 두었다 — 스모크 테스트 `passed: true`이고 doctor에 `문제` 항목이 없는 것.
- 직접 확인하지 못한 것은 "미확인"이라고 말한다. 소리가 제대로 들리는지는 에이전트가 들을 수 없으니 사람이 들어 봐야 한다. 편집기 앱에서 파일이 실제로 열리는지, Windows·Linux·Intel Mac에서 잘 도는지는 이 하네스가 확인하지 않는다. 화면을 볼 수 있는 도구가 있는 에이전트라면 편집기를 열어 볼 수 있지만, `status.handoff_verified_by_user`는 사용자의 확인으로만 기록한다.
- 시스템 도구를 설치하거나 에이전트의 스킬 폴더를 바꾸는 명령은 실행 전에 명령 그대로 보여 주고 확인을 받는다.
- 비밀값은 받지도 출력하지도 않는다. 키가 필요하면 `.env`에 직접 채우게 하고 채워졌는지만 확인한다.
- 실패를 감추지 않는다. 실패한 모듈, 이유, 재시도 명령을 그대로 알린다.
- 긴 JSON을 그대로 붙여넣지 않는다. 필요한 값만 옮긴다.

## 10. 참고 문서

`${SKILL_DIR}/references/` 아래에 있다. 해당하는 선택을 했을 때만 읽는다.

| 문서 | 언제 읽나 |
|---|---|
| `workflows.md` | 0단계 출발점을 묻거나, 사용자가 두 흐름 중 어느 쪽인지 헷갈려 할 때 |
| `module-hyperframes.md` | 렌더 엔진으로 HyperFrames를 골랐을 때 |
| `module-remotion.md` | 렌더 엔진으로 Remotion을 골랐을 때(라이선스 안내 포함) |
| `module-handoff-capcut.md` | 편집기로 CapCut을 골랐을 때 |
| `module-handoff-premiere.md` | 편집기로 Premiere Pro를 골랐을 때 |
| `module-voice-local-mlx.md` | 목소리를 로컬 복제로 골랐을 때(Apple Silicon 전용) |
| `module-voice-cloud.md` | 목소리를 클라우드 TTS로 골랐을 때 |
| `module-voice-record.md` | 목소리를 직접 녹음·원음으로 골랐을 때 |
| `module-transcribe.md` | 전사 단계를 설명하거나 모델을 바꿀 때 |
| `module-stock.md` | 소재 수급에 무료 스톡을 골랐을 때 |
| `module-higgsfield.md` | 소재 수급에 Higgsfield를 골랐을 때(인증·크레딧) |
| `module-watch.md` | 레퍼런스 분석 스킬을 설치하거나 3-1a로 레퍼런스를 모을 때 |
| `style-system.md` | 3-1·3-2에서 스타일과 일관성을 설명할 때, `frame.md`를 설명할 때 |
| `script-rhythm.md` | 9단계에서 대본 운율을 설명할 때, 작업 공간에 놓일 대본 규칙을 확인할 때 |
| `pitfalls.md` | 설치나 렌더가 실패했을 때. 증상 → 원인 → 해결로 정리되어 있다 |
