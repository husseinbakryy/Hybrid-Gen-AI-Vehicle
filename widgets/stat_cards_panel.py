from PyQt6.QtWidgets import QFrame, QGridLayout, QVBoxLayout, QLabel
from PyQt6.QtCore import Qt


class StatCardsPanel(QFrame):
    """Four small metric tiles: cost, time, CO2, range remaining."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("card")
        layout = QGridLayout(self)
        layout.setSpacing(10)

        self.value_labels = {}
        specs = [("COST", "cost", "$--"), ("TIME", "time", "--"),
                 ("CO2", "co2", "--"), ("RANGE LEFT", "range", "--")]
        for col, (title, key, default) in enumerate(specs):
            tile = QFrame()
            tile.setObjectName("statTile")
            tile_layout = QVBoxLayout(tile)
            title_lbl = QLabel(title)
            title_lbl.setStyleSheet("color: #6a6a73; font-size: 11px;")
            title_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            value_lbl = QLabel(default)
            value_lbl.setStyleSheet("color: #e8e8ec; font-size: 16px; font-weight: 600;")
            value_lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            tile_layout.addWidget(title_lbl)
            tile_layout.addWidget(value_lbl)
            layout.addWidget(tile, 0, col)
            self.value_labels[key] = value_lbl

    def set_stats(self, cost: float, time_str: str, co2: float, range_left: float):
        self.value_labels["cost"].setText(f"${cost:.2f}")
        self.value_labels["time"].setText(time_str)
        self.value_labels["co2"].setText(f"{co2:.1f}kg")
        self.value_labels["range"].setText(f"{round(range_left)} mi")

    def reset_stats(self):
        self.value_labels["cost"].setText("$--")
        self.value_labels["time"].setText("--")
        self.value_labels["co2"].setText("--")
        self.value_labels["range"].setText("--")
