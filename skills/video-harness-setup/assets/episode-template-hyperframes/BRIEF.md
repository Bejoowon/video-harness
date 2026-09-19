# 회차 템플릿 — BRIEF

이 폴더는 채널마다 새 회차를 만들 때 복사해 쓰는 HyperFrames 시작 프로젝트다. 색·글꼴·크기·위치·모션 값은 전부 `tokens.css`(채널 `frame.md`에서 생성)에서 온다 — `index.html`을 채널마다 고치지 않는다.

## 렌더 전에 반드시 해야 할 일

**`assets/narration.wav`는 이 템플릿에 들어 있지 않다.** 저장소 `.gitignore`가 `*.wav`를 무시하고, 실제 음성은 이 설치 스킬의 스크립트(`smoke_test.py` 등)가 채워 넣기 때문이다. 이 폴더를 그대로 복사해서 `hyperframes check`나 `render`를 돌리면 `#narration` 오디오 소스가 없어서 실패한다 — **음성 파일을 `assets/narration.wav`에 먼저 넣은 뒤에** check/render를 실행한다.

## 치환 지점 (data-slot)

주석이 아니라 `id` 속성으로 표시한다. 이 설치 스킬의 `smoke_test.py`가 이 id를 그대로 찾는다.

- `#title-text` — 제목
- `#caption-text` — 자막 한 줄
- `#source-text` — 출처 표기
- `#footage` — 배경 이미지/영상 자리 (기본은 `assets/footage-placeholder.png`)
- `#narration` — 오디오(`<audio>`)

루트 `<div id="root">`는 `data-composition-id="main"`이고, `data-duration`은 `smoke_test`가 실제 음성 길이에 맞춰 다시 쓴다.

## 폰트

`assets/fonts/넣는_방법.md`를 읽는다. 프로젝트 폰트 파일이 없으면 설치된 한글 시스템 폰트로 자동 대체된다.

## 고정 버전

- HyperFrames `0.8.43` (`package.json`의 모든 스크립트가 `npx --yes hyperframes@0.8.43 ...`)
- GSAP `3.14.2` (`assets/gsap.min.js`로 동봉, CDN을 쓰지 않는다)

## macOS에서 "Navigation timeout"이 나면

기본 오디오 출력 장치가 USB 마이크 등 출력 불가 장치로 잡혀 있으면 헤드리스 크롬의 WebAudio 초기화가 멈춘다. `도구/chrome-noaudio.py`(오디오 출력을 끄는 크롬 래퍼)를 쓴다.

```
HARNESS_CHROME=$(npx --yes hyperframes@0.8.43 browser path)
HYPERFRAMES_BROWSER_PATH=<이 작업 공간의 chrome-noaudio.py 절대경로>
```

두 환경변수를 설정하고 `check`/`render`를 다시 실행한다.
