"""
Shared visual tokens for the dashboard UI.

The palette is intentionally compact so widget styling stays consistent and
future restyles only need to change this file.
"""

from PyQt6.QtGui import QColor


class Colors:
    # Core surfaces
    BACKGROUND = QColor("#070911")
    DASHBOARD = QColor("#0c111b")
    CARD = QColor("#141926")
    CARD_HOVER = QColor("#1c2435")
    BORDER = QColor("#2b3447")
    BORDER_ACTIVE = QColor("#3b4a63")

    # Typography
    TEXT = QColor("#f5f7fb")
    TEXT_SECONDARY = QColor("#9aa4b2")
    TEXT_DISABLED = QColor("#6d7587")

    # New dashboard accents
    RANGE = QColor("#4da3ff")
    COST = QColor("#f6c744")
    TIME = QColor("#ff4d57")
    CO2 = QColor("#35df78")
    AI = QColor("#8a90a4")
    RANGE_LEFT = QColor("#a78bfa")  # soft violet, distinct from the shared blue/gold/red/green palette

    # Action and state accents
    ACCENT = RANGE
    ACCENT_DARK = QColor("#2c7fe0")
    ACCENT_GLOW = QColor("#8fd1ff")
    SUCCESS = CO2
    WARNING = COST
    DANGER = TIME

    # Misc
    SHADOW = QColor(0, 0, 0, 180)
    GRAPHITE = QColor("#1b2230")
    TICK_MARK = QColor("#353b4b")
    NEEDLE = QColor("#ff6b6b")
    NEEDLE_RING = QColor("#ff7e5f")
    SPEED_ZONE_ECO = CO2
    SPEED_ZONE_MID = COST
    SPEED_ZONE_HIGH = TIME

    # Backward-compatible aliases for existing widgets
    EV = RANGE
    EV_DARK = ACCENT_DARK
    EV_GLOW = ACCENT_GLOW
    EV_BADGE_BG = QColor("#0f3d38")
    GAS = QColor("#ff8c42")
    GAS_BADGE_BG = QColor("#3d1f0f")
    GAS_LIGHT = QColor("#ffb477")
    GREEN = CO2
    YELLOW = COST
    RED = TIME
    AMBIENT_GLOW = QColor(77, 163, 255, 40)


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
    MIN_SPEED = 1
    MAX_SPEED = 120
    NEEDLE_WIDTH = 3
    ARC_WIDTH = 12
    HUB_RADIUS = 8
    SPEED_TEXT_SIZE = 18
    SPEED_TEXT_Y_OFFSET = 40


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