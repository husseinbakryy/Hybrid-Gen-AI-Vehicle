"""
Dashboard header: app title on the left, a live clock on the right.
Uses the #Title and #Value stylesheet rules already defined in styles.py
(added back in the foundation step) - no new styling needed here.
"""

from PyQt6.QtCore import QTimer, Qt, QTime
from PyQt6.QtWidgets import QWidget, QLabel, QHBoxLayout

from theme import Clock


class Header(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 8)

        self.title = QLabel("HYBRID TRIP PLANNER")
        self.title.setObjectName("Title")

        self.clock = QLabel()
        self.clock.setObjectName("Value")
        self.clock.setAlignment(Qt.AlignmentFlag.AlignRight)

        layout.addWidget(self.title)
        layout.addStretch()
        layout.addWidget(self.clock)

        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update_clock)
        self.timer.start(1000)

        self._update_clock()

    def _update_clock(self):
        self.clock.setText(QTime.currentTime().toString(Clock.FORMAT))