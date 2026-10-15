"""First-run setup wizard: install Ollama -> download model -> ready.

Non-blocking QDialog (use .open(), not .exec()). Closable at any time; nothing
runs until the user presses a button, so importing this module is side-effect free.
"""

import re

from PySide6.QtCore import Qt, QProcess, QUrl
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QDialog, QWidget, QVBoxLayout, QHBoxLayout, QStackedWidget, QFrame, QLabel,
    QPushButton, QLineEdit, QTextEdit, QProgressBar,
)

from app_name import APP_NAME
from brain import Brain, DEFAULT_LOCAL_MODEL
from theme import GOLD

_PERCENT_RE = re.compile(r"(\d{1,3})\s*%")


def ollama_available() -> bool:
    """True if a local Ollama brain answers on localhost.

    The backend exposes is_local_available() as an *instance* method, so we
    probe it via a throwaway Brain() (constructor does no network I/O).
    """
    try:
        return bool(Brain().is_local_available())
    except Exception:
        return False


class SetupWizard(QDialog):
    """3-step first-run wizard."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"{APP_NAME} \u00B7 Setup")
        self.setMinimumSize(740, 540)
        self.setModal(False)  # non-blocking

        root = QVBoxLayout(self)
        root.setContentsMargins(36, 30, 36, 30)
        root.setSpacing(18)

        title = QLabel("Welcome. Let's set you up.")
        title.setStyleSheet("font-size: 22px; font-weight: 600;")
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        sub = QLabel("One-time setup \u00B7 about 10 minutes \u00B7 after this, everything runs on your PC")
        sub.setStyleSheet(f"color: {GOLD['dim']}; font-size: 13.5px;")
        sub.setAlignment(Qt.AlignmentFlag.AlignCenter)
        root.addWidget(title)
        root.addWidget(sub)

        # step indicator
        self._step_dots = QHBoxLayout()
        self._step_dots.setSpacing(8)
        self._dots = []
        for i, label in enumerate(("1 \u00B7 Install Ollama", "2 \u00B7 Download model", "3 \u00B7 Meet Vicky Talk")):
            dot = QLabel(label)
            dot.setProperty("pill", True)
            self._step_dots.addWidget(dot)
            self._dots.append(dot)
        dots_wrap = QWidget()
        dots_wrap.setLayout(self._step_dots)
        root.addWidget(dots_wrap, alignment=Qt.AlignmentFlag.AlignHCenter)

        self._stack = QStackedWidget()
        self._stack.addWidget(self._page_install())
        self._stack.addWidget(self._page_model())
        self._stack.addWidget(self._page_ready())
        root.addWidget(self._stack, 1)

        self._stack.currentChanged.connect(self._update_dots)
        self._update_dots(0)

        self._pull_proc = None
        self._pull_buf = ""

    # ------------------------------------------------------------------ pages
    def _page_install(self) -> QWidget:
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setSpacing(14)
        lay.addStretch(1)

        self._ollama_status = QLabel("")
        self._ollama_status.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._ollama_status.setStyleSheet("font-size: 14px;")
        lay.addWidget(self._ollama_status)

        desc = QLabel(
            "Vicky Talk needs Ollama \u2014 the free engine that runs the AI on your PC. "
            "Install it, then come back and press RE-CHECK."
        )
        desc.setWordWrap(True)
        desc.setAlignment(Qt.AlignmentFlag.AlignCenter)
        desc.setStyleSheet(f"color: {GOLD['dim']}; font-size: 13px;")
        lay.addWidget(desc)

        row = QHBoxLayout()
        row.addStretch(1)
        dl = QPushButton("DOWNLOAD OLLAMA")
        dl.setProperty("gold", True)
        dl.clicked.connect(lambda: QDesktopServices.openUrl(QUrl("https://ollama.com")))
        recheck = QPushButton("RE-CHECK")
        recheck.clicked.connect(self._check_ollama)
        row.addWidget(dl)
        row.addWidget(recheck)
        row.addStretch(1)
        lay.addLayout(row)

        lay.addStretch(1)
        nav = QHBoxLayout()
        nav.addStretch(1)
        self._install_next = QPushButton("CONTINUE \u2192")
        self._install_next.setProperty("gold", True)
        self._install_next.clicked.connect(lambda: self._stack.setCurrentIndex(1))
        nav.addWidget(self._install_next)
        lay.addLayout(nav)
        return page

    def _page_model(self) -> QWidget:
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setSpacing(12)

        row = QHBoxLayout()
        row.setSpacing(10)
        self._model_edit = QLineEdit(str(DEFAULT_LOCAL_MODEL))
        pull = QPushButton("DOWNLOAD MODEL")
        pull.setProperty("gold", True)
        pull.clicked.connect(self._start_pull)
        row.addWidget(self._model_edit, 1)
        row.addWidget(pull, 0)
        lay.addLayout(row)

        self._pull_progress = QProgressBar()
        self._pull_progress.setRange(0, 100)
        self._pull_progress.setValue(0)
        self._pull_progress.setTextVisible(True)
        lay.addWidget(self._pull_progress)

        self._pull_status = QLabel("Press DOWNLOAD MODEL to fetch the brain (one-time download).")
        self._pull_status.setStyleSheet(f"color: {GOLD['dim']}; font-size: 12.5px;")
        lay.addWidget(self._pull_status)

        self._pull_log = QTextEdit()
        self._pull_log.setReadOnly(True)
        self._pull_log.setStyleSheet("font-family: 'Cascadia Code', Consolas, monospace; font-size: 11px;")
        self._pull_log.setMaximumHeight(150)
        lay.addWidget(self._pull_log)

        lay.addStretch(1)
        nav = QHBoxLayout()
        back = QPushButton("\u2190 BACK")
        back.clicked.connect(lambda: self._stack.setCurrentIndex(0))
        nav.addWidget(back)
        nav.addStretch(1)
        self._model_next = QPushButton("CONTINUE \u2192")
        self._model_next.setProperty("gold", True)
        self._model_next.setEnabled(False)
        self._model_next.clicked.connect(lambda: self._stack.setCurrentIndex(2))
        nav.addWidget(self._model_next)
        lay.addLayout(nav)
        return page

    def _page_ready(self) -> QWidget:
        page = QWidget()
        lay = QVBoxLayout(page)
        lay.setSpacing(16)
        lay.addStretch(1)

        check = QLabel("\u2713")
        check.setAlignment(Qt.AlignmentFlag.AlignCenter)
        check.setStyleSheet(f"font-size: 54px; color: {GOLD['green']};")
        lay.addWidget(check)

        msg = QLabel(f"Your assistant is ready.\nSay hello \u2014 {APP_NAME} is ready to work.")
        msg.setAlignment(Qt.AlignmentFlag.AlignCenter)
        msg.setStyleSheet("font-size: 16px;")
        lay.addWidget(msg)

        note = QLabel("<b>Free forever.</b> No account, no subscription. "
                      "Optional: add your own API key later in <b>Brain</b> for smarter answers.")
        note.setWordWrap(True)
        note.setAlignment(Qt.AlignmentFlag.AlignCenter)
        note.setStyleSheet(f"color: {GOLD['dim']}; font-size: 12.5px;")
        lay.addWidget(note)

        lay.addStretch(1)
        nav = QHBoxLayout()
        back = QPushButton("\u2190 BACK")
        back.clicked.connect(lambda: self._stack.setCurrentIndex(1))
        nav.addWidget(back)
        nav.addStretch(1)
        meet = QPushButton(f"MEET {APP_NAME.upper()} \u2192")
        meet.setProperty("gold", True)
        meet.clicked.connect(self.accept)
        nav.addWidget(meet)
        lay.addLayout(nav)
        return page

    # ------------------------------------------------------------------ logic
    def showEvent(self, event) -> None:  # noqa: N802
        super().showEvent(event)
        self._check_ollama()

    def _update_dots(self, index: int) -> None:
        for i, dot in enumerate(self._dots):
            active = i <= index
            dot.setStyleSheet(
                f"color: {'#f2c14e' if active else '#a89a7c'}; font-size: 11px; "
                "border: 1px solid rgba(242,193,78,"
                f"{'92' if active else '41'}); border-radius: 12px; padding: 5px 14px;"
                f"background: {'rgba(242,193,78,22)' if active else 'transparent'};"
            )

    def _check_ollama(self) -> None:
        ok = ollama_available()
        if ok:
            self._ollama_status.setText("\u2713 Ollama detected \u2014 you're good to go.")
            self._ollama_status.setStyleSheet(f"font-size: 14px; color: {GOLD['green']};")
            self._install_next.setEnabled(True)
        else:
            self._ollama_status.setText("\u25CB Ollama not detected yet.")
            self._ollama_status.setStyleSheet(f"font-size: 14px; color: {GOLD['amber']};")
            self._install_next.setEnabled(False)

    def _start_pull(self) -> None:
        model = self._model_edit.text().strip()
        if not model:
            return
        if self._pull_proc is not None and self._pull_proc.state() != QProcess.ProcessState.NotRunning:
            return  # already pulling
        self._pull_buf = ""
        self._pull_log.clear()
        self._pull_progress.setValue(0)
        self._pull_status.setText(f"Downloading {model}\u2026")
        self._pull_status.setStyleSheet(f"color: {GOLD['dim']}; font-size: 12.5px;")
        self._model_next.setEnabled(False)

        self._pull_proc = QProcess(self)
        # ollama streams its progress bar on stderr -> merge channels
        self._pull_proc.setProcessChannelMode(QProcess.ProcessChannelMode.MergedChannels)
        self._pull_proc.readyReadStandardOutput.connect(self._on_pull_output)
        self._pull_proc.finished.connect(self._on_pull_finished)
        self._pull_proc.start("ollama", ["pull", model])

    def _on_pull_output(self) -> None:
        data = bytes(self._pull_proc.readAllStandardOutput()).decode("utf-8", errors="replace")
        self._pull_buf += data
        # keep the log short: show only the tail
        lines = self._pull_buf.strip().splitlines()
        self._pull_log.setPlainText("\n".join(lines[-12:]))
        matches = _PERCENT_RE.findall(data)
        if matches:
            self._pull_progress.setValue(max(0, min(100, int(matches[-1]))))

    def _on_pull_finished(self, exit_code: int, _status) -> None:
        if exit_code == 0:
            self._pull_progress.setValue(100)
            self._pull_status.setText("\u2713 Model ready.")
            self._pull_status.setStyleSheet(f"color: {GOLD['green']}; font-size: 12.5px;")
            self._model_next.setEnabled(True)
        else:
            self._pull_status.setText(
                "\u2717 Download failed \u2014 is Ollama installed and running? "
                "You can also run `ollama pull` in a terminal and RE-CHECK."
            )
            self._pull_status.setStyleSheet(f"color: {GOLD['red']}; font-size: 12.5px;")
