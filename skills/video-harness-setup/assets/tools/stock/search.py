#!/usr/bin/env python3
"""무료 스톡 영상·이미지 검색 (Pexels 비디오, Wikimedia Commons). 표준 라이브러리만 쓴다.

이 도구는 작업 공간 `도구/stock/`에 복사되어 실행된다. 결과 JSON 목록만 출력하며
아무것도 내려받지 않는다 — 검색 결과를 보여주고 사용자가 승인한 뒤에만 에이전트가
내려받기를 별도로 수행한다(AGENTS.md 규칙).

공식 문서 확인 결과(2026-09-19):
- Pexels 비디오 검색 — https://www.pexels.com/api/documentation/
  문서 제목: "GET https://api.pexels.com/v1/videos/search"
  같은 페이지에 "The https://api.pexels.com/videos/ endpoints will be deprecated
  in the future, please update your code to use the new path."라고 명시되어 있어
  v1 없는 옛 경로 대신 v1 경로를 쓴다.
  인증: Authorization 헤더에 키를 그대로 넣는다(스킴 접두어 없음).
  파라미터: query(필수), orientation(landscape|portrait|square), per_page(기본 15, 최대 80).
  응답: videos[].id/.url(페이지)/.duration/.user.name, videos[].video_files[].{link,width,height}.
- Wikimedia Commons 검색 — https://www.mediawiki.org/wiki/API:Search (generator=search),
  https://www.mediawiki.org/wiki/API:Imageinfo (prop=imageinfo, iiprop=url|size|mime|extmetadata)
  파일 이름공간은 6번(gsrnamespace=6). extmetadata 안의 LicenseShortName·Artist 값을 쓴다.
  User-Agent 정책 — https://foundation.wikimedia.org/wiki/Policy:User-Agent_policy
  형식: "<클라이언트>/<버전> (<연락처>) <라이브러리>/<버전>". 이 도구는 공개 봇이 아니라
  로컬 1회성 스크립트이므로 브리프가 정한 대로 "video-harness/1.0 (<작업 공간 이름>)"만 쓴다.
"""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
import urllib.error
import urllib.parse
import urllib.request
from datetime import date
from pathlib import Path

PEXELS_API_BASE = "https://api.pexels.com/v1/videos/search"
WIKIMEDIA_API_BASE = "https://commons.wikimedia.org/w/api.php"
PEXELS_LICENSE = "Pexels License"

_TAG_RE = re.compile(r"<[^>]+>")


class SearchError(Exception):
    """검색 요청이 실패했을 때 던진다. 메시지에는 API 키를 절대 담지 않는다."""


def read_env(path: Path) -> dict:
    """.env 파일에서 KEY=VALUE 쌍만 읽는다. 주석(#)과 빈 줄, '='가 없는 줄은 무시한다."""
    result: dict = {}
    path = Path(path)
    if not path.is_file():
        return result
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, _, value = stripped.partition("=")
        result[key.strip()] = value.strip()
    return result


def pexels_request(query: str, orientation: str | None, per_page: int, api_key: str) -> tuple[str, dict]:
    """Pexels 비디오 검색 요청의 (url, headers)를 만든다. 네트워크 호출은 하지 않는다."""
    params = {"query": query}
    if orientation:
        params["orientation"] = orientation
    params["per_page"] = str(per_page)
    url = f"{PEXELS_API_BASE}?{urllib.parse.urlencode(params)}"
    headers = {"Authorization": api_key}
    return url, headers


def _best_video_file(video_files: list[dict]) -> dict | None:
    if not video_files:
        return None
    return max(video_files, key=lambda f: (f.get("width") or 0) * (f.get("height") or 0))


def _slug_from_page_url(page_url: str) -> str:
    path = urllib.parse.urlparse(page_url).path.rstrip("/")
    return Path(path).name.replace("-", " ")


def parse_pexels(payload: dict) -> list[dict]:
    """Pexels 검색 응답을 공통 결과 항목 리스트로 바꾼다."""
    items = []
    for video in payload.get("videos", []):
        best = _best_video_file(video.get("video_files", []))
        page_url = video.get("url", "")
        items.append(
            {
                "source": "pexels",
                "id": video.get("id"),
                "title": video.get("title") or _slug_from_page_url(page_url),
                "page_url": page_url,
                "download_url": best.get("link") if best else None,
                "width": (best or {}).get("width", video.get("width")),
                "height": (best or {}).get("height", video.get("height")),
                "duration": video.get("duration"),
                "license": PEXELS_LICENSE,
                "author": video.get("user", {}).get("name", ""),
            }
        )
    return items


def wikimedia_request(query: str, limit: int, user_agent: str) -> tuple[str, dict]:
    """Wikimedia Commons 검색(generator=search + imageinfo) 요청의 (url, headers)를 만든다."""
    params = {
        "action": "query",
        "generator": "search",
        "gsrsearch": query,
        "gsrnamespace": "6",
        "gsrlimit": str(limit),
        "prop": "imageinfo",
        "iiprop": "url|size|mime|extmetadata",
        "format": "json",
    }
    url = f"{WIKIMEDIA_API_BASE}?{urllib.parse.urlencode(params)}"
    headers = {"User-Agent": user_agent}
    return url, headers


def _strip_html(value: str) -> str:
    return html.unescape(_TAG_RE.sub("", value)).strip()


def parse_wikimedia(payload: dict) -> list[dict]:
    """Wikimedia 검색 응답을 공통 결과 항목 리스트로 바꾼다. imageinfo가 없는 항목은 건너뛴다.

    정지 이미지는 duration이 None이다(iiprop에 영상 길이 정보를 요청하지 않는다).
    """
    items = []
    pages = payload.get("query", {}).get("pages", {})
    for page_id, page in pages.items():
        infos = page.get("imageinfo")
        if not infos:
            continue
        info = infos[0]
        extmeta = info.get("extmetadata", {})
        license_name = extmeta.get("LicenseShortName", {}).get("value", "")
        author_raw = extmeta.get("Artist", {}).get("value", "")
        author = _strip_html(author_raw) if author_raw else ""
        items.append(
            {
                "source": "wikimedia",
                "id": page.get("pageid", page_id),
                "title": page.get("title", ""),
                "page_url": info.get("descriptionurl", ""),
                "download_url": info.get("url", ""),
                "width": info.get("width"),
                "height": info.get("height"),
                "duration": None,
                "license": license_name,
                "author": author,
            }
        )
    return items


def provenance_entry(item: dict, used_in: str, today: str | None = None) -> dict:
    """검색 결과 항목을 provenance.json 항목 형태로 바꾼다.

    today는 테스트에서 날짜를 고정하기 위한 주입 지점이며, 생략하면 오늘 날짜(ISO)를 쓴다.
    """
    return {
        "source": item.get("source", ""),
        "url": item.get("page_url", ""),
        "license": item.get("license", ""),
        "author": item.get("author", ""),
        "title": item.get("title", ""),
        "used_in": used_in,
        "retrieved": today or date.today().isoformat(),
    }


def _ascii_safe_user_agent_name(name: str) -> str:
    """HTTP 헤더는 latin-1만 허용하므로, 작업 공간 이름이 한글 등 비-ASCII면 percent-encode한다."""
    try:
        name.encode("ascii")
        return name
    except UnicodeEncodeError:
        return urllib.parse.quote(name)


def _fetch_json(url: str, headers: dict, opener, label: str) -> dict:
    req = urllib.request.Request(url, headers=headers)
    try:
        with opener(req) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        raise SearchError(f"{label} 요청이 실패했습니다 (HTTP {e.code}).") from None
    except urllib.error.URLError as e:
        raise SearchError(f"{label} 요청이 실패했습니다: {e.reason}") from None


def run_search(
    query: str,
    source: str = "all",
    orientation: str | None = None,
    limit: int = 10,
    env: dict | None = None,
    user_agent: str = "video-harness/1.0 (unknown)",
    opener=urllib.request.urlopen,
) -> dict:
    """Pexels·Wikimedia 검색을 실행해 {"query", "results", "skipped"}를 돌려준다.

    Pexels 키가 없으면(--source all/wikimedia일 때) 에러 없이 건너뛰고 skipped에 이유를
    남긴다. --source pexels를 명시했는데 키가 없으면 SearchError를 던진다. 네트워크 오류나
    비2xx 응답도 SearchError로 감싼다(메시지에 API 키를 절대 넣지 않는다).
    """
    env = env or {}
    sources = ("pexels", "wikimedia") if source == "all" else (source,)
    results: list[dict] = []
    skipped: list[str] = []

    if "pexels" in sources:
        api_key = env.get("PEXELS_API_KEY")
        if not api_key:
            if source == "pexels":
                raise SearchError("PEXELS_API_KEY가 없습니다. .env 파일에 직접 키를 넣어주세요.")
            skipped.append("pexels: PEXELS_API_KEY 없음 (건너뜀)")
        else:
            url, headers = pexels_request(query, orientation, limit, api_key)
            payload = _fetch_json(url, headers, opener, "Pexels")
            results.extend(parse_pexels(payload))

    if "wikimedia" in sources:
        url, headers = wikimedia_request(query, limit, user_agent)
        payload = _fetch_json(url, headers, opener, "Wikimedia")
        results.extend(parse_wikimedia(payload))

    return {"query": query, "results": results, "skipped": skipped}


def main(argv: list[str] | None = None, opener=urllib.request.urlopen) -> int:
    parser = argparse.ArgumentParser(description="Pexels·Wikimedia에서 무료 스톡을 검색한다(내려받기는 하지 않는다).")
    parser.add_argument("query", help="검색어")
    parser.add_argument("--source", choices=["pexels", "wikimedia", "all"], default="all")
    parser.add_argument("--orientation", choices=["landscape", "portrait", "square"], default=None)
    parser.add_argument("--limit", type=int, default=10)
    parser.add_argument("--env", type=Path, default=Path(".env"), help=".env 파일 경로 (기본: 현재 디렉터리의 .env)")
    parser.add_argument("--workspace-name", default=None, help="Wikimedia User-Agent에 넣을 작업 공간 이름 (기본: 현재 폴더 이름)")
    args = parser.parse_args(argv)

    env = read_env(args.env)
    workspace_name = _ascii_safe_user_agent_name(args.workspace_name or Path.cwd().name)
    user_agent = f"video-harness/1.0 ({workspace_name})"

    try:
        result = run_search(
            args.query,
            source=args.source,
            orientation=args.orientation,
            limit=args.limit,
            env=env,
            user_agent=user_agent,
            opener=opener,
        )
    except SearchError as e:
        print(str(e), file=sys.stderr)
        return 1

    print(json.dumps(result, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
