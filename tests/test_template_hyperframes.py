import json, re
from pathlib import Path

T = Path(__file__).resolve().parents[1] / "skills/video-harness-setup/assets/episode-template-hyperframes"


def html():
    return (T / "index.html").read_text(encoding="utf-8")


def test_contract():
    h = html()
    assert 'data-composition-id="main"' in h and 'data-width="1080"' in h and 'data-height="1920"' in h
    assert 'window.__timelines["main"]' in h and "paused: true" in h
    assert "<template" not in h                       # standalone 루트는 template로 감싸지 않는다
    assert 'src="assets/gsap.min.js"' in h            # CDN 아님
    assert "crossorigin" not in h
    assert re.search(r'<audio[^>]*id="narration"', h)  # audio는 id 필수


def test_uses_tokens_not_literals():
    h = html()
    assert 'href="tokens.css"' in h
    style = re.search(r"<style>(.*?)</style>", h, re.S).group(1)
    assert not re.findall(r"#[0-9a-fA-F]{6}\b", style), "색은 tokens.css 변수로만"
    assert "var(--f-caption)" in style and "var(--l-caption-bottom)" in style


def test_no_px_literals_outside_font_face():
    h = html()
    style = re.search(r"<style>(.*?)</style>", h, re.S).group(1)
    style_no_font_face = re.sub(r"@font-face\s*\{[^}]*\}", "", style)
    assert not re.findall(r"\d+px", style_no_font_face), "위치·크기 값은 tokens.css 변수로만 (@font-face 제외)"


def test_slots_present():
    for slot in ["title-text", "caption-text", "source-text", "footage"]:
        assert f'id="{slot}"' in html(), slot


def test_no_clip_visibility_tween():
    assert "autoAlpha" not in html()


def test_pinned_version():
    pkg = json.loads((T / "package.json").read_text(encoding="utf-8"))
    assert all("hyperframes@0.8.43" in v for v in pkg["scripts"].values())
    assert (T / "assets/gsap.min.js").stat().st_size > 50_000


def test_gsap_license_present():
    p = T / "assets/gsap-LICENSE.txt"
    text = p.read_text(encoding="utf-8")
    assert text.strip()
    assert "GSAP" in text or "GreenSock" in text
