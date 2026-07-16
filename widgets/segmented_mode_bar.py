from PyQt6.QtWidgets import QWidget, QSizePolicy
from PyQt6.QtGui import QPainter, QPen, QColor
from PyQt6.QtCore import Qt, QPointF, QRectF

from theme import Colors


class SegmentedModeBar(QWidget):
    """Trip-length bar showing every planned Electric/Gas segment as a
    colored block, a dimmed overlay for distance not yet traveled, and a
    tick mark for each manual charging stop. Colors from theme.Colors."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedHeight(16)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._segments: list[list] = []
        self._stops: list[int] = []
        self._distance = 1.0
        self._traveled = 0.0

    def set_plan(self, segments: list[list], stops: list[int], distance: float):
        self._segments = segments
        self._stops = stops
        self._distance = max(1.0, distance)
        self.update()

    def set_traveled(self, miles: float):
        self._traveled = miles
        self.update()

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = self.width(), self.height()

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(Colors.CARD_HOVER)
        painter.drawRoundedRect(0, 0, w, h, h / 2, h / 2)

        for start, end, mode in self._segments:
            x1 = (start / self._distance) * w
            x2 = (end / self._distance) * w
            color = Colors.EV if mode == "Electric" else Colors.GAS
            painter.setBrush(color)
            painter.drawRect(QRectF(x1, 0, max(1.0, x2 - x1), h))

        traveled_x = (min(self._traveled, self._distance) / self._distance) * w
        if traveled_x < w:
            dim = QColor(Colors.DASHBOARD)
            dim.setAlpha(150)
            painter.setBrush(dim)
            painter.drawRect(QRectF(traveled_x, 0, w - traveled_x, h))

        painter.setPen(QPen(Colors.TEXT, 1.4))
        for stop in self._stops:
            x = (stop / self._distance) * w
            painter.drawLine(QPointF(x, 1), QPointF(x, h - 1))