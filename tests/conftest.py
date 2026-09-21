import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "video-harness-setup"
FINDER = ROOT / "skills" / "video-reference-finder"
sys.path.insert(0, str(SKILL / "scripts"))
for sub in ("style", "tts", "transcribe", "stock", "export", "script"):
    sys.path.insert(0, str(SKILL / "assets" / "tools" / sub))
# 레퍼런스 찾기 스킬은 따로 설치될 수 있는 별개의 스킬이다. 세팅 스킬의 모듈을 가리지
# 않도록 맨 뒤에 붙인다 (이름이 겹치면 세팅 스킬 쪽이 이긴다).
sys.path.append(str(FINDER / "scripts"))
