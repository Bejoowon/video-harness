# transcribe 모듈

## 무엇을 설치하나

- 엔진은 플랫폼으로 자동 결정된다. Apple Silicon은 `<workspace>/도구/transcribe/.venv`에 `mlx-whisper`를, 그 외(Windows·Intel Mac·Linux)는 `faster-whisper`를 설치한다. CUDA가 있으면 GPU를, 없으면 CPU를 자동으로 쓴다.
- `transcribe.py` 도구는 모듈 선택과 무관하게 스캐폴드 단계에서 항상 `<workspace>/도구/transcribe/`에 배치된다.
- 기본 모델은 `large-v3-turbo`다. mlx-whisper는 `mlx-community/whisper-large-v3-turbo`로, faster-whisper는 이름 그대로(`mobiuslabsgmbh/faster-whisper-large-v3-turbo`로 내부 매핑) 받는다.

## 사용자에게 알릴 것

- 첫 실행 때 모델을 내려받느라 시간이 걸릴 수 있다.
- 결과는 JSON(전체 텍스트 + 구간 + 단어 단위 타임스탬프)으로 저장되고, 원하면 SRT도 함께 만든다.
- 언어 기본값은 한국어(`ko`)다.
- 인터뷰 6단계에서 고른 모델은 `harness.config.json`의 `modules.transcribe.model`에, 엔진은 `modules.transcribe.engine`에 기록된다. **이 값은 실행할 때 직접 넘겨야 적용된다** — `transcribe.py`는 설정 파일을 읽지 않는다(작업 공간 도구는 세팅 스크립트를 임포트하지 않는다는 규칙 때문이다).

## 설치 뒤 확인

- `<workspace>/도구/transcribe/.venv`가 있는지 확인한다. `python3 "${SKILL_DIR}/scripts/doctor.py" "<workspace>" --json`으로도 같은 항목을 볼 수 있다.
- 실제 전사 확인은 가상환경 파이썬으로 `transcribe.py <오디오파일> --out <출력.json> --engine <설정의 modules.transcribe.engine> --model <설정의 modules.transcribe.model>`을 한 번 실행해 파일이 만들어지는지 본다. 설정값을 빼먹으면 도구 기본값(`auto` / `large-v3-turbo`)으로 돌아가므로, 사용자가 다른 모델을 골랐다면 확인 자체가 무의미해진다.

## 자주 막히는 곳

- 출력 파일(`--out`, `--srt`)이 이미 있으면 실행이 실패한다(덮어쓰지 않는다). 다른 이름으로 다시 실행한다.
- Apple Silicon이 아닌 곳에서 `--engine mlx-whisper`를 강제로 지정하면 오류가 난다. `--engine auto`(기본값)를 쓴다.
- 모델 다운로드가 멈추면 `HF_HUB_DISABLE_XET=1`로 한 번 재시도한다(`pitfalls.md` 참고).
- 회차 폴더 안에서 명령을 실행하면 로그와 결과 폴더가 흩어진다. 항상 작업 공간 루트에서 실행한다.
