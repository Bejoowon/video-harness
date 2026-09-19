# voice-cloud 모듈

## 무엇을 설치하나

- `<workspace>/도구/tts/.venv` 가상환경을 만든다(추가 패키지는 없다 — ElevenLabs 호출은 표준 라이브러리 HTTP만으로 구현되어 있다).
- `generate_cloud.py`·`postprocess.py` 도구가 `<workspace>/도구/tts/`에 함께 배치된다.
- 마지막 단계는 수동 확인 항목이다: `.env`에 `ELEVENLABS_API_KEY`를 직접 채우기.

## 사용자에게 알릴 것

- 기준 구현으로 ElevenLabs를 쓴다. 목소리 복제와 한국어를 지원하는지 공식 문서로 확인했다(`eleven_multilingual_v2` 모델이 한국어를 포함한 29개 언어를 지원한다).
- **이 하네스에서는 실제 API 호출을 검증하지 않았다.** 공식 문서를 바탕으로 구현했을 뿐이므로, 처음 쓸 때는 결과를 직접 확인한다.
- ElevenLabs는 유료 API다. 사용한 만큼 비용이 발생한다.
- API 키는 이 스킬이 받지 않는다. 사용자가 `.env`에 직접 채워 넣고, 채팅으로는 붙여넣지 않는다.
- 목소리 복제 기능을 쓰려면 그 목소리의 주인에게 동의를 받아야 한다.

## 설치 뒤 확인

- `python3 "${SKILL_DIR}/scripts/doctor.py" "<workspace>" --json`으로 `ELEVENLABS_API_KEY` 항목이 채워졌는지 확인한다(값 자체는 출력하지 않는다).
- 실제 생성 확인은 `<workspace>/도구/tts/.venv`의 파이썬으로 `generate_cloud.py --voice-id <id> --text <대본.txt> --output <출력.wav>`를 한 번 실행해 파일이 만들어지는지 본다.

## 자주 막히는 곳

- `.env`에 키가 없으면 곧바로 오류로 멈춘다. `.env`부터 확인한다.
- `--output` 확장자는 `.mp3` 또는 `.wav`만 지원한다.
- 출력 경로에 파일이 이미 있으면 실행이 실패한다(덮어쓰지 않는다). 다른 이름으로 다시 실행한다.
- 에이전트는 소리를 듣지 못한다. 생성된 목소리가 자연스러운지 청취 확인은 사람이 직접 한다.
