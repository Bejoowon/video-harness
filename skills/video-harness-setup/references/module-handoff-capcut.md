# handoff-capcut 모듈

## 무엇을 설치하나

- `install_module.py run "<workspace>" handoff-capcut`을 실행하면 그 안에서 `preflight.py "<workspace>" --json`을 호출해 CapCut 설치 여부·버전·초안 폴더를 감지한다(CapCut/Premiere 감지는 두 모듈이 공유하는 한 단계다). 감지 결과를 `harness.config.json`에 기록하는 것은 `install_module.py` 쪽이고, `preflight.py` 자신은 config를 건드리지 않는다.
- `<workspace>/도구/.venv`에 `pycapcut==0.0.3`(고정 버전)은 `tools-venv` 모듈이 설치한다(핸드오프 편집기로 CapCut을 골랐을 때 패키지 목록에 자동으로 들어간다). `to_capcut.py`의 JSON 보정(`fix_text_style_ranges`, `fix_text_refs`)이 이 버전을 대상으로 작성·검증되어 있어서 버전을 고정한다.
- `handoff_common.py`·`to_capcut.py` 도구가 `<workspace>/도구/export/`에 배치된다.
- 초안 폴더 위치: macOS는 `~/Movies/CapCut/User Data/Projects/com.lveditor.draft`, Windows는 `%LOCALAPPDATA%\CapCut\User Data\Projects\com.lveditor.draft`.

## 사용자에게 알릴 것

- CapCut 앱이 없으면 자동으로 설치하지 않는다. 설치 링크만 안내한다.
- `pycapcut`이 만드는 초안 파일은 `draft_content.json`이다. 반면 macOS의 CapCut 앱이 직접 만드는 초안은 `draft_info.json`이라는 다른 이름을 쓴다.
- **이 하네스가 만든 초안을 CapCut 9.4.0(macOS)이 실제로 여는지는 이 문서를 쓰는 시점 기준으로 실기 확인 대기 상태다.** 열린다고 단정하지 않는다.
- `pycapcut`을 쓸 수 없거나 초안이 안 열리더라도, SRT + 컷 목록 + 가져오는 방법(수동 묶음)은 항상 만들어지는 안전한 대안이다.
- 넘기기는 단방향이다. 넘긴 뒤에는 CapCut 프로젝트가 원본이 되고, 이후 CapCut에서 바뀐 내용은 이 하네스로 되읽지 않는다.

## 설치 뒤 확인

- `python3 "${SKILL_DIR}/scripts/doctor.py" "<workspace>" --json`에서 `handoff.capcut 감지` 항목이 정상인지 확인한다. 감지를 아직 실행하지 않았으면 주의로 표시된다.
- 같은 점검의 `CapCut 버전` 항목은 이 하네스에서 검증된 버전이 아직 없어 항상 "검증된 버전이 없다"는 주의를 낸다. 이는 오류가 아니다.
- 편집기로 CapCut을 골랐으면 스모크 테스트가 컷 2개·자막 1줄·음성 1트랙짜리 미니 프로젝트를 만들어 `<workspace>/도구/logs/smoke/<시각>/handoff/`에 남긴다. 파일 구조(JSON 파싱, 참조 미디어 존재)는 스크립트가 검증하지만, CapCut 앱에서 실제로 열리는지는 사용자에게 직접 확인받아야 한다.

## 자주 막히는 곳

- `도구/.venv`에 `pycapcut`이 없으면 초안 생성은 건너뛰고 수동 묶음만 만든다. 이는 오류가 아니라 정해진 대체 경로다.
- CapCut 앱이 업데이트되면 초안 형식이 바뀔 수 있다. 감지된 버전이 검증된 버전과 다르면 doctor가 경고한다.
- macOS 실제 CapCut 초안 폴더의 파일명(`draft_info.json`)과 `pycapcut` 출력 파일명(`draft_content.json`)을 혼동하지 않는다(`pitfalls.md` 참고).
