# -*- coding: utf-8 -*-
"""Vicky Talk text-to-speech — offline voice output.

Wraps pyttsx3 (imported lazily, inside __init__) so machines without it
still run fine. speak() runs in a daemon thread and never blocks the UI or
raises — if the engine is missing, speak() simply returns silently.
"""


class Speaker:
    """Offline TTS voice. Never raises from speak()/stop()."""

    def __init__(self, rate=175):
        self._engine = None
        try:
            import pyttsx3
            engine = pyttsx3.init()
            try:
                engine.setProperty("rate", rate)
            except Exception:
                pass
            self._engine = engine
        except Exception:
            self._engine = None

    @property
    def available(self):
        """True if a speech engine was initialised successfully."""
        return self._engine is not None

    def speak(self, text):
        """Speak text aloud in a background thread; never blocks or raises."""
        if not self._engine or not text:
            return
        try:
            import threading

            def _run():
                try:
                    self._engine.stop()
                    self._engine.say(str(text))
                    self._engine.runAndWait()
                except Exception:
                    pass

            t = threading.Thread(target=_run, daemon=True)
            t.start()
        except Exception:
            pass

    def stop(self):
        """Stop current speech. Never raises."""
        try:
            if self._engine:
                self._engine.stop()
        except Exception:
            pass
