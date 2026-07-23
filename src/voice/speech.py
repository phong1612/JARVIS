import subprocess
from pathlib import Path
import tempfile
import os

BASE_DIR = Path(__file__).parent

PIPER_MODEL = (
    BASE_DIR 
    / "Voices"
    / "en_GB-northern_english_male-medium.onnx"
)


def speak(text: str):
    """
    Convert text to speech using Piper and play it.
    """

    if not PIPER_MODEL.exists():
        print(f"Piper model not found: {PIPER_MODEL}")
        return

    with tempfile.NamedTemporaryFile(
        suffix=".wav",
        delete=False
    ) as tmp:

        tmp_file = tmp.name
    try:
        piper = subprocess.run(
            [
                "piper",
                "--model",
                str(PIPER_MODEL),
                "--output_file",
                tmp_file
            ],
            input=text.encode("utf-8"),
            capture_output = True
        )
        if piper.returncode != 0:
            print(f"Piper failed: {piper.stderr.decode(errors='ignore')}")
            return
        
        subprocess.run(["afplay", tmp_file])
    finally:
        if os.path.exists(tmp_file):
            os.remove(tmp_file)

    