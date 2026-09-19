import json
import postprocess as pp
import generate_local_mlx as gl
import generate_cloud as gc
import transcribe as tr


def test_filter_speed_only():
    assert pp.audio_filter(1.2, 0) == "aresample=48000,atempo=1.2"


def test_filter_pitch_keeps_total_speed():
    f = pp.audio_filter(1.2, 1)
    assert "asetrate=50854" in f
    tempo = float(f.split("atempo=")[1])
    assert abs(tempo * (50854 / 48000) - 1.2) < 1e-6


def test_split_paragraphs():
    assert gl.split_paragraphs("첫 문단.\n이어짐.\n\n\n둘째 문단.\n") == ["첫 문단.\n이어짐.", "둘째 문단."]


def test_cloud_request_shape():
    url, headers, body = gc.build_request("VOICE", "안녕하세요.", "eleven_multilingual_v2", "k")
    assert url.endswith("/v1/text-to-speech/VOICE") and headers["xi-api-key"] == "k"
    assert json.loads(body)["text"] == "안녕하세요."


def test_read_env_ignores_comments(tmp_path):
    p = tmp_path / ".env"
    p.write_text("# 주석\nELEVENLABS_API_KEY=abc\nEMPTY=\n", encoding="utf-8")
    assert gc.read_env(p) == {"ELEVENLABS_API_KEY": "abc", "EMPTY": ""}


def test_pick_engine():
    assert tr.pick_engine("auto", True) == "mlx-whisper"
    assert tr.pick_engine("auto", False) == "faster-whisper"
    assert tr.pick_engine("faster-whisper", True) == "faster-whisper"


def test_pick_engine_rejects_mlx_off_apple_silicon():
    try:
        tr.pick_engine("mlx-whisper", apple_silicon=False)
    except ValueError as e:
        assert "Apple Silicon" in str(e)
    else:
        raise AssertionError("ValueError를 기대했습니다")


def test_to_srt():
    srt = tr.to_srt([{"start": 0.0, "end": 1.5, "text": " 안녕하세요"}, {"start": 1.5, "end": 3.25, "text": "반갑습니다"}])
    assert srt.startswith("1\n00:00:00,000 --> 00:00:01,500\n안녕하세요\n\n2\n00:00:01,500 --> 00:00:03,250\n반갑습니다")


def test_to_srt_skips_empty_segments_and_renumbers():
    srt = tr.to_srt([
        {"start": 0.0, "end": 1.0, "text": "하나"},
        {"start": 1.0, "end": 2.0, "text": "   "},
        {"start": 2.0, "end": 3.0, "text": "둘"},
    ])
    assert srt == "1\n00:00:00,000 --> 00:00:01,000\n하나\n\n2\n00:00:02,000 --> 00:00:03,000\n둘\n\n"
