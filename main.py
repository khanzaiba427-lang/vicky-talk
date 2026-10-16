"""Vicky Talk main window: top bar + 4 views + brain/tool/reminder wiring.

Import-safe: importing this module creates no QApplication and performs no
network calls. Run with `python main.py` (or `python -m main`) from this dir.
"""

import sys

from PySide6.QtCore import QThread, Signal, QTimer
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QLabel, QPushButton, QStackedWidget, QButtonGroup, QMessageBox,
)

from app_name import APP_NAME
from theme import apply_theme, GOLD
from orb import OrbWidget  # noqa: F401 (re-exported for convenience)
from command_center import CommandCenterWidget
from agent_view import AgentView
from notes_view import NotesView
from brain_view import BrainView
from setup_wizard import SetupWizard, ollama_available

# ---- backend contract (sibling agent provides these modules) ----
from brain import Brain, DEFAULT_LOCAL_MODEL  # noqa: F401
from tools import ToolDispatcher
from memory import Memory
from tts import Speaker
from reminders import ReminderService
from stt import LISTEN_AVAILABLE, Listener

# node label -> view index in the stacked widget
_NODE_TARGETS = {"memory": 2, "skills": 1, "soul": 3, "settings": 3}


class _ChatWorker(QThread):
    """Runs Brain.chat_stream + Brain.decide_tool off the GUI thread."""

    done = Signal(str, object, object)  # reply, tool_name|None, args dict
    failed = Signal(str)
    partial = Signal(str)  # streamed reply chunks, emitted as they arrive

    def __init__(self, config: dict, user_text: str):
        super().__init__()
        self._config = config
        self._text = user_text

    def run(self) -> None:  # noqa: N802
        try:
            brain = Brain(
                mode=self._config.get("mode", "local"),
                model=self._config.get("model") or None,
                api_key=self._config.get("api_key") or None,
                base_url=self._config.get("base_url") or None,
            )
            name = self._config.get("assistant_name", APP_NAME)
            tone = self._config.get("tone", "Friendly & warm")
            language = self._config.get("language", "Roman Urdu")
            lang_instruction = {
                "English": "Always reply in English.",
                "Urdu (اردو)": "Always reply in Urdu, using Urdu script.",
            }.get(
                language,
                "Always reply in Roman Urdu (Urdu written in Latin script, "
                "the way people text in Pakistan).",
            )
            system = (
                f"You are {name}, a helpful desktop AI assistant. "
                f"Tone: {tone}. {lang_instruction} "
                f"Keep answers concise and practical."
            )
            reply_parts = []
            for chunk in brain.chat_stream([
                {"role": "system", "content": system},
                {"role": "user", "content": self._text},
            ]):
                reply_parts.append(chunk)
                self.partial.emit(chunk)
            reply = "".join(reply_parts)
            tool_name, tool_args = None, {}
            try:
                decided = brain.decide_tool(self._text)
                if decided:
                    tool_name, tool_args = decided[0], (decided[1] or {})
            except Exception:
                pass  # tool routing is best-effort
            self.done.emit(str(reply), tool_name, tool_args)
        except Exception as exc:
            self.failed.emit(str(exc))


class _ToolWorker(QThread):
    """Runs ToolDispatcher.dispatch off the GUI thread."""

    done = Signal(dict)
    failed = Signal(str)

    def __init__(self, name: str, args: dict):
        super().__init__()
        self._name = name
        self._args = args

    def run(self) -> None:  # noqa: N802
        try:
            # Already confirmed in the GUI thread before this worker started.
            dispatcher = ToolDispatcher(confirm_fn=lambda _t, _x: True)
            result = dispatcher.dispatch(self._name, **self._args)
            self.done.emit(dict(result) if isinstance(result, dict) else {"ok": True, "result": str(result)})
        except Exception as exc:
            self.failed.emit(str(exc))


class _ListenWorker(QThread):
    """Records + transcribes mic input off the GUI thread."""

    done = Signal(bool, str)  # ok, text-or-error

    def __init__(self, seconds: int = 6):
        super().__init__()
        self._seconds = seconds

    def run(self) -> None:  # noqa: N802
        try:
            ok, text = Listener().listen(seconds=self._seconds)
            self.done.emit(bool(ok), str(text))
        except Exception as exc:  # never crash the app from here
            self.done.emit(False, f"Voice input failed: {exc}")


class MainWindow(QMainWindow):
    """Vicky Talk main window."""

    reminder_fired = Signal(object)  # marshals ReminderService callbacks to the GUI thread

    def __init__(self):
        super().__init__()
        self.setWindowTitle(APP_NAME)
        self._busy = False
        self._speaker = None
        self._wizard = None

        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._build_topbar())

        self.stack = QStackedWidget()
        self.command_center = CommandCenterWidget()
        self.agent_view = AgentView()
        self.notes_view = NotesView()
        self.brain_view = BrainView()
        for view in (self.command_center, self.agent_view, self.notes_view, self.brain_view):
            self.stack.addWidget(view)
        root.addWidget(self.stack, 1)

        self._wire()
        self._refresh_brain_status()
        self._setup_reminders()

        # mic button follows voice-input availability (offline faster-whisper)
        self.command_center.mic_button.setEnabled(bool(LISTEN_AVAILABLE))
        if LISTEN_AVAILABLE:
            self.command_center.mic_button.setToolTip("Click and speak (6 seconds)")
            self.command_center.mic_button.clicked.connect(self._on_mic_clicked)
        else:
            self.command_center.mic_button.setToolTip(
                "Voice input needs: pip install faster-whisper sounddevice")

        # first-run setup check, slightly delayed so the window paints first
        QTimer.singleShot(600, self._maybe_first_run)

    # ------------------------------------------------------------------ chrome
    def _build_topbar(self) -> QWidget:
        bar = QWidget()
        bar.setStyleSheet(
            f"background-color: {GOLD['bg0']};"
            f"border-bottom: 1px solid {GOLD['line']};"
        )
        lay = QHBoxLayout(bar)
        lay.setContentsMargins(16, 10, 16, 10)
        lay.setSpacing(12)

        mini = QLabel()
        mini.setFixedSize(22, 22)
        mini.setStyleSheet(
            "background: qradialgradient(cx:0.38, cy:0.32, radius:0.9, fx:0.38, fy:0.32,"
            " stop:0 #fff6dd, stop:0.45 #f2c14e, stop:1 #8a5a1d);"
            "border-radius: 11px;"
        )
        lay.addWidget(mini)

        name = QLabel(APP_NAME.upper())
        name.setStyleSheet(f"color: {GOLD['gold']}; font-weight: 700; font-size: 14px;")
        lay.addWidget(name)
        lay.addStretch(1)

        self.brain_pill = QLabel("")
        self.brain_pill.setProperty("pill", True)
        self.brain_pill.setStyleSheet(
            f"color: {GOLD['green']}; font-size: 11px; "
            "border: 1px solid rgba(52,211,153,90); border-radius: 12px; "
            "padding: 5px 12px; background: rgba(52,211,153,20);"
        )
        lay.addWidget(self.brain_pill)

        self._nav_group = QButtonGroup(self)
        self._nav_group.setExclusive(True)
        for i, label in enumerate(("Command Center", "Agent", "Notes", "Brain")):
            btn = QPushButton(label)
            btn.setProperty("nav", True)
            btn.setCheckable(True)
            btn.setChecked(i == 0)
            btn.clicked.connect(lambda _c, idx=i: self.stack.setCurrentIndex(idx))
            self._nav_group.addButton(btn, i)
            lay.addWidget(btn)
        return bar

    # ------------------------------------------------------------------ wiring
    def _wire(self) -> None:
        cc = self.command_center
        cc.start_ai_clicked.connect(self._on_start_ai)
        cc.agent_selected.connect(
            lambda key: cc.append_line(f"[agent] {key} selected"))
        cc.node_clicked.connect(self._on_node_clicked)
        self.stack.currentChanged.connect(self._on_view_changed)
        self.brain_view.config_changed.connect(self._refresh_brain_status)
        self.agent_view.pause_clicked.connect(
            lambda: self.agent_view.log_line("[\u275A\u275A] paused by user"))
        self.agent_view.stop_clicked.connect(
            lambda: self.agent_view.log_line("[\u25A0] stopped by user"))
        self.reminder_fired.connect(self._show_reminder)

    def _on_view_changed(self, index: int) -> None:
        btn = self._nav_group.button(index)
        if btn is not None:
            btn.setChecked(True)
        if index == 0:
            self._refresh_brain_status()

    def _on_node_clicked(self, key: str) -> None:
        target = _NODE_TARGETS.get(key)
        if target is not None:
            self.stack.setCurrentIndex(target)

    # ------------------------------------------------------------------- brain
    def _refresh_brain_status(self) -> None:
        cfg = self.brain_view.current_config()
        if cfg["mode"] == "api":
            text = f"API \u00B7 {cfg['provider']}"
        else:
            model = (cfg["model"] or str(DEFAULT_LOCAL_MODEL)).split()[0]
            text = f"Local \u00B7 {model}"
        self.brain_pill.setText(f"\u25CF {text}")
        self.command_center.set_brain_status(text)

    # -------------------------------------------------------------------- chat
    def _on_start_ai(self) -> None:
        text = self.command_center.user_input.text().strip()
        if not text or self._busy:
            return
        self._busy = True
        cc = self.command_center
        cc.append_line(f"user: \"{text}\"")
        cc.append_line("[\u2026] thinking\u2026")
        cc.set_orb_state("thinking")
        self.agent_view.log_line(f"[\u2026] user asked: {text[:80]}")

        self._chat_worker = _ChatWorker(self.brain_view.current_config(), text)
        self._chat_worker.done.connect(self._on_chat_done)
        self._chat_worker.failed.connect(self._on_chat_failed)
        self._chat_worker.partial.connect(self._on_chat_partial)
        self._chat_worker.finished.connect(self._on_chat_finished)
        self._streaming = False
        self._chat_worker.start()

    def _on_chat_partial(self, chunk: str) -> None:
        cc = self.command_center
        if not self._streaming:
            self._streaming = True
            cc.stream_start(f"{self.brain_view.current_config()['assistant_name']}: ")
        cc.stream_append(chunk)

    def _on_chat_finished(self) -> None:
        self._busy = False

    def _on_chat_done(self, reply: str, tool_name, tool_args) -> None:
        cc = self.command_center
        if self._streaming:
            cc.stream_end()
        else:
            cc.append_line(f"{self.brain_view.current_config()['assistant_name']}: {reply}")
        self.agent_view.log_line(f"[ok] reply ({len(reply)} chars)")
        cc.set_orb_state("speaking")
        self._speak(reply)
        QTimer.singleShot(2500, lambda: cc.set_orb_state("idle"))

        if tool_name:
            args_preview = ", ".join(f"{k}={v!r}" for k, v in (tool_args or {}).items())
            question = (
                f"{self.brain_view.current_config()['assistant_name']} wants to run "
                f"'{tool_name}'"
                + (f" with:\n{args_preview}" if args_preview else "")
                + "\n\nAllow?"
            )
            ok = QMessageBox.question(
                self, "Run tool?", question,
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            ) == QMessageBox.StandardButton.Yes
            if ok:
                cc.append_line(f"[tool] running {tool_name}\u2026")
                self.agent_view.log_line(f"[tool] running {tool_name}\u2026")
                self._tool_worker = _ToolWorker(tool_name, tool_args or {})
                self._tool_worker.done.connect(
                    lambda res: self._on_tool_done(tool_name, res))
                self._tool_worker.failed.connect(
                    lambda err: cc.append_line(f"[tool] {tool_name} failed: {err}"))
                self._tool_worker.start()
            else:
                cc.append_line(f"[tool] {tool_name} declined by user.")

    def _on_chat_failed(self, err: str) -> None:
        if self._streaming:
            self.command_center.stream_end()
            self._streaming = False
        self.command_center.append_line(f"[\u2717] brain error: {err}")
        self.agent_view.log_line(f"[\u2717] brain error: {err}")
        self.command_center.set_orb_state("idle")

    def _on_tool_done(self, tool_name: str, result: dict) -> None:
        ok = result.get("ok")
        body = result.get("result", "")
        line = f"[tool] {tool_name}: {'ok' if ok else 'failed'} \u2014 {body}"
        self.command_center.append_line(line)
        self.agent_view.log_line(line)

    # ------------------------------------------------------------ voice input
    def _on_mic_clicked(self) -> None:
        if self._busy:
            return
        cc = self.command_center
        cc.mic_button.setEnabled(False)
        cc.set_orb_state("listening")
        cc.append_line("[\U0001F399\uFE0F] listening\u2026 speak now (6s)")
        self.agent_view.log_line("[\U0001F399\uFE0F] voice input started")

        self._listen_worker = _ListenWorker(seconds=6)
        self._listen_worker.done.connect(self._on_listen_done)
        self._listen_worker.start()

    def _on_listen_done(self, ok: bool, text: str) -> None:
        cc = self.command_center
        cc.mic_button.setEnabled(True)
        cc.set_orb_state("idle")
        text = (text or "").strip()
        if ok and text:
            cc.append_line(f"[\U0001F399\uFE0F] heard: \"{text}\"")
            cc.user_input.setText(text)
            self._on_start_ai()
        else:
            _fallback = 'did not catch that \u2014 try again'
            cc.append_line(
                f"[\U0001F399\uFE0F] {text or _fallback}")
            self.agent_view.log_line(f"[\U0001F399\uFE0F] listen failed: {text}")

    # --------------------------------------------------------------------- tts
    def _speak(self, text: str) -> None:
        """Speak the reply; stop any in-progress speech first."""
        try:
            if self._speaker is None:
                self._speaker = Speaker()
            self._speaker.stop()
            self._speaker.speak(text)
        except Exception as exc:
            self.command_center.append_line(f"[tts] unavailable: {exc}")

    # --------------------------------------------------------------- reminders
    def _setup_reminders(self) -> None:
        self._memory = Memory()
        try:
            self._reminder_service = ReminderService(self._memory, on_due=self._on_reminder_due)
            self._reminder_service.start()
        except Exception as exc:
            self._reminder_service = None
            print(f"[reminders] service failed to start: {exc}")

    def _on_reminder_due(self, reminder) -> None:
        # May be called from the service's thread -> marshal to the GUI thread.
        self.reminder_fired.emit(reminder)

    def _show_reminder(self, reminder) -> None:
        text = reminder.get("text") if isinstance(reminder, dict) else str(reminder)
        self.command_center.append_line(f"[\u23F0] reminder: {text}")
        QMessageBox.information(self, f"{APP_NAME} \u00B7 Reminder", str(text))

    # ------------------------------------------------------------------ setup
    def _maybe_first_run(self) -> None:
        """Open the setup wizard (non-blocking) if no local brain is available."""
        if not ollama_available():
            self._wizard = SetupWizard(self)
            self._wizard.open()

    # ------------------------------------------------------------------- close
    def closeEvent(self, event) -> None:  # noqa: N802
        try:
            if getattr(self, "_reminder_service", None) is not None:
                self._reminder_service.stop()
        except Exception:
            pass
        try:
            if self._speaker is not None:
                self._speaker.stop()
        except Exception:
            pass
        try:
            self.brain_view.save_settings()
        except Exception:
            pass
        super().closeEvent(event)


def main() -> int:
    app = QApplication(sys.argv)
    apply_theme(app)
    win = MainWindow()
    win.showMaximized()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
