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
        # Reduce font-size and internal padding so a 2x3 grid fits comfortably
        # without changing the tile's accent color or overall style.
        self.value_label.setObjectName("LargeValue")
        self.value_label.setAlignment(Qt.AlignmentFlag.AlignLeft)
        self.value_label.setStyleSheet("font-size: 14px;")
        self.value_label.setContentsMargins(6, 4, 6, 4)
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
        # Tighter spacing to reduce overall panel height when using a 2x3 grid
        layout.setSpacing(6)

        # Arrange tiles in a 2x3 grid to accommodate the additional Fuel and
        # Battery tiles required by the backend integration.
        self.cost_tile = _StatTile("Cost", Colors.COST)
        self.time_tile = _StatTile("Time", Colors.TIME)
        self.co2_tile = _StatTile("CO2", Colors.CO2)
        self.range_tile = _StatTile("Range Left", Colors.RANGE)
        self.fuel_tile = _StatTile("Fuel Used", Colors.GAS)
        self.battery_tile = _StatTile("Battery Used", Colors.EV)

        layout.addWidget(self.cost_tile, 0, 0)
        layout.addWidget(self.time_tile, 0, 1)
        layout.addWidget(self.co2_tile, 0, 2)
        layout.addWidget(self.range_tile, 1, 0)
        layout.addWidget(self.fuel_tile, 1, 1)
        layout.addWidget(self.battery_tile, 1, 2)

    def set_stats(self, cost: float, time_str: str, co2: float, range_left: float):
        # Backwards-compatible: set the original four tiles
        self.cost_tile.set_value(f"${cost:.2f}")
        self.time_tile.set_value(time_str)
        self.co2_tile.set_value(f"{co2:.1f}kg")
        self.range_tile.set_value(f"{round(range_left)} km")

    def set_extended_stats(self, cost: float, time_str: str, co2: float, range_left: float, fuel_l: float, battery_kwh: float):
        """Set all six tiles (cost, time, co2, range left, fuel used, battery used)."""
        self.cost_tile.set_value(f"${cost:.2f}")
        self.time_tile.set_value(time_str)
        self.co2_tile.set_value(f"{co2:.1f}kg")
        self.range_tile.set_value(f"{round(range_left)} km")
        self.fuel_tile.set_value(f"{fuel_l:.2f} L")
        self.battery_tile.set_value(f"{battery_kwh:.1f} kWh")

    def reset_stats(self):
        for tile in (self.cost_tile, self.time_tile, self.co2_tile, self.range_tile, self.fuel_tile, self.battery_tile):
            tile.reset()