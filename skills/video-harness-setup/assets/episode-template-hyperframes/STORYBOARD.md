# 회차 템플릿 — STORYBOARD

10초 기본 구성. 회차마다 이 표의 내용만 바꾸고 레이아웃(트랙 순서, 위치, 모션)은 그대로 둔다.

| 트랙 | 요소 | 구간 | 내용 |
| --- | --- | --- | --- |
| 0 | `#footage` | 0.0s – 10.0s | 배경 이미지/영상 (기본값: `assets/footage-placeholder.png`) |
| 2 | `#title-text` | 0.0s – 10.0s | 제목. 0.1s에 위에서 아래로 들어오는 진입 모션 |
| 3 | `#caption-text` | 0.4s – 10.0s | 자막 한 줄. 0.4s에 아래에서 위로 들어오는 진입 모션 |
| 4 | `#source-text` | 0.0s – 10.0s | 출처 표기 (우하단 고정) |
| — | `#narration` | 0.0s ~ | 음성. 실제 길이에 맞춰 루트 `data-duration`을 다시 쓴다 |

## 하지 말 것

- 트랙(`data-track-index`)이나 클립 요소(`class="clip"`)의 `opacity`/`autoAlpha`를 직접 트윈하지 않는다 — 자식 텍스트 요소만 애니메이션한다.
- 색·글꼴·크기·위치·모션 시간값을 `index.html`에 직접 쓰지 않는다 — 전부 `tokens.css`의 `var(--...)`를 통해서만 쓴다.
- `#narration` 없이 `check`/`render`를 돌리지 않는다 (`BRIEF.md` 참고).
