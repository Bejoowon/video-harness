# handoff-premiere 모듈

## 무엇을 설치하나

- `install_module.py run "<workspace>" handoff-premiere`를 실행하면 그 안에서 `preflight.py "<workspace>" --json`을 호출해 Premiere Pro 설치 여부를 감지한다(CapCut/Premiere 감지는 두 모듈이 공유하는 한 단계다). 감지 결과를 `harness.config.json`에 기록하는 것은 `install_module.py` 쪽이고, `preflight.py` 자신은 config를 건드리지 않는다. 추가로 설치하는 패키지는 없다.
- `handoff_common.py`·`to_premiere_xml.py` 도구가 `<workspace>/도구/export/`에 배치된다.

## 사용자에게 알릴 것

- Premiere Pro 앱이 없으면 자동으로 설치하지 않는다. 설치 여부만 확인한다.
- 넘기는 형식은 FCP7 XML(시퀀스·컷·오디오 트랙) + `.srt`다. Premiere에서 `파일 > 가져오기`로 XML을 가져온 뒤, SRT도 같은 방법으로 가져와 캡션 트랙으로 붙인다.
- 원본 영상 파일 경로가 바뀌었으면 Premiere가 "미디어 찾기" 대화상자를 띄운다.
- 넘기기는 단방향이다. 넘긴 뒤에는 Premiere 프로젝트가 원본이 되고, 이후 Premiere에서 바뀐 내용은 이 하네스로 되읽지 않는다.
- FCP7 XML은 오래된 표준 교환 형식이라 위험이 낮다. 실제로 이 방식으로 XML을 Premiere에서 열고 재생까지 확인한 사례가 있다.

## 설치 뒤 확인

- `python3 "${SKILL_DIR}/scripts/doctor.py" "<workspace>" --json`에서 `handoff.premiere 감지` 항목이 정상인지 확인한다. 감지를 아직 실행하지 않았으면 주의로 표시된다.
- 편집기로 Premiere를 골랐으면 스모크 테스트가 컷 2개·자막 1줄·음성 1트랙짜리 미니 프로젝트를 XML/SRT로 만들어 `<workspace>/도구/logs/smoke/<시각>/handoff/`에 남긴다. 파일 구조(XML 파싱, 참조 미디어 존재)는 스크립트가 검증하지만, Premiere에서 실제로 열리는지는 사용자에게 직접 확인받아야 한다.

## 자주 막히는 곳

- Premiere Pro가 설치되어 있지 않으면 감지 단계는 "설치되어 있지 않다"는 안내만 남기고 넘어간다. 설치한 뒤 감지를 다시 실행한다.
- 시퀀스 길이는 비디오·오버레이·오디오 트랙 중 가장 늦게 끝나는 클립을 기준으로 계산된다. 내레이션이 마지막 영상 컷보다 길면 시퀀스도 그만큼 길어진다.
- 회차 폴더 안에서 넘기기 명령을 실행하면 결과 폴더가 흩어진다. 항상 작업 공간 루트에서 실행한다.
