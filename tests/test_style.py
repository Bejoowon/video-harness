import pytest
yaml = pytest.importorskip("yaml")
from pathlib import Path
import build_tokens as bt
import check_style as cs
import scaffold as s

TMPL = Path(__file__).resolve().parents[1] / "skills/video-harness-setup/assets/templates/frame.md.tmpl"


def frame(tmp_path):
    p = tmp_path / "frame.md"
    p.write_text(TMPL.read_text(encoding="utf-8").replace("{{channel_name}}", "동네한바퀴"), encoding="utf-8")
    return p


def frame_variant(tmp_path, consistency):
    """scaffold가 실제로 쓰는 일관성 수준 변형 frame.md를 만든다."""
    text = TMPL.read_text(encoding="utf-8").replace("{{channel_name}}", "테스트채널")
    text = s._set_frame_consistency(text, {"consistency": consistency})
    p = tmp_path / f"frame-{consistency}.md"
    p.write_text(text, encoding="utf-8")
    return p


def test_template_parses_and_is_draft(tmp_path):
    f = bt.load_frame(frame(tmp_path))
    assert f["status"] == "draft" and f["typography"]["caption"]["size"] == 80


def test_load_frame_raises_on_missing_frontmatter(tmp_path):
    p = tmp_path / "frame.md"
    p.write_text("# 그냥 제목\n본문만 있고 머리말이 없다.\n", encoding="utf-8")
    with pytest.raises(ValueError, match="머리말"):
        bt.load_frame(p)


def test_load_frame_raises_on_unclosed_frontmatter(tmp_path):
    p = tmp_path / "frame.md"
    p.write_text("---\nstatus: draft\ncanvas: {width: 1080, height: 1920, fps: 30}\n", encoding="utf-8")
    with pytest.raises(ValueError, match="닫히지"):
        bt.load_frame(p)


def test_css_has_all_vars(tmp_path):
    css = bt.to_css(bt.load_frame(frame(tmp_path)))
    for v in ["--c-accent: #FFE14D", "--f-caption-size: 80px", "--l-caption-bottom: 420px", "--l-source-bottom: 96px", "--m-in-ease: power3.out"]:
        assert v in css, v


def test_theme_ts_exports_const(tmp_path):
    ts = bt.to_theme_ts(bt.load_frame(frame(tmp_path)))
    assert ts.startswith("export const theme = ") and "captionSize: 80" in ts
    assert "canvas:" in ts
    assert "sourceBottom: 96" in ts


def test_extract_values():
    v = cs.extract_values('h1{font-family:"Paperlogy";font-size:96px;color:#FFE14D} tl.from(x,{ease:"back.out(2)"})')
    assert v["colors"] == {"#ffe14d"} and v["fonts"] == {"Paperlogy"} and v["font_sizes"] == {96}
    assert v["eases"] == {"back.out(2)"}


def test_locked_font_violation_is_error(tmp_path):
    f = bt.load_frame(frame(tmp_path))
    src = tmp_path / "index.html"
    src.write_text("<style>p{font-family:'Comic Sans MS';font-size:80px}</style>", encoding="utf-8")
    r = cs.check(f, [src])
    assert any("Comic Sans MS" in e for e in r["errors"])


def test_unknown_color_is_free_note_when_illustration_free(tmp_path):
    f = bt.load_frame(frame(tmp_path))
    src = tmp_path / "index.html"
    src.write_text("<style>svg{fill:#123456}</style>", encoding="utf-8")
    r = cs.check(f, [src])
    assert r["errors"] == [] and any("#123456" in n for n in r["free_notes"])


def test_var_reference_passes(tmp_path):
    f = bt.load_frame(frame(tmp_path))
    src = tmp_path / "index.html"
    src.write_text("<style>p{color:var(--c-accent);font-family:var(--f-caption)}</style>", encoding="utf-8")
    assert cs.check(f, [src])["errors"] == []


def test_foreign_ease_is_warning_not_error(tmp_path):
    f = bt.load_frame(frame(tmp_path))
    src = tmp_path / "index.html"
    src.write_text('<script>tl.from("#a",{ease:"elastic.out(1,0.3)"})</script>', encoding="utf-8")
    r = cs.check(f, [src])
    assert r["errors"] == [] and any("elastic" in w for w in r["warnings"])


def test_js_literal_font_family_is_error(tmp_path):
    f = bt.load_frame(frame(tmp_path))
    src = tmp_path / "TitleBar.tsx"
    src.write_text('const s = { fontFamily: "Comic Sans MS" };', encoding="utf-8")
    r = cs.check(f, [src])
    assert any("Comic Sans MS" in e for e in r["errors"])


def test_js_literal_font_size_is_error(tmp_path):
    f = bt.load_frame(frame(tmp_path))
    src = tmp_path / "TitleBar.tsx"
    src.write_text("const s = { fontSize: 72 };", encoding="utf-8")
    r = cs.check(f, [src])
    assert any("72" in e for e in r["errors"])


def test_js_theme_reference_font_family_and_size_pass(tmp_path):
    f = bt.load_frame(frame(tmp_path))
    src = tmp_path / "TitleBar.tsx"
    src.write_text(
        "const s = { fontFamily: theme.typography.caption.family, "
        "fontSize: theme.typography.caption.size };",
        encoding="utf-8",
    )
    r = cs.check(f, [src])
    assert r["errors"] == []


def test_js_template_literal_theme_font_family_passes(tmp_path):
    # 실제 Remotion 템플릿 관례: `${theme.typography.titleFamily}, "Apple SD Gothic Neo", ...`
    f = bt.load_frame(frame(tmp_path))
    src = tmp_path / "TitleBar.tsx"
    src.write_text(
        'const s = { fontFamily: `${theme.typography.titleFamily}, "Apple SD Gothic Neo", '
        '"Malgun Gothic", sans-serif` };',
        encoding="utf-8",
    )
    r = cs.check(f, [src])
    assert r["errors"] == []


def test_all_consistency_variants_parse(tmp_path):
    for value in ("fixed", "variation", "decide-later"):
        f = bt.load_frame(frame_variant(tmp_path, value))
        assert f["status"] == "draft"
        assert isinstance(f["consistency"]["choose"], dict)
        assert bt.to_css(f).startswith(bt.GENERATED_CSS_HEADER)
        assert "canvas:" in bt.to_theme_ts(f)
    assert bt.load_frame(frame_variant(tmp_path, "fixed"))["consistency"]["choose"] == {}


def test_fixed_frame_makes_unknown_color_an_error(tmp_path):
    f = bt.load_frame(frame_variant(tmp_path, "fixed"))
    assert "illustration_colors" not in f["consistency"]["free"]
    src = tmp_path / "index.html"
    src.write_text("<style>svg{fill:#123456}</style>", encoding="utf-8")
    r = cs.check(f, [src])
    assert any("#123456" in e for e in r["errors"])
    assert r["free_notes"] == []


def test_declared_free_illustration_colors_beat_locked_accent(tmp_path):
    """사람이 frame.md를 고쳐 강조색을 잠그고도 삽화 색을 자유로 두면 선언을 따른다."""
    f = bt.load_frame(frame_variant(tmp_path, "fixed"))
    f["consistency"]["free"] = ["illustration_colors", "footage"]
    assert "colors.accent" in f["consistency"]["locked"]
    src = tmp_path / "index.html"
    src.write_text("<style>svg{fill:#123456}</style>", encoding="utf-8")
    r = cs.check(f, [src])
    assert r["errors"] == [] and any("#123456" in n for n in r["free_notes"])


def test_fixed_frame_rejects_colors_from_accent_sets(tmp_path):
    """포맷 고정형은 `choose`가 비어 있으므로 `accent_sets`의 색도 후보가 아니다(M14).

    `colors.accent` 자체(`#FFE14D`)는 여전히 통과한다 — 잠긴 것은 "회차마다 고르는
    것"이지 채널 강조색이 아니다.
    """
    f = bt.load_frame(frame_variant(tmp_path, "fixed"))
    f["colors"]["accent_sets"] = [["#FFE14D", "#FF5A5A"]]
    src = tmp_path / "index.html"
    src.write_text("<style>p{color:#FF5A5A}h1{color:#FFE14D}</style>", encoding="utf-8")
    errors = cs.check(f, [src])["errors"]
    assert any("#ff5a5a" in e.lower() for e in errors), errors
    assert not any("#ffe14d" in e.lower() for e in errors), errors


def test_decide_later_keeps_unknown_color_as_free_note(tmp_path):
    f = bt.load_frame(frame_variant(tmp_path, "decide-later"))
    src = tmp_path / "index.html"
    src.write_text("<style>svg{fill:#123456}</style>", encoding="utf-8")
    r = cs.check(f, [src])
    assert r["errors"] == [] and any("#123456" in n for n in r["free_notes"])


def test_js_easing_keyword_string_literal_is_warning_not_error(tmp_path):
    f = bt.load_frame(frame(tmp_path))
    src = tmp_path / "easing.ts"
    src.write_text('const e = { easing: "elastic.out(1,0.3)" };', encoding="utf-8")
    r = cs.check(f, [src])
    assert r["errors"] == [] and any("elastic" in w for w in r["warnings"])


# --- `choose`가 비면 후보 색도 후보가 아니다 (M14) ---


def _frame_with_accent_sets(tmp_path, consistency, name):
    text = TMPL.read_text(encoding="utf-8").replace("{{channel_name}}", "테스트채널")
    text = text.replace(
        'accent_sets: []         # choose 후보. 예: [["#FFE14D","#FF5A5A"],["#7CE0D6","#FFE14D"]]',
        'accent_sets: [["#FFE14D", "#FF5A5A"]]',
    )
    text = s._set_frame_consistency(text, {"consistency": consistency})
    p = tmp_path / name
    p.write_text(text, encoding="utf-8")
    return bt.load_frame(p)


def _source_using_accent_set_color(tmp_path):
    src = tmp_path / "index.html"
    src.write_text("<style>p{color:#FF5A5A}</style>", encoding="utf-8")
    return src


def test_accent_set_color_is_allowed_when_accent_is_choosable(tmp_path):
    f = _frame_with_accent_sets(tmp_path, "variation", "frame-variation.md")
    assert cs.check(f, [_source_using_accent_set_color(tmp_path)])["errors"] == []


def test_accent_set_color_is_rejected_when_choose_is_empty(tmp_path):
    """포맷 고정형은 `choose`가 비어 강조색까지 고정된다 — 검사기도 그 선언을 따른다."""
    f = _frame_with_accent_sets(tmp_path, "fixed", "frame-fixed.md")
    r = cs.check(f, [_source_using_accent_set_color(tmp_path)])
    assert any("#ff5a5a" in e.lower() for e in r["errors"]), r
