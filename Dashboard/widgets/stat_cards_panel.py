"""
Four stat tiles (Cost, Time, CO2, Range Left), each its own accent-colored
Card - Cost/Range in EV teal, Time in gas orange, CO2 in green.

StatCardsPanel itself stays a plain container with the SAME public methods
as before (set_stats / reset_stats), so main_window.py doesn't need any
changes - only the internals here changed.
"""

from PyQt6.QtWidgets import QWidget, QGridLayout, QLabel
from PyQt6.QtCore import Qt

from widgets.card import Card
from theme import Colors


class _StatTile(Card):
    def __init__(self, title: str, accent_color):
        super().__init__(title, accent_color)

        self.value_label = QLabel("--")
        self.value_label.setObjectName("LargeValue")
        self.value_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.add_widget(self.value_label)

    def set_value(self, text: str):
        self.value_label.setText(text)

    def reset(self):
        self.value_label.setText("--")


class StatCardsPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QGridLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        self.cost_tile = _StatTile("Cost", Colors.COST)
        self.time_tile = _StatTile("Time", Colors.TIME)
        self.co2_tile = _StatTile("CO2", Colors.CO2)
        self.range_tile = _StatTile("Range Left", Colors.RANGE)

        layout.addWidget(self.cost_tile, 0, 0)
        layout.addWidget(self.time_tile, 0, 1)
        layout.addWidget(self.co2_tile, 0, 2)
        layout.addWidget(self.range_tile, 0, 3)

    def set_stats(self, cost: float, time_str: str, co2: float, range_left: float):
        self.cost_tile.set_value(f"${cost:.2f}")
        self.time_tile.set_value(time_str)
        self.co2_tile.set_value(f"{co2:.1f}kg")
        self.range_tile.set_value(f"{round(range_left)} mi")

    def reset_stats(self):
        for tile in (self.cost_tile, self.time_tile, self.co2_tile, self.range_tile):
            tile.reset()