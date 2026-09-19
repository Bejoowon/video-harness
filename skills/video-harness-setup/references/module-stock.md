# stock 모듈

## 무엇을 설치하나

- 설치할 패키지는 없다. `search.py` 도구가 `<workspace>/도구/stock/`에 배치된다.
- 마지막 단계는 수동 확인 항목이다: `.env`에 `PEXELS_API_KEY`(선택)를 채우기. 없으면 Wikimedia Commons만 검색한다.
- Wikimedia Commons는 키가 필요 없고, 대신 요청마다 작업 공간 이름이 들어간 User-Agent(`video-harness/1.0 (<workspace 이름>)`)를 보낸다.

## 사용자에게 알릴 것

- **Pexels 쪽 실제 API 호출은 이 프로젝트에서 검증하지 않았다.** 공식 문서를 바탕으로 구현했다.
- Pexels 영상은 Pexels License를 따른다. Wikimedia 결과는 파일마다 라이선스가 다르므로(`LicenseShortName`으로 확인) 저작자 표기가 필요할 수 있다.
- `search.py`는 검색 결과만 보여주고 아무것도 내려받지 않는다. 사용자가 승인한 항목만 별도로 내려받는다.
- 내려받은 자료는 반드시 출처와 라이선스를 `출처와제작기록.md`·`provenance.json`에 기록한다.

## 설치 뒤 확인

- `<workspace>/도구/stock/search.py`가 있는지 확인한다. `python3 "${SKILL_DIR}/scripts/doctor.py" "<workspace>" --json`에서도 같은 항목을 볼 수 있다.
- 실제 검색 확인: `python3 "<workspace>/도구/stock/search.py" "검색어" --workspace-name <이름>`을 실행해 JSON 결과가 나오는지 본다(네트워크 필요).

## 자주 막히는 곳

- `PEXELS_API_KEY` 없이 `--source pexels`로 명시하면 오류가 난다. `--source all`(기본값)이면 Pexels만 건너뛰고 Wikimedia 결과는 그대로 준다.
- Wikimedia 결과 중 정지 이미지는 `duration`이 항상 비어 있다(영상이 아니라서다).
- 출처 기록을 빼먹으면 나중에 어떤 파일이 어떤 라이선스인지 알 수 없게 된다. 검색 직후에 바로 기록한다.
