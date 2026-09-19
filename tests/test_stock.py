import json
import urllib.error

import pytest

import search as s


def test_pexels_request():
    url, headers = s.pexels_request("ocean wave", "portrait", 5, "KEY")
    assert url.startswith("https://api.pexels.com/v1/videos/search?") and "orientation=portrait" in url and "per_page=5" in url
    assert headers == {"Authorization": "KEY"}


def test_parse_pexels_picks_largest_file():
    payload = {"videos": [{"id": 7, "url": "https://www.pexels.com/video/7/", "width": 1080, "height": 1920, "duration": 12,
                           "user": {"name": "Kim"},
                           "video_files": [{"link": "a.mp4", "width": 540, "height": 960}, {"link": "b.mp4", "width": 1080, "height": 1920}]}]}
    item = s.parse_pexels(payload)[0]
    assert item["download_url"] == "b.mp4" and item["license"] == "Pexels License" and item["author"] == "Kim"


def test_wikimedia_request_sets_user_agent():
    url, headers = s.wikimedia_request("Cimabue", 3, "video-harness/1.0 (테스트)")
    assert "commons.wikimedia.org/w/api.php" in url and "gsrnamespace=6" in url
    assert headers["User-Agent"].startswith("video-harness/1.0")


def test_parse_wikimedia_reads_license():
    payload = {"query": {"pages": {"1": {"title": "File:X.jpg", "imageinfo": [{
        "url": "https://upload.wikimedia.org/x.jpg", "descriptionurl": "https://commons.wikimedia.org/wiki/File:X.jpg",
        "width": 2000, "height": 3000,
        "extmetadata": {"LicenseShortName": {"value": "CC BY-SA 4.0"}, "Artist": {"value": "<a>Lee</a>"}}}]}}}}
    item = s.parse_wikimedia(payload)[0]
    assert item["license"] == "CC BY-SA 4.0" and item["author"] == "Lee" and item["source"] == "wikimedia"


def test_parse_wikimedia_skips_pages_without_imageinfo():
    payload = {"query": {"pages": {"1": {"title": "File:NoInfo.jpg"}}}}
    assert s.parse_wikimedia(payload) == []


def test_parse_wikimedia_duration_none_for_still_image():
    payload = {"query": {"pages": {"1": {"title": "File:X.jpg", "imageinfo": [{
        "url": "https://upload.wikimedia.org/x.jpg", "descriptionurl": "https://commons.wikimedia.org/wiki/File:X.jpg",
        "width": 2000, "height": 3000, "mime": "image/jpeg",
        "extmetadata": {"LicenseShortName": {"value": "CC0"}, "Artist": {"value": "Lee"}}}]}}}}
    item = s.parse_wikimedia(payload)[0]
    assert item["duration"] is None


def test_provenance_entry():
    e = s.provenance_entry({"source": "pexels", "page_url": "u", "license": "Pexels License", "author": "Kim", "title": "t"}, "007 0:12-0:18")
    assert e["used_in"] == "007 0:12-0:18" and e["license"] == "Pexels License" and "retrieved" in e


def test_provenance_entry_uses_injected_date():
    e = s.provenance_entry({"source": "wikimedia", "page_url": "u", "license": "CC0", "author": "Lee", "title": "t"}, "008", today="2026-09-19")
    assert e["retrieved"] == "2026-09-19"


class _FakeResponse:
    def __init__(self, payload):
        self._data = json.dumps(payload).encode("utf-8")

    def read(self):
        return self._data

    def __enter__(self):
        return self

    def __exit__(self, *exc):
        return False


def test_pexels_skipped_when_no_key_but_wikimedia_still_runs():
    wiki_payload = {"query": {"pages": {}}}

    def fake_opener(req):
        assert "commons.wikimedia.org" in req.full_url
        return _FakeResponse(wiki_payload)

    result = s.run_search("lighthouse", source="all", env={}, opener=fake_opener)
    assert result["results"] == []
    assert any("pexels" in reason for reason in result["skipped"])


def test_explicit_pexels_without_key_raises_error():
    with pytest.raises(s.SearchError):
        s.run_search("lighthouse", source="pexels", env={})


def test_explicit_pexels_without_key_exits_1_with_korean_message(tmp_path, capsys):
    exit_code = s.main(["lighthouse", "--source", "pexels", "--env", str(tmp_path / "없음.env")])
    captured = capsys.readouterr()
    assert exit_code == 1
    assert captured.out == ""
    assert ".env" in captured.err
    assert "Traceback" not in captured.err


def test_http_error_exits_1_with_korean_message_no_traceback(tmp_path, capsys):
    env_file = tmp_path / ".env"
    env_file.write_text("PEXELS_API_KEY=SECRET123\n", encoding="utf-8")

    def fake_opener(req):
        raise urllib.error.HTTPError(req.full_url, 401, "Unauthorized", None, None)

    exit_code = s.main(["lighthouse", "--source", "pexels", "--env", str(env_file)], opener=fake_opener)
    captured = capsys.readouterr()
    assert exit_code == 1
    assert captured.out == ""
    assert "Pexels" in captured.err
    assert "Traceback" not in captured.err


def test_main_builds_ascii_safe_user_agent_for_korean_workspace_name(tmp_path):
    # 실기 확인에서 발견: 워크스페이스 이름이 한글이면 User-Agent 헤더가 latin-1로 인코딩되지
    # 않아 http.client가 UnicodeEncodeError를 던진다. main()이 이를 percent-encode해야 한다.
    captured_headers = {}

    def fake_opener(req):
        captured_headers.update(req.headers)
        return _FakeResponse({"query": {"pages": {}}})

    exit_code = s.main(
        ["lighthouse", "--source", "wikimedia", "--workspace-name", "테스트작업실"],
        opener=fake_opener,
    )
    assert exit_code == 0
    user_agent = captured_headers.get("User-agent", "")
    user_agent.encode("ascii")  # 이 줄이 예외를 던지면 안 된다
    assert user_agent.startswith("video-harness/1.0 (")


def test_api_key_never_appears_in_stdout_or_stderr(tmp_path, capsys):
    env_file = tmp_path / ".env"
    env_file.write_text("PEXELS_API_KEY=SECRET123\n", encoding="utf-8")

    def fake_opener(req):
        raise urllib.error.HTTPError(req.full_url, 401, "Unauthorized", None, None)

    s.main(["lighthouse", "--source", "pexels", "--env", str(env_file)], opener=fake_opener)
    captured = capsys.readouterr()
    assert "SECRET123" not in captured.out
    assert "SECRET123" not in captured.err
