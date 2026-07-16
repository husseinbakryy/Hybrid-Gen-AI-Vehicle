"""
Global Qt stylesheet, built from theme.py's design tokens rather than
hardcoded values.

Keeps our EXISTING selector names (#card, #statTile, #startBtn, etc.) so
nothing visually changes and no other file needs editing yet. Also adds
the new Card-based selectors (#Dashboard, #Card, #Title, #SectionTitle,
#Value, #LargeValue, #Muted, #Secondary) so future widgets can use them
immediately once we migrate to the Card base class (see widgets/card.py).
"""

from theme import Colors, Fonts, Dashboard, Cards, Buttons


def get_dark_style() -> str:
    return f"""
QMainWindow {{ background-color: {Colors.DASHBOARD.name()}; }}
QLabel {{ color: {Colors.TEXT.name()}; }}

/* --- existing selectors (unchanged visually) --- */
QFrame#card {{
    background-color: {Colors.CARD.name()};
    border: 1px solid {Colors.BORDER.name()};
    border-radius: 12px;
}}
QFrame#statTile {{
    background-color: {Colors.CARD_HOVER.name()};
    border-radius: 8px;
}}
QPushButton {{
    background-color: transparent;
    color: {Colors.TEXT_SECONDARY.name()};
    border: 1px solid #333;
    border-radius: 6px;
    padding: 8px;
}}
QPushButton:hover {{ background-color: {Colors.CARD_HOVER.name()}; }}
QPushButton#startBtn {{
    background-color: {Colors.EV.name()};
    color: #04342c;
    border: none;
    font-weight: 600;
}}
QPushButton#startBtn:hover {{ background-color: {Colors.EV_GLOW.name()}; }}
QComboBox, QSpinBox {{
    background-color: {Colors.CARD_HOVER.name()};
    color: {Colors.TEXT.name()};
    border: 1px solid #333;
    border-radius: 4px;
    padding: 4px;
}}
QSlider::groove:horizontal {{
    height: 4px;
    background: {Colors.CARD_HOVER.name()};
    border-radius: 2px;
}}
QSlider::handle:horizontal {{
    background: {Colors.EV.name()};
    width: 14px;
    height: 14px;
    margin: -6px 0;
    border-radius: 7px;
}}

/* --- new Card-based selectors, ready for step 3 widget migration --- */
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
QFrame#StatTile {{
    background-color: {Colors.CARD.name()};
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
QPushButton#Secondary {{
    background-color: transparent;
    color: {Colors.TEXT_SECONDARY.name()};
    border: 1px solid {Colors.BORDER.name()};
}}
QPushButton#Secondary:hover {{
    background-color: {Colors.CARD_HOVER.name()};
    color: {Colors.TEXT.name()};
}}
"""


# Kept as a module-level constant so `from styles import DARK_STYLE` in
# main.py keeps working unchanged.
DARK_STYLE = get_dark_style()
