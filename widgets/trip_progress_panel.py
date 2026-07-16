from PyQt6.QtWidgets import QFrame, QVBoxLayout, QHBoxLayout, QLabel, QProgressBar, QPushButton
from PyQt6.QtCore import Qt, pyqtSignal

from widgets.segmented_mode_bar import SegmentedModeBar


class TripProgressPanel(QFrame):
    """Mode split bar, battery/fuel levels, and start/reset controls."""

    startClicked = pyqtSignal()
    resetClicked = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("card")
        layout = QVBoxLayout(self)

        header = QHBoxLayout()
        title = QLabel("MODE SPLIT")
        title.setStyleSheet("color: #8a8a93; font-size: 11px; letter-spacing: 1px;")
        self.mode_badge = QLabel("Ready")
        self.mode_badge.setStyleSheet(
            "background-color: #0f3d38; color: #00d9c0; font-size: 11px; "
            "padding: 3px 10px; border-radius: 6px;"
        )
        header.addWidget(title)
        header.addStretch()
        header.addWidget(self.mode_badge)
        layout.addLayout(header)

        self.mode_bar = SegmentedModeBar()
        layout.addWidget(self.mode_bar)

        labels_row = QHBoxLayout()
        self.mile_label = QLabel("0 mi")
        self.next_event_label = QLabel("no charging stops planned")
        self.dist_label = QLabel("65 mi")
        for lbl in (self.mile_label, self.next_event_label, self.dist_label):
            lbl.setStyleSheet("color: #6a6a73; font-size: 12px;")
        labels_row.addWidget(self.mile_label)
        labels_row.addStretch()
        labels_row.addWidget(self.next_event_label)
        labels_row.addStretch()
        labels_row.addWidget(self.dist_label)
        layout.addLayout(labels_row)

        bars_row = QHBoxLayout()
        bars_row.addLayout(self._make_mini_bar("Battery", "#00d9c0", "battery"))
        bars_row.addLayout(self._make_mini_bar("Fuel", "#ff8a5c", "fuel"))
        layout.addLayout(bars_row)

        btn_row = QHBoxLayout()
        self.start_btn = QPushButton("Start trip")
        self.start_btn.setObjectName("startBtn")
        self.reset_btn = QPushButton("Reset")
        btn_row.addWidget(self.start_btn)
        btn_row.addWidget(self.reset_btn)
        layout.addLayout(btn_row)

        self.start_btn.clicked.connect(self.startClicked.emit)
        self.reset_btn.clicked.connect(self.resetClicked.emit)

    def _style_bar(self, bar: QProgressBar, color: str):
        bar.setStyleSheet(f"""
            QProgressBar {{ background-color: #1c1c22; border: none; border-radius: 8px; }}
            QProgressBar::chunk {{ background-color: {color}; border-radius: 8px; }}
        """)

    def _make_mini_bar(self, label_text, color, attr_prefix):
        col = QVBoxLayout()
        row = QHBoxLayout()
        lbl = QLabel(label_text)
        lbl.setStyleSheet("color: #6a6a73; font-size: 11px;")
        pct = QLabel("100%")
        pct.setStyleSheet("color: #6a6a73; font-size: 11px;")
        row.addWidget(lbl)
        row.addStretch()
        row.addWidget(pct)
        col.addLayout(row)

        bar = QProgressBar()
        bar.setRange(0, 100)
        bar.setValue(100)
        bar.setTextVisible(False)
        bar.setFixedHeight(8)
        self._style_bar(bar, color)
        col.addWidget(bar)

        setattr(self, f"{attr_prefix}_bar", bar)
        setattr(self, f"{attr_prefix}_pct", pct)
        return col

    def set_mode(self, mode: str):
        if mode == "Electric":
            self.mode_badge.setText("Electric")
            self.mode_badge.setStyleSheet(
                "background-color: #0f3d38; color: #00d9c0; font-size: 11px; "
                "padding: 3px 10px; border-radius: 6px;"
            )
        elif mode == "Gas":
            self.mode_badge.setText("Gas")
            self.mode_badge.setStyleSheet(
                "background-color: #3d1f0f; color: #ff8a5c; font-size: 11px; "
                "padding: 3px 10px; border-radius: 6px;"
            )
        else:
            self.mode_badge.setText("Ready")
            self.mode_badge.setStyleSheet(
                "background-color: #0f3d38; color: #00d9c0; font-size: 11px; "
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
