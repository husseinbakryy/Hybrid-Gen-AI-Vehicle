from PyQt6.QtWidgets import QWidget, QSizePolicy
from PyQt6.QtGui import QPainter, QPen, QColor, QPainterPath
from PyQt6.QtCore import Qt, QPointF, QRectF

from theme import Colors
from animations import animate_value


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
        self._traveled_anim = None

    def set_plan(self, segments: list[list], stops: list[int], distance: float):
        self._segments = segments
        self._stops = stops
        self._distance = max(1.0, distance)
        self.update()

    def set_traveled(self, miles: float):
        self._traveled = miles
        self.update()

    def animate_traveled(self, miles: float, duration: int):
        """Glide self._traveled to miles over duration ms, instead of
        snapping instantly - same gap-measured animation treatment already
        applied to the speedometer and battery/fuel bars."""
        if self._traveled_anim is not None:
            self._traveled_anim.stop()

        self._traveled_anim = animate_value(
            self._set_traveled_display,
            self._traveled,
            miles,
            duration=duration,
            parent=self,
        )

    def _set_traveled_display(self, value: float):
        self._traveled = value
        self.update()

    def set_recommended_mode(self, mode: str | None):
        """Set the recommended mode (e.g. 'ev', 'hybrid', 'ice') which will
        cause the widget to render a single colored badge. Pass None to
        restore the segmented rendering behaviour."""
        self._recommended_mode = mode
        self.update()

    def paintEvent(self, a0):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        w, h = float(self.width()), float(self.height())

        # Clip all drawing strictly inside the rounded pill container (smooth rounded corners)
        clip_path = QPainterPath()
        clip_path.addRoundedRect(QRectF(0, 0, w, h), h / 2.0, h / 2.0)
        painter.setClipPath(clip_path)

        # Background base fill
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(Colors.CARD_HOVER)
        painter.drawRect(QRectF(0, 0, w, h))

        # Single badge mode (if active)
        if getattr(self, '_recommended_mode', None) is not None:
            mode = self._recommended_mode
            bg = Colors.EV_BADGE_BG if mode == "ev" else Colors.GAS_BADGE_BG
            fg = Colors.EV if mode == "ev" else Colors.GAS
            text = "Electric" if mode == "ev" else "Gas"

            painter.setBrush(bg)
            rect = QRectF(0, 0, w, h)
            painter.drawRect(rect)
            painter.setPen(fg)
            painter.drawText(rect, Qt.AlignmentFlag.AlignCenter, text)
            return

        # Ensure segments cover 100% of the bar to the maximum total distance
        segs = list(self._segments) if self._segments else []
        if not segs:
            segs = [[0.0, self._distance, "Electric"]]
        else:
            # Copy segments and stretch the current active segment to 100% maximum distance
            segs = [list(s) for s in segs]
            segs[-1][1] = self._distance

        # Draw 100% filled colored mode segments
        for start, end, mode in segs:
            x1 = (float(start) / self._distance) * w
            x2 = (float(end) / self._distance) * w
            color = Colors.EV if mode in ("Electric", "ev") else Colors.GAS
            painter.setBrush(color)
            painter.drawRect(QRectF(x1, 0, max(1.0, x2 - x1), h))

        # Dimmed untraveled overlay across remaining route
        traveled_x = (min(self._traveled, self._distance) / self._distance) * w
        if traveled_x < w:
            dim = QColor(Colors.DASHBOARD)
            dim.setAlpha(160)
            painter.setBrush(dim)
            painter.drawRect(QRectF(traveled_x, 0, w - traveled_x, h))

            # Smooth glowing progress indicator line at current traveled head
            if traveled_x > 2.0:
                painter.setPen(QPen(QColor(255, 255, 255, 220), 2.0))
                painter.drawLine(QPointF(traveled_x, 0), QPointF(traveled_x, h))

        # Manual stop markers
        painter.setPen(QPen(Colors.TEXT, 1.4))
        for stop in self._stops:
            x = (stop / self._distance) * w
            painter.drawLine(QPointF(x, 1), QPointF(x, h - 1))