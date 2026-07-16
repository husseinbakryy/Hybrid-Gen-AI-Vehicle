"""
Click-to-toggle passenger seats, drawn top-down inside a car outline.

v2 design: adds visible wheel wells at the four corners, a windshield/
rear-window band separating the cabin glass from the hood/trunk, and
small side mirrors - the previous version was just a rounded body with
no wheels or glass, which is why it didn't read as an actual car.
"""

from PyQt6.QtWidgets import QWidget, QSizePolicy
from PyQt6.QtGui import QPainter, QPen
from PyQt6.QtCore import Qt, QPointF, QRectF, pyqtSignal

from theme import Colors


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

        # --- Body ---
        painter.setPen(QPen(Colors.EV, 1.6))
        painter.setBrush(Colors.GRAPHITE)
        painter.drawRoundedRect(QRectF(10, 6, 80, 148), 32, 46)

        # --- Side mirrors (small ellipses just outside the body, level
        # with the windshield) - one of the clearest "this is a car" cues ---
        painter.setPen(QPen(Colors.EV, 1.3))
        painter.setBrush(Colors.GRAPHITE)
        painter.drawEllipse(QPointF(7, 34), 4, 5)
        painter.drawEllipse(QPointF(93, 34), 4, 5)

        # --- Wheel wells at the four corners - dark recessed rounded
        # rects with a small red hub accent, giving the body actual wheels
        # instead of reading as a featureless pill ---
        painter.setPen(QPen(Colors.EV, 1.2))
        painter.setBrush(Colors.DASHBOARD)
        wheel_positions = [(12, 26), (75, 26), (12, 110), (75, 110)]
        for wx, wy in wheel_positions:
            painter.drawRoundedRect(QRectF(wx, wy, 13, 24), 6, 6)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(Colors.RED)
        for wx, wy in wheel_positions:
            painter.drawEllipse(QPointF(wx + 6.5, wy + 12), 3, 3)

        # --- Interior tub ---
        painter.setBrush(Colors.DASHBOARD)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawRoundedRect(QRectF(24, 26, 52, 108), 16, 16)

        # --- Windshield / rear-window glass bands - separates the cabin
        # from the hood and trunk, another key "this is a car" cue ---
        painter.setBrush(Colors.CARD_HOVER)
        painter.drawRoundedRect(QRectF(28, 28, 44, 7), 4, 4)   # windshield
        painter.drawRoundedRect(QRectF(28, 127, 44, 7), 4, 4)  # rear window

        # --- Steering wheel ---
        painter.setPen(QPen(Colors.TEXT_SECONDARY, 1.3))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.drawEllipse(QPointF(19, 46), 5, 5)
        painter.drawLine(QPointF(19, 42), QPointF(19, 50))
        painter.drawLine(QPointF(15, 46), QPointF(23, 46))

        # --- Seats ---
        for seat in self.seats:
            r = seat["rect"]
            if seat["occupied"]:
                painter.setPen(Qt.PenStyle.NoPen)
                painter.setBrush(Colors.EV)
            else:
                painter.setPen(QPen(Colors.EV, 1.5))
                painter.setBrush(Colors.CARD_HOVER)
            painter.drawRoundedRect(r, 4, 4)