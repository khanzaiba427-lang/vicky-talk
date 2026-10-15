"""Glowing golden orb widget with rotating dashed rings."""

import math

from PySide6.QtCore import Qt, QTimer, QPointF, QRectF
from PySide6.QtGui import QPainter, QPen, QColor, QRadialGradient
from PySide6.QtWidgets import QWidget

# Animation parameters per state: rotation speed (deg per tick), glow strength,
# breathing amplitude.
_ORB_STATES = {
    "idle": {"speed": 1.2, "glow": 0.55, "pulse": 0.05},
    "listening": {"speed": 4.0, "glow": 0.85, "pulse": 0.10},
    "thinking": {"speed": 8.0, "glow": 1.00, "pulse": 0.16},
    "speaking": {"speed": 5.0, "glow": 0.90, "pulse": 0.12},
}

_GOLD = (242, 193, 78)


class OrbWidget(QWidget):
    """A ~200px golden orb: radial-gradient sphere, outer glow, and two
    counter-rotating dashed rings. set_state() changes animation behaviour."""

    def __init__(self, parent=None, size: int = 200):
        super().__init__(parent)
        self.setFixedSize(size, size)
        self._angle = 0.0
        self._pulse = 0.0
        self._params = _ORB_STATES["idle"]
        self._timer = QTimer(self)
        self._timer.timeout.connect(self._tick)
        self._timer.start(30)  # ~33 fps

    def set_state(self, state: str) -> None:
        """Switch animation state: 'idle' | 'listening' | 'thinking' | 'speaking'."""
        self._params = _ORB_STATES.get(state, _ORB_STATES["idle"])

    def _tick(self) -> None:
        self._angle = (self._angle + self._params["speed"]) % 360.0
        self._pulse += 0.06
        self.update()

    def paintEvent(self, event) -> None:  # noqa: N802 (Qt naming)
        p = QPainter(self)
        p.setRenderHint(QPainter.RenderHint.Antialiasing)
        cx, cy = self.width() / 2.0, self.height() / 2.0
        base_r = min(self.width(), self.height()) / 2.0 - 16.0
        glow_strength = self._params["glow"]

        # --- outer glow halo ---
        halo_r = base_r * 1.45
        halo = QRadialGradient(cx, cy, halo_r)
        halo.setColorAt(0.0, QColor(*_GOLD, int(70 * glow_strength)))
        halo.setColorAt(0.6, QColor(*_GOLD, int(22 * glow_strength)))
        halo.setColorAt(1.0, QColor(*_GOLD, 0))
        p.setPen(Qt.PenStyle.NoPen)
        p.setBrush(halo)
        p.drawEllipse(QPointF(cx, cy), halo_r, halo_r)

        # --- orb body (breathing) ---
        r = base_r * (1.0 + 0.035 * math.sin(self._pulse) * (self._params["pulse"] / 0.05))
        body = QRadialGradient(cx - r * 0.30, cy - r * 0.35, r * 0.15, cx, cy, r)
        body.setColorAt(0.00, QColor("#fff8e2"))
        body.setColorAt(0.18, QColor("#ffe6ad"))
        body.setColorAt(0.45, QColor("#f2c14e"))
        body.setColorAt(0.72, QColor("#9a6a24"))
        body.setColorAt(1.00, QColor("#170e02"))
        p.setBrush(body)
        p.drawEllipse(QPointF(cx, cy), r, r)

        # --- specular highlight ---
        hi = QRadialGradient(cx - r * 0.32, cy - r * 0.38, r * 0.05, cx - r * 0.32, cy - r * 0.38, r * 0.42)
        hi.setColorAt(0.0, QColor(255, 250, 230, 150))
        hi.setColorAt(1.0, QColor(255, 250, 230, 0))
        p.setBrush(hi)
        p.drawEllipse(QPointF(cx - r * 0.32, cy - r * 0.38), r * 0.42, r * 0.42)

        # --- two counter-rotating dashed rings ---
        self._draw_dashed_ring(p, cx, cy, r + 7, dashes=14, span_deg=16,
                               offset=self._angle, alpha=int(150 * glow_strength))
        self._draw_dashed_ring(p, cx, cy, r + 17, dashes=10, span_deg=22,
                               offset=-self._angle * 0.6, alpha=int(90 * glow_strength))

    def _draw_dashed_ring(self, p: QPainter, cx: float, cy: float, radius: float,
                          dashes: int, span_deg: float, offset: float, alpha: int) -> None:
        pen = QPen(QColor(*_GOLD, alpha))
        pen.setWidth(2)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        p.setPen(pen)
        p.setBrush(Qt.BrushStyle.NoBrush)
        rect = QRectF(cx - radius, cy - radius, radius * 2.0, radius * 2.0)
        for i in range(dashes):
            start = (offset + i * (360.0 / dashes)) % 360.0
            # Qt drawArc uses 1/16th of a degree, 0 = 3 o'clock, counter-clockwise.
            p.drawArc(rect, int(start * 16), int(span_deg * 16))
