import math
from PyQt6.QtWidgets import QWidget, QSizePolicy
from PyQt6.QtGui import QPainter, QPen, QColor, QFont
from PyQt6.QtCore import Qt, QPointF, QRectF


class Speedometer(QWidget):
    """A hand-drawn speedometer, 0-80 mph, with colored zones and a needle."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(240, 170)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)
        self._speed = 0.0

    def setSpeed(self, value: float):
        self._speed = max(0.0, min(80.0, value))
        self.update()

    def speed(self) -> float:
        return self._speed

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        w, h = self.width(), self.height()
        cx, cy = w / 2, h * 0.75
        radius = min(w, h * 1.3) * 0.42

        pen = QPen(QColor("#1c1c22"), radius * 0.12)
        pen.setCapStyle(Qt.PenCapStyle.FlatCap)
        painter.setPen(pen)
        rect = QRectF(cx - radius, cy - radius, radius * 2, radius * 2)
        painter.drawArc(rect, 0, 180 * 16)

        zones = [(0, 40, "#0ed440"), (40, 65, "#854f0b"), (65, 80, "#993c1d")]
        for lo, hi, color in zones:
            start_angle = 180 - (lo / 80) * 180
            span_angle = -(hi - lo) / 80 * 180
            pen.setColor(QColor(color))
            painter.setPen(pen)
            painter.drawArc(rect, int(start_angle * 16), int(span_angle * 16))

        painter.setPen(QPen(QColor("#3a3a42"), 2))
        for mph in range(0, 81, 20):
            angle_deg = 180 - (mph / 80) * 180
            rad = math.radians(angle_deg)
            x1 = cx + (radius * 0.82) * math.cos(rad)
            y1 = cy - (radius * 0.82) * math.sin(rad)
            x2 = cx + (radius * 0.92) * math.cos(rad)
            y2 = cy - (radius * 0.92) * math.sin(rad)
            painter.drawLine(QPointF(x1, y1), QPointF(x2, y2))

        angle_deg = 180 - (self._speed / 80) * 180
        rad = math.radians(angle_deg)
        tip_x = cx + (radius * 0.78) * math.cos(rad)
        tip_y = cy - (radius * 0.78) * math.sin(rad)
        painter.setPen(QPen(QColor("#ff433d"), 3))
        painter.drawLine(QPointF(cx, cy), QPointF(tip_x, tip_y))

        painter.setBrush(QColor("#242430"))
        painter.setPen(QPen(QColor("#ff5c3d"), 2))
        painter.drawEllipse(QPointF(cx, cy), 8, 8)

        painter.setPen(QColor("#e8e8ec"))
        painter.setFont(QFont("Arial", 16, QFont.Weight.Medium))
        painter.drawText(
            QRectF(0, cy + radius * 0.15, w, 40),
            Qt.AlignmentFlag.AlignCenter,
            f"{round(self._speed)} MPH",
        )
