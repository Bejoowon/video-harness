# higgsfield 모듈

## 무엇을 설치하나

인증 방식에 따라 설치 내용이 다르다.

- **구독 계정 방식**(`account`): 세 가지 모두 수동 확인 항목이다 — `npx skills add higgsfield-ai/skills` 설치 안내, `npm install -g @higgsfield/cli` 설치 안내, `higgsfield auth login` 로그인 안내.
- **API 키 방식**(`api-key`): `<workspace>/도구/.venv`에 `higgsfield-client`를 설치하고, `.env`에 `HF_KEY`를 `KEY_ID:KEY_SECRET` 형식으로 채우라는 수동 확인 항목이 붙는다.
- 인증 방식을 아직 정하지 않았으면 설치 없이 "인증 방식을 선택하라"는 안내만 남는다.
- 어떤 방식이든 마지막에 크레딧 관련 안내가 항상 붙는다.
- 생성물은 `<채널>/01_원본영상/<작업명>/ai생성/`에 두고, 프롬프트·모델·비용을 `출처와제작기록.md`/`provenance.json`에 기록한다.

## 사용자에게 알릴 것

세팅 중 아래 네 가지를 반드시 표시한다.

1. 웹 구독의 Unlimited 혜택은 MCP·CLI·API 어디에도 적용되지 않고 항상 크레딧이 차감된다.
2. 모델별 9:16 지원·길이·오디오는 `higgsfield model get <모델>`로 세팅 시점에 조회한다.
3. 웹앱 브라우저 자동화와 크레딧 우회형 커뮤니티 MCP는 약관 위반 소지가 있어 금지한다.
4. 실존 인물의 얼굴·음성은 본인 동의가 필요하다.

추가로: API 키 방식은 사용한 만큼 비용이 청구되는 유료 서비스다. 정확한 단가는 콘솔에서 그때그때 확인한다.

## 설치 뒤 확인

- **구독 계정 방식**: `higgsfield auth login`은 브라우저 로그인이라 스크립트가 완료 여부를 확인할 수 없다. 로그인을 마쳤는지 사용자에게 직접 확인받는다. `doctor.py`도 이 방식에 대해서는 디스크 흔적이 없어 항목을 만들지 않는다.
- **API 키 방식**: `python3 "${SKILL_DIR}/scripts/doctor.py" "<workspace>" --json`으로 `.env`의 `HF_KEY` 값이 채워졌는지(값 자체는 출력하지 않는다) 확인한다. `<workspace>/도구/.venv` 존재는 `tools-venv` 모듈의 흔적으로 같은 점검에 나오지만, 이는 공유 가상환경 자체의 존재만 보는 것이라 `higgsfield-client`가 실제로 그 안에 설치됐는지까지 확인하려면 그 가상환경 파이썬으로 `import higgsfield_client`를 직접 해 본다.

## 자주 막히는 곳

- 인증 방식을 아직 못 정한 채로 넘어가면 설치가 안내 문구만 남기고 끝난다. 방식을 정한 뒤 `python3 "${SKILL_DIR}/scripts/install_module.py" run "<workspace>" higgsfield`를 다시 실행한다.
- 모델마다 9:16 지원·길이·오디오 지원 여부가 다르고 시점에 따라 바뀔 수 있다. 조사 시점 자료를 그대로 믿지 말고 세팅 시점에 다시 조회한다.
- 실존 인물이 나오는 생성물을 만들 때는 동의를 확인하지 않은 채 진행하지 않는다.
