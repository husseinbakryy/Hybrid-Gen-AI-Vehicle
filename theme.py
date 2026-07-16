"""
Defines the visual design system for the application.
Widgets should import their colors, fonts, dimensions, and animation
timings from here rather than hardcoding hex values or pixel sizes -
that's what makes a full restyle later a one-file change instead of a
hunt through every widget.
"""

from PyQt6.QtGui import QColor


class Colors:
    # Main backgrounds
    BACKGROUND = QColor("#000000")       # pure black surround (fullscreen, step 2)
    DASHBOARD = QColor("#0a0a0d")        # matches our existing app background
    CARD = QColor("#131318")             # matches our existing card background
    CARD_HOVER = QColor("#1c1c22")       # matches our existing input/track background

    # Borders
    BORDER = QColor("#2a2a30")           # matches our existing card border
    BORDER_ACTIVE = QColor("#3D4250")

    # Text
    TEXT = QColor("#e8e8ec")             # primary
    TEXT_SECONDARY = QColor("#8a8a93")   # secondary
    TEXT_DISABLED = QColor("#6a6a73")    # muted

    # EV / Electric - single accent color, reused everywhere EV appears
    EV = QColor("#00d9c0")
    EV_DARK = QColor("#00B39E")
    EV_GLOW = QColor("#5BFFE8")

    # Gas - distinct warm color, never reused for anything else
    GAS = QColor("#c0572e")
    GAS_LIGHT = QColor("#FFB088")

    # Status colors - kept separate from EV/GAS so the mode bar's fills
    # never collide visually with alerts
    GREEN = QColor("#39D98A")    # CO2 savings, positive deltas only
    YELLOW = QColor("#FFC857")   # warnings
    RED = QColor("#e2504a")      # critical battery/fuel, errors - matches our existing accent

    # Misc
    SHADOW = QColor(0, 0, 0, 180)
    AMBIENT_GLOW = QColor(0, 217, 192, 30)  # matches EV accent

    # Status badge backgrounds (the "Ready/Electric/Gas" pill) - dark
    # tinted versions of EV/GAS so the badge text pops against them
    EV_BADGE_BG = QColor("#0f3d38")
    GAS_BADGE_BG = QColor("#3d1f0f")

    # Dark graphite fill - reused for the car body and the speedometer hub
    GRAPHITE = QColor("#242430")

    # Speedometer-specific
    TICK_MARK = QColor("#3a3a42")
    NEEDLE = QColor("#ff433d")
    NEEDLE_RING = QColor("#ff5c3d")
    SPEED_ZONE_ECO = QColor("#0ed440")
    SPEED_ZONE_MID = QColor("#f3931d")
    SPEED_ZONE_HIGH = QColor("#cf0606")


class Fonts:
    FAMILY = "Segoe UI, Inter, SF Pro Display, Arial"

    HEADER = 26
    SECTION = 11
    BODY = 12
    VALUE = 20
    LARGE_VALUE = 30
    SMALL = 10


class Dashboard:
    WIDTH = 1500
    HEIGHT = 960
    MIN_WIDTH = 1100
    MIN_HEIGHT = 780

    BORDER_RADIUS = 20
    BORDER_WIDTH = 1
    PADDING = 24
    SPACING = 16

    GLOW_BLUR = 80
    GLOW_OPACITY = 60


class Cards:
    RADIUS = 12
    PADDING = 12
    CONTENT_SPACING = 8
    SHADOW_BLUR = 28
    ACCENT_WIDTH = 4


class Buttons:
    HEIGHT = 40
    RADIUS = 6


class SpeedometerTheme:
    MIN_SPEED = 0
    MAX_SPEED = 120
    NEEDLE_WIDTH = 3
    ARC_WIDTH = 12
    HUB_RADIUS = 8
    SPEED_TEXT_SIZE = 18
    SPEED_TEXT_Y_OFFSET = 50


class Animation:
    FAST = 150
    NORMAL = 250
    SLOW = 500
    STARTUP = 1800
    NEEDLE_SWEEP = 1600
    COUNTER = 700


class Shadow:
    BLUR = 32
    X_OFFSET = 0
    Y_OFFSET = 8


class Clock:
    FORMAT = "hh:mm"