"""Command Center: full-screen 3-column view (agents | orb | live feed)."""

import math

from PySide6.QtCore import Qt, QTimer, Signal, QPointF
from PySide6.QtGui import QPainter, QPen, QColor, QRadialGradient, QFont
from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QVBoxLayout, QGridLayout, QFrame, QLabel,
    QPushButton, QLineEdit, QTextEdit, QButtonGroup,
)

from theme import GOLD, refresh_dynamic_style
from orb import OrbWidget

# (key, display name, role, initials)
AGENTS = [
    ("scout", "Scout", "Research", "SC"),
    ("forge", "Forge", "Files & Apps", "FO"),
    ("echo", "Echo", "Voice", "EC"),
    ("pulse", "Pulse", "System", "PU"),
]

# (emoji, label)
SKILLS = [
    ("\U0001F4C1", "Files"),
    ("\U0001F310", "Web"),
    ("\U0001F5A5\uFE0F", "Apps"),
    ("\u23F0", "Remind"),
    ("\U0001F9E0", "Memory"),
    ("\U0001F399\uFE0F", "Voice"),
]

# (node key, label)
NODES = [
    ("memory", "MEMORY"),
    ("skills", "SKILLS"),
    ("soul", "SOUL"),
    ("settings", "SETTINGS"),
]

_MONO = "'Cascadia Code', Consolas, monospace"


class _Clickable(QFrame):
    """QFrame that emits clicked(key) on mouse press."""
    clicked = Signal(str)

    def __init__(self, key: str, parent=None):
        super().__init__(parent)
        self._key = key
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def mousePressEvent(self, event) -> None:  # noqa: N802
        self.clicked.emit(self._key)
        super().mousePressEvent(event)


class _AgentCard(_Clickable):
    def __init__(self, key: str, name: str, role: str, initials: str, parent=None):
        super().__init__(key, parent)
        self.setProperty("card", True)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 12, 8, 12)
        layout.setSpacing(6)
        avatar = QLabel(initials)
        avatar.setAlignment(Qt.AlignmentFlag.AlignCenter)
        avatar.setStyleSheet(
            "font-weight: 700; font-size: 13px; color: #a89a7c;"
            "border: 1px solid rgba(242,193,78,41); border-radius: 20px;"
            "min-width: 40px; min-height: 40px; max-width: 40px; max-height: 40px;"
        )
        name_lbl = QLabel(name)
        name_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        name_lbl.setStyleSheet("font-weight: 600; font-size: 12.5px;")
        role_lbl = QLabel(role)
        role_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        role_lbl.setStyleSheet("color: #a89a7c; font-size: 10.5px;")
        for w in (avatar, name_lbl, role_lbl):
            w.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        layout.addWidget(avatar, alignment=Qt.AlignmentFlag.AlignHCenter)
        layout.addWidget(name_lbl)
        layout.addWidget(role_lbl)
        self._avatar = avatar

    def set_selected(self, selected: bool) -> None:
        self.setProperty("selected", selected)
        refresh_dynamic_style(self)
        self._avatar.setStyleSheet(
            "font-weight: 700; font-size: 13px;"
            f"color: {'#f2c14e' if selected else '#a89a7c'};"
            f"border: 1px solid rgba(242,193,78,{'92' if selected else '41'}); border-radius: 20px;"
            "min-width: 40px; min-height: 40px; max-width: 40px; max-height: 40px;"
        )


class _NodeLabel(QLabel):
    clicked = Signal(str)

    def __init__(self, key: str, text: str, parent=None):
        super().__init__(text, parent)
        self._key = key
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet(
            "color: #a89a7c; font-size: 12px; padding: 8px 14px;"
            "border: 1px solid rgba(242,193,78,41); border-radius: 10px;"
            "background: rgba(255,255,255,4);"
        )

    def mousePressEvent(self, event) -> None:  # noqa: N802
        self.clicked.emit(self._key)
        super().mousePressEvent(event)

    def enterEvent(self, event) -> None:  # noqa: N802
        self.setStyleSheet(
            "color: #f2c14e; font-size: 12px; font-weight: 600; padding: 8px 14px;"
            "border: 1px solid rgba(242,193,78,92); border-radius: 10px;"
            "background: rgba(242,193,78,22);"
        )
        super().enterEvent(event)

    def leaveEvent(self, event) -> None:  # noqa: N802
        self.setStyleSheet(
            "color: #a89a7c; font-size: 12px; padding: 8px 14px;"
            "border: 1px solid rgba(242,193,78,41); border-radius: 10px;"
            "background: rgba(255,255,255,4);"
        )
        super().leaveEvent(event)


class SystemVisual(QWidget):
    """Mini animated system visual: concentric rings, orbiting dots, glowing core."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(150)
        self._angle = 0.0
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(50)

    def _tick(self) -> None:
        self._angle = (self._angle + 2.5) % 360.0
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        cx, cy = self.width() / 2.0, self.height() / 2.0
        gold = (242, 193, 78)

        for radius, alpha in ((34, 90), (54, 60), (74, 36)):
            pen = QPen(QColor(*gold, alpha))
            pen.setWidth(1)
            p.setPen(pen)
            p.setBrush(Qt.BrushStyle.NoBrush)
            p.drawEllipse(QPointF(cx, cy), radius, radius)

        # orbiting dots (opposite directions)
        for radius, ang, color in (
            (74, self._angle, QColor(*gold, 220)),
            (54, -self._angle * 1.4, QColor(52, 211, 153, 220)),
        ):
            rad = math.radians(ang)
            dot = QPointF(cx + radius * math.cos(rad), cy + radius * math.sin(rad))
            p.setPen(Qt.PenStyle.NoPen)
            p.setBrush(color)
            p.drawEllipse(dot, 4.5, 4.5)

        # glowing core
        core = QRadialGradient(cx, cy, 26)
        core.setColorAt(0.0, QColor("#fff6dd"))
        core.setColorAt(0.5, QColor(242, 193, 78, 200))
        core.setColorAt(1.0, QColor(242, 193, 78, 0))
        p.setBrush(core)
        p.drawEllipse(QPointF(cx, cy), 26, 26)


class CommandCenterWidget(QWidget):
    """3-column command center.

    Signals:
        start_ai_clicked: START AI button pressed (or Enter in the input line).
        agent_selected(str): agent key, e.g. 'scout'.
        node_clicked(str): node key, e.g. 'memory'.
        vi_toggled(bool): visual-intelligence toggle changed.
    """

    start_ai_clicked = Signal()
    agent_selected = Signal(str)
    node_clicked = Signal(str)
    vi_toggled = Signal(bool)

    def __init__(self, parent=None):
        super().__init__(parent)
        root = QHBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        root.addWidget(self._build_left(), 0)
        root.addWidget(self._build_center(), 1)
        root.addWidget(self._build_right(), 0)

    # ------------------------------------------------------------------ left
    def _build_left(self) -> QWidget:
        col = QWidget()
        col.setFixedWidth(300)
        layout = QVBoxLayout(col)
        layout.setContentsMargins(16, 18, 16, 18)
        layout.setSpacing(8)

        layout.addWidget(self._heading("SELECTED AGENT"))
        grid = QGridLayout()
        grid.setSpacing(10)
        self._agent_cards = {}
        for i, (key, name, role, initials) in enumerate(AGENTS):
            card = _AgentCard(key, name, role, initials)
            card.clicked.connect(self._on_agent_clicked)
            self._agent_cards[key] = card
            grid.addWidget(card, i // 2, i % 2)
        layout.addLayout(grid)
        self._agent_cards["scout"].set_selected(True)
        self._selected_agent = "scout"

        layout.addSpacing(10)
        layout.addWidget(self._heading("SKILLS"))
        sgrid = QGridLayout()
        sgrid.setSpacing(8)
        for i, (emoji, label) in enumerate(SKILLS):
            tile = QFrame()
            tile.setProperty("card", True)
            tl = QVBoxLayout(tile)
            tl.setContentsMargins(4, 10, 4, 10)
            tl.setSpacing(5)
            ic = QLabel(emoji)
            ic.setAlignment(Qt.AlignmentFlag.AlignCenter)
            ic.setStyleSheet("font-size: 17px;")
            nm = QLabel(label)
            nm.setAlignment(Qt.AlignmentFlag.AlignCenter)
            nm.setStyleSheet("color: #a89a7c; font-size: 10.5px;")
            tl.addWidget(ic)
            tl.addWidget(nm)
            sgrid.addWidget(tile, i // 3, i % 3)
        layout.addLayout(sgrid)

        layout.addStretch(1)
        layout.addWidget(self._heading("SYSTEM"))
        layout.addWidget(SystemVisual())
        return col

    def _on_agent_clicked(self, key: str) -> None:
        for k, card in self._agent_cards.items():
            card.set_selected(k == key)
        self._selected_agent = key
        self.agent_selected.emit(key)

    # ---------------------------------------------------------------- center
    def _build_center(self) -> QWidget:
        col = QWidget()
        layout = QVBoxLayout(col)
        layout.setContentsMargins(26, 22, 26, 22)
        layout.setSpacing(14)

        # node labels row (clickable -> node_clicked)
        nodes = QHBoxLayout()
        nodes.setSpacing(10)
        nodes.addStretch(1)
        for key, label in NODES:
            nl = _NodeLabel(key, f"[ {label} ]")
            nl.clicked.connect(self.node_clicked.emit)
            nodes.addWidget(nl)
        nodes.addStretch(1)
        layout.addLayout(nodes)

        # orb + start button
        center_box = QVBoxLayout()
        center_box.setSpacing(10)
        self.orb = OrbWidget(size=190)
        center_box.addWidget(self.orb, alignment=Qt.AlignmentFlag.AlignHCenter)

        self.start_button = QPushButton("START AI")
        self.start_button.setProperty("gold", True)
        self.start_button.setCursor(Qt.CursorShape.PointingHandCursor)
        self.start_button.setStyleSheet("font-size: 13px; letter-spacing: 2px;")
        self.start_button.clicked.connect(self.start_ai_clicked.emit)
        center_box.addWidget(self.start_button, alignment=Qt.AlignmentFlag.AlignHCenter)

        self.brain_status_label = QLabel("")
        self.brain_status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.brain_status_label.setStyleSheet(f"color: {GOLD['dim']}; font-size: 11px;")
        center_box.addWidget(self.brain_status_label)
        layout.addLayout(center_box)

        # slim text input row (voice-first design; typing is the fallback)
        input_row = QHBoxLayout()
        input_row.setSpacing(8)
        self.user_input = QLineEdit()
        self.user_input.setPlaceholderText("Type or speak...  (Enter = ask Vicky Talk)")
        self.user_input.returnPressed.connect(self.start_ai_clicked.emit)
        self.mic_button = QPushButton("\U0001F399\uFE0F")
        self.mic_button.setFixedWidth(48)
        self.mic_button.setToolTip("Voice input")
        input_row.addWidget(self.user_input, 1)
        input_row.addWidget(self.mic_button, 0)
        layout.addLayout(input_row)

        # visual intelligence panel
        vi = QFrame()
        vi.setProperty("panel", True)
        vi_layout = QHBoxLayout(vi)
        vi_layout.setContentsMargins(18, 14, 18, 14)
        vi_layout.setSpacing(14)
        vi_title = QLabel("<b>VISUAL INTELLIGENCE</b>")
        vi_title.setStyleSheet(f"color: {GOLD['text']}; font-size: 11px;")
        vi_layout.addWidget(vi_title)

        self._vi_chips = QButtonGroup(self)
        self._vi_chips.setExclusive(False)
        for label, on in (("SCREEN AWARE", True), ("VOICE", True), ("AUTO PILOT", False)):
            chip = QPushButton(label)
            chip.setProperty("chip", True)
            chip.setCheckable(True)
            chip.setChecked(on)
            self._vi_chips.addButton(chip)
            vi_layout.addWidget(chip)
        vi_layout.addStretch(1)

        self.vi_toggle = QPushButton("ON")
        self.vi_toggle.setCheckable(True)
        self.vi_toggle.setChecked(True)
        self.vi_toggle.setProperty("chip", True)
        self.vi_toggle.toggled.connect(self._on_vi_toggled)
        vi_layout.addWidget(self.vi_toggle)
        layout.addWidget(vi)

        layout.addStretch(1)
        return col

    def _on_vi_toggled(self, on: bool) -> None:
        self.vi_toggle.setText("ON" if on else "OFF")
        self.vi_toggled.emit(on)

    # ----------------------------------------------------------------- right
    def _build_right(self) -> QWidget:
        col = QWidget()
        col.setFixedWidth(350)
        layout = QVBoxLayout(col)
        layout.setContentsMargins(16, 18, 16, 18)
        layout.setSpacing(8)
        layout.addWidget(self._heading("LIVE FEED"))
        self.feed = QTextEdit()
        self.feed.setReadOnly(True)
        self.feed.setStyleSheet(f"font-family: {_MONO}; font-size: 11.5px; color: #ffe3a3;")
        layout.addWidget(self.feed, 1)
        return col

    # ---------------------------------------------------------------- helpers
    @staticmethod
    def _heading(text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setProperty("heading", True)
        return lbl

    def append_line(self, text: str) -> None:
        """Append a line to the live feed (auto-scrolls)."""
        self.feed.append(text)

    def set_brain_status(self, text: str) -> None:
        """Update the small brain-status label under START AI."""
        self.brain_status_label.setText(text)

    def set_orb_state(self, state: str) -> None:
        """Proxy to OrbWidget.set_state ('idle'|'listening'|'thinking'|'speaking')."""
        self.orb.set_state(state)

    @property
    def selected_agent(self) -> str:
        return self._selected_agent
