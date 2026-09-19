#!/usr/bin/env python3
"""클라우드 TTS(ElevenLabs) 클라이언트. 표준 라이브러리 HTTP만 쓴다.

이 도구는 작업 공간 `도구/tts/`에 복사되어 도구 가상환경 안에서 실행된다.
API 키는 `.env` 파일(`--env`, 기본 현재 디렉터리의 `.env`)에서
`ELEVENLABS_API_KEY`로 읽고 절대 출력하지 않는다.

공식 문서(https://elevenlabs.io/docs/api-reference/text-to-speech/convert) 확인 결과:
- 엔드포인트: POST https://api.elevenlabs.io/v1/text-to-speech/{voice_id}
- 인증 헤더: xi-api-key
- 요청 본문(JSON): {"text", "model_id"}
- 출력 포맷은 쿼리 파라미터 output_format으로 고른다(본문이 아니다).
  mp3는 "mp3_44100_128", 무손실 PCM은 "pcm_24000" 등을 쓸 수 있다.
- eleven_multilingual_v2는 한국어를 포함한 29개 언어를 지원한다(기본 모델로 적합).

--output이 .wav면 output_format=pcm_24000(16비트 리틀엔디안 모노 PCM)을 요청해
표준 라이브러리 wave 모듈로 WAV 헤더를 직접 씌운다. .mp3면 output_format=
mp3_44100_128을 요청해 응답 바이트를 그대로 저장한다.
"""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request
import wave
from pathlib import Path

API_BASE = "https://api.elevenlabs.io"
DEFAULT_MODEL = "eleven_multilingual_v2"
WAV_OUTPUT_FORMAT = "pcm_24000"
WAV_SAMPLE_RATE = 24000
MP3_OUTPUT_FORMAT = "mp3_44100_128"


def read_env(path: Path) -> dict:
    """.env 파일에서 KEY=VALUE 쌍만 읽는다. 주석(#으로 시작)과 빈 줄, '='가 없는 줄은 무시한다."""
    result: dict = {}
    if not path.is_file():
        return result
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, _, value = stripped.partition("=")
        result[key.strip()] = value.strip()
    return result


def build_request(voice_id: str, text: str, model: str, api_key: str) -> tuple[str, dict, bytes]:
    """ElevenLabs TTS 요청의 (url, headers, body)를 만든다. 네트워크 호출은 하지 않는다."""
    url = f"{API_BASE}/v1/text-to-speech/{voice_id}"
    headers = {"xi-api-key": api_key, "Content-Type": "application/json"}
    body = json.dumps({"text": text, "model_id": model}, ensure_ascii=False).encode("utf-8")
    return url, headers, body


def _write_wav_pcm16_mono(path: Path, pcm_bytes: bytes, sample_rate: int) -> None:
    with wave.open(str(path), "wb") as out:
        out.setnchannels(1)
        out.setsampwidth(2)
        out.setframerate(sample_rate)
        out.writeframes(pcm_bytes)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="ElevenLabs 클라우드 TTS로 mp3/wav를 생성한다.")
    parser.add_argument("--voice-id", required=True)
    parser.add_argument("--text", type=Path, required=True, help="생성할 텍스트가 담긴 txt 파일 경로")
    parser.add_argument("--output", type=Path, required=True, help="출력 경로(.mp3 또는 .wav)")
    parser.add_argument("--model", default=DEFAULT_MODEL)
    parser.add_argument("--env", type=Path, default=Path(".env"), help=".env 파일 경로 (기본: 현재 디렉터리의 .env)")
    args = parser.parse_args(argv)

    if not args.text.is_file():
        parser.error(f"텍스트 파일이 없습니다: {args.text}")
    if args.output.exists():
        parser.error(f"출력 파일이 이미 있습니다: {args.output}")
    suffix = args.output.suffix.lower()
    if suffix not in (".mp3", ".wav"):
        parser.error("출력 확장자는 .mp3 또는 .wav만 지원합니다.")

    env = read_env(args.env)
    api_key = env.get("ELEVENLABS_API_KEY")
    if not api_key:
        parser.error(f"{args.env}에 ELEVENLABS_API_KEY가 없습니다.")

    text = args.text.read_text(encoding="utf-8").strip()
    if not text:
        parser.error("생성할 텍스트가 비어 있습니다.")

    url, headers, body = build_request(args.voice_id, text, args.model, api_key)
    is_wav = suffix == ".wav"
    output_format = WAV_OUTPUT_FORMAT if is_wav else MP3_OUTPUT_FORMAT
    request_url = f"{url}?output_format={output_format}"

    req = urllib.request.Request(request_url, data=body, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req) as resp:
            audio_bytes = resp.read()
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"ElevenLabs 요청이 실패했습니다 (HTTP {e.code}): {detail}") from None
    except urllib.error.URLError as e:
        raise RuntimeError(f"ElevenLabs 요청이 실패했습니다: {e.reason}") from None

    args.output.parent.mkdir(parents=True, exist_ok=True)
    if is_wav:
        _write_wav_pcm16_mono(args.output, audio_bytes, WAV_SAMPLE_RATE)
    else:
        args.output.write_bytes(audio_bytes)

    print(f"저장: {args.output.resolve()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
