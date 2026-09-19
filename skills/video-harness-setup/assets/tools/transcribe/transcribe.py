#!/usr/bin/env python3
"""오디오를 전사해 JSON(+SRT)으로 저장한다. Apple Silicon은 mlx-whisper, 그 외는
faster-whisper를 쓴다.

이 도구는 작업 공간 `도구/transcribe/`에 복사되어 도구 가상환경 안에서
실행된다. 무거운 임포트(mlx_whisper, faster_whisper)는 각 엔진을 실제로
쓰는 함수 안에서만 한다 — 그래야 이 파일이 해당 패키지가 없는 개발
가상환경에서도 순수 함수 테스트가 돈다.

공식 문서 확인 결과:
- mlx_whisper.transcribe(path, path_or_hf_repo=..., word_timestamps=True, language=...)는
  {"text", "language", "segments":[{...,"words":[{"word","start","end","probability"}]}]}를
  돌려준다(word_timestamps=True일 때만 "words"가 채워진다).
- faster_whisper.WhisperModel(model, device="auto", compute_type="auto").transcribe(path,
  word_timestamps=True, language=...)는 (segments 제너레이터, info)를 돌려주고,
  각 Segment는 start/end/text/words 속성을, 각 Word는 word/start/end/probability
  속성을 갖는다.
- faster-whisper는 "large-v3-turbo"라는 이름을 자체적으로
  mobiuslabsgmbh/faster-whisper-large-v3-turbo로 매핑하므로 그대로 넘기면 된다.
  mlx-whisper는 그런 별칭이 없어 mlx-community/whisper-large-v3-turbo를 직접
  path_or_hf_repo로 줘야 한다.
"""

from __future__ import annotations

import argparse
import json
import platform
import sys
from pathlib import Path

# 친숙한 모델 이름 -> 엔진별 실제 식별자. faster-whisper는 별도 매핑이 필요 없어
# 표에 없는 이름은 그대로 통과시킨다.
_MLX_MODEL_MAP = {
    "large-v3-turbo": "mlx-community/whisper-large-v3-turbo",
}


def pick_engine(requested: str, apple_silicon: bool) -> str:
    """--engine 요청값과 Apple Silicon 여부로 실제 쓸 엔진을 정한다."""
    if requested == "auto":
        return "mlx-whisper" if apple_silicon else "faster-whisper"
    if requested not in ("mlx-whisper", "faster-whisper"):
        raise ValueError(f"알 수 없는 전사 엔진입니다: {requested}")
    if requested == "mlx-whisper" and not apple_silicon:
        raise ValueError("mlx-whisper는 Apple Silicon(M 시리즈)에서만 쓸 수 있습니다.")
    return requested


def _format_srt_timestamp(seconds: float) -> str:
    total_ms = round(seconds * 1000)
    hours, rem = divmod(total_ms, 3_600_000)
    minutes, rem = divmod(rem, 60_000)
    secs, ms = divmod(rem, 1000)
    return f"{hours:02d}:{minutes:02d}:{secs:02d},{ms:03d}"


def to_srt(segments: list[dict]) -> str:
    """segments를 SRT 자막 텍스트로 바꾼다. 빈 세그먼트는 건너뛰고 번호를 다시 매긴다."""
    blocks = []
    index = 1
    for seg in segments:
        text = seg["text"].strip()
        if not text:
            continue
        start = _format_srt_timestamp(seg["start"])
        end = _format_srt_timestamp(seg["end"])
        blocks.append(f"{index}\n{start} --> {end}\n{text}")
        index += 1
    if not blocks:
        return ""
    return "\n\n".join(blocks) + "\n\n"


def _apple_silicon() -> bool:
    return platform.system() == "Darwin" and platform.machine() == "arm64"


def _run_mlx_whisper(audio: Path, model: str, language: str) -> dict:
    import mlx_whisper

    result = mlx_whisper.transcribe(
        str(audio),
        path_or_hf_repo=_MLX_MODEL_MAP.get(model, model),
        word_timestamps=True,
        language=language,
    )
    segments = []
    for seg in result["segments"]:
        words = [{"word": w["word"], "start": w["start"], "end": w["end"]} for w in seg.get("words", [])]
        segments.append({"start": seg["start"], "end": seg["end"], "text": seg["text"], "words": words})
    return {"text": result["text"], "segments": segments}


def _run_faster_whisper(audio: Path, model: str, language: str) -> dict:
    from faster_whisper import WhisperModel

    whisper_model = WhisperModel(model, device="auto", compute_type="auto")
    segments_iter, _info = whisper_model.transcribe(str(audio), word_timestamps=True, language=language)

    segments = []
    text_parts = []
    for seg in segments_iter:
        words = [{"word": w.word, "start": w.start, "end": w.end} for w in (seg.words or [])]
        segments.append({"start": seg.start, "end": seg.end, "text": seg.text, "words": words})
        text_parts.append(seg.text)
    return {"text": "".join(text_parts), "segments": segments}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="오디오를 전사해 JSON(+SRT)으로 저장한다.")
    parser.add_argument("audio", type=Path, help="전사할 오디오 파일")
    parser.add_argument("--out", type=Path, required=True, help="출력 JSON 경로")
    parser.add_argument("--engine", default="auto", choices=["auto", "mlx-whisper", "faster-whisper"])
    parser.add_argument("--model", default="large-v3-turbo")
    parser.add_argument("--language", default="ko")
    parser.add_argument("--srt", type=Path, help="함께 만들 SRT 경로(선택)")
    args = parser.parse_args(argv)

    if not args.audio.is_file():
        parser.error(f"오디오 파일이 없습니다: {args.audio}")
    if args.out.exists():
        parser.error(f"출력 파일이 이미 있습니다: {args.out}")
    if args.srt and args.srt.exists():
        parser.error(f"SRT 출력 파일이 이미 있습니다: {args.srt}")

    try:
        engine = pick_engine(args.engine, _apple_silicon())
    except ValueError as e:
        parser.error(str(e))
        return 2  # pragma: no cover - parser.error already exits

    if engine == "mlx-whisper":
        result = _run_mlx_whisper(args.audio, args.model, args.language)
    else:
        result = _run_faster_whisper(args.audio, args.model, args.language)

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(result, ensure_ascii=False, indent=2), encoding="utf-8")

    if args.srt:
        args.srt.parent.mkdir(parents=True, exist_ok=True)
        args.srt.write_text(to_srt(result["segments"]), encoding="utf-8")

    print(f"저장: {args.out.resolve()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
