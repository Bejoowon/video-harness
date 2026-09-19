#!/usr/bin/env python3
"""로컬 음성 복제(voice cloning) TTS. Apple Silicon + mlx-audio(Qwen3-TTS) 전용.

이 도구는 작업 공간 `도구/tts/`에 복사되어 도구 가상환경(mlx-audio 포함) 안에서
실행된다. 모델 경로·레퍼런스 음성·레퍼런스 대본은 항상 인자로만 받는다(고정
경로 없음). 무거운 임포트(mlx_audio, mlx, numpy)는 main() 안에서만 한다 —
그래야 이 파일이 해당 패키지가 없는 개발 가상환경에서도 순수 함수 테스트가
돈다.

파일럿 채널의 local-tts/generate.py를 일반화했다: 문단마다 따로 생성해 이어 붙이되
문단 사이에 침묵을 추가하지 않는다(침묵을 넣으면 목소리가 끊겨 들린다).
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
import tempfile
from pathlib import Path

_BLANK_LINE_RE = re.compile(r"\n\s*\n")


def split_paragraphs(text: str) -> list[str]:
    """빈 줄로 나뉜 문단 목록을 돌려준다. 앞뒤 공백은 문단마다 정리하고 빈 문단은 버린다."""
    parts = _BLANK_LINE_RE.split(text.strip())
    return [p.strip() for p in parts if p.strip()]


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="로컬 음성 복제 TTS로 wav를 생성한다(mlx-audio, Apple Silicon 전용).")
    parser.add_argument("--model", type=Path, required=True, help="mlx-audio 모델 디렉터리")
    parser.add_argument("--ref-audio", type=Path, required=True, help="레퍼런스 음성 파일(wav/m4a/mov)")
    parser.add_argument("--ref-text", type=Path, required=True, help="레퍼런스 음성의 대본 txt 파일")
    parser.add_argument("--text", type=Path, required=True, help="생성할 대본 txt 파일")
    parser.add_argument("--output", type=Path, required=True, help="출력 wav 경로")
    parser.add_argument("--by-paragraph", action="store_true", help="빈 줄로 나눈 문단마다 생성해 이어 붙인다")
    parser.add_argument("--lang-code", default="korean", help="mlx-audio lang_code (기본 korean)")
    args = parser.parse_args(argv)

    for path, label in ((args.model, "모델 디렉터리"), (args.ref_audio, "레퍼런스 음성"), (args.ref_text, "레퍼런스 대본"), (args.text, "생성 대본")):
        if not path.exists():
            parser.error(f"{label} 경로가 없습니다: {path}")
    if args.output.exists():
        parser.error(f"출력 파일이 이미 있습니다: {args.output}")

    reference = args.ref_text.read_text(encoding="utf-8").strip()
    text = args.text.read_text(encoding="utf-8").strip()
    if not reference or not text:
        parser.error("레퍼런스 대본과 생성 대본은 비어 있으면 안 됩니다.")

    paragraphs = split_paragraphs(text) if args.by_paragraph else [text]
    if not paragraphs:
        parser.error("생성할 텍스트가 비어 있습니다.")

    import numpy as np
    import mlx.core as mx
    import wave
    from mlx_audio.tts.utils import load_model

    model = load_model(str(args.model))

    with tempfile.TemporaryDirectory() as tmp:
        ref_wav = Path(tmp) / "reference.wav"
        subprocess.run(
            ["ffmpeg", "-v", "error", "-i", str(args.ref_audio), "-ac", "1", "-ar", "24000", "-c:a", "pcm_s16le", str(ref_wav)],
            check=True,
        )
        with wave.open(str(ref_wav)) as f:
            samples = np.frombuffer(f.readframes(f.getnframes()), dtype="<i2").astype(np.float32) / 32768

        paragraph_audio: list = []
        paragraph_seconds: list[float] = []
        rate = None
        for paragraph in paragraphs:
            chunks = []
            for result in model.generate(
                text=paragraph,
                ref_audio=mx.array(samples),
                ref_text=reference,
                lang_code=args.lang_code,
                max_tokens=2048,
            ):
                chunks.append(np.asarray(result.audio).reshape(-1))
                rate = result.sample_rate
            if not chunks:
                raise RuntimeError(f"생성된 오디오가 없습니다: {paragraph!r}")
            audio = np.concatenate(chunks)
            paragraph_audio.append(audio)
            paragraph_seconds.append(len(audio) / rate)

        full_audio = np.concatenate(paragraph_audio)
        if not np.isfinite(full_audio).all():
            raise RuntimeError("출력에 유효하지 않은 샘플이 있습니다.")

        args.output.parent.mkdir(parents=True, exist_ok=True)
        with wave.open(str(args.output), "wb") as out:
            out.setnchannels(1)
            out.setsampwidth(2)
            out.setframerate(rate)
            out.writeframes((np.clip(full_audio, -1, 1) * 32767).astype("<i2").tobytes())

        if args.by_paragraph:
            segments_path = Path(str(args.output) + ".segments.json")
            segments_path.write_text(
                json.dumps({"paragraphs": paragraph_seconds}, ensure_ascii=False, indent=2),
                encoding="utf-8",
            )

    print(f"저장: {args.output.resolve()} / {len(full_audio) / rate:.2f}초")
    return 0


if __name__ == "__main__":
    sys.exit(main())
