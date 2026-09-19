# remotion 모듈

## 무엇을 설치하나

- 채널마다 이미 배치된 Remotion 시작 프로젝트(`<채널>/03_편집프로젝트/_채널공용/회차템플릿-remotion/`, 스캐폴드 단계에서 복사됨) 안에서 `npm install --no-audit --no-fund`를 실행한다. 채널이 여러 개면 채널마다 한 번씩 실행한다.
- 마지막 단계는 수동 확인 항목이다: `npx skills add remotion-dev/skills` 설치 안내.
- 렌더에 쓰는 색·글꼴·크기·위치·모션 값은 채널 `frame.md`에서 `build_tokens.py --ts`로 생성한 `src/theme.ts` 하나에 모인다. 컴포넌트 파일(`src/Episode.tsx`, `src/parts/*.tsx`)은 채널마다 고치지 않는다.

## 사용자에게 알릴 것

- 버전 고정: `remotion`/`@remotion/cli`/`@remotion/media` 모두 `4.0.526`, React `19.2.3`, TypeScript `5.9.3`.
- Remotion은 오픈소스이지만 무료 범위가 있다. 개인, 직원 3명 이하 영리 법인, 비영리 단체는 무료이고, 그보다 큰 영리 법인은 유료 Company License가 필요하다. 정확한 조건과 가격은 공식 문서를 확인한다: https://www.remotion.dev/license
- `public/narration.wav`는 템플릿에 들어 있지 않다(저장소가 오디오 파일을 무시한다). 실제 음성을 먼저 `public/`에 넣은 뒤에 렌더한다.
- `motion.inEase`/`motion.outEase`는 GSAP 이름(`power3.out` 등)으로 적혀 있고, `src/parts/easing.ts`가 Remotion의 `Easing` 함수로 자동 변환한다.

## 설치 뒤 확인

- 회차템플릿-remotion 폴더 안에 `node_modules`가 생겼는지 확인한다.
- 다만 스모크 테스트는 이 `node_modules`를 쓰지 않는다. 회차템플릿을 스크래치 폴더로 복사할 때 `node_modules`를 빼고 복사하므로(수백 MB를 복사하지 않으려는 의도적인 선택), 스모크는 복사본 안에서 `npm install`을 매번 새로 돌린다. 그래서 Remotion 스모크는 몇 분이 걸릴 수 있고 인터넷이 필요하다. 사용자에게 미리 알린다.
- doctor.py는 remotion 설치 자체를 따로 점검하는 항목을 두지 않는다. 실제 확인은 스모크 테스트로 한다: `python3 "${SKILL_DIR}/scripts/smoke_test.py" "<workspace>" --engine remotion`이 렌더까지 끝내고 ffprobe로 해상도·길이·오디오를 검증한다.

## 자주 막히는 곳

- `npm install`이 네트워크 오류로 실패하면 다시 실행한다.
- 회차템플릿-remotion 폴더 자체가 없으면(아직 스캐폴드하지 않은 채널) `python3 "${SKILL_DIR}/scripts/scaffold.py" "<workspace>" --channel <채널id>`를 먼저 실행한다.
- 프로젝트 폴더에 폰트 파일이 없으면 설치된 한글 시스템 폰트로 자동 대체된다(`public/넣는_방법.md` 참고).
- HDR/H.265 원본을 배경으로 쓰면 색이 틀어져 보일 수 있다. `pitfalls.md`를 본다.
