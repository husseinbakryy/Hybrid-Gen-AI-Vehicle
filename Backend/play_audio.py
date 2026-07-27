import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Optional
from urllib import request

from dotenv import load_dotenv

_THIS_DIR = Path(__file__).resolve().parent
load_dotenv(_THIS_DIR / ".env")


def play_audio_file(audio_path: str | Path) -> Path:
    """Play an audio file headlessly at 1.7x speed."""
    output_path = Path(audio_path).resolve()
    if not output_path.exists():
        raise FileNotFoundError(f"Audio file not found: {output_path}")

    if sys.platform.startswith("win"):
        # MediaPlayer with SpeedRatio set to 1.7
        ps_script = (
            f"Add-Type -AssemblyName presentationCore; "
            f"$player = New-Object System.Windows.Media.MediaPlayer; "
            f"$player.Open([Uri]'{output_path}'); "
            f"Start-Sleep -Milliseconds 100; "
            f"$player.SpeedRatio = 1.7; "
            f"$player.Play(); "
            f"Start-Sleep -Milliseconds 200; "
            f"while ($player.NaturalDuration.HasTimeSpan -eq $false) {{ Start-Sleep -Milliseconds 100 }}; "
            f"$duration = $player.NaturalDuration.TimeSpan.TotalSeconds / 1.7; "
            f"Start-Sleep -Seconds ([math]::Ceiling($duration)); "
            f"$player.Close()"
        )
        try:
            subprocess.run(
                ["powershell", "-NoProfile", "-Command", ps_script],
                timeout=60,
                check=False,
            )
        except Exception as exc:
            print(f"[Audio] PowerShell playback failed: {exc}")
        return output_path

    if sys.platform == "darwin":
        subprocess.run(["afplay", "-r", "1.7", str(output_path)], check=False)
    else:
        subprocess.run(["ffplay", "-nodisp", "-autoexit", "-af", "atempo=1.7", str(output_path)], check=False)

    return output_path


def _is_valid_mp3(data: bytes) -> bool:
    if len(data) < 4:
        return False
    if data[:3] == b"ID3":
        return True
    if data[0] == 0xFF and (data[1] & 0xE0) == 0xE0:
        return True
    return False


def _generate_tts_gtts(text: str, output_file: str) -> Optional[Path]:
    try:
        from gtts import gTTS
    except ImportError:
        print("[TTS] gTTS not installed.")
        return None

    try:
        tts = gTTS(text=text, lang="en", slow=False)
        output_path = Path(output_file)
        tts.save(str(output_path))
        return output_path
    except Exception as exc:
        print(f"[TTS/gTTS] Failed: {exc}")
        return None


def generate_tts_audio(
    text: str,
    output_file: str | None = None,
    voice: str = "alloy",
    model: str = "openai/tts-1",
) -> Optional[Path]:
    api_key = os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENAI_API_KEY")

    if not text or not text.strip():
        return None

    if len(text) > 4000:
        text = text[:4000] + "..."

    if output_file is None:
        output_file = str(_THIS_DIR / "tts_recommendation.mp3")

    if api_key:
        tts_url = "https://openrouter.ai/api/v1/audio/speech"
        payload = {
            "model": model,
            "input": text,
            "voice": voice,
            "response_format": "mp3",
            "speed": 1.7,  # Set API speed parameter to 1.7
        }

        req = request.Request(
            tts_url,
            data=json.dumps(payload).encode("utf-8"),
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
                "HTTP-Referer": os.getenv("OPENROUTER_HTTP_REFERER", "http://localhost"),
                "X-Title": os.getenv("OPENROUTER_APP_TITLE", "Hybrid-Vehicle-Agent"),
            },
            method="POST",
        )

        try:
            with request.urlopen(req, timeout=15) as response:
                audio_bytes = response.read()

            if audio_bytes and len(audio_bytes) >= 100 and _is_valid_mp3(audio_bytes):
                output_path = Path(output_file)
                output_path.write_bytes(audio_bytes)
                return output_path
        except Exception as exc:
            print(f"[TTS] OpenRouter fast-path failed: {exc}. Falling back to gTTS.")

    return _generate_tts_gtts(text, output_file)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        text_input = sys.argv[1]
        output_file = sys.argv[2] if len(sys.argv) > 2 else "audio_output.mp3"
        path = generate_tts_audio(text_input, output_file)
        if path:
            play_audio_file(path)