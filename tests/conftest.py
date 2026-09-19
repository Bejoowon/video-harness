import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / "skills" / "video-harness-setup"
sys.path.insert(0, str(SKILL / "scripts"))
for sub in ("style", "tts", "transcribe", "stock", "export"):
    sys.path.insert(0, str(SKILL / "assets" / "tools" / sub))
