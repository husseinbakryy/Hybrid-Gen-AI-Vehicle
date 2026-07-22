import base64
import os
import subprocess
import sys
from pathlib import Path
from typing import Optional

def play_audio_file(audio_path: str | Path) -> Path:
    output_path = Path(audio_path)
    if not output_path.exists():
        raise FileNotFoundError(f"Audio file not found: {output_path}")

    if sys.platform.startswith("win"):
        try:
            os.startfile(str(output_path))  # type: ignore[attr-defined]
        except Exception:
            subprocess.Popen(
                [
                    "powershell",
                    "-NoProfile",
                    "-Command",
                    f"Start-Process -FilePath '{output_path}' -Verb open",
                ]
            )
        return output_path

    if sys.platform == "darwin":
        subprocess.Popen(["open", str(output_path)])
    else:
        subprocess.Popen(["xdg-open", str(output_path)])

    return output_path

def save_base64_audio(base64_string: str, output_file: str) -> Path:
    if not base64_string:
        raise ValueError("Base64 audio string is empty")

    if base64_string.startswith("data:"):
        base64_string = base64_string.split(",", 1)[1]

    audio_bytes = base64.b64decode(base64_string)
    output_path = Path(output_file)
    output_path.write_bytes(audio_bytes)
    print(f"Saved audio to {output_path}")
    return output_path

def play_base64_audio(base64_string: str, output_file: str = "audio_output.mp3") -> Path:
    output_path = save_base64_audio(base64_string, output_file)
    print(f"Playing audio: {output_path}")
    return play_audio_file(output_path)

if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python play_audio.py <base64_string> [output_file]")
        sys.exit(1)

    base64_string = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else "audio_output.mp3"
    play_base64_audio(base64_string, output_file)
    print(f"Saved and opened {output_file}")