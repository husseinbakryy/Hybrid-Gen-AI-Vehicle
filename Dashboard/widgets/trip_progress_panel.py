"""
Mode split bar, battery/fuel levels, and start/reset controls - built on
the Card base class. Public interface (attributes, methods, signals) is
UNCHANGED from before, so main_window.py needs no edits.
"""

from PyQt6.QtWidgets import QVBoxLayout, QHBoxLayout, QLabel, QProgressBar, QPushButton
from PyQt6.QtCore import pyqtSignal

from widgets.card import Card
from widgets.segmented_mode_bar import SegmentedModeBar
from theme import Colors


class TripProgressPanel(Card):
    startClicked = pyqtSignal()
    resetClicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__("Mode Split", Colors.EV)

        self.mode_badge = QLabel()
        self.add_header_widget(self.mode_badge)

        self.mode_bar = SegmentedModeBar()
        self.add_widget(self.mode_bar)

        labels_row = QHBoxLayout()
        self.mile_label = QLabel("0 mi")
        self.next_event_label = QLabel("no charging stops planned")
        self.dist_label = QLabel("65 mi")
        for lbl in (self.mile_label, self.next_event_label, self.dist_label):
            lbl.setStyleSheet(f"color: {Colors.TEXT_DISABLED.name()}; font-size: 12px;")
        labels_row.addWidget(self.mile_label)
        labels_row.addStretch()
        labels_row.addWidget(self.next_event_label)
        labels_row.addStretch()
        labels_row.addWidget(self.dist_label)
        self.add_layout(labels_row)

        bars_row = QHBoxLayout()
        bars_row.addLayout(self._make_mini_bar("Battery", Colors.EV, "battery"))
        bars_row.addLayout(self._make_mini_bar("Fuel", Colors.GAS, "fuel"))
        self.add_layout(bars_row)

        btn_row = QHBoxLayout()
        self.start_btn = QPushButton("Start trip")
        self.start_btn.setObjectName("startBtn")
        self.reset_btn = QPushButton("Reset")
        self.reset_btn.setObjectName("Secondary")
        btn_row.addWidget(self.start_btn)
        btn_row.addWidget(self.reset_btn)
        self.add_layout(btn_row)

        self.start_btn.clicked.connect(self.startClicked.emit)
        self.reset_btn.clicked.connect(self.resetClicked.emit)

        self.set_mode("Ready")

    def _style_progress_bar(self, bar: QProgressBar, color):
        bar.setStyleSheet(f"""
            QProgressBar {{
                background-color: {Colors.CARD_HOVER.name()};
                border: none; border-radius: 8px;
            }}
            QProgressBar::chunk {{
                background-color: {color.name()}; border-radius: 8px;
            }}
        """)

    def _make_mini_bar(self, label_text, color, attr_prefix):
        col = QVBoxLayout()
        row = QHBoxLayout()
        lbl = QLabel(label_text)
        lbl.setStyleSheet(f"color: {Colors.TEXT_DISABLED.name()}; font-size: 11px;")
        pct = QLabel("100%")
        pct.setStyleSheet(f"color: {Colors.TEXT_DISABLED.name()}; font-size: 11px;")
        row.addWidget(lbl)
        row.addStretch()
        row.addWidget(pct)
        col.addLayout(row)

        bar = QProgressBar()
        bar.setRange(0, 100)
        bar.setValue(100)
        bar.setTextVisible(False)
        bar.setFixedHeight(8)
        self._style_progress_bar(bar, color)
        col.addWidget(bar)

        setattr(self, f"{attr_prefix}_bar", bar)
        setattr(self, f"{attr_prefix}_pct", pct)
        return col

    def set_mode(self, mode: str):
        if mode == "Electric":
            bg, fg = "#0f3d38", Colors.EV.name()
        elif mode == "Gas":
            bg, fg = "#3d1f0f", Colors.GAS.name()
        else:
            bg, fg = "#0f3d38", Colors.EV.name()
        self.mode_badge.setText(mode)
        self.mode_badge.setStyleSheet(
            f"background-color: {bg}; color: {fg}; font-size: 11px; "
            "padding: 3px 10px; border-radius: 6px;"
        )

    def set_plan(self, segments: list[list], stops: list[int], distance: float):
        self.mode_bar.set_plan(segments, stops, distance)

    def set_battery(self, pct: float):
        self.battery_bar.setValue(round(pct))
        self.battery_pct.setText(f"{round(pct)}%")

    def set_fuel(self, pct: float):
        self.fuel_bar.setValue(round(pct))
        self.fuel_pct.setText(f"{round(pct)}%")

    def reset_display(self):
        self.set_mode("Ready")
        self.set_plan([], [], 1)
        self.mode_bar.set_traveled(0)
        self.set_battery(100)
        self.set_fuel(100)
        self.mile_label.setText("0 mi")
        self.next_event_label.setText("no charging stops planned")