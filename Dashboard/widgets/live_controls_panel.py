"""
Live Controls Panel - pedal-shaped GAS and BRAKE buttons matching modern dark mode
aesthetic, with asymmetric rounded corners, vertical linear gradients, soft manual
drop shadows, diagonal tread ridges, and upper text labels.
"""

from PyQt6.QtWidgets import QPushButton, QHBoxLayout, QSizePolicy
from PyQt6.QtCore import pyqtSignal, Qt, QRectF, QPointF
from PyQt6.QtGui import QColor, QPainter, QPainterPath, QLinearGradient, QPen

from widgets.card import Card
from theme import Colors


class _PedalButton(QPushButton):
    """Custom-painted press-and-hold pedal button for GAS / BRAKE controls.

    Overrides mousePressEvent / mouseReleaseEvent to grab/release mouse focus,
    allowing QPushButton's native pressed/released signals to track press state
    reliably even if the cursor leaves button bounds during a hold.
    """

    def __init__(
        self,
        label: str,
        top_color: QColor,
        base_color: QColor,
        bottom_color: QColor,
        parent=None,
    ):
        super().__init__(parent)
        self.label_text = label
        self.top_color = top_color
        self.base_color = base_color
        self.bottom_color = bottom_color

        self.setMinimumHeight(140)
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)

    def mousePressEvent(self, ev):
        try:
            self.grabMouse()
        except Exception:
            pass
        super().mousePressEvent(ev)

    def mouseReleaseEvent(self, ev):
        try:
            self.releaseMouse()
        except Exception:
            pass
        super().mouseReleaseEvent(ev)

    def _build_pedal_path(self, rect: QRectF, r_top: float, r_bot: float) -> QPainterPath:
        path = QPainterPath()
        x = rect.x()
        y = rect.y()
        w = rect.width()
        h = rect.height()

        r_top = max(1.0, min(r_top, w / 2.0, h / 2.0))
        r_bot = max(1.0, min(r_bot, w / 2.0, h / 2.0))

        # Top-left corner to top-right
        path.moveTo(x + r_top, y)
        path.lineTo(x + w - r_top, y)
        path.arcTo(x + w - 2 * r_top, y, 2 * r_top, 2 * r_top, 90, -90)

        # Right edge to bottom-right
        path.lineTo(x + w, y + h - r_bot)
        path.arcTo(x + w - 2 * r_bot, y + h - 2 * r_bot, 2 * r_bot, 2 * r_bot, 0, -90)

        # Bottom edge to bottom-left
        path.lineTo(x + r_bot, y + h)
        path.arcTo(x, y + h - 2 * r_bot, 2 * r_bot, 2 * r_bot, 270, -90)

        # Left edge to top-left
        path.lineTo(x, y + r_top)
        path.arcTo(x, y, 2 * r_top, 2 * r_top, 180, -90)

        path.closeSubpath()
        return path

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        rect = QRectF(self.rect())
        pad_inset = 6.0
        pad_rect = rect.adjusted(pad_inset, pad_inset, -pad_inset, -pad_inset)

        if self.isDown():
            pad_rect.translate(0, 2.0)

        short_dim = min(pad_rect.width(), pad_rect.height())
        r_top = short_dim * 0.13
        r_bot = short_dim * 0.26

        # 1. Soft Drop Shadow painted BEFORE pad (no QGraphicsDropShadowEffect)
        shadow_offsets = [3.0, 6.0, 9.0]
        shadow_opacities = [0.20, 0.12, 0.06]
        for offset, op in zip(shadow_offsets, shadow_opacities):
            shadow_rect = pad_rect.translated(0, offset)
            shadow_path = self._build_pedal_path(shadow_rect, r_top, r_bot)
            painter.fillPath(shadow_path, QColor(0, 0, 0, int(255 * op)))

        # 2. Main Pedal Pad with Vertical Gradient
        pad_path = self._build_pedal_path(pad_rect, r_top, r_bot)
        grad = QLinearGradient(
            pad_rect.center().x(),
            pad_rect.top(),
            pad_rect.center().x(),
            pad_rect.bottom(),
        )
        grad.setColorAt(0.0, self.top_color)
        grad.setColorAt(0.45, self.base_color)
        grad.setColorAt(1.0, self.bottom_color)
        painter.fillPath(pad_path, grad)

        # Subtle highlight border around pad
        border_pen = QPen(QColor(255, 255, 255, 35), 1.2)
        painter.setPen(border_pen)
        painter.drawPath(pad_path)

        # 3. 5 Diagonal Ridge Lines across LOWER ~58% of pad
        y_start = pad_rect.top() + 0.42 * pad_rect.height()
        y_end = pad_rect.top() + 0.92 * pad_rect.height()
        total_h = y_end - y_start

        margin_x = pad_rect.width() * 0.22
        x_left = pad_rect.left() + margin_x
        x_right = pad_rect.right() - margin_x

        ridge_pen = QPen(
            QColor(0, 0, 0, int(255 * 0.28)),
            3.0,
            Qt.PenStyle.SolidLine,
            Qt.PenCapStyle.RoundCap,
        )
        painter.setPen(ridge_pen)

        num_ridges = 5
        for i in range(num_ridges):
            fraction = (i + 0.5) / num_ridges
            base_y = y_start + fraction * total_h
            p1 = QPointF(x_left, base_y + 8.0)
            p2 = QPointF(x_right, base_y - 8.0)
            painter.drawLine(p1, p2)

        # 4. Label Text bold, centered, upper portion (~25-30% down)
        font = painter.font()
        font.setBold(True)
        font.setPixelSize(18)
        painter.setFont(font)

        text_y_center = pad_rect.top() + pad_rect.height() * 0.27
        text_rect = QRectF(pad_rect.left(), text_y_center - 20, pad_rect.width(), 40)

        # Text shadow for legibility
        shadow_text_rect = text_rect.translated(1.5, 2.0)
        painter.setPen(QColor(0, 0, 0, 120))
        painter.drawText(shadow_text_rect, int(Qt.AlignmentFlag.AlignCenter), self.label_text)

        # White text
        painter.setPen(QColor(255, 255, 255))
        painter.drawText(text_rect, int(Qt.AlignmentFlag.AlignCenter), self.label_text)


class LiveControlsPanel(Card):
    """Card panel containing pedal controls for real-time acceleration and braking."""

    accelerateStarted = pyqtSignal()
    accelerateStopped = pyqtSignal()
    brakeStarted = pyqtSignal()
    brakeStopped = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__("Live Controls", Colors.EV)

        # GAS pedal color gradient derived from Colors.CO2 (#35df78)
        gas_base = Colors.CO2
        gas_top = gas_base.lighter(145)
        gas_bottom = gas_base.darker(140)

        # BRAKE pedal color gradient derived from Colors.TIME (#ff4d57)
        brake_base = Colors.TIME
        brake_top = brake_base.lighter(145)
        brake_bottom = brake_base.darker(140)

        self.gas_btn = _PedalButton("GAS", gas_top, gas_base, gas_bottom)
        self.brake_btn = _PedalButton("BRAKE", brake_top, brake_base, brake_bottom)

        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(14)
        row.addWidget(self.gas_btn)
        row.addWidget(self.brake_btn)

        self.add_layout(row)

        # Wire pedal signals to panel signals
        self.gas_btn.pressed.connect(self.accelerateStarted.emit)
        self.gas_btn.released.connect(self.accelerateStopped.emit)
        self.brake_btn.pressed.connect(self.brakeStarted.emit)
        self.brake_btn.released.connect(self.brakeStopped.emit)
