"""
Reusable animations used throughout the application. Nothing here depends
on any specific widget - these are generic helpers any widget can call.
"""

from PyQt6.QtCore import (
    QEasingCurve,
    QPoint,
    QPropertyAnimation,
    QVariantAnimation,
    QParallelAnimationGroup,
)
from PyQt6.QtWidgets import (
    QWidget,
    QLabel,
    QGraphicsOpacityEffect,
    QGraphicsDropShadowEffect,
)

from theme import Animation, Shadow, Colors


def fade_in(widget: QWidget, duration=Animation.SLOW):
    effect = QGraphicsOpacityEffect(widget)
    widget.setGraphicsEffect(effect)

    animation = QPropertyAnimation(effect, b"opacity")
    animation.setDuration(duration)
    animation.setStartValue(0)
    animation.setEndValue(1)
    animation.setEasingCurve(QEasingCurve.Type.OutCubic)

    widget._fade_animation = animation
    animation.start()


def slide_down(widget: QWidget, distance=30, duration=Animation.SLOW):
    start = widget.pos() - QPoint(0, distance)
    end = widget.pos()

    animation = QPropertyAnimation(widget, b"pos")
    animation.setDuration(duration)
    animation.setStartValue(start)
    animation.setEndValue(end)
    animation.setEasingCurve(QEasingCurve.Type.OutCubic)

    widget._slide_animation = animation
    animation.start()


def fade_and_slide(widget: QWidget):
    fade_in(widget)
    slide_down(widget)


def add_shadow(widget: QWidget, blur=Shadow.BLUR):
    """Plain drop shadow - used for cards/panels sitting above the
    background (gives the 'elevation' look)."""
    shadow = QGraphicsDropShadowEffect(widget)
    shadow.setBlurRadius(blur)
    shadow.setOffset(Shadow.X_OFFSET, Shadow.Y_OFFSET)
    shadow.setColor(Colors.SHADOW)

    widget.setGraphicsEffect(shadow)


def add_glow(widget: QWidget, color=None, blur=40):
    """Zero-offset colored shadow - reads as an ambient glow rather than
    a drop shadow. Used behind the floating dashboard panel."""
    if color is None:
        color = Colors.EV_GLOW
    glow = QGraphicsDropShadowEffect(widget)
    glow.setBlurRadius(blur)
    glow.setOffset(0, 0)
    glow.setColor(color)

    widget.setGraphicsEffect(glow)


def animate_counter(label: QLabel, start, end, prefix="", suffix="", decimals=0):
    """Counts a QLabel's text up/down from start to end - used for the
    stat cards (Cost, Time, CO2, Range) so the numbers animate in
    instead of just snapping to the final value."""
    animation = QVariantAnimation(label)
    animation.setStartValue(start)
    animation.setEndValue(end)
    animation.setDuration(Animation.COUNTER)
    animation.setEasingCurve(QEasingCurve.Type.OutCubic)

    def update(value):
        if decimals == 0:
            text = f"{prefix}{int(value)}{suffix}"
        else:
            text = f"{prefix}{value:.{decimals}f}{suffix}"
        label.setText(text)

    animation.valueChanged.connect(update)

    label._counter_animation = animation
    animation.start()


def animate_value(setter, start: float, end: float, duration=Animation.NORMAL,
                   easing=QEasingCurve.Type.OutCubic, parent=None):
    """Generic float-value animation - calls setter(value) each tick.
    Used for things like the speedometer needle sweep, where we're
    driving a custom paintEvent rather than a QLabel's text."""
    animation = QVariantAnimation(parent)
    animation.setStartValue(float(start))
    animation.setEndValue(float(end))
    animation.setDuration(duration)
    animation.setEasingCurve(easing)
    animation.valueChanged.connect(lambda v: setter(float(v)))
    animation.start()
    return animation


def startup_sequence(widgets):
    """Staggered fade-in for a list of widgets shown when the dashboard
    first appears."""
    group = QParallelAnimationGroup()

    for widget in widgets:
        effect = QGraphicsOpacityEffect(widget)
        widget.setGraphicsEffect(effect)

        animation = QPropertyAnimation(effect, b"opacity")
        animation.setDuration(500)
        animation.setStartValue(0)
        animation.setEndValue(1)
        animation.setEasingCurve(QEasingCurve.Type.OutCubic)
        animation.setLoopCount(1)

        group.addAnimation(animation)

    widgets[0]._startup_group = group if widgets else None
    group.start()
    return group
