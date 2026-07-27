"""
Dashboard header: app title on the left, live-controls cluster in the middle (hidden by default),
and a live clock on the right.
Uses the #Title and #Value stylesheet rules already defined in styles.py.
"""

from PyQt6.QtCore import QTimer, Qt, QTime, pyqtSignal, QRectF, QPointF
from PyQt6.QtGui import QPainter, QPainterPath, QColor, QPen
from PyQt6.QtWidgets import QWidget, QLabel, QHBoxLayout, QPushButton, QComboBox

from theme import Clock, Colors


class _MuteIconButton(QPushButton):
    """
    Checkable, custom-painted icon button representing sound/mute state.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFixedSize(40, 40)
        self.setCheckable(True)
        self.setChecked(False)
        self.setCursor(Qt.CursorShape.PointingHandCursor)

    def paintEvent(self, a0):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Rounded-square background filling the button (40x40, radius ~8px)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(Colors.CARD_HOVER)
        painter.drawRoundedRect(QRectF(self.rect()), 8.0, 8.0)

        # Filled speaker body & cone shape
        path = QPainterPath()
        path.moveTo(10, 17)
        path.lineTo(14, 17)
        path.lineTo(19, 13)
        path.lineTo(19, 27)
        path.lineTo(14, 23)
        path.lineTo(10, 23)
        path.closeSubpath()

        painter.setBrush(Colors.TEXT)
        painter.drawPath(path)

        if not self.isChecked():
            # Unmuted state: two concentric sound-wave arcs
            arc_color = QColor(Colors.TEXT)
            arc_color.setAlphaF(0.75)
            arc_pen = QPen(arc_color, 2.0, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
            painter.setPen(arc_pen)
            painter.setBrush(Qt.BrushStyle.NoBrush)

            # Inner arc
            painter.drawArc(QRectF(10, 14, 12, 12), -45 * 16, 90 * 16)
            # Outer arc
            painter.drawArc(QRectF(6, 10, 20, 20), -45 * 16, 90 * 16)
        else:
            # Muted state: single diagonal line struck through icon
            line_pen = QPen(Colors.TEXT, 2.5, Qt.PenStyle.SolidLine, Qt.PenCapStyle.RoundCap)
            painter.setPen(line_pen)
            painter.drawLine(QPointF(10, 28), QPointF(28, 12))

        painter.end()


class Header(QWidget):
    muteToggled = pyqtSignal(bool)
    multiplierChanged = pyqtSignal(int)
    stopClicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 8)

        self.title = QLabel("HYBRID TRIP PLANNER")
        self.title.setObjectName("Title")

        # Live-controls cluster (Part 3)
        self.live_controls = QWidget()
        cluster_layout = QHBoxLayout(self.live_controls)
        cluster_layout.setContentsMargins(0, 0, 0, 0)
        cluster_layout.setSpacing(12)

        self.mute_btn = _MuteIconButton()

        self.multiplier_combo = QComboBox()
        self.multiplier_combo.addItems(["1x", "5x", "10x", "50x"])
        self.multiplier_combo.setCurrentIndex(0)
        self.multiplier_combo.setCursor(Qt.CursorShape.PointingHandCursor)
        self.multiplier_combo.setStyleSheet(f"""
            QComboBox {{
                background: transparent;
                border: none;
                color: {Colors.TEXT.name()};
                padding: 4px 18px 4px 6px;
                font-weight: bold;
            }}
            QComboBox::drop-down {{
                border: none;
                background: transparent;
            }}
            QComboBox QAbstractItemView {{
                background-color: {Colors.CARD_HOVER.name()};
                color: {Colors.TEXT.name()};
                selection-background-color: {Colors.BORDER.name()};
                border: 1px solid {Colors.BORDER.name()};
            }}
        """)

        self.stop_btn = QPushButton("Stop Trip")
        self.stop_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.stop_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: #ffb2b6;
                color: {Colors.TIME.name()};
                border: none;
                border-radius: 8px;
                padding: 6px 14px;
                font-weight: bold;
            }}
        """)

        cluster_layout.addWidget(self.mute_btn, alignment=Qt.AlignmentFlag.AlignVCenter)
        cluster_layout.addWidget(self.multiplier_combo, alignment=Qt.AlignmentFlag.AlignVCenter)
        cluster_layout.addWidget(self.stop_btn, alignment=Qt.AlignmentFlag.AlignVCenter)

        # Cluster starts HIDDEN by default
        self.live_controls.setVisible(False)

        # Clock
        self.clock = QLabel()
        self.clock.setObjectName("Value")
        self.clock.setAlignment(Qt.AlignmentFlag.AlignRight)

        # Layout order (Part 4): Title, Stretch, Live Controls, Fixed Spacing, Clock
        layout.addWidget(self.title, alignment=Qt.AlignmentFlag.AlignVCenter)
        layout.addStretch()
        layout.addWidget(self.live_controls, alignment=Qt.AlignmentFlag.AlignVCenter)
        layout.addSpacing(16)
        layout.addWidget(self.clock, alignment=Qt.AlignmentFlag.AlignVCenter)

        # Signals (Part 5)
        self.mute_btn.toggled.connect(self.muteToggled)
        self.multiplier_combo.currentTextChanged.connect(self._on_multiplier_changed)
        self.stop_btn.clicked.connect(self.stopClicked)

        # Live clock timer (Part 1)
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update_clock)
        self.timer.start(1000)

        self._update_clock()

    def _update_clock(self):
        self.clock.setText(QTime.currentTime().toString(Clock.FORMAT))

    def _on_multiplier_changed(self, text: str):
        clean = text.rstrip("xX")
        try:
            val = int(clean)
            self.multiplierChanged.emit(val)
        except ValueError:
            pass

    def show_live_controls(self):
        self.live_controls.show()

    def hide_live_controls(self):
        self.live_controls.hide()

        self.mute_btn.blockSignals(True)
        self.multiplier_combo.blockSignals(True)

        self.mute_btn.setChecked(False)
        self.multiplier_combo.setCurrentIndex(0)

        self.mute_btn.blockSignals(False)
        self.multiplier_combo.blockSignals(False)