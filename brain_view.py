"""Brain view: Local (free) <-> API (smarter) mode, model, voice, soul, safety.

Settings persist to QSettings(APP_NAME, APP_NAME). current_config() returns the
dict main.py uses to build a Brain.
"""

from PySide6.QtCore import Qt, Signal, QThread, QSettings
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QGridLayout, QFrame, QLabel,
    QPushButton, QLineEdit, QComboBox, QScrollArea,
)

from app_name import APP_NAME
from brain import Brain, DEFAULT_LOCAL_MODEL
from theme import GOLD, refresh_dynamic_style
from .setup_wizard import ollama_available


class _ModeCard(QFrame):
    clicked = Signal(str)  # 'local' | 'api'

    def __init__(self, mode: str, title: str, badge: str, desc: str, parent=None):
        super().__init__(parent)
        self._mode = mode
        self.setProperty("card", True)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 18, 20, 18)
        layout.setSpacing(8)
        head = QHBoxLayout()
        name = QLabel(f"<b style='font-size:15px'>{title}</b>")
        badge_lbl = QLabel(badge)
        badge_lbl.setProperty("pill", True)
        head.addWidget(name)
        head.addWidget(badge_lbl)
        head.addStretch(1)
        layout.addLayout(head)
        d = QLabel(desc)
        d.setWordWrap(True)
        d.setStyleSheet(f"color: {GOLD['dim']}; font-size: 12.5px;")
        layout.addWidget(d)

    def mousePressEvent(self, event) -> None:  # noqa: N802
        self.clicked.emit(self._mode)
        super().mousePressEvent(event)

    def set_selected(self, selected: bool) -> None:
        self.setProperty("selected", selected)
        refresh_dynamic_style(self)


class _ApiTestWorker(QThread):
    """Runs Brain(mode='api').chat(['ping']) off the GUI thread."""

    ok = Signal(str)
    failed = Signal(str)

    def __init__(self, api_key: str, base_url: str | None):
        super().__init__()
        self._api_key = api_key
        self._base_url = base_url

    def run(self) -> None:  # noqa: N802
        try:
            brain = Brain(mode="api", api_key=self._api_key,
                          base_url=self._base_url or None)
            reply = brain.chat([{"role": "user", "content": "ping"}])
            self.ok.emit(str(reply)[:300])
        except Exception as exc:
            self.failed.emit(str(exc))


class BrainView(QWidget):
    """Brain settings. Emits config_changed whenever a value changes."""

    config_changed = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._mode = "local"
        self._settings = QSettings(APP_NAME, APP_NAME)
        self._test_worker = None

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setFrameShape(QFrame.Shape.NoFrame)
        host = QWidget()
        layout = QVBoxLayout(host)
        layout.setContentsMargins(26, 22, 26, 22)
        layout.setSpacing(16)

        # ---- mode cards ----
        modes = QHBoxLayout()
        modes.setSpacing(14)
        self.local_card = _ModeCard(
            "local", "\U0001F3E0 Local", "FREE",
            "Runs on your PC via Ollama. No cost, no account, works offline. "
            "Great for daily tasks.")
        self.api_card = _ModeCard(
            "api", "\u2601\uFE0F API", "SMARTER",
            "Use your own API key (OpenAI / Anthropic / compatible). "
            "Smarter answers \u2014 billed by your provider.")
        self.local_card.clicked.connect(self._set_mode)
        self.api_card.clicked.connect(self._set_mode)
        modes.addWidget(self.local_card, 1)
        modes.addWidget(self.api_card, 1)
        layout.addLayout(modes)

        # ---- settings grid ----
        grid = QGridLayout()
        grid.setSpacing(14)

        # local box
        local_box = QFrame()
        local_box.setProperty("card", True)
        lb = QVBoxLayout(local_box)
        lb.setContentsMargins(20, 18, 20, 18)
        lb.setSpacing(12)
        lb.addWidget(self._heading("LOCAL MODEL"))
        self.ollama_status = QLabel("\u25CB checking Ollama\u2026")
        self.ollama_status.setStyleSheet(f"color: {GOLD['dim']}; font-size: 12.5px;")
        lb.addWidget(self.ollama_status)
        lb.addWidget(self._labeled("MODEL", self._model_combo()))
        lb.addWidget(self._labeled("VOICE", self._voice_combo()))
        grid.addWidget(local_box, 0, 0)

        # api box
        self.api_box = QFrame()
        self.api_box.setProperty("card", True)
        ab = QVBoxLayout(self.api_box)
        ab.setContentsMargins(20, 18, 20, 18)
        ab.setSpacing(12)
        ab.addWidget(self._heading("API KEY (OPTIONAL)"))
        self.provider_combo = QComboBox()
        self.provider_combo.addItems(["OpenAI", "Anthropic", "Custom (OpenAI-compatible)"])
        self.provider_combo.currentIndexChanged.connect(self._on_provider_changed)
        self.provider_combo.currentIndexChanged.connect(lambda _i: self._changed())
        ab.addWidget(self._labeled("PROVIDER", self.provider_combo))
        self.baseurl_edit = QLineEdit()
        self.baseurl_edit.setPlaceholderText("https://your-host/v1")
        self.baseurl_edit.setVisible(False)
        self.baseurl_edit.editingFinished.connect(self._changed)
        self.baseurl_wrap = self._labeled("BASE URL", self.baseurl_edit)
        self.baseurl_wrap.setVisible(False)
        ab.addWidget(self.baseurl_wrap)
        self.key_edit = QLineEdit()
        self.key_edit.setEchoMode(QLineEdit.EchoMode.Password)
        self.key_edit.setPlaceholderText("sk-...")
        self.key_edit.editingFinished.connect(self._changed)
        ab.addWidget(self._labeled("API KEY", self.key_edit))
        self.test_button = QPushButton("TEST CONNECTION")
        self.test_button.clicked.connect(self._test_connection)
        ab.addWidget(self.test_button)
        self.test_result = QLabel("")
        self.test_result.setWordWrap(True)
        self.test_result.setStyleSheet("font-size: 12px;")
        ab.addWidget(self.test_result)
        grid.addWidget(self.api_box, 0, 1)

        # soul box
        soul_box = QFrame()
        soul_box.setProperty("card", True)
        sb = QVBoxLayout(soul_box)
        sb.setContentsMargins(20, 18, 20, 18)
        sb.setSpacing(12)
        sb.addWidget(self._heading("SOUL \u00B7 PERSONALITY"))
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText(APP_NAME)
        self.name_edit.editingFinished.connect(self._changed)
        sb.addWidget(self._labeled("ASSISTANT NAME", self.name_edit))
        self.tone_combo = QComboBox()
        self.tone_combo.addItems(["Friendly & warm", "Professional", "Funny"])
        self.tone_combo.currentIndexChanged.connect(lambda _i: self._changed())
        sb.addWidget(self._labeled("TONE", self.tone_combo))
        grid.addWidget(soul_box, 1, 0)

        # safety box
        safety_box = QFrame()
        safety_box.setProperty("card", True)
        fb = QVBoxLayout(safety_box)
        fb.setContentsMargins(20, 18, 20, 18)
        fb.setSpacing(12)
        fb.addWidget(self._heading("SAFETY"))
        self.safety_combo = QComboBox()
        self.safety_combo.addItems([
            "Deleting files \u00B7 shutdown \u00B7 purchases",
            "Everything risky",
            "Nothing (expert mode)",
        ])
        self.safety_combo.currentIndexChanged.connect(lambda _i: self._changed())
        fb.addWidget(self._labeled("ASK BEFORE", self.safety_combo))
        note = QLabel(
            f"{APP_NAME} always asks before anything destructive. "
            "Your data never leaves your PC in Local mode."
        )
        note.setWordWrap(True)
        note.setStyleSheet(f"color: {GOLD['dim']}; font-size: 12px;")
        fb.addWidget(note)
        grid.addWidget(safety_box, 1, 1)

        layout.addLayout(grid)
        layout.addStretch(1)
        scroll.setWidget(host)
        outer.addWidget(scroll)

        self._load_settings()
        self._set_mode(self._mode, silent=True)
        self._refresh_ollama_status()

    # ---------------------------------------------------------------- widgets
    @staticmethod
    def _heading(text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setProperty("heading", True)
        return lbl

    @staticmethod
    def _labeled(label: str, widget) -> QWidget:
        wrap = QWidget()
        lay = QVBoxLayout(wrap)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(6)
        cap = QLabel(label)
        cap.setStyleSheet(f"color: {GOLD['dim']}; font-size: 11px;")
        lay.addWidget(cap)
        lay.addWidget(widget)
        return wrap

    def _model_combo(self) -> QComboBox:
        self.model_combo = QComboBox()
        self.model_combo.setEditable(True)
        items = [
            str(DEFAULT_LOCAL_MODEL),
            "llama-8b-q4 (recommended \u00B7 4.7 GB)",
            "qwen-7b-q4 (4.5 GB)",
            "phi-4-mini (2.4 GB)",
        ]
        # de-dupe while keeping order
        seen = set()
        for it in items:
            if it not in seen:
                seen.add(it)
                self.model_combo.addItem(it)
        self.model_combo.currentIndexChanged.connect(lambda _i: self._changed())
        self.model_combo.editTextChanged.connect(lambda _t: self._changed())
        return self.model_combo

    def _voice_combo(self) -> QComboBox:
        self.voice_combo = QComboBox()
        self.voice_combo.addItems([
            "Eva \u00B7 English (female)",
            "Danish \u00B7 English (male)",
            "Urdu voice",
        ])
        self.voice_combo.currentIndexChanged.connect(lambda _i: self._changed())
        return self.voice_combo

    # ------------------------------------------------------------------ logic
    def _set_mode(self, mode: str, silent: bool = False) -> None:
        self._mode = mode
        self.local_card.set_selected(mode == "local")
        self.api_card.set_selected(mode == "api")
        # dim the inactive settings box
        self.api_box.setEnabled(mode == "api")
        self.api_box.setStyleSheet(
            "" if mode == "api" else "QFrame[card=\"true\"] { background-color: #0d0904; }"
        )
        if not silent:
            self._changed()

    def _on_provider_changed(self) -> None:
        custom = self.provider_combo.currentText().startswith("Custom")
        self.baseurl_wrap.setVisible(custom)
        self.baseurl_edit.setVisible(custom)

    def _refresh_ollama_status(self) -> None:
        ok = ollama_available()
        if ok:
            self.ollama_status.setText("\u25CF Ollama running")
            self.ollama_status.setStyleSheet(f"color: {GOLD['green']}; font-size: 12.5px;")
        else:
            self.ollama_status.setText("\u25CB Ollama not detected \u2014 run Setup")
            self.ollama_status.setStyleSheet(f"color: {GOLD['amber']}; font-size: 12.5px;")

    def _test_connection(self) -> None:
        key = self.key_edit.text().strip()
        if not key:
            self.test_result.setText("Enter an API key first.")
            self.test_result.setStyleSheet(f"color: {GOLD['amber']}; font-size: 12px;")
            return
        self.test_button.setEnabled(False)
        self.test_result.setText("Testing\u2026")
        self.test_result.setStyleSheet(f"color: {GOLD['dim']}; font-size: 12px;")
        base = self.baseurl_edit.text().strip() if self.baseurl_wrap.isVisible() else ""
        self._test_worker = _ApiTestWorker(key, base or None)
        self._test_worker.ok.connect(self._on_test_ok)
        self._test_worker.failed.connect(self._on_test_failed)
        self._test_worker.finished.connect(lambda: self.test_button.setEnabled(True))
        self._test_worker.start()

    def _on_test_ok(self, reply: str) -> None:
        self.test_result.setText(f"\u2713 Connected \u2014 reply: {reply!r}")
        self.test_result.setStyleSheet(f"color: {GOLD['green']}; font-size: 12px;")

    def _on_test_failed(self, err: str) -> None:
        self.test_result.setText(f"\u2717 Failed: {err}")
        self.test_result.setStyleSheet(f"color: {GOLD['red']}; font-size: 12px;")

    # -------------------------------------------------------------- settings
    def _changed(self) -> None:
        self.save_settings()
        self.config_changed.emit()

    def save_settings(self) -> None:
        s = self._settings
        s.setValue("brain/mode", self._mode)
        s.setValue("brain/model", self.model_combo.currentText())
        s.setValue("brain/provider", self.provider_combo.currentText())
        s.setValue("brain/base_url", self.baseurl_edit.text())
        # NOTE: the API key is deliberately NOT persisted to disk settings.
        s.setValue("brain/voice", self.voice_combo.currentText())
        s.setValue("soul/name", self.name_edit.text())
        s.setValue("soul/tone", self.tone_combo.currentText())
        s.setValue("safety/level", self.safety_combo.currentText())
        s.sync()

    def _load_settings(self) -> None:
        s = self._settings
        self._mode = s.value("brain/mode", "local")
        model = s.value("brain/model", str(DEFAULT_LOCAL_MODEL))
        self.model_combo.setCurrentText(model)
        provider = s.value("brain/provider", "OpenAI")
        idx = self.provider_combo.findText(provider)
        if idx >= 0:
            self.provider_combo.setCurrentIndex(idx)
        self.baseurl_edit.setText(s.value("brain/base_url", ""))
        self._on_provider_changed()
        voice = s.value("brain/voice", "")
        if voice:
            self.voice_combo.setCurrentText(voice)
        self.name_edit.setText(s.value("soul/name", APP_NAME))
        tone = s.value("soul/tone", "")
        if tone:
            self.tone_combo.setCurrentText(tone)
        safety = s.value("safety/level", "")
        if safety:
            self.safety_combo.setCurrentText(safety)

    def current_config(self) -> dict:
        """Config dict used by main.py to construct a Brain."""
        return {
            "mode": self._mode,
            "model": self.model_combo.currentText().strip(),
            "provider": self.provider_combo.currentText(),
            "api_key": self.key_edit.text().strip(),
            "base_url": (self.baseurl_edit.text().strip()
                         if self.baseurl_wrap.isVisible() else "") or None,
            "voice": self.voice_combo.currentText(),
            "assistant_name": self.name_edit.text().strip() or APP_NAME,
            "tone": self.tone_combo.currentText(),
            "safety": self.safety_combo.currentText(),
        }
