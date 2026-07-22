"""
Global Qt stylesheet built from the shared theme tokens.
"""

from theme import Colors, Fonts, Dashboard, Cards


def get_dark_style() -> str:
    return f"""
QMainWindow {{ background-color: {Colors.DASHBOARD.name()}; }}
QLabel {{ color: {Colors.TEXT.name()}; }}

QPushButton {{
    background-color: transparent;
    color: {Colors.TEXT_SECONDARY.name()};
    border: 1px solid {Colors.BORDER.name()};
    border-radius: 8px;
    padding: 8px 12px;
}}
QPushButton:hover {{
    background-color: {Colors.CARD_HOVER.name()};
    color: {Colors.TEXT.name()};
}}
QPushButton#startBtn {{
    background-color: {Colors.RANGE.name()};
    color: {Colors.TEXT.name()};
    border: 1px solid {Colors.ACCENT_DARK.name()};
    font-weight: 600;
}}
QPushButton#startBtn:hover {{
    background-color: {Colors.ACCENT_DARK.name()};
}}
QPushButton#Secondary {{
    background-color: {Colors.CARD_HOVER.name()};
    color: {Colors.TEXT.name()};
    border: 1px solid {Colors.BORDER.name()};
}}
QPushButton#Secondary:hover {{
    background-color: {Colors.CARD.name()};
}}
QComboBox, QSpinBox, QDoubleSpinBox, QLineEdit {{
    background-color: {Colors.CARD_HOVER.name()};
    color: {Colors.TEXT.name()};
    border: 1px solid {Colors.BORDER.name()};
    border-radius: 6px;
    padding: 4px;
}}
QComboBox QAbstractItemView {{
    background-color: {Colors.CARD_HOVER.name()};
    color: {Colors.TEXT.name()};
    border: 1px solid {Colors.BORDER.name()};
    selection-background-color: {Colors.RANGE.name()};
    selection-color: {Colors.TEXT.name()};
    outline: none;
}}
QSlider::groove:horizontal {{
    height: 4px;
    background: {Colors.CARD_HOVER.name()};
    border-radius: 2px;
}}
QSlider::handle:horizontal {{
    background: {Colors.RANGE.name()};
    width: 14px;
    height: 14px;
    margin: -6px 0;
    border-radius: 7px;
}}
QFrame#Dashboard {{
    background-color: {Colors.DASHBOARD.name()};
    border: {Dashboard.BORDER_WIDTH}px solid {Colors.BORDER.name()};
    border-radius: {Dashboard.BORDER_RADIUS}px;
}}
QFrame#Card {{
    background-color: {Colors.CARD.name()};
    border: 1px solid {Colors.BORDER.name()};
    border-radius: {Cards.RADIUS}px;
}}
QLabel#Title {{
    font-size: {Fonts.HEADER}px;
    font-weight: 700;
    letter-spacing: 1px;
    color: {Colors.TEXT.name()};
}}
QLabel#SectionTitle {{
    font-size: {Fonts.SECTION}px;
    font-weight: 600;
    color: {Colors.TEXT_SECONDARY.name()};
    letter-spacing: 1px;
}}
QLabel#Value {{
    font-size: {Fonts.VALUE}px;
    font-weight: 600;
    color: {Colors.TEXT.name()};
}}
QLabel#LargeValue {{
    font-size: {Fonts.LARGE_VALUE}px;
    font-weight: 700;
    color: {Colors.TEXT.name()};
}}
QLabel#Muted {{
    font-size: {Fonts.SMALL + 1}px;
    color: {Colors.TEXT_DISABLED.name()};
}}
"""

DARK_STYLE = get_dark_style()
