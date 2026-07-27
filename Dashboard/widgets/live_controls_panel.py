"""
Live Controls panel: large press-and-hold pedals, mute toggle,
time multiplier, and stop button. Designed to be purely UI-side and
emit signals for external wiring.

Do NOT add backend/networking logic here; this file only provides
the controls and emits signals. The pedal buttons implement grabMouse
on press so that a subsequent release anywhere still generates the
corresponding "stopped" signal, preventing a stuck-held state.
"""

from PyQt6.QtWidgets import (
    QHBoxLayout, QVBoxLayout, QPushButton, QLabel, QComboBox, QSizePolicy
)
from PyQt6.QtCore import pyqtSignal, Qt
from PyQt6.QtGui import QPainter, QPainterPath, QPen

from widgets.card import Card
from theme import Colors


class _PedalButton(QPushButton):
    """A QPushButton that emits press-and-hold semantics via mouse
    events. Uses grabMouse()/releaseMouse() so a release outside the
    button still delivers the mouseReleaseEvent here, ensuring the
    corresponding "stopped" signal always fires and the held state
    cannot get stuck.

    This approach is robust cross-platform and simpler than attempting
    to track global mouse state via the application object.
    """

    def __init__(self, label: str, parent=None):
        super().__init__(label, parent)
        self._pressed = False

    def mousePressEvent(self, ev):
        # Mark pressed and grab the mouse to ensure we receive the
        # release even if the cursor leaves the widget bounds.
        self._pressed = True
        try:
            self.grabMouse()
        except Exception:
            pass
        super().mousePressEvent(ev)

    def mouseReleaseEvent(self, ev):
        # Only act if we thought we were pressed - this guarantees a
        # single "stopped" emission even if multiple release events
        # come through. Release the mouse grab to restore normal
        # event routing.
        if self._pressed:
            self._pressed = False
            try:
                self.releaseMouse()
            except Exception:
                pass
        super().mouseReleaseEvent(ev)

    def leaveEvent(self, ev):
        # Intentionally do not cancel the pressed state on leave; the
        # grabMouse() ensures release will arrive here. This prevents
        # accidental cancellation while the user intentionally drags
        # off the control and releases.
        super().leaveEvent(ev)


class _MuteIconButton(QPushButton):
    """Icon-only toggle button that paints a speaker glyph and either
    sound-wave arcs (unmuted) or a diagonal strike line (muted).

    The icon is painted directly so it looks identical across platforms.
    """

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setCheckable(True)
        self.setFixedSize(40, 40)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setFlat(True)

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Draw rounded background matching minimal button style
        bg_rect = self.rect().adjusted(2, 2, -2, -2)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(Colors.CARD_HOVER)
        painter.drawRoundedRect(bg_rect, 6, 6)

        # Icon color
        color = Colors.TEXT
        pen = QPen(color)
        pen.setWidth(2)
        painter.setPen(pen)
        painter.setBrush(color)

        # Speaker body: small rectangle + trapezoid cone
        w = self.width()
        h = self.height()
        cx = w * 0.28
        cy = h * 0.5

        # rectangle (speaker box)
        box_w = w * 0.10
        box_h = h * 0.20
        box_rect = (cx - box_w, cy - box_h / 2, box_w, box_h)
        painter.drawRect(int(box_rect[0]), int(box_rect[1]), int(box_rect[2]), int(box_rect[3]))

        # cone trapezoid
        cone = QPainterPath()
        cone.moveTo(int(cx - box_w/2 + box_w), int(cy - box_h/2))
        cone.lineTo(int(cx + box_w*1.6), int(cy - box_h))
        cone.lineTo(int(cx + box_w*1.6), int(cy + box_h))
        cone.lineTo(int(cx - box_w/2 + box_w), int(cy + box_h/2))
        cone.closeSubpath()
        painter.drawPath(cone)

        if not self.isChecked():
            # Draw two arc-shaped sound waves to the right
            arc_pen = QPen(color)
            arc_pen.setWidth(2)
            painter.setPen(arc_pen)
            # small arc
            r1 = int(w * 0.36)
            rect1 = self.rect().adjusted(int(w*0.48), int(h*0.22), int(-w*0.12), int(-h*0.22))
            painter.drawArc(rect1, -45 * 16, 90 * 16)
            # larger arc
            rect2 = self.rect().adjusted(int(w*0.42), int(h*0.14), int(-w*0.06), int(-h*0.14))
            painter.drawArc(rect2, -45 * 16, 90 * 16)
        else:
            # Muted: draw diagonal strike line
            strike_pen = QPen(color)
            strike_pen.setWidth(3)
            painter.setPen(strike_pen)
            painter.drawLine(int(w*0.22), int(h*0.22), int(w*0.78), int(h*0.78))

        painter.end()


class LiveControlsPanel(Card):
    """Panel exposing large gas/brake pedals, mute toggle, time
    multiplier, and a Stop button. All actions are emitted as signals
    so external code can wire them to real trip controls.
    """

    accelerateStarted = pyqtSignal()
    accelerateStopped = pyqtSignal()
    brakeStarted = pyqtSignal()
    brakeStopped = pyqtSignal()

    muteToggled = pyqtSignal(bool)  # True = muted
    multiplierChanged = pyqtSignal(int)
    stopClicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__("Live Controls", Colors.EV)

        # Pedals row
        pedals_row = QHBoxLayout()

        self.gas_btn = _PedalButton("GAS")
        self.gas_btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.gas_btn.setMinimumHeight(140)
        self.gas_btn.setStyleSheet(f"background-color: {Colors.CO2.name()}; font-size: 20px; font-weight:700; border-radius:10px;")
        pedals_row.addWidget(self.gas_btn)

        self.brake_btn = _PedalButton("BRAKE")
        self.brake_btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.brake_btn.setMinimumHeight(140)
        self.brake_btn.setStyleSheet(f"background-color: {Colors.TIME.name()}; font-size: 20px; font-weight:700; border-radius:10px;")
        pedals_row.addWidget(self.brake_btn)

        self.add_layout(pedals_row)

        # Consolidated controls row: mute icon, compact multiplier, Stop Trip
        controls_row = QHBoxLayout()
        controls_row.setSpacing(12)

        self.mute_btn = _MuteIconButton()
        controls_row.addWidget(self.mute_btn)

        self.multiplier_combo = QComboBox()
        self.multiplier_combo.addItems(["1x", "5x", "10x", "50x"])
        self.multiplier_combo.setCurrentIndex(0)
        # Restyle to be compact and text-only (transparent background, no border)
        self.multiplier_combo.setStyleSheet(f"QComboBox {{ background: transparent; border: none; color: {Colors.TEXT.name()}; padding: 4px 6px; }} QComboBox::drop-down {{ border: none; }}")
        self.multiplier_combo.setMinimumHeight(28)
        controls_row.addWidget(self.multiplier_combo)

        controls_row.addStretch()

        self.stop_btn = QPushButton("Stop Trip")
        self.stop_btn.setFlat(True)
        self.stop_btn.setStyleSheet(f"color: {Colors.TIME.name()}; background: transparent; border: none;")
        self.stop_btn.setMinimumHeight(28)
        controls_row.addWidget(self.stop_btn)

        self.add_layout(controls_row)

        # Wire internal events to signals. Note: these only emit; real
        # networking or trip-control logic is handled elsewhere.
        self.gas_btn.pressed.connect(self.accelerateStarted.emit)
        self.gas_btn.released.connect(self.accelerateStopped.emit)

        self.brake_btn.pressed.connect(self.brakeStarted.emit)
        self.brake_btn.released.connect(self.brakeStopped.emit)

        # Mute icon toggled
        self.mute_btn.toggled.connect(self._on_mute_toggled)

        # Parse the "x" suffix and emit integer multiplier values.
        self.multiplier_combo.currentTextChanged.connect(self._on_multiplier_changed)

        self.stop_btn.clicked.connect(self.stopClicked.emit)

    def _on_mute_toggled(self, checked: bool):
        # Emit the same signal as before; visual state handled by the
        # custom paint in _MuteIconButton.
        self.muteToggled.emit(checked)

    def _on_multiplier_changed(self, text: str):
        try:
            val = int(text.rstrip('x'))
        except Exception:
            val = 1
        self.multiplierChanged.emit(val)

    def reset(self):
        """Return the panel to its default visual state. This does not
        affect external trip state; callers should invoke additional
        reset logic if needed.
        """
        self.mute_btn.setChecked(False)
        self.multiplier_combo.setCurrentIndex(0)
"""
Live Controls panel - shown in the right sidebar while a trip is in progress,
replacing the Trip Setup form (which reappears when the trip is reset).

Design notes
------------
* Inherits Card exactly like TripSetupForm and TripProgressPanel do, so it
  blends in without any extra styling boilerplate.
* Accent color is Colors.EV (blue), consistent with TripProgressPanel which
  also uses Colors.EV as its accent.
* The panel is deliberately wider than any other button in the app because its
  whole purpose is to surface large, thumb-friendly pedal buttons.

Press-and-hold edge-case strategy
----------------------------------
For the GAS and BRAKE pedal buttons, we need to guarantee that the "stopped"
signal always fires even if the user drags the mouse off the button while
holding it down. We handle this with two complementary overrides on each
pedal's inner _PedalButton class:

  1. mouseReleaseEvent - fires on any release inside the button's bounds.
  2. leaveEvent - fires when the cursor leaves the button's rect while the
     left mouse button is still physically held (tracked via self._pressed).
     Qt delivers leaveEvent even when a mouse button is held, so the button
     will always get this event when the cursor exits, making it impossible
     to leave the button stuck in a "held" visual/signal state.

We do NOT rely on mouseMoveEvent for this because Qt stops delivering
mouseMoveEvents to a widget once the cursor leaves its bounds (unless mouse
tracking + grabMouse() are active, which adds more complexity than leaveEvent).
leaveEvent is simpler and sufficient: it fires exactly once per leave, letting
us check _pressed and emit the "stopped" signal unconditionally.
"""

from PyQt6.QtWidgets import (
    QHBoxLayout, QLabel, QComboBox, QPushButton, QVBoxLayout, QWidget,
    QSizePolicy,
)
from PyQt6.QtCore import Qt, pyqtSignal
from PyQt6.QtGui import QMouseEvent

from widgets.card import Card
from theme import Colors, Fonts


# ---------------------------------------------------------------------------
# Internal helper: a large pedal-style button with press-and-hold semantics.
# ---------------------------------------------------------------------------

class _PedalButton(QPushButton):
    """QPushButton subclass that emits pressed_started / press_stopped signals
    on physical mouse press / release (not the default click semantics).

    The leaveEvent override ensures press_stopped always fires if the user
    drags the cursor off the button while holding the mouse button down,
    preventing the button from getting stuck in a "held" state.
    """

    press_started = pyqtSignal()
    press_stopped = pyqtSignal()

    def __init__(self, label: str, bg_color, parent=None):
        super().__init__(label, parent)

        # Track whether this button is currently being held down so leaveEvent
        # can decide whether to emit press_stopped.
        self._pressed = False

        # Size policy: expand to fill whatever horizontal space is given,
        # but keep a tall minimum height so the pedals are prominent.
        self.setSizePolicy(
            QSizePolicy.Policy.Expanding,
            QSizePolicy.Policy.Preferred,
        )
        self.setMinimumHeight(80)

        # Build the stylesheet using the supplied background color. Active
        # (pressed) state darkens the button slightly for tactile feedback.
        dark_hex = self._darken(bg_color, 0.75)
        self.setStyleSheet(f"""
            QPushButton {{
                background-color: {bg_color.name()};
                color: {Colors.TEXT.name()};
                border: none;
                border-radius: 10px;
                font-size: {Fonts.VALUE}px;
                font-weight: 700;
                letter-spacing: 2px;
            }}
            QPushButton:pressed {{
                background-color: {dark_hex};
            }}
            QPushButton:disabled {{
                background-color: {Colors.CARD_HOVER.name()};
                color: {Colors.TEXT_DISABLED.name()};
            }}
        """)

    @staticmethod
    def _darken(color, factor: float) -> str:
        """Return a hex string of `color` with each RGB channel scaled by
        `factor` (0.0 = black, 1.0 = unchanged)."""
        r = int(color.red()   * factor)
        g = int(color.green() * factor)
        b = int(color.blue()  * factor)
        return f"#{r:02x}{g:02x}{b:02x}"

    # ------------------------------------------------------------------
    # Press-and-hold event overrides
    # ------------------------------------------------------------------

    def mousePressEvent(self, a0: QMouseEvent):
        """Emit press_started on left-button press and mark button as held."""
        if a0.button() == Qt.MouseButton.LeftButton:
            self._pressed = True
            self.press_started.emit()
        super().mousePressEvent(a0)

    def mouseReleaseEvent(self, a0: QMouseEvent):
        """Emit press_stopped on left-button release (cursor inside bounds)."""
        if a0.button() == Qt.MouseButton.LeftButton and self._pressed:
            self._pressed = False
            self.press_stopped.emit()
        super().mouseReleaseEvent(a0)

    def leaveEvent(self, a0):
        """Emit press_stopped when the cursor leaves the button while held.

        Qt delivers leaveEvent even with a mouse button held down (unlike
        mouseMoveEvent, which stops being delivered once the cursor exits the
        widget without mouse grabbing). This is the safest hook for detecting
        a "dragged off while held" scenario. We check self._pressed so we only
        emit when the user was actually holding the button at departure.
        """
        if self._pressed:
            self._pressed = False
            self.press_stopped.emit()
        super().leaveEvent(a0)


# ---------------------------------------------------------------------------
# Public panel
# ---------------------------------------------------------------------------

class LiveControlsPanel(Card):
    """Right-sidebar panel that replaces Trip Setup while a trip is running.

    Signals
    -------
    accelerateStarted : ()   - emitted when the user presses and holds GAS
    accelerateStopped : ()   - emitted when GAS is released or left
    brakeStarted      : ()   - emitted when the user presses and holds BRAKE
    brakeStopped      : ()   - emitted when BRAKE is released or left
    muteToggled       : (bool) - True = muted, False = unmuted
    multiplierChanged : (int)  - 1, 5, 10, or 50 (the "x" suffix is stripped)
    stopClicked       : ()   - emitted when the STOP button is clicked
    """

    accelerateStarted = pyqtSignal()
    accelerateStopped = pyqtSignal()
    brakeStarted = pyqtSignal()
    brakeStopped = pyqtSignal()
    muteToggled = pyqtSignal(bool)
    multiplierChanged = pyqtSignal(int)
    stopClicked = pyqtSignal()

    # Map of combo label -> integer value (strips the "x" suffix in one place)
    _MULTIPLIER_MAP: dict[str, int] = {"1x": 1, "5x": 5, "10x": 10, "50x": 50}

    def __init__(self, parent=None):
        super().__init__("Live Controls", Colors.EV)

        # Match the Trip Setup sidebar width exactly so the stack swap is
        # visually seamless (TripSetupForm uses setFixedWidth(260)).
        self.setFixedWidth(260)

        # -- Section label: Pedals ----------------------------------------
        pedals_label = QLabel("PEDALS")
        pedals_label.setObjectName("SectionTitle")
        self.add_widget(pedals_label)

        # Gas and Brake sit side by side in one row, each taking half the
        # available width. Both buttons are as tall as possible to be
        # thumb-friendly - this panel exists specifically to give them room.
        pedals_row = QHBoxLayout()
        pedals_row.setSpacing(8)

        self._gas_btn = _PedalButton("GAS", Colors.CO2)
        self._brake_btn = _PedalButton("BRAKE", Colors.TIME)

        pedals_row.addWidget(self._gas_btn)
        pedals_row.addWidget(self._brake_btn)
        self.add_layout(pedals_row)

        self.add_spacing(4)

        # -- Mute toggle --------------------------------------------------
        mute_label = QLabel("VOICE")
        mute_label.setObjectName("SectionTitle")
        self.add_widget(mute_label)

        self._mute_btn = QPushButton("Mute Voice")
        self._mute_btn.setCheckable(True)
        self._mute_btn.setChecked(False)   # starts unmuted
        self._mute_btn.setObjectName("Secondary")
        self._mute_btn.setMinimumHeight(38)
        self.add_widget(self._mute_btn)

        self.add_spacing(4)

        # -- Time multiplier ----------------------------------------------
        mult_label = QLabel("TIME MULTIPLIER")
        mult_label.setObjectName("SectionTitle")
        self.add_widget(mult_label)

        self._mult_combo = QComboBox()
        self._mult_combo.addItems(list(self._MULTIPLIER_MAP.keys()))
        self._mult_combo.setCurrentText("1x")   # default
        self.add_widget(self._mult_combo)

        self.add_spacing(4)

        # -- Stop button --------------------------------------------------
        # Styled with objectName "Secondary" to match the app's existing
        # Reset/Cancel button convention (see TripProgressPanel.reset_btn
        # and TripSetupForm.add_vehicle_btn).
        self._stop_btn = QPushButton("Stop Trip")
        self._stop_btn.setObjectName("Secondary")
        self._stop_btn.setMinimumHeight(38)
        self.add_widget(self._stop_btn)

        self.add_stretch()

        # -- Wire internal signals ----------------------------------------
        self._gas_btn.press_started.connect(self.accelerateStarted)
        self._gas_btn.press_stopped.connect(self.accelerateStopped)
        self._brake_btn.press_started.connect(self.brakeStarted)
        self._brake_btn.press_stopped.connect(self.brakeStopped)

        self._mute_btn.toggled.connect(self._on_mute_toggled)
        self._mult_combo.currentTextChanged.connect(self._on_multiplier_changed)
        self._stop_btn.clicked.connect(self.stopClicked)

    # ------------------------------------------------------------------
    # Internal signal handlers
    # ------------------------------------------------------------------

    def _on_mute_toggled(self, checked: bool):
        """Update button label and re-emit with the boolean mute state."""
        self._mute_btn.setText("Unmute Voice" if checked else "Mute Voice")
        self.muteToggled.emit(checked)

    def _on_multiplier_changed(self, text: str):
        """Strip the 'x' suffix and emit an int, not the raw string."""
        value = self._MULTIPLIER_MAP.get(text, 1)
        self.multiplierChanged.emit(value)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def reset(self):
        """Return the panel to its default idle visual state.

        Call this when a trip ends so the panel is clean if the user
        starts another trip. Nothing in the current codebase calls this yet -
        it will be hooked up when real trip-end logic is wired in later.
        """
        # Block signals while resetting so the mute/multiplier signals don't
        # fire spuriously during a programmatic reset (they would otherwise
        # print debug lines and - later - send unnecessary network messages).
        self._mute_btn.blockSignals(True)
        self._mult_combo.blockSignals(True)

        self._mute_btn.setChecked(False)
        self._mute_btn.setText("Mute Voice")
        self._mult_combo.setCurrentText("1x")

        self._mute_btn.blockSignals(False)
        self._mult_combo.blockSignals(False)
