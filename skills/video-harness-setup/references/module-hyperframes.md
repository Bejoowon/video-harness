# hyperframes 모듈

## 무엇을 설치하나

- 버전은 `0.8.43`으로 고정한다. 모든 명령이 `npx --yes hyperframes@0.8.43 ...` 형태다.
- 순서대로: 헤드리스 크롬 준비(`browser ensure`) → 브라우저 경로 확인(`browser path`, 결과를 `<workspace>/도구/chrome-path.txt`에 저장) → `doctor --json`.
- 마지막 단계는 수동 확인 항목이다: `npx --yes hyperframes@0.8.43 skills` 설치 안내. 에이전트의 스킬 폴더를 바꾸는 작업이라 사용자에게 확인받은 뒤에만 실행한다.
- 채널을 만들 때(스캐폴드 단계, 이 모듈과 별개) `<채널>/03_편집프로젝트/_채널공용/회차템플릿/`에 시작 프로젝트가 복사되고, `<workspace>/도구/chrome-noaudio.py`(오디오 출력 끄는 크롬 래퍼)가 함께 배치된다.

## 사용자에게 알릴 것

- HyperFrames `0.8.43`, GSAP `3.14.2`로 버전을 고정한다. GSAP은 CDN이 아니라 템플릿에 파일로 동봉되어 있다.
- 기준 해상도는 쇼츠 1080×1920, 롱폼 1920×1080, 모두 30fps다.
- 헤드리스 크롬을 처음 준비할 때 내려받는 시간이 걸릴 수 있다.
- 스킬 설치 단계는 에이전트의 스킬 폴더 자체를 바꾸므로, 먼저 사용자에게 실행해도 되는지 확인한 뒤에만 명령을 실행한다.

## 설치 뒤 확인

- `<workspace>/도구/chrome-path.txt` 파일이 있고 내용이 실제 크롬 실행 파일 경로인지 확인한다.
- `python3 "${SKILL_DIR}/scripts/doctor.py" "<workspace>" --json`을 실행해 `도구/chrome-path.txt` 항목이 정상인지 본다.
- 최종 증명은 스모크 테스트다: `python3 "${SKILL_DIR}/scripts/smoke_test.py" "<workspace>"`가 실제로 10초 세로 영상을 렌더해 해상도·길이·오디오까지 검증한다.

## 자주 막히는 곳

- 렌더가 "Navigation timeout"으로 멈추면 macOS 기본 오디오 출력 장치부터 의심한다. 원인과 해결(`chrome-noaudio.py` 래퍼, 필요한 환경변수)은 `pitfalls.md`에 있다.
- HDR/H.265로 찍힌 원본을 배경으로 쓰면 색이 틀어져 보일 수 있다. `pitfalls.md`를 본다.
- transform 속성이 있는 SVG `<g>`에 직접 GSAP 트윈을 걸면 값이 덮어써진다. `pitfalls.md`를 본다.
- `hyperframes preview` 서버나 `chrome-headless-shell` 프로세스가 남아 다음 렌더를 방해할 수 있다. `pitfalls.md`의 정리 방법을 따른다.
- 회차 폴더 안에서 명령을 실행하면 상태 폴더가 흩어진다. 명령은 항상 작업 공간 루트에서 실행한다.
