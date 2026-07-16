from PyQt6.QtWidgets import QWidget, QSizePolicy
from PyQt6.QtGui import QPainter, QPen, QColor
from PyQt6.QtCore import Qt, QPointF, QRectF, pyqtSignal


class CarSeatSelector(QWidget):
    """Click-to-toggle passenger seats, drawn top-down inside a car outline."""

    passengersChanged = pyqtSignal(int)
    DESIGN_W, DESIGN_H = 100, 160

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMinimumSize(110, 176)
        self.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Maximum)
        self.seats = [
            {"rect": QRectF(30, 38, 16, 16), "fixed": True, "occupied": True},
            {"rect": QRectF(54, 38, 16, 16), "fixed": False, "occupied": False},
            {"rect": QRectF(28, 76, 15, 16), "fixed": False, "occupied": False},
            {"rect": QRectF(43, 90, 15, 16), "fixed": False, "occupied": False},
            {"rect": QRectF(58, 76, 15, 16), "fixed": False, "occupied": False},
        ]

    def passenger_count(self) -> int:
        return sum(1 for s in self.seats if s["occupied"])

    def _scale(self):
        return self.width() / self.DESIGN_W, self.height() / self.DESIGN_H

    def mousePressEvent(self, event):
        sx, sy = self._scale()
        pos = event.position()
        design_pt = QPointF(pos.x() / sx, pos.y() / sy)
        for seat in self.seats:
            if seat["fixed"]:
                continue
            if seat["rect"].contains(design_pt):
                seat["occupied"] = not seat["occupied"]
                self.update()
                self.passengersChanged.emit(self.passenger_count())
                return

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        sx, sy = self._scale()
        painter.scale(sx, sy)

        painter.setPen(QPen(QColor("#00d9c0"), 1.6))
        painter.setBrush(QColor("#242430"))
        painter.drawRoundedRect(QRectF(10, 6, 80, 148), 32, 46)

        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QColor("#e2504a"))
        for cx, cy in [(18, 16), (82, 16), (18, 144), (82, 144)]:
            painter.drawEllipse(QPointF(cx, cy), 5, 5)

        painter.setBrush(QColor("#0a0a0d"))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(QRectF(24, 26, 52, 108), 16, 16)

        painter.setPen(QPen(QColor("#8a8a93"), 1.3))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(QPointF(19, 46), 5, 5)
        painter.drawLine(QPointF(19, 42), QPointF(19, 50))
        painter.drawLine(QPointF(15, 46), QPointF(23, 46))

        for seat in self.seats:
            r = seat["rect"]
            if seat["occupied"]:
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(QColor("#00d9c0"))
            else:
                painter.setPen(QPen(QColor("#00d9c0"), 1.5))
                painter.setBrush(QColor("#1c1c22"))
            painter.drawRoundedRect(r, 4, 4)
