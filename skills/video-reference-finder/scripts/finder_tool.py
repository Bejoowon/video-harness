#!/usr/bin/env python3
"""레퍼런스 찾기 도구: detect / brief / verify / record.

브라우저 에이전트가 찾아 온 후보는 **주장**일 뿐이다. 이 도구는 그 주장을 실제
엔드포인트에 물어 확인하고, 확인하지 못한 것을 확인했다고 말하지 않게 한다.

이 스킬은 세팅 스킬(`video-harness-setup`)과 따로 설치될 수 있으므로 그 스킬의
코드를 import하지 않는다. 설정 파일에 값을 **쓸 때만** 세팅 스킬의 `config_tool.py`를
바깥에서 실행한다 — 설정의 기록 창구는 그것 하나여야 한다.

표준 라이브러리만 사용한다.
"""

from __future__ import annotations

import argparse
import html
import json
import re
import shutil
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

CONFIG_NAME = "harness.config.json"
ASIDE = "aside"
DEFAULT_COUNT = 8
TIMEOUT = 15
# 페이지에서 읽을 최대 바이트. 유튜브 채널 페이지는 `<title>`이 앞쪽 스크립트 뒤
# 760KB쯤에 있다(2026-09-21 실제 확인). 그보다 적게 읽으면 채널 이름을 실제 값으로
# 덮어쓰지 못하고 에이전트가 적어 온 이름이 그대로 남는다.
READ_LIMIT = 1_200_000
USER_AGENT = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/125.0 Safari/537.36"
)

FORMATS = ("9:16", "16:9")
PLATFORMS = ("youtube", "instagram", "tiktok")
PLATFORM_LABELS = {
    "youtube": "유튜브(쇼츠·일반)",
    "instagram": "인스타그램 릴스",
    "tiktok": "틱톡",
}
FORMAT_LABELS = {"9:16": "9:16 (세로)", "16:9": "16:9 (가로)"}
WORKFLOW_LABELS = {
    "script-first": "대본 먼저",
    "footage-first": "찍은 영상 먼저",
    "per-episode": "회차마다 정함",
}
FOCUS_CHOICES = ("자막", "구성", "컷 템포", "말투", "썸네일", "제목", "전부")

# 확인 상태. 이 네 가지 말고 다른 말을 쓰지 않는다 (design §5-6).
STATUS_CONFIRMED = "확인됨"
STATUS_MISSING = "없는 주소"
STATUS_MANUAL = "직접 확인 필요"
STATUS_FAILED = "확인 실패"
NO_DESCRIPTION = "설명 없음"

# 인터뷰 답에서 채널 쪽으로 옮겨 적는 값들 (있는 것만).
CHANNEL_KEYS = ("id", "name", "format", "workflow", "audience", "scope", "tone", "platforms")

CANDIDATE_FILE = "레퍼런스_후보.md"
CANDIDATE_HEADER = "| 번호 | 주소 | 무엇인지 | 마음에 드는 점 | 확인 상태 |"
CANDIDATE_INTRO = """# 레퍼런스 후보

사용자가 고른 참고 영상·채널이다. 레퍼런스는 분석용이다 — 레퍼런스 영상의 화면·소리를
내 영상에 그대로 가져다 쓰지 않는다.

확인 상태는 주소가 실제로 열리는지만 본 값이다. `직접 확인 필요`는 자동으로 확인할 수
없다는 뜻이지 가짜라는 뜻이 아니다.
"""


# --------------------------------------------------------------------------- 공통


def _fail(message: str) -> int:
    print(message, file=sys.stderr)
    return 2


def _dump(data) -> None:
    print(json.dumps(data, ensure_ascii=False, indent=2))


def _read_text(path: Path) -> tuple[str | None, str | None]:
    try:
        return Path(path).read_text(encoding="utf-8"), None
    except OSError as error:
        return None, f"파일을 읽지 못했습니다: {path} ({error})"


# --------------------------------------------------------------------------- detect


def find_config_tool() -> str | None:
    """옆에 설치된 세팅 스킬의 `config_tool.py`를 찾는다. 없으면 None (단독 모드).

    설치 위치는 사람마다 다르므로 이 파일의 실제 경로에서 상대로 푼다.
    """
    candidate = Path(__file__).resolve().parents[2] / "video-harness-setup" / "scripts" / "config_tool.py"
    return str(candidate) if candidate.exists() else None


def _load_config(folder: Path) -> tuple[dict | None, str | None]:
    """(설정, 오류). 파일이 없으면 (None, None), 깨져 있으면 (None, 오류 메시지)."""
    path = Path(folder) / CONFIG_NAME
    if not path.exists():
        return None, None
    try:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle), None
    except (OSError, json.JSONDecodeError) as error:
        return None, f"{CONFIG_NAME}을 읽지 못했습니다: {error}"


def detect(folder, which_fn=shutil.which, config_tool_fn=find_config_tool) -> dict:
    """지금 폴더가 작업 공간인지, 채널이 무엇이 있는지, Aside가 있는지 알려 준다."""
    config, config_error = _load_config(Path(folder))
    aside_path = which_fn(ASIDE)
    is_workspace = config is not None or config_error is not None

    report: dict = {
        "mode": "workspace" if is_workspace else "standalone",
        "channels": [],
        "aside": {"found": aside_path is not None, "path": aside_path},
        "config_tool": config_tool_fn(),
        "watch_installed": False,
    }
    if config_error:
        report["config_error"] = config_error
        return report
    if config is None:
        return report

    for index, channel in enumerate(config.get("channels") or []):
        entry: dict = {"index": index}
        for key in CHANNEL_KEYS:
            value = channel.get(key)
            if value:
                entry[key] = value
        entry["references_count"] = len(channel.get("references") or [])
        report["channels"].append(entry)

    watch = config.get("modules", {}).get("reference", {}).get("watch")
    report["watch_installed"] = watch is True
    return report


# --------------------------------------------------------------------------- brief


def _unique(values) -> list:
    seen = []
    for value in values:
        if value not in seen:
            seen.append(value)
    return seen


def validate_answers(answers) -> list[str]:
    """인터뷰 답을 검증한다. 오류 메시지 목록(한국어)을 돌려주고, 비었으면 통과."""
    if not isinstance(answers, dict):
        return ["답은 JSON 객체 하나여야 합니다."]

    errors: list[str] = []

    for key, label in (("field", "분야"), ("audience", "누가 보는지")):
        value = answers.get(key)
        if not isinstance(value, str) or not value.strip():
            errors.append(f"{key}: {label}를 비어 있지 않은 문장으로 적으세요.")

    if answers.get("format") not in FORMATS:
        errors.append(f"format: 포맷은 {' 또는 '.join(FORMATS)}입니다.")

    workflow = answers.get("workflow")
    if workflow is not None and (not isinstance(workflow, str) or not workflow.strip()):
        errors.append("workflow: 출발점은 비어 있지 않은 문자열이어야 합니다.")

    platforms = answers.get("platforms")
    if not isinstance(platforms, list) or not platforms:
        errors.append(f"platforms: 찾을 곳을 하나 이상 고르세요 ({', '.join(PLATFORMS)}).")
    else:
        for platform in platforms:
            if platform not in PLATFORMS:
                errors.append(f"platforms: 알 수 없는 값 '{platform}' (허용: {', '.join(PLATFORMS)})")

    focus = answers.get("focus")
    if not isinstance(focus, list) or not focus:
        errors.append(f"focus: 특히 보고 싶은 것을 하나 이상 고르세요 ({' · '.join(FOCUS_CHOICES)}).")
    else:
        for item in focus:
            if item not in FOCUS_CHOICES:
                errors.append(f"focus: 알 수 없는 값 '{item}' (허용: {' · '.join(FOCUS_CHOICES)})")

    avoid = answers.get("avoid")
    if avoid is not None and not isinstance(avoid, str):
        errors.append("avoid: 피하고 싶은 것은 한 줄 문장으로 적으세요.")

    similar = answers.get("similar_to")
    if similar is not None:
        if not isinstance(similar, list) or any(not isinstance(item, str) for item in similar):
            errors.append("similar_to: 이미 아는 채널·영상 주소를 문자열 목록으로 적으세요.")

    return errors


_BRIEF_RETURN_FIELDS = (
    ("url", "영상 또는 채널 주소. 실제로 연 주소 그대로"),
    ("what", "무엇인지 한 줄 (채널인지 영상인지, 어떤 내용인지)"),
    ("why_fit", "위 조건에 왜 맞는지 한 줄"),
    ("caution", "주의할 점 한 줄 (없으면 빈 문자열)"),
    ("numbers_seen_on_page", "선택. 페이지에서 **직접 본** 구독자·조회수만. 못 봤으면 이 항목을 빼세요"),
)

_BRIEF_RULES = (
    "**보기만 한다.** 구독·좋아요·댓글·팔로우·메시지·저장을 하지 않는다.",
    "로그인 정보·비밀번호를 입력하지 않는다. **로그인 화면이 나오면 그 플랫폼은 건너뛰고, "
    "건너뛰었다고 그대로 알린다.**",
    "아무것도 내려받지 않는다.",
    "채널 이름·주소·숫자를 지어내지 않는다. 실제로 연 페이지에서 본 것만 적는다.",
    "구독자·조회수는 페이지에서 직접 본 경우에만 적는다. 못 봤으면 그 항목을 아예 뺀다.",
)

_BRIEF_EXAMPLE = """[
  {"url": "https://…", "what": "…", "why_fit": "…", "caution": ""}
]"""


def build_brief(answers: dict, count: int = DEFAULT_COUNT) -> str:
    """탐색 지시문을 정해진 틀로 조립한다. 같은 답이면 언제나 같은 글이 나온다."""
    platforms = _unique(answers.get("platforms") or [])
    focus = _unique(answers.get("focus") or [])
    workflow = answers.get("workflow")

    lines = [
        "# 레퍼런스 탐색 지시문",
        "",
        "아래 조건에 맞는 영상·채널을 찾아 주세요. 보기만 하고, 아무것도 바꾸지 않습니다.",
        "",
        "## 무엇을 찾나",
        "",
        f"- 분야: {answers.get('field', '')}",
        f"- 누가 보나: {answers.get('audience', '')}",
        f"- 포맷: {FORMAT_LABELS.get(answers.get('format'), answers.get('format', ''))}",
    ]
    if workflow:
        lines.append(f"- 출발점: {WORKFLOW_LABELS.get(workflow, workflow)}")
    lines.append(f"- 찾을 곳: {', '.join(PLATFORM_LABELS.get(p, p) for p in platforms)}")
    lines.append(f"- 특히 볼 것: {', '.join(focus)}")
    if answers.get("avoid"):
        lines.append(f"- 피하고 싶은 것: {answers['avoid']}")
    similar = answers.get("similar_to") or []
    if similar:
        lines.append(f"- 이런 곳과 비슷한 곳: {', '.join(similar)}")
    lines.append(f"- 후보 수: {count}개")

    lines += ["", "## 후보마다 돌려줄 것", "", "| 항목 | 뜻 |", "|---|---|"]
    for key, meaning in _BRIEF_RETURN_FIELDS:
        lines.append(f"| `{key}` | {meaning} |")

    lines += ["", "## 지킬 것 (보기 전용)", ""]
    for rule in _BRIEF_RULES:
        lines.append(f"- {rule}")

    lines += [
        "",
        "## 결과 형식",
        "",
        "JSON 배열 하나만 돌려준다. 앞뒤에 다른 말을 쓰지 않는다.",
        "",
        _BRIEF_EXAMPLE,
        "",
    ]
    return "\n".join(lines)


# --------------------------------------------------------------------------- 주소 다듬기

_YOUTUBE_HOSTS = {"youtube.com", "m.youtube.com", "music.youtube.com", "youtube-nocookie.com"}
_YOUTUBE_SHORT_HOST = "youtu.be"
_TIKTOK_HOSTS = {"tiktok.com", "vm.tiktok.com", "vt.tiktok.com"}
_INSTAGRAM_HOSTS = {"instagram.com", "instagr.am"}

# 주소를 가리키는 데 필요 없는 꼬리표들. 같은 영상을 다른 것으로 세지 않기 위해 뗀다.
_TRACKING_PARAMS = {
    "si", "feature", "pp", "ab_channel", "app", "gclid", "fbclid", "igsh", "igshid",
    "is_from_webapp", "sender_device", "sender_web_id", "web_id", "_r", "_t", "source",
    "utm_source", "utm_medium", "utm_campaign", "utm_term", "utm_content", "utm_id",
}
_YOUTUBE_VIDEO_PATHS = ("/shorts/", "/embed/", "/live/", "/v/")
_YOUTUBE_CHANNEL_PREFIXES = ("/@", "/channel/", "/c/", "/user/")

_URL_RE = re.compile(r"https?://[^\s<>\"')\]}]+")
_TRAILING_PUNCTUATION = ".,;:!?'\"`>"
_TITLE_RE = re.compile(r"<title[^>]*>(.*?)</title>", re.S | re.I)


def _clean_query(query: str) -> str:
    pairs = urllib.parse.parse_qsl(query, keep_blank_values=False)
    kept = [(key, value) for key, value in pairs if key.lower() not in _TRACKING_PARAMS]
    return urllib.parse.urlencode(kept)


def _youtube_video_id(path: str, query: str) -> str | None:
    if path == "/watch":
        values = dict(urllib.parse.parse_qsl(query))
        return values.get("v") or None
    for prefix in _YOUTUBE_VIDEO_PATHS:
        if path.startswith(prefix):
            rest = path[len(prefix):].split("/")[0]
            return rest or None
    return None


def normalise_url(raw: str) -> str:
    """같은 곳을 가리키는 주소를 한 모양으로 맞춘다 (중복 합치기와 이미 있는지 판단용)."""
    text = (raw or "").strip()
    if not text:
        return ""
    if "://" not in text:
        text = "https://" + text

    parts = urllib.parse.urlsplit(text)
    host = parts.netloc.lower()
    if host.startswith("www."):
        host = host[4:]
    path = parts.path.rstrip("/")
    query = _clean_query(parts.query)

    if host == _YOUTUBE_SHORT_HOST:
        video_id = path.lstrip("/").split("/")[0]
        if video_id:
            return f"https://www.youtube.com/watch?v={video_id}"
        host = "youtube.com"
    if host in _YOUTUBE_HOSTS:
        video_id = _youtube_video_id(path, query)
        if video_id:
            return f"https://www.youtube.com/watch?v={video_id}"
        host = "youtube.com"
    elif host in _TIKTOK_HOSTS:
        host = "tiktok.com"
    elif host in _INSTAGRAM_HOSTS:
        host = "instagram.com"

    return urllib.parse.urlunsplit(("https", f"www.{host}", path, query, ""))


def classify(url: str) -> str:
    """주소를 확인 방법별로 나눈다: youtube-video · youtube-page · tiktok · instagram · other."""
    parts = urllib.parse.urlsplit(normalise_url(url))
    host = parts.netloc.lower()
    if host.startswith("www."):
        host = host[4:]
    if host in _YOUTUBE_HOSTS or host == _YOUTUBE_SHORT_HOST:
        if _youtube_video_id(parts.path, parts.query):
            return "youtube-video"
        return "youtube-page"
    if host in _TIKTOK_HOSTS:
        return "tiktok"
    if host in _INSTAGRAM_HOSTS:
        return "instagram"
    return "other"


# --------------------------------------------------------------------------- verify


def http_get(url: str, timeout: int = TIMEOUT) -> tuple[int | None, str]:
    """읽기만 하는 GET. (상태 코드, 본문). 네트워크가 안 되면 (None, 이유)."""
    request = urllib.request.Request(url, headers={"User-Agent": USER_AGENT}, method="GET")
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            body = response.read(READ_LIMIT).decode("utf-8", errors="replace")
            return response.status, body
    except urllib.error.HTTPError as error:
        body = ""
        if error.fp is not None:
            body = error.read(2_000).decode("utf-8", errors="replace")
        return error.code, body
    except Exception as error:  # noqa: BLE001 - 네트워크는 무엇으로든 실패할 수 있다
        return None, f"{type(error).__name__}: {error}"


def _oembed_url(base: str, target: str) -> str:
    return base + urllib.parse.quote(target, safe="")


def _status_for_code(code: int | None) -> str:
    """상태 코드를 확인 상태로 옮긴다.

    4xx는 "그 주소가 없다"는 대답이다(유튜브 oEmbed는 없는 영상에 404가 아니라 400을 준다).
    429와 5xx는 상대 서버 사정이지 주소가 없다는 뜻이 아니므로 빼지 않고 `확인 실패`로 둔다.
    """
    if code is None:
        return STATUS_FAILED
    if code == 200:
        return STATUS_CONFIRMED
    if 400 <= code < 500 and code != 429:
        return STATUS_MISSING
    return STATUS_FAILED


def _page_title(body: str) -> str | None:
    match = _TITLE_RE.search(body or "")
    if not match:
        return None
    title = html.unescape(re.sub(r"\s+", " ", match.group(1))).strip()
    for suffix in (" - YouTube", " - 유튜브"):
        if title.endswith(suffix):
            title = title[: -len(suffix)].strip()
    return title or None


def _verify_oembed(candidate: dict, endpoint: str, fetch) -> None:
    code, body = fetch(_oembed_url(endpoint, candidate["url"]))
    status = _status_for_code(code)
    if status != STATUS_CONFIRMED:
        candidate["status"] = status
        candidate["note"] = _note_for(status, code, body)
        return
    try:
        payload = json.loads(body)
    except json.JSONDecodeError:
        candidate["status"] = STATUS_FAILED
        candidate["note"] = "확인용 응답을 읽지 못했습니다. 직접 열어 보세요."
        return
    candidate["status"] = STATUS_CONFIRMED
    if payload.get("title"):
        candidate["title"] = payload["title"]
    if payload.get("author_name"):
        candidate["author"] = payload["author_name"]


def _verify_page(candidate: dict, fetch) -> None:
    code, body = fetch(candidate["url"])
    status = _status_for_code(code)
    candidate["status"] = status
    if status != STATUS_CONFIRMED:
        candidate["note"] = _note_for(status, code, body)
        return
    title = _page_title(body)
    if title:
        candidate["title"] = title


def _note_for(status: str, code: int | None, body: str) -> str:
    if status == STATUS_MISSING:
        return f"주소가 열리지 않습니다 (응답 {code}). 목록에서 뺐습니다."
    if code is None:
        return f"네트워크로 확인하지 못했습니다: {body}"
    return f"확인하지 못했습니다 (응답 {code}). 직접 열어 보세요."


_MANUAL_NOTES = {
    "instagram": "인스타그램은 없는 주소에도 200을 주기 때문에 자동으로 확인할 수 없습니다. 직접 열어 보세요.",
    "other": "확인 방법을 모르는 주소입니다. 직접 열어 보세요.",
}


def _merge(candidates) -> list[dict]:
    """같은 곳을 가리키는 후보를 하나로 합친다. 먼저 온 값이 이긴다."""
    merged: dict[str, dict] = {}
    for raw in candidates:
        if not isinstance(raw, dict):
            continue
        url = normalise_url(raw.get("url", ""))
        if not url:
            continue
        item = merged.get(url)
        if item is None:
            item = {key: value for key, value in raw.items() if key != "url"}
            item["url"] = url
            merged[url] = item
            continue
        for key, value in raw.items():
            if key == "url":
                continue
            if value and not item.get(key):
                item[key] = value
    return list(merged.values())


def verify_candidates(candidates, fetch=None) -> dict:
    """후보의 주소가 실제로 열리는지 확인하고 상태를 붙인다.

    `fetch`는 `(상태 코드 또는 None, 본문)`을 돌려주는 함수다. 테스트가 네트워크 없이
    돌 수 있도록 바깥에서 넣는다. 확인하지 못한 것은 확인했다고 하지 않는다.
    """
    if fetch is None:
        fetch = http_get

    kept: list[dict] = []
    dropped: list[dict] = []
    summary = {STATUS_CONFIRMED: 0, STATUS_MANUAL: 0, STATUS_FAILED: 0, STATUS_MISSING: 0}

    for candidate in _merge(candidates):
        kind = classify(candidate["url"])
        if kind == "youtube-video":
            _verify_oembed(candidate, "https://www.youtube.com/oembed?format=json&url=", fetch)
        elif kind == "youtube-page":
            _verify_page(candidate, fetch)
        elif kind == "tiktok":
            _verify_oembed(candidate, "https://www.tiktok.com/oembed?url=", fetch)
        else:
            candidate["status"] = STATUS_MANUAL
            candidate["note"] = _MANUAL_NOTES[kind]

        summary[candidate["status"]] += 1
        if candidate["status"] == STATUS_MISSING:
            dropped.append(candidate)
        else:
            kept.append(candidate)

    return {"candidates": kept, "dropped": dropped, "summary": summary}


def parse_candidates(raw: str) -> list[dict]:
    """JSON 배열이면 그대로, 아니면 글에서 주소를 뽑아 `설명 없음`으로 표시한다."""
    try:
        data = json.loads(raw)
    except (json.JSONDecodeError, TypeError):
        data = None
    if isinstance(data, list):
        return [item for item in data if isinstance(item, dict)]

    found: list[dict] = []
    seen = set()
    for match in _URL_RE.finditer(raw or ""):
        url = match.group(0).rstrip(_TRAILING_PUNCTUATION)
        if not url or url in seen:
            continue
        seen.add(url)
        found.append({"url": url, "what": NO_DESCRIPTION})
    return found


def _cell(value) -> str:
    text = "" if value is None else str(value)
    return re.sub(r"\s+", " ", text).replace("|", "\\|").strip()


def what_cell(candidate: dict) -> str:
    """"무엇인지" 칸. 에이전트가 적어 온 설명 뒤에 **확인된 실제 이름**을 덧붙인다.

    에이전트가 가져온 제목·채널명은 주장일 뿐이다. 확인된 값이 따로 있으면 나란히
    보여 줘서, 지어낸 이름이 사용자에게 사실처럼 보이지 않게 한다.
    """
    said = (candidate.get("what") or "").strip()
    real = " / ".join(part for part in (candidate.get("title"), candidate.get("author")) if part)
    if not real or real in said:
        return said or real
    return f"{said} — 실제: {real}" if said else f"실제: {real}"


def render_table(result: dict) -> str:
    """사용자가 보고 고를 표. 확인 상태를 마지막 칸에 그대로 보여 준다."""
    lines = [
        "| 번호 | 주소 | 무엇인지 | 왜 맞는지 | 주의점 | 확인 상태 |",
        "|---|---|---|---|---|---|",
    ]
    for index, candidate in enumerate(result.get("candidates") or [], start=1):
        what = what_cell(candidate)
        lines.append(
            "| {0} | {1} | {2} | {3} | {4} | {5} |".format(
                index,
                _cell(candidate.get("url")),
                _cell(what),
                _cell(candidate.get("why_fit")),
                _cell(candidate.get("caution")),
                _cell(candidate.get("status")),
            )
        )
    dropped = result.get("dropped") or []
    if dropped:
        lines.append("")
        lines.append(f"목록에서 뺀 주소({len(dropped)}개, 열리지 않음): " + ", ".join(_cell(d.get("url")) for d in dropped))
    return "\n".join(lines)


# --------------------------------------------------------------------------- record


def _existing_urls(text: str) -> set[str]:
    return {normalise_url(match.group(0).rstrip(_TRAILING_PUNCTUATION)) for match in _URL_RE.finditer(text)}


def _last_table_line(lines: list[str]) -> int | None:
    for index in range(len(lines) - 1, -1, -1):
        if lines[index].lstrip().startswith("|"):
            return index
    return None


def _last_row_number(lines: list[str]) -> int:
    highest = 0
    for line in lines:
        match = re.match(r"^\|\s*(\d+)\s*\|", line.strip())
        if match:
            highest = max(highest, int(match.group(1)))
    return highest


def _row(number: int, picked: dict) -> str:
    return "| {0} | {1} | {2} | {3} | {4} |".format(
        number,
        _cell(picked.get("url")),
        _cell(picked.get("what") or picked.get("title")),
        _cell(picked.get("likes")),
        _cell(picked.get("status")),
    )


def record_standalone(folder, picked) -> dict:
    """단독 모드에서 고른 레퍼런스를 `레퍼런스_후보.md`에 남긴다.

    이미 있는 줄은 고치지 않고, 이미 적힌 주소는 건너뛰고, 새 줄만 표 끝에 덧붙인다.
    """
    folder = Path(folder)
    folder.mkdir(parents=True, exist_ok=True)
    path = folder / CANDIDATE_FILE
    created = not path.exists()

    if created:
        lines = CANDIDATE_INTRO.rstrip("\n").splitlines()
        lines += ["", CANDIDATE_HEADER, "|---|---|---|---|---|"]
    else:
        lines = path.read_text(encoding="utf-8").splitlines()

    known = _existing_urls("\n".join(lines))
    number = _last_row_number(lines)
    new_rows: list[str] = []
    added: list[str] = []
    skipped: list[str] = []

    for item in picked or []:
        if not isinstance(item, dict):
            continue
        url = (item.get("url") or "").strip()
        if not url:
            continue
        key = normalise_url(url)
        if key in known:
            skipped.append(url)
            continue
        known.add(key)
        number += 1
        new_rows.append(_row(number, item))
        added.append(url)

    if new_rows:
        at = _last_table_line(lines)
        at = len(lines) - 1 if at is None else at
        lines[at + 1: at + 1] = new_rows

    path.write_text("\n".join(lines).rstrip("\n") + "\n", encoding="utf-8")
    return {"path": str(path), "created": created, "added": added, "skipped": skipped}


# --------------------------------------------------------------------------- CLI


def cmd_detect(args: argparse.Namespace) -> int:
    _dump(detect(Path(args.folder)))
    return 0


def cmd_brief(args: argparse.Namespace) -> int:
    text, error = _read_text(Path(args.answers))
    if error:
        return _fail(error)
    try:
        answers = json.loads(text)
    except json.JSONDecodeError as parse_error:
        return _fail(f"답 파일이 JSON이 아닙니다: {parse_error}")

    errors = validate_answers(answers)
    if errors:
        print("답이 올바르지 않아 지시문을 만들지 않았습니다:", file=sys.stderr)
        for item in errors:
            print(f"  - {item}", file=sys.stderr)
        return 2
    if args.count < 1:
        return _fail("--count는 1 이상이어야 합니다.")

    print(build_brief(answers, args.count))
    return 0


def cmd_verify(args: argparse.Namespace) -> int:
    text, error = _read_text(Path(args.candidates))
    if error:
        return _fail(error)

    result = verify_candidates(parse_candidates(text), fetch=lambda url: http_get(url))
    if args.table:
        print(render_table(result))
    else:
        _dump(result)
    return 0


def cmd_record(args: argparse.Namespace) -> int:
    text, error = _read_text(Path(args.picked))
    if error:
        return _fail(error)
    try:
        picked = json.loads(text)
    except json.JSONDecodeError as parse_error:
        return _fail(f"고른 목록이 JSON이 아닙니다: {parse_error}")
    if not isinstance(picked, list):
        return _fail("고른 목록은 JSON 배열이어야 합니다.")

    _dump(record_standalone(Path(args.standalone), picked))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="레퍼런스 찾기 도구")
    sub = parser.add_subparsers(dest="command", required=True)

    detect_parser = sub.add_parser("detect", help="작업 공간인지, 채널과 Aside가 있는지 본다")
    detect_parser.add_argument("folder", help="지금 폴더의 절대경로")

    brief_parser = sub.add_parser("brief", help="탐색 지시문을 만든다")
    brief_parser.add_argument("--answers", required=True, help="인터뷰 답을 담은 JSON 파일")
    brief_parser.add_argument("--count", type=int, default=DEFAULT_COUNT, help=f"후보 수 (기본 {DEFAULT_COUNT})")

    verify_parser = sub.add_parser("verify", help="후보의 주소가 실제로 열리는지 확인한다")
    verify_parser.add_argument("candidates", help="후보 JSON 배열 또는 글이 든 파일")
    verify_parser.add_argument("--table", action="store_true", help="한국어 표로 출력")

    record_parser = sub.add_parser("record", help="단독 모드에서 고른 레퍼런스를 파일로 남긴다")
    record_parser.add_argument("--standalone", required=True, help="파일을 만들 폴더의 절대경로")
    record_parser.add_argument("--picked", required=True, help="사용자가 고른 목록 JSON 파일")

    return parser


_COMMANDS = {"detect": cmd_detect, "brief": cmd_brief, "verify": cmd_verify, "record": cmd_record}


def main(argv: list[str] | None = None) -> int:
    # Windows 콘솔에서 한국어가 깨지지 않게 한다.
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass
    args = build_parser().parse_args(argv)
    return _COMMANDS[args.command](args)


if __name__ == "__main__":
    sys.exit(main())
