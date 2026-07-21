"""
Reusable animations used throughout the application. Nothing here depends
on any specific widget - these are generic helpers any widget can call.
"""

from PyQt6.QtCore import QEasingCurve, QVariantAnimation
from PyQt6.QtWidgets import QLabel

from theme import Animation


def animate_counter(label: QLabel, start, end, prefix="", suffix="", decimals=0,
                     duration=Animation.COUNTER):
    """Counts a QLabel's text up/down from start to end - used for the
    stat cards (Cost, Time, CO2, Range) so the numbers animate in
    instead of just snapping to the final value."""
    animation = QVariantAnimation(label)
    animation.setStartValue(start)
    animation.setEndValue(end)
    animation.setDuration(duration)
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

