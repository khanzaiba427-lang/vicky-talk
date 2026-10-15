# -*- coding: utf-8 -*-
"""Vicky Talk speech-to-text — offline voice input.

Mic -> text via `sounddevice` (capture) + `faster-whisper` (tiny.en model,
~75MB, lazy-downloaded once to ~/.vickytalk/models/). CPU-friendly (int8),
no cloud APIs, no internet needed after the first model download.

Import-safe: if the optional dependencies are missing, LISTEN_AVAILABLE is
False and every public method degrades to a clean error string — the app
never crashes because of this module.
"""

from pathlib import Path

MODEL_NAME = "tiny.en"
MODEL_DIR = Path.home() / ".vickytalk" / "models"
DEFAULT_SECONDS = 6
SAMPLE_RATE = 16000

try:
    import numpy as _np
    import sounddevice as _sd
    from faster_whisper import WhisperModel as _WhisperModel
    LISTEN_AVAILABLE = True
except Exception:
    _np = None
    _sd = None
    _WhisperModel = None
    LISTEN_AVAILABLE = False


def deps_missing_hint() -> str:
    """Human-readable install hint shown when deps are absent."""
    return "Voice input needs: pip install faster-whisper sounddevice"


class Listener:
    """Record from the default mic and transcribe offline.

    All public methods return (ok: bool, payload) tuples and never raise:
    payload is the result on success, or a human-readable error message
    on failure.
    """

    def __init__(self, model_name: str = MODEL_NAME, model_dir: Path = MODEL_DIR):
        self._model_name = model_name
        self._model_dir = Path(model_dir)
        self._model = None

    # ------------------------------------------------------------- helpers
    def _ensure_model(self):
        """Lazy-load the whisper model (downloads once on first use)."""
        if self._model is not None:
            return self._model
        if not LISTEN_AVAILABLE:
            raise RuntimeError(deps_missing_hint())
        self._model_dir.mkdir(parents=True, exist_ok=True)
        self._model = _WhisperModel(
            self._model_name,
            device="cpu",
            compute_type="int8",
            download_root=str(self._model_dir),
        )
        return self._model

    def list_mics(self):
        """Return names of available input devices ([] if none/unavailable)."""
        if not LISTEN_AVAILABLE:
            return []
        try:
            return [
                d["name"]
                for d in _sd.query_devices()
                if d.get("max_input_channels", 0) > 0
            ]
        except Exception:
            return []

    # --------------------------------------------------------------- record
    def record(self, seconds: int = DEFAULT_SECONDS):
        """Capture mono 16kHz float32 audio from the default mic.

        Returns (True, numpy array) or (False, error message). Never raises.
        """
        if not LISTEN_AVAILABLE:
            return False, deps_missing_hint()
        try:
            inputs = [
                d for d in _sd.query_devices()
                if d.get("max_input_channels", 0) > 0
            ]
            if not inputs:
                return False, "No microphone found \u2014 plug one in and try again."
        except Exception as exc:
            return False, f"Could not list audio devices: {exc}"
        try:
            frames = int(SAMPLE_RATE * max(1, seconds))
            audio = _sd.rec(
                frames, samplerate=SAMPLE_RATE, channels=1,
                dtype="float32", blocking=True,
            )
            return True, _np.asarray(audio, dtype=_np.float32).reshape(-1)
        except Exception as exc:
            return False, f"Microphone error: {exc}"

    # ------------------------------------------------------------ transcribe
    def transcribe(self, audio):
        """Transcribe a mono 16kHz float32 numpy array.

        Returns (True, text) or (False, error message). Never raises.
        """
        if not LISTEN_AVAILABLE:
            return False, deps_missing_hint()
        try:
            model = self._ensure_model()
        except Exception as exc:
            return False, f"Could not load voice model: {exc}"
        try:
            segments, _info = model.transcribe(audio, beam_size=5)
            text = " ".join(seg.text for seg in segments).strip()
            return True, text
        except Exception as exc:
            return False, f"Transcription failed: {exc}"

    # ---------------------------------------------------------------- listen
    def listen(self, seconds: int = DEFAULT_SECONDS):
        """Record + transcribe in one call.

        Returns (True, text) or (False, error message). Never raises.
        """
        ok, audio = self.record(seconds=seconds)
        if not ok:
            return False, audio
        return self.transcribe(audio)
