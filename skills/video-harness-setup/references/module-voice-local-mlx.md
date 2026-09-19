# voice-local-mlx 모듈

## 무엇을 설치하나

- Apple Silicon 전용이다. 다른 플랫폼에서는 선택지에 나타나지 않는다.
- `<workspace>/도구/tts/.venv`라는 분리된 가상환경에 `mlx-audio==0.5.3`과 `numpy`를 설치한다.
- 모델 경로를 아직 모르면 Qwen3-TTS 1.7B 8bit 모델(`mlx-community/Qwen3-TTS-12Hz-1.7B-Base-8bit`)을 `<workspace>/도구/tts/models/Qwen3-TTS-12Hz-1.7B-Base-8bit/`로 백그라운드 다운로드한다.
- 마지막 단계는 수동 확인 항목이다: 참고 녹음 10~20초와 정확한 대본을 `<workspace>/도구/tts/녹음/`에 넣기(`녹음가이드.md` 참고, 스캐폴드 단계에서 이미 생성됨).
- `generate_local_mlx.py`·`postprocess.py` 도구가 `<workspace>/도구/tts/`에 함께 배치된다.

## 사용자에게 알릴 것

- 모델 다운로드 크기는 약 2.9GB다. 첫 실행에 시간이 걸린다.
- 로컬 목소리 복제는 Apple Silicon Mac에서만 동작한다.
- 이 기능은 목소리를 복제하는 기능이다. 참고 녹음은 본인 목소리이거나, 본인이 아니라면 그 사람의 동의를 받은 목소리여야 한다.
- 문단은 빈 줄 단위로 나눠 따로 생성한 뒤 이어 붙이고, 문단 사이에 인위적인 침묵을 넣지 않는다.
- TTS는 돌릴 때마다 톤이 조금씩 달라질 수 있다. 기준이 되는 참고 음성·생성 설정·후처리 값을 한 번 정하면 그대로 고정해서 쓴다(`pitfalls.md` 참고).

## 설치 뒤 확인

- `<workspace>/도구/tts/.venv`가 있고, `harness.config.json`의 `modules.voice.model_path`에 모델 경로가 기록됐는지 확인한다.
- `python3 "${SKILL_DIR}/scripts/doctor.py" "<workspace>" --json`으로 위 항목이 정상인지 본다.
- 참고 녹음 폴더에 오디오와 대본 txt가 모두 있어야 스모크 테스트가 실제 목소리로 생성한다. 없으면 신호음으로 대체되어 통과 여부만 확인되고 목소리는 확인되지 않는다.

## 자주 막히는 곳

- 모델 다운로드가 멈추면 `HF_HUB_DISABLE_XET=1`로 한 번 재시도한다. 자세한 내용은 `pitfalls.md`를 본다.
- `도구/tts/.venv`는 기존 파이썬 환경과 반드시 분리해서 쓴다. 이유는 `pitfalls.md`를 본다.
- 녹음 폴더에 `.DS_Store` 같은 잡파일이 섞이면 참고 음성·대본을 찾는 순서가 흐트러질 수 있다(`pitfalls.md` 참고).
- 에이전트는 소리를 듣지 못한다. 실제 목소리가 자연스러운지 청취 확인은 사람이 직접 한다.
