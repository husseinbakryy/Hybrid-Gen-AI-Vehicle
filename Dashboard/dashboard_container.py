"""
Fullscreen black background that centers a fixed-aspect-ratio floating
"Dashboard" panel (the rounded card everything else sits inside).

NOTE: deliberately has ZERO QGraphicsEffect usage (no drop shadow, no
opacity/fade animation) - those caused a repaint bug where hovering over
any widget made content disappear. Once this plain version is confirmed
stable, we can re-add a glow/shadow more carefully (e.g. painted directly
via paintEvent instead of QGraphicsDropShadowEffect, which seems to be
the specific thing misbehaving here).
"""

from PyQt6.QtWidgets import QWidget, QFrame, QVBoxLayout
from PyQt6.QtCore import Qt, QTimer

from theme import Dashboard, Colors
from main_window import DashboardView


class DashboardContainer(QWidget):
    ASPECT_RATIO = Dashboard.WIDTH / Dashboard.HEIGHT

    def __init__(self):
        super().__init__()
        self.setStyleSheet(f"background-color: {Colors.BACKGROUND.name()};")

        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setAlignment(Qt.AlignmentFlag.AlignCenter)

        # QFrame (not QWidget) so the QFrame#Dashboard stylesheet rule
        # from styles.py applies (background, border, radius) - plain QSS
        # only, no QGraphicsEffect.
        self.panel = QFrame()
        self.panel.setObjectName("Dashboard")

        panel_layout = QVBoxLayout(self.panel)
        panel_layout.setContentsMargins(
            Dashboard.PADDING, Dashboard.PADDING,
            Dashboard.PADDING, Dashboard.PADDING,
        )

        self.dashboard_view = DashboardView()
        panel_layout.addWidget(self.dashboard_view)

        outer.addWidget(self.panel)

        # After the window is shown, Qt may report transient/stale sizes while
        # DPI scaling settles (especially when PassThrough rounding policy is
        # in use). Schedule a delayed recompute of the panel size so the
        # fixed size is corrected once the final geometry is available.
        # This avoids intermittently locking in a wrong size on first show.
        QTimer.singleShot(100, self._recompute_panel_size)

    def showEvent(self, ev):
        super().showEvent(ev)
        # Also schedule an immediate zero-delay recompute after show to
        # handle environments where the geometry is ready right after
        # showEvent. The 100ms singleShot above is a safety net.
        QTimer.singleShot(0, self._recompute_panel_size)

    def resizeEvent(self, a0):
        super().resizeEvent(a0)
        # Use the shared recompute routine so both resize and delayed
        # recomputes use identical logic.
        self._recompute_panel_size()

    def _recompute_panel_size(self):
        """Compute and apply the panel's fixed size based on the current
        container geometry. Extracted from resizeEvent so it can be
        invoked again after show to avoid transient/stale sizes.
        """
        available_w = self.width() * 0.94
        available_h = self.height() * 0.94

        w = min(available_w, Dashboard.WIDTH)
        h = w / self.ASPECT_RATIO
        if h > available_h:
            h = available_h
            w = h * self.ASPECT_RATIO

        w = max(w, Dashboard.MIN_WIDTH)
        h = max(h, Dashboard.MIN_HEIGHT)

        self.panel.setFixedSize(int(w), int(h))
