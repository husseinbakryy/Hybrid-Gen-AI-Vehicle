import json
import os
import queue
import subprocess
import sys
import threading
import uuid
from pathlib import Path
from typing import Optional
from urllib import request

from dotenv import load_dotenv

_THIS_DIR = Path(__file__).resolve().parent
load_dotenv(_THIS_DIR / ".env")

_playback_lock = threading.Lock()
_current_process = None   # subprocess.Popen | None
_is_muted = False
_audio_queue = queue.Queue()
_worker_thread = None


def set_muted(muted: bool) -> None:
    """Enable or disable audio muting globally across the application."""
    global _is_muted
    _is_muted = muted
    if muted:
        clear_audio_queue()
        stop_current_playback()


def is_muted() -> bool:
    """Check if audio playback is muted."""
    return _is_muted


def clear_audio_queue() -> None:
    """Clear all pending audio requests in the queue."""
    while not _audio_queue.empty():
        try:
            _audio_queue.get_nowait()
        except queue.Empty:
            break


def stop_current_playback() -> None:
    """Immediately terminate whatever audio is currently playing,
    if anything. Safe to call even if nothing is playing."""
    global _current_process
    with _playback_lock:
        if _current_process is not None and _current_process.poll() is None:
            try:
                if sys.platform.startswith("win"):
                    subprocess.run(
                        ["taskkill", "/F", "/T", "/PID", str(_current_process.pid)],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                    )
                else:
                    _current_process.kill()
            except Exception:
                pass
        _current_process = None


def enqueue_tts(text: str) -> None:
    """Enqueue a text-to-speech request. Immediately stops any currently playing audio
    and clears stale pending requests so speech never overlaps.
    """
    if _is_muted or not text or not text.strip():
        return

    clear_audio_queue()
    stop_current_playback()

    _audio_queue.put(text)
    _ensure_worker_running()


def _ensure_worker_running():
    global _worker_thread
    with _playback_lock:
        if _worker_thread is None or not _worker_thread.is_alive():
            _worker_thread = threading.Thread(target=_audio_worker_loop, daemon=True)
            _worker_thread.start()


def _audio_worker_loop():
    while True:
        try:
            text = _audio_queue.get(timeout=30)
        except queue.Empty:
            break

        if _is_muted:
            continue

        unique_file = str(_THIS_DIR / f"tts_{uuid.uuid4().hex[:8]}.mp3")
        try:
            audio_path = generate_tts_audio(text, output_file=unique_file)
            if audio_path and not _is_muted:
                play_audio_file(audio_path)
        except Exception:
            pass
        finally:
            try:
                p = Path(unique_file)
                if p.exists():
                    p.unlink()
            except Exception:
                pass


def play_audio_file(audio_path: str | Path) -> Path:
    """Play an audio file headlessly from the beginning at 1.4x speed."""
    if _is_muted:
        return Path(audio_path).resolve()

    stop_current_playback()

    output_path = Path(audio_path).resolve()
    if not output_path.exists():
        raise FileNotFoundError(f"Audio file not found: {output_path}")

    if sys.platform.startswith("win"):
        ps_script = (
            f"Add-Type -AssemblyName presentationCore; "
            f"$player = New-Object System.Windows.Media.MediaPlayer; "
            f"$player.Open([Uri]'{output_path}'); "
            f"Start-Sleep -Milliseconds 150; "
            f"$player.Position = [System.TimeSpan]::Zero; "
            f"$player.SpeedRatio = 1.4; "
            f"$player.Play(); "
            f"while ($player.NaturalDuration.HasTimeSpan -eq $false) {{ Start-Sleep -Milliseconds 50 }}; "
            f"$duration = $player.NaturalDuration.TimeSpan.TotalSeconds / 1.4; "
            f"Start-Sleep -Seconds ([math]::Ceiling($duration)); "
            f"$player.Close()"
        )
        process = subprocess.Popen(["powershell", "-NoProfile", "-Sta", "-Command", ps_script])
        with _playback_lock:
            _current_process = process
        process.wait()
        with _playback_lock:
            if _current_process is process:
                _current_process = None
        return output_path

    if sys.platform == "darwin":
        process = subprocess.Popen(["afplay", "-r", "1.4", str(output_path)])
    else:
        process = subprocess.Popen(["ffplay", "-nodisp", "-autoexit", "-af", "atempo=1.4", str(output_path)])
    
    with _playback_lock:
        _current_process = process
    process.wait()
    with _playback_lock:
        if _current_process is process:
            _current_process = None

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
        return None

    try:
        tts = gTTS(text=text, lang="en", slow=False)
        output_path = Path(output_file)
        tts.save(str(output_path))
        return output_path
    except Exception:
        return None


def generate_tts_audio(
    text: str,
    output_file: str | None = None,
    voice: str = "alloy",
    model: str = "openai/tts-1",
) -> Optional[Path]:
    api_key = os.getenv("OPENROUTER_API_KEY") or os.getenv("OPENAI_API_KEY")

    if _is_muted or not text or not text.strip():
        return None

    if len(text) > 4000:
        text = text[:4000] + "..."

    if output_file is None:
        output_file = str(_THIS_DIR / f"tts_{uuid.uuid4().hex[:8]}.mp3")

    if api_key:
        tts_url = "https://openrouter.ai/api/v1/audio/speech"
        payload = {
            "model": model,
            "input": text,
            "voice": voice,
            "response_format": "mp3",
            "speed": 1.4,
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
            with request.urlopen(req, timeout=10) as response:
                audio_bytes = response.read()

            if audio_bytes and len(audio_bytes) >= 100 and _is_valid_mp3(audio_bytes):
                output_path = Path(output_file)
                output_path.write_bytes(audio_bytes)
                return output_path
        except Exception:
            pass

    return _generate_tts_gtts(text, output_file)


if __name__ == "__main__":
    if len(sys.argv) > 1:
        text_input = sys.argv[1]
        output_file = sys.argv[2] if len(sys.argv) > 2 else "audio_output.mp3"
        path = generate_tts_audio(text_input, output_file)
        if path:
            play_audio_file(path)