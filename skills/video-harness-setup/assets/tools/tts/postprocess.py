#!/usr/bin/env python3
"""오디오 파일의 속도·피치를 ffmpeg로 후처리한다.

이 도구는 작업 공간 `도구/tts/`에 복사되어 도구 가상환경 안에서 실행된다.
표준 라이브러리(subprocess)만 쓰며 무거운 서드파티 의존성은 없다.
"""

from __future__ import annotations

import argparse
import subprocess
import sys
from pathlib import Path


def audio_filter(speed: float, pitch_semitones: float) -> str:
    """speed(배속)와 pitch_semitones(반음)로 ffmpeg -af 필터 문자열을 만든다.

    pitch가 0이면 속도만 바꾸고(atempo), 아니면 asetrate로 피치를 올린 뒤
    atempo로 전체 속도를 speed에 맞춘다(파일럿 채널 render_episode.py의 검증된 식).
    """
    if pitch_semitones == 0:
        return f"aresample=48000,atempo={speed}"
    rate = round(48000 * 2 ** (pitch_semitones / 12))
    tempo = speed / (rate / 48000)
    return f"aresample=48000,asetrate={rate},aresample=48000,atempo={tempo:.10f}"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="오디오 속도·피치를 ffmpeg로 후처리한다.")
    parser.add_argument("input", type=Path, help="입력 오디오 파일")
    parser.add_argument("output", type=Path, help="출력 오디오 파일")
    parser.add_argument("--speed", type=float, default=1.0, help="배속 (기본 1.0)")
    parser.add_argument("--pitch", type=float, default=0, help="피치 조정, 반음 단위 (기본 0)")
    args = parser.parse_args(argv)

    if not args.input.is_file():
        parser.error(f"입력 파일이 없습니다: {args.input}")
    if args.output.exists():
        parser.error(f"출력 파일이 이미 있습니다: {args.output}")

    filt = audio_filter(args.speed, args.pitch)

    args.output.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(
        ["ffmpeg", "-v", "error", "-i", str(args.input), "-af", filt, "-n", str(args.output)],
        check=True,
    )
    print(f"저장: {args.output.resolve()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
