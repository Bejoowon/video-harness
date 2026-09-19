# 회차 템플릿(Remotion) — BRIEF

이 폴더는 채널마다 새 회차를 만들 때 복사해 쓰는 Remotion 시작 프로젝트다.
색·글꼴·크기·위치·모션 값은 전부 `src/theme.ts`(채널 `frame.md`에서
`도구/style/build_tokens.py --ts`로 생성)에서 온다 — 컴포넌트 파일(`src/Episode.tsx`,
`src/parts/*.tsx`)을 채널마다 고치지 않는다.

## 컴포지션

- id: `Episode` (`src/Root.tsx`에 등록)
- props: `{title: string, caption: string, source: string, narration: string | null, durationInSeconds: number}`
- 길이는 `calculateMetadata`가 `durationInSeconds * theme.canvas.fps`로 계산한다.
- 해상도·fps는 `theme.canvas.width/height/fps`에서 온다(기본 1080×1920, 30fps).

## 자리(슬롯)

- `title` — 상단 제목(`src/parts/TitleBar.tsx`)
- `caption` — 하단 중앙 자막, 외곽선 포함(`src/parts/Caption.tsx`)
- `source` — 우하단 출처 표기(`src/parts/SourceLabel.tsx`)
- 배경(footage) — `src/Episode.tsx`의 전체화면 `AbsoluteFill`. 지금은 `theme.colors.bg` 단색이고, 실제 촬영본을 쓰려면 이 자리를 `@remotion/media`의 `<Video>`로 바꾼다.
- `narration` — 내레이션 오디오 파일명(`public/` 아래). `null`이면 오디오 없이 렌더한다. 채워지면 `staticFile(narration)`으로 찾는다.

## 렌더 전에 반드시 해야 할 일

**`public/narration.wav`는 이 템플릿에 들어 있지 않다.** 저장소 `.gitignore`와
이 템플릿의 `.gitignore`가 오디오·영상 파일을 무시하고, 실제 음성은 이 설치
스킬의 스크립트(`smoke_test.py` 등)가 채워 넣기 때문이다. `narration` prop에 파일명을
넣어 렌더하려면 그 전에 파일을 `public/`에 먼저 넣는다.

## 이징(easing)

`theme.ts`의 `motion.inEase`/`motion.outEase`는 GSAP 스타일 이름(`power3.out`
등)이다. Remotion에는 그 이름이 없으므로 `src/parts/easing.ts`의
`toEasing(name)`이 Remotion `Easing` 함수로 바꿔 준다(`power1~4.in/out/inOut`
→ `Easing.in/out/inOut(Easing.poly(n+1))`, `none`/`linear` → `Easing.linear`,
그 외 → `Easing.out(Easing.cubic)`).

## 폰트

`public/넣는_방법.md`를 읽는다. 프로젝트 폰트 파일이 없으면 설치된 한글 시스템
폰트로 자동 대체된다.

## 렌더하는 법

```bash
npm install --no-audit --no-fund
npx remotion render src/index.ts Episode out/episode.mp4 --props=./props.json
```

`props.json` 예:

```json
{
  "title": "제목",
  "caption": "자막 한 줄",
  "source": "출처",
  "narration": "narration.wav",
  "durationInSeconds": 12
}
```

미리보기(스튜디오)는 `npx remotion studio`.

## 고정 버전

- `remotion` / `@remotion/cli` / `@remotion/media` 모두 `4.0.526` (캐럿 없이 고정)
- React `19.2.3`, TypeScript `5.9.3` (같은 Remotion 버전의 공식 blank 템플릿과 동일)

## 라이선스 — 반드시 읽을 것

Remotion은 오픈소스지만 무료 사용 범위가 있다. 개인, 직원 3명 이하의 영리
법인, 비영리 단체는 무료로 쓸 수 있고, 그보다 큰 영리 법인은 유료 Company
License가 필요하다(정확한 조건과 가격은 공식 라이선스 문서를 따른다):
https://www.remotion.dev/license
