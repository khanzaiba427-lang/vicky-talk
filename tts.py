# -*- coding: utf-8 -*-
"""Vicky Talk text-to-speech — offline voice output.

Wraps pyttsx3 (imported lazily, inside __init__) so machines without it
still run fine. speak() runs in a daemon thread and never blocks the UI or
raises — if the engine is missing, speak() simply returns silently.
"""


class Speaker:
    """Offline TTS voice. Never raises from speak()/stop()."""

    def __init__(self, rate=175):
        self._rate = rate
        self._engine = None
        self._init_error = ""
        self._speaking = None
        try:
            import pyttsx3
            engine = pyttsx3.init()
            try:
                engine.setProperty("rate", rate)
            except Exception:
                pass
            self._engine = engine
        except Exception as exc:
            self._engine = None
            self._init_error = str(exc) or type(exc).__name__

    @property
    def available(self):
        """True if a speech engine was initialised successfully."""
        return self._engine is not None

    def diagnose(self):
        """Return (ok: bool, info: dict) describing the TTS engine state.

        Used by the TEST VOICE button — surfaces the real error instead of
        failing silently.
        """
        try:
            import pyttsx3  # noqa: F401
        except Exception as exc:
            return False, {"error": "pyttsx3 import failed: %s" % exc}
        if self._engine is None:
            return False, {
                "error": "voice engine failed to start: %s"
                % (self._init_error or "unknown reason")
            }
        info = {}
        try:
            voices = self._engine.getProperty("voices") or []
            info["voices"] = [getattr(v, "name", "?") for v in voices]
        except Exception as exc:
            info["voices_error"] = str(exc)
        return True, info

    def speak(self, text):
        """Speak text aloud in a background thread; never blocks or raises.

        The whole engine lifecycle (init -> say -> runAndWait) happens inside
        the worker thread: Windows SAPI/COM voice objects must be created AND
        used on the same thread, otherwise speech silently fails.
        """
        if not text:
            return
        self.stop()  # interrupt any current speech first
        try:
            import threading

            def _run():
                engine = None
                try:
                    import pyttsx3
                    engine = pyttsx3.init()
                    try:
                        engine.setProperty("rate", self._rate)
                    except Exception:
                        pass
                    self._speaking = engine
                    engine.say(str(text))
                    engine.runAndWait()
                except Exception:
                    pass
                finally:
                    try:
                        if engine is not None:
                            engine.stop()
                    except Exception:
                        pass
                    if self._speaking is engine:
                        self._speaking = None

            t = threading.Thread(target=_run, daemon=True)
            t.start()
        except Exception:
            pass

    def stop(self):
        """Stop current speech. Never raises."""
        try:
            if self._speaking is not None:
                self._speaking.stop()
        except Exception:
            pass
        try:
            if self._engine is not None:
                self._engine.stop()
        except Exception:
            pass
