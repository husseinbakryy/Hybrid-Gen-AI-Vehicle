import base64
import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Optional
from urllib import error, request

from dotenv import load_dotenv

# Load .env from the same directory as this file
_THIS_DIR = Path(__file__).resolve().parent
load_dotenv(_THIS_DIR / ".env")


def play_audio_file(audio_path: str | Path) -> Path:
    """Play an audio file (mp3/wav) directly without opening a media-player GUI.

    On Windows the function drives the Windows Media Player COM object via
    PowerShell so playback is headless (no window pops up) and truly
    automatic.  On macOS/Linux it falls back to ``afplay``/``ffplay``
    respectively, both of which also play without showing a GUI.
    """
    output_path = Path(audio_path).resolve()
    if not output_path.exists():
        raise FileNotFoundError(f"Audio file not found: {output_path}")

    if sys.platform.startswith("win"):
        # Use PowerShell to play via Windows Media Player COM object.
        # This is headless – no media-player window opens – and blocks
        # until playback completes (which is fine because we call this
        # from a background daemon thread).
        ps_script = (
            f"Add-Type -AssemblyName presentationCore; "
            f"$player = New-Object System.Windows.Media.MediaPlayer; "
            f"$player.Open([Uri]'{output_path}'); "
            f"Start-Sleep -Milliseconds 500; "  # let the player buffer
            f"$player.Play(); "
            f"Start-Sleep -Milliseconds 500; "  # wait for duration to populate
            f"while ($player.NaturalDuration.HasTimeSpan -eq $false) {{ Start-Sleep -Milliseconds 200 }}; "
            f"$duration = $player.NaturalDuration.TimeSpan.TotalSeconds; "
            f"Start-Sleep -Seconds ([math]::Ceiling($duration)); "
            f"$player.Close()"
        )
        try:
            subprocess.run(
                ["powershell", "-NoProfile", "-Command", ps_script],
                timeout=120,
                check=False,
            )
        except subprocess.TimeoutExpired:
            print(f"[Audio] Playback timed out for {output_path}")
        except Exception as exc:
            print(f"[Audio] PowerShell playback failed: {exc}")
        return output_path

    if sys.platform == "darwin":
        # afplay blocks until done – perfect for a background thread.
        subprocess.run(["afplay", str(output_path)], check=False)
    else:
        # ffplay is available on most Linux distros with ffmpeg installed.
        subprocess.run(
            ["ffplay", "-nodisp", "-autoexit", str(output_path)],
            check=False,
        )

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


def _is_valid_mp3(data: bytes) -> bool:
    """Quick check that *data* looks like an MP3 (not an HTML error page)."""
    if len(data) < 4:
        return False
    # MP3 frames start with the sync word 0xFF 0xFB/0xF3/0xF2 or an ID3 tag.
    if data[:3] == b"ID3":
        return True
    if data[0] == 0xFF and (data[1] & 0xE0) == 0xE0:
        return True
    return False


def _generate_tts_gtts(
    text: str,
    output_file: str,
) -> tuple[Optional[str], Optional[Path]]:
    """Offline-friendly TTS via gTTS (Google Translate).

    Works through most corporate proxies (including ZScaler) because it
    hits translate.google.com which is typically allow-listed.
    """
    try:
        from gtts import gTTS  # type: ignore[import-untyped]
    except ImportError:
        print("[TTS] gTTS not installed. Run: pip install gTTS")
        return None, None

    try:
        tts = gTTS(text=text, lang="en")
        output_path = Path(output_file)
        tts.save(str(output_path))
        audio_bytes = output_path.read_bytes()
        print(f"[TTS/gTTS] Saved audio ({len(audio_bytes)} bytes) to {output_path}")
        audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")
        return audio_b64, output_path
    except Exception as exc:
        print(f"[TTS/gTTS] gTTS generation failed: {exc}")
        return None, None


def generate_tts_audio(
    text: str,
    output_file: str | None = None,
    voice: str = "alloy",
    model: str = "openai/tts-1",
) -> tuple[Optional[str], Optional[Path]]:
    """Generate TTS audio from text using OpenAI's TTS API via OpenRouter.

    Returns a tuple of (base64_encoded_audio, saved_file_path).
    Both may be None if the API key is missing or the call fails.
    The audio is saved to disk and the base64 string can be sent in API responses.

    Falls back to gTTS (Google Translate TTS) if the OpenRouter API is
    blocked (e.g. by a corporate proxy like ZScaler) or otherwise fails.
    """
    api_key = os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENAI_API_KEY")

    if not text or not text.strip():
        print("[TTS] Empty text provided. Skipping TTS.")
        return None, None

    # Truncate very long texts to stay within TTS limits (4096 chars max)
    if len(text) > 4000:
        text = text[:4000] + "..."

    if output_file is None:
        output_file = str(_THIS_DIR / "tts_recommendation.mp3")

    # --- Attempt 1: OpenRouter TTS API ---
    if api_key:
        tts_url = "https://openrouter.ai/api/v1/audio/speech"

        payload = {
            "model": model,
            "input": text,
            "voice": voice,
            "response_format": "mp3",
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
            with request.urlopen(req, timeout=30) as response:
                audio_bytes = response.read()

            if not audio_bytes or len(audio_bytes) < 100:
                print("[TTS] Received empty or too-small audio response. Trying gTTS fallback.")
            elif not _is_valid_mp3(audio_bytes):
                print("[TTS] OpenRouter response is NOT valid audio (likely proxy/firewall block). Trying gTTS fallback.")
            else:
                # Valid MP3 from OpenRouter
                output_path = Path(output_file)
                output_path.write_bytes(audio_bytes)
                print(f"[TTS] Saved audio ({len(audio_bytes)} bytes) to {output_path}")
                audio_b64 = base64.b64encode(audio_bytes).decode("utf-8")
                return audio_b64, output_path

        except Exception as exc:
            print(f"[TTS] OpenRouter TTS API call failed: {exc}. Trying gTTS fallback.")
    else:
        print("[TTS] No API key found. Trying gTTS fallback.")

    # --- Attempt 2: gTTS fallback ---
    return _generate_tts_gtts(text, output_file)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage: python play_audio.py <base64_string> [output_file]")
        sys.exit(1)

    base64_string = sys.argv[1]
    output_file = sys.argv[2] if len(sys.argv) > 2 else "audio_output.mp3"
    play_base64_audio(base64_string, output_file)
    print(f"Saved and opened {output_file}")