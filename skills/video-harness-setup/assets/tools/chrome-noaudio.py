#!/usr/bin/env python3
"""HyperFrames용 헤드리스 크롬 래퍼.

macOS에서 기본 오디오 출력이 USB 마이크처럼 출력 불가 장치로 잡히면 헤드리스 크롬의
WebAudio 초기화가 멈춰 check·snapshot·render가 "Navigation timeout"으로 실패한다.
오디오 출력을 끄면 해결된다. 영상의 소리는 ffmpeg가 따로 합치므로 잃는 것이 없다.

사용: HYPERFRAMES_BROWSER_PATH=<이 파일> HARNESS_CHROME=<실제 크롬 경로> npx hyperframes render ...
HARNESS_CHROME이 없으면 같은 폴더의 chrome-path.txt를 읽는다.
"""
import os
import sys
from pathlib import Path

real = os.environ.get("HARNESS_CHROME")
if not real:
    note = Path(__file__).with_name("chrome-path.txt")
    real = note.read_text(encoding="utf-8").strip() if note.is_file() else ""
if not real or not Path(real).exists():
    sys.exit("chrome-noaudio: 실제 크롬 경로를 찾지 못했습니다. `npx hyperframes browser path` 결과를 chrome-path.txt에 적으세요.")
os.execv(real, [real, "--disable-audio-output", *sys.argv[1:]])
