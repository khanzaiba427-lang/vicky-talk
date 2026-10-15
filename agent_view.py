"""Agent view: current objective, steps checklist, live log, capability chips."""

from PySide6.QtCore import Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QFrame, QLabel,
    QPushButton, QListWidget, QListWidgetItem, QTextEdit, QProgressBar,
)

from theme import GOLD

_MONO = "'Cascadia Code', Consolas, monospace"

# step state -> (glyph, color)
_STEP_STYLE = {
    "done": ("\u2713", GOLD["green"]),
    "active": ("\u25CF", GOLD["gold"]),
    "todo": ("\u25CB", GOLD["dim"]),
}


class AgentView(QWidget):
    """Shows one running objective: header + progress, steps, live log, chips.

    Signals:
        pause_clicked / stop_clicked: emitted by the header buttons.
    """

    pause_clicked = Signal()
    stop_clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(26, 22, 26, 22)
        layout.setSpacing(16)

        # ---- objective header card ----
        header = QFrame()
        header.setProperty("card", True)
        header.setProperty("selected", True)
        hl = QHBoxLayout(header)
        hl.setContentsMargins(22, 18, 22, 18)
        hl.setSpacing(18)

        left = QVBoxLayout()
        left.setSpacing(8)
        cap = QLabel("CURRENT OBJECTIVE")
        cap.setProperty("heading", True)
        self.objective_name = QLabel("No objective running")
        self.objective_name.setStyleSheet("font-size: 17px; font-weight: 600;")
        self.objective_name.setWordWrap(True)
        self.progress = QProgressBar()
        self.progress.setRange(0, 100)
        self.progress.setValue(0)
        self.progress.setTextVisible(True)
        left.addWidget(cap)
        left.addWidget(self.objective_name)
        left.addWidget(self.progress)
        hl.addLayout(left, 1)

        self.pct_label = QLabel("0%")
        self.pct_label.setStyleSheet(
            f"font-size: 22px; font-weight: 700; color: {GOLD['gold']};"
        )
        hl.addWidget(self.pct_label)

        self.pause_button = QPushButton("\u275A\u275A PAUSE")
        self.pause_button.clicked.connect(self.pause_clicked.emit)
        self.stop_button = QPushButton("\u25A0 STOP")
        self.stop_button.setProperty("danger", True)
        self.stop_button.clicked.connect(self.stop_clicked.emit)
        hl.addWidget(self.pause_button)
        hl.addWidget(self.stop_button)
        layout.addWidget(header)

        # ---- steps + log columns ----
        cols = QHBoxLayout()
        cols.setSpacing(16)

        steps_card = QFrame()
        steps_card.setProperty("card", True)
        sl = QVBoxLayout(steps_card)
        sl.setContentsMargins(18, 16, 18, 16)
        steps_cap = QLabel("STEPS")
        steps_cap.setProperty("heading", True)
        sl.addWidget(steps_cap)
        self.steps_list = QListWidget()
        sl.addWidget(self.steps_list, 1)
        cols.addWidget(steps_card, 1)

        log_card = QFrame()
        log_card.setProperty("card", True)
        ll = QVBoxLayout(log_card)
        ll.setContentsMargins(18, 16, 18, 16)
        log_cap = QLabel("LIVE LOG")
        log_cap.setProperty("heading", True)
        ll.addWidget(log_cap)
        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.log.setStyleSheet(f"font-family: {_MONO}; font-size: 12px; color: #ffe3a3;")
        ll.addWidget(self.log, 1)
        cols.addWidget(log_card, 1)

        layout.addLayout(cols, 1)

        # ---- capability chips ----
        chips = QHBoxLayout()
        chips.setSpacing(10)
        for name, desc in (
            ("Files", "read / write / organize"),
            ("Apps", "open / close"),
            ("Browser", "surf / fill / upload"),
            ("System", "with confirmation"),
        ):
            chip = QLabel(f"<b>{name}</b> \u00B7 {desc}")
            chip.setProperty("pill", True)
            chip.setStyleSheet(chip.styleSheet() + "padding: 8px 16px; font-size: 11.5px;")
            chips.addWidget(chip)
        chips.addStretch(1)
        layout.addLayout(chips)

    # ------------------------------------------------------------------ API
    def set_objective(self, name: str, progress: int) -> None:
        """Set the objective title and progress (0-100)."""
        self.objective_name.setText(name)
        progress = max(0, min(100, int(progress)))
        self.progress.setValue(progress)
        self.pct_label.setText(f"{progress}%")

    def set_steps(self, steps) -> None:
        """Replace the checklist. steps: iterable of (text, state) where
        state is 'done' | 'active' | 'todo'."""
        self.steps_list.clear()
        for text, state in steps:
            glyph, color = _STEP_STYLE.get(state, _STEP_STYLE["todo"])
            item = QListWidgetItem(f"{glyph}   {text}")
            item.setForeground(QColor(color))
            self.steps_list.addItem(item)

    def log_line(self, text: str) -> None:
        """Append a line to the live log."""
        self.log.append(text)
