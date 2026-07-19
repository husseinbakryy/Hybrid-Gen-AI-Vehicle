"""
Circular automotive-style speedometer: 270-degree sweep, dark background
disc, radial tick marks with numbers, a single-color progress arc, and a
glowing needle + hub. All colors/sizes from theme.py.

Needle/arc/number smoothly animate toward each new setSpeed() target via
animate_value (a QVariantAnimation-based value interpolator - NOT a
QGraphicsEffect, so it's unaffected by the earlier shadow/opacity bug).
Since setSpeed() can be called every ~100ms during a running trip, any
in-flight animation is stopped before starting a new one - otherwise
multiple animations would fight over the needle position and jitter
instead of smoothly chasing the latest target.
"""

from math import cos, sin, radians

from PyQt6.QtWidgets import QWidget, QSizePolicy
from PyQt6.QtGui import QPainter, QPen, QFont
from PyQt6.QtCore import Qt, QRectF

from theme import Colors, Fonts, SpeedometerTheme, Animation
from animations import animate_value


class Speedometer(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(260, 260)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self._speed = 0.0
        self._display_speed = 0.0
        self._sweep_anim = None

    def setSpeed(self, value: float):
        target = max(SpeedometerTheme.MIN_SPEED, min(SpeedometerTheme.MAX_SPEED, value))
        self._speed = target

        if self._sweep_anim is not None:
            self._sweep_anim.stop()

        self._sweep_anim = animate_value(
            self._set_display_speed,
            self._display_speed,
            target,
            duration=Animation.FAST,
            parent=self,
        )

    def _set_display_speed(self, value: float):
        self._display_speed = value
        self.update()

    def speed(self) -> float:
        return self._speed

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        rect = QRectF(self.rect()).adjusted(20, 20, -20, -20)
        center = rect.center()
        radius = min(rect.width(), rect.height()) / 2

        self._draw_background(painter, center, radius)
        self._draw_ticks(painter, center, radius)
        self._draw_arc(painter, center, radius)
        self._draw_needle(painter, center, radius)
        self._draw_speed_text(painter, center)

    def _draw_background(self, painter, center, radius):
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(Colors.DASHBOARD)
        painter.drawEllipse(center, radius, radius)

    def _draw_arc(self, painter, center, radius):
        pen = QPen(Colors.EV, SpeedometerTheme.ARC_WIDTH)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)

        arc_rect = QRectF(
            center.x() - radius + 15, center.y() - radius + 15,
            (radius - 15) * 2, (radius - 15) * 2,
        )
        start_deg = 225
        span_deg = 270 * (self._display_speed / SpeedometerTheme.MAX_SPEED)
        painter.drawArc(arc_rect, int(start_deg * 16), int(-span_deg * 16))

    def _draw_ticks(self, painter, center, radius):
        painter.setPen(QPen(Colors.TEXT_SECONDARY, 2))
        for value in range(SpeedometerTheme.MIN_SPEED, SpeedometerTheme.MAX_SPEED + 1, 10):
            angle = radians(225 - (270 * value / SpeedometerTheme.MAX_SPEED))
            outer, inner = radius - 8, radius - 24
            x1 = center.x() + outer * cos(angle)
            y1 = center.y() - outer * sin(angle)
            x2 = center.x() + inner * cos(angle)
            y2 = center.y() - inner * sin(angle)
            painter.drawLine(int(x1), int(y1), int(x2), int(y2))

            text_radius = radius - 45
            tx = center.x() + text_radius * cos(angle)
            ty = center.y() - text_radius * sin(angle)
            painter.setFont(QFont(Fonts.FAMILY, 10))
            painter.drawText(int(tx - 12), int(ty - 10), 24, 20,
                              Qt.AlignmentFlag.AlignCenter, str(value))

    def _draw_needle(self, painter, center, radius):
        angle = radians(225 - (270 * self._display_speed / SpeedometerTheme.MAX_SPEED))
        length = radius - 55
        x = center.x() + length * cos(angle)
        y = center.y() - length * sin(angle)

        pen = QPen(Colors.EV_GLOW, SpeedometerTheme.NEEDLE_WIDTH)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        painter.drawLine(center, center.__class__(int(x), int(y)))

        painter.setBrush(Colors.EV)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(center, SpeedometerTheme.HUB_RADIUS, SpeedometerTheme.HUB_RADIUS)

    def _draw_speed_text(self, painter, center):
        painter.setPen(Colors.TEXT)
        painter.setFont(QFont(Fonts.FAMILY, SpeedometerTheme.SPEED_TEXT_SIZE, QFont.Weight.Bold))
        text_rect = self.rect().translated(0, SpeedometerTheme.SPEED_TEXT_Y_OFFSET)
        painter.drawText(text_rect, Qt.AlignmentFlag.AlignCenter, str(round(self._display_speed)))

        painter.setFont(QFont(Fonts.FAMILY, Fonts.SMALL + 1))
        mph_y = int(center.y()) + 40 + SpeedometerTheme.SPEED_TEXT_Y_OFFSET
        painter.drawText(0, mph_y, self.width(), 30,
                          Qt.AlignmentFlag.AlignHCenter, "MPH")