# tests/test_script_rhythm.py
"""`도구/script/check_rhythm.py` — 음절을 세어 보여 주는 보조 도구.

합격·불합격을 가르는 관문이 아니다. 그래서 여기서도 "기본 종료 코드는 언제나 0"을
함께 고정한다.
"""
import json
from pathlib import Path

import check_rhythm as cr

# 브리프에서 손으로 세어 확인한 예시. 검사기의 셈이 이것과 어긋나면 도구가 틀린 것이다.
VERIFIED = [
    ("오늘은 / 우리 동네 / 숨은 맛집 / 가 볼게", [3, 4, 4, 3], cr.GRADE_OK),
    ("냉장고에 / 남은 재료 / 이것만은 / 꼭 넣어", [4, 4, 4, 3], cr.GRADE_OK),
    ("딱 하나만 / 기억하세요", [4, 5], cr.GRADE_TOLERATED),
]


def _write(tmp_path, text, name="대본.md"):
    path = tmp_path / name
    path.write_text(text, encoding="utf-8")
    return path


def _analyze_line(line):
    result = cr.analyze(line)
    assert len(result["lines"]) == 1, line
    return result["lines"][0]


# --- 음절 세기 ---


def test_counts_only_hangul_syllables():
    assert cr.syllables("가 볼게") == 3
    assert cr.syllables("숨은 맛집!") == 4
    assert cr.syllables("  ") == 0


def test_verified_examples_keep_their_counts_and_grades():
    for line, counts, grade in VERIFIED:
        row = _analyze_line(line)
        assert row["counts"] == counts, line
        assert row["pattern"] == "/".join(str(c) for c in counts), line
        assert row["grade"] == grade, line


# --- 판정 ---


def test_five_syllable_group_is_tolerated_not_a_hit():
    assert _analyze_line("네 마디로 / 끊어 읽어요")["grade"] == cr.GRADE_TOLERATED


def test_a_too_short_and_a_too_long_group_fall_off():
    row = _analyze_line("한번 / 여섯음절짜리는")
    assert row["counts"] == [2, 7]
    assert row["grade"] == cr.GRADE_OFF


def test_too_many_groups_fall_off():
    row = _analyze_line("하나만 / 둘째로 / 셋째로 / 넷째로 / 다섯째")
    assert row["grade"] == cr.GRADE_OFF


def test_limits_are_overridable():
    counts = [3, 6]
    assert cr.grade(counts) == cr.GRADE_OFF
    assert cr.grade(counts, max_syllables=6) == cr.GRADE_TOLERATED


# --- 셈에서 빼는 줄 ---


def test_a_line_without_marks_is_listed_but_not_counted():
    result = cr.analyze("마디 표시를 아직 안 붙인 줄이다")
    row = result["lines"][0]
    assert row["grade"] == cr.GRADE_UNMARKED
    assert row["pattern"] == "-"
    assert result["counted"] == 0 and result["unmarked"] == 1


def test_digits_or_latin_letters_are_flagged_and_left_out_of_the_rate():
    result = cr.analyze("오늘은 / 3개만 / 골라 봐요")
    row = result["lines"][0]
    assert row["grade"] == cr.GRADE_SPELL_OUT
    assert result["counted"] == 0 and result["spell_out"] == 1

    latin = cr.analyze("오늘은 / AI가 / 골라 봐요")["lines"][0]
    assert latin["grade"] == cr.GRADE_SPELL_OUT


def test_blank_comment_and_heading_lines_are_skipped_entirely():
    result = cr.analyze("# 제목\n\n## 작은 제목\n# 메모: 여기는 설명\n오늘은 / 우리 동네 / 숨은 맛집 / 가 볼게\n")
    assert [row["line"] for row in result["lines"]] == [5]


def test_list_marker_and_speaker_label_do_not_change_the_count():
    assert _analyze_line("- 오늘은 / 우리 동네 / 숨은 맛집 / 가 볼게")["counts"] == [3, 4, 4, 3]
    assert _analyze_line("내레이션: 오늘은 / 우리 동네 / 숨은 맛집 / 가 볼게")["counts"] == [3, 4, 4, 3]


# --- 비율 ---


def test_rate_counts_hits_and_tolerated_over_counted_lines():
    text = "\n".join([VERIFIED[0][0], VERIFIED[2][0], "한번 / 여섯음절짜리는", "표시 없는 줄"])
    result = cr.analyze(text)
    assert result["counted"] == 3
    assert (result["hit"], result["tolerated"], result["off"]) == (1, 1, 1)
    assert abs(result["rate"] - 2 / 3) < 1e-9


def test_rate_is_none_when_nothing_could_be_counted():
    assert cr.analyze("표시 없는 줄\n또 없는 줄")["rate"] is None


# --- ` / ` 빼기 ---


def test_strip_removes_marks_and_keeps_line_breaks():
    text = "오늘은 / 우리 동네 / 숨은 맛집 / 가 볼게\n\n딱 하나만 / 기억하세요\n"
    assert cr.strip_marks(text) == "오늘은 우리 동네 숨은 맛집 가 볼게\n\n딱 하나만 기억하세요\n"


def test_strip_command_prints_only_the_script(tmp_path, capsys):
    path = _write(tmp_path, "오늘은 / 우리 동네 / 숨은 맛집 / 가 볼게\n")
    assert cr.main([str(path), "--strip"]) == 0
    out = capsys.readouterr().out
    assert out == "오늘은 우리 동네 숨은 맛집 가 볼게\n"


# --- 명령줄 ---


def test_default_run_prints_a_korean_table_and_exits_zero(tmp_path, capsys):
    path = _write(tmp_path, "\n".join(line for line, _, _ in VERIFIED) + "\n한번 / 여섯음절짜리는\n")
    assert cr.main([str(path)]) == 0
    out = capsys.readouterr().out
    assert "3/4/4/3" in out
    assert cr.GRADE_OK in out and cr.GRADE_OFF in out
    assert "뜻이 먼저" in out


def test_utf8_round_trip_keeps_the_text_as_written(tmp_path, capsys):
    path = _write(tmp_path, "오늘은 / 우리 동네 / 숨은 맛집 / 가 볼게\n")
    assert path.read_text(encoding="utf-8").startswith("오늘은")
    assert cr.main([str(path), "--json"]) == 0
    data = json.loads(capsys.readouterr().out)
    assert data["lines"][0]["text"] == "오늘은 / 우리 동네 / 숨은 맛집 / 가 볼게"
    assert data["rate"] == 1.0


def test_min_rate_gates_only_when_asked(tmp_path, capsys):
    path = _write(tmp_path, "한번 / 여섯음절짜리는\n" + VERIFIED[0][0] + "\n")
    assert cr.main([str(path)]) == 0  # 기본은 언제나 통과다
    capsys.readouterr()
    assert cr.main([str(path), "--min-rate", "0.7"]) == 1
    assert cr.main([str(path), "--min-rate", "0.5"]) == 0


def test_min_rate_does_not_fail_when_there_is_nothing_to_judge(tmp_path):
    path = _write(tmp_path, "표시 없는 줄\n")
    assert cr.main([str(path), "--min-rate", "0.9"]) == 0


def test_missing_file_is_a_korean_error_with_exit_two(tmp_path, capsys):
    assert cr.main([str(tmp_path / "없는파일.md")]) == 2
    assert "없습니다" in capsys.readouterr().err


def test_non_utf8_file_is_a_korean_error_with_exit_two(tmp_path, capsys):
    path = tmp_path / "cp949.md"
    path.write_bytes("오늘은 / 우리 동네".encode("cp949"))
    assert cr.main([str(path)]) == 2
    assert "UTF-8" in capsys.readouterr().err


# --- 도구 자체의 제약 ---


def test_the_tool_is_standalone_and_stdlib_only():
    source = (cr.__file__ and open(cr.__file__, encoding="utf-8").read()) or ""
    assert "harness_lib" not in source
    for third_party in ("import yaml", "import requests", "import numpy"):
        assert third_party not in source, third_party


# --- 대본 구역: 양식을 복사해 쓴 파일에서는 "## 대본" 아래만 대본이다 -------------------------

TEMPLATE = Path(__file__).resolve().parents[1] / "skills/video-harness-setup/assets/templates/대본_양식.md.tmpl"


def _script_from_form(body: str) -> str:
    import scaffold  # 양식의 운율 안내 블록은 스캐폴드가 채운다 — 실제로 만들어지는 파일과 같게 한다.

    form = TEMPLATE.read_text(encoding="utf-8").replace("{{channel_name}}", "동네한바퀴")
    form = form.replace("{{script_rhythm_block}}", scaffold.SCRIPT_RHYTHM_FORM_BLOCKS["meter"])
    assert "{{" not in form
    assert "(여기에 쓴다)" in form
    return form.replace("(여기에 쓴다)", body)


def test_only_the_script_section_of_the_form_is_counted():
    text = _script_from_form("오늘은 / 우리 동네 / 숨은 맛집 / 가 볼게\n\n딱 하나만 / 기억하세요")
    result = cr.analyze(text)
    assert [row["grade"] for row in result["lines"]] == [cr.GRADE_OK, cr.GRADE_TOLERATED]
    assert result["counted"] == 2 and result["unmarked"] == 0 and result["spell_out"] == 0
    assert result["scope"] == "section"


def test_strip_on_the_form_prints_only_the_script():
    text = _script_from_form("오늘은 / 우리 동네 / 숨은 맛집 / 가 볼게\n\n\n딱 하나만 / 기억하세요")
    assert cr.strip_marks(text) == "오늘은 우리 동네 숨은 맛집 가 볼게\n\n딱 하나만 기억하세요\n"


def test_the_untouched_form_has_nothing_to_count_or_print():
    text = _script_from_form("(여기에 쓴다)")
    assert cr.analyze(text)["lines"] == []
    assert cr.strip_marks(text) == ""


def test_section_ends_at_the_next_heading_of_same_or_higher_level():
    text = "# 회차\n\n## 대본\n\n오늘은 / 우리 동네 / 숨은 맛집 / 가 볼게\n\n### 메모\n\n이 줄도 / 대본 구역 / 안쪽이다 / 셉니다\n\n## 출처\n\n여기는 / 대본이 / 아닙니다 / 안 셈\n"
    result = cr.analyze(text)
    assert [row["line"] for row in result["lines"]] == [5, 9]


def test_original_line_numbers_are_reported_inside_a_section():
    text = "머리말\n\n## 대본\n딱 하나만 / 기억하세요\n"
    assert [row["line"] for row in cr.analyze(text)["lines"]] == [4]


def test_without_a_script_heading_the_whole_file_is_the_script():
    text = "# 메모\n오늘은 / 우리 동네 / 숨은 맛집 / 가 볼게\n```\n예시 / 줄은 / 세지 / 않는다\n```\n딱 하나만 / 기억하세요\n"
    result = cr.analyze(text)
    assert result["scope"] == "whole-file"
    assert [row["line"] for row in result["lines"]] == [2, 6]
    assert cr.strip_marks(text) == "오늘은 우리 동네 숨은 맛집 가 볼게\n딱 하나만 기억하세요\n"


def test_list_marker_is_dropped_from_the_stripped_script():
    text = "- 냉장고에 / 남은 재료 / 이것만은 / 꼭 넣어\n"
    assert cr.analyze(text)["lines"][0]["pattern"] == "4/4/4/3"
    assert cr.strip_marks(text) == "냉장고에 남은 재료 이것만은 꼭 넣어\n"


def test_report_says_which_scope_was_counted(tmp_path, capsys):
    path = tmp_path / "대본.md"
    path.write_text("## 대본\n딱 하나만 / 기억하세요\n", encoding="utf-8")
    assert cr.main([str(path)]) == 0
    assert '"## 대본" 아래만' in capsys.readouterr().out
