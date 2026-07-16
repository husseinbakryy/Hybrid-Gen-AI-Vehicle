from PyQt6.QtWidgets import QWidget, QSizePolicy
from PyQt6.QtGui import QPainter, QPen, QColor
from PyQt6.QtCore import Qt, QPointF, QRectF


class SegmentedModeBar(QWidget):
    """Trip-length bar showing every planned Electric/Gas segment as a
    colored block, a dimmed overlay for distance not yet traveled, and a
    tick mark for each manual charging stop."""

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
        painter.setBrush(QColor("#1c1c22"))
        painter.drawRoundedRect(0, 0, w, h, h / 2, h / 2)

        painter.setBrush(QColor("#1c1c22"))
        for start, end, mode in self._segments:
            x1 = (start / self._distance) * w
            x2 = (end / self._distance) * w
            color = QColor("#00d9c0") if mode == "Electric" else QColor("#ff8a5c")
            painter.setBrush(color)
            painter.drawRect(QRectF(x1, 0, max(1.0, x2 - x1), h))

        traveled_x = (min(self._traveled, self._distance) / self._distance) * w
        if traveled_x < w:
            painter.setBrush(QColor(10, 10, 13, 150))
            painter.drawRect(QRectF(traveled_x, 0, w - traveled_x, h))

        painter.setPen(QPen(QColor("#e8e8ec"), 1.4))
        for stop in self._stops:
            x = (stop / self._distance) * w
            painter.drawLine(QPointF(x, 1), QPointF(x, h - 1))
