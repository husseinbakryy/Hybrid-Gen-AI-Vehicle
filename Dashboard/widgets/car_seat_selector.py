from PyQt6.QtWidgets import (
    QWidget,
    QSizePolicy,
    QHBoxLayout,
    QPushButton,
    QVBoxLayout,
)
from PyQt6.QtCore import pyqtSignal, Qt

from theme import Colors


class CarSeatSelector(QWidget):
    passengersChanged = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)

        self._count = 1
        self._buttons = []

        self.setSizePolicy(
            QSizePolicy.Policy.Preferred,
            QSizePolicy.Policy.Maximum,
        )

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        row = QHBoxLayout()
        row.setSpacing(12)
        row.setAlignment(Qt.AlignmentFlag.AlignCenter)

        for i in range(5):
            btn = QPushButton()
            btn.setFixedSize(28, 28)
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.clicked.connect(lambda _, idx=i: self._clicked(idx))
            self._buttons.append(btn)
            row.addWidget(btn)

        layout.addLayout(row)

        self._refresh()

    def passenger_count(self):
        return self._count

    def set_passenger_count(self, count):
        count = max(1, min(5, count))
        self._count = count
        self._refresh()

    def _clicked(self, index):
        new_count = index + 1

        if new_count == self._count and self._count > 1:
            self._count -= 1
        else:
            self._count = new_count

        self._refresh()
        self.passengersChanged.emit(self._count)

    def _refresh(self):
        for i, btn in enumerate(self._buttons):
            selected = i < self._count

            if selected:
                bg = Colors.EV.name()
                border = Colors.EV.name()
            else:
                bg = Colors.CARD_HOVER.name()
                border = Colors.TEXT_SECONDARY.name()

            btn.setStyleSheet(
                f"""
                QPushButton {{
                    background-color: {bg};
                    border: 2px solid {border};
                    border-radius: 14px;
                }}

                QPushButton:hover {{
                    border: 2px solid {Colors.EV.name()};
                }}
                """
            )