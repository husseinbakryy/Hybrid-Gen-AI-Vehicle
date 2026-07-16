from PyQt6.QtWidgets import (
    QFrame, QVBoxLayout, QHBoxLayout, QLabel, QComboBox, QSpinBox, QSlider,
    QPushButton, QListWidget
)
from PyQt6.QtCore import Qt, pyqtSignal

from widgets.car_seat_selector import CarSeatSelector


class TripSetupForm(QFrame):
    """Vehicle, distance, speed, temperature, traffic, driving style, seats,
    and charging stops."""

    speedChanged = pyqtSignal(int)
    distanceChanged = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("card")
        self.setFixedWidth(260)
        layout = QVBoxLayout(self)

        title = QLabel("TRIP SETUP")
        title.setStyleSheet("color: #8a8a93; font-size: 11px; letter-spacing: 1px;")
        layout.addWidget(title)

        layout.addWidget(self._label("Vehicle"))
        self.vehicle_combo = QComboBox()
        self.vehicle_combo.addItem("Toyota Prius (44mi EV)", 44)
        self.vehicle_combo.addItem("Toyota RAV4 Hybrid (42mi EV)", 42)
        self.vehicle_combo.addItem("Lexus NX350h (37mi EV)", 37)
        layout.addWidget(self.vehicle_combo)

        layout.addWidget(self._label("Distance (mi)"))
        self.distance_spin = QSpinBox()
        self.distance_spin.setRange(1, 400)
        self.distance_spin.setValue(65)
        layout.addWidget(self.distance_spin)

        self.speed_value_label = self._label("Avg speed: 45 mph")
        layout.addWidget(self.speed_value_label)
        self.speed_slider = QSlider(Qt.Orientation.Horizontal)
        self.speed_slider.setRange(0, 80)
        self.speed_slider.setValue(45)
        layout.addWidget(self.speed_slider)

        self.temp_value_label = self._label("Temperature: 20C")
        layout.addWidget(self.temp_value_label)
        self.temp_slider = QSlider(Qt.Orientation.Horizontal)
        self.temp_slider.setRange(-10, 42)
        self.temp_slider.setValue(20)
        layout.addWidget(self.temp_slider)

        layout.addWidget(self._label("Traffic"))
        self.traffic_combo = QComboBox()
        self.traffic_combo.addItems(["Low", "Medium", "High"])
        self.traffic_combo.setCurrentText("Medium")
        layout.addWidget(self.traffic_combo)

        layout.addWidget(self._label("Driving style"))
        self.style_combo = QComboBox()
        self.style_combo.addItems(["Eco", "Normal", "Aggressive"])
        self.style_combo.setCurrentText("Normal")
        layout.addWidget(self.style_combo)

        layout.addWidget(self._label("Passengers"))
        self.seat_selector = CarSeatSelector()
        layout.addWidget(self.seat_selector)
        self.pax_label = QLabel("1 passenger")
        self.pax_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.pax_label.setStyleSheet("color: #6a6a73; font-size: 11px;")
        layout.addWidget(self.pax_label)

        self.charging_stops: list[int] = []

        layout.addWidget(self._label("Charging stops (mi)"))
        stop_row = QHBoxLayout()
        self.stop_mile_spin = QSpinBox()
        self.stop_mile_spin.setRange(1, self.distance_spin.value() - 1)
        self.add_stop_btn = QPushButton("Add")
        stop_row.addWidget(self.stop_mile_spin)
        stop_row.addWidget(self.add_stop_btn)
        layout.addLayout(stop_row)

        self.stops_list = QListWidget()
        self.stops_list.setFixedHeight(64)
        layout.addWidget(self.stops_list)

        self.remove_stop_btn = QPushButton("Remove selected stop")
        layout.addWidget(self.remove_stop_btn)

        layout.addStretch()

        self.speed_slider.valueChanged.connect(self._on_speed_changed)
        self.distance_spin.valueChanged.connect(self._on_distance_changed)
        self.temp_slider.valueChanged.connect(
            lambda v: self.temp_value_label.setText(f"Temperature: {v}C")
        )
        self.seat_selector.passengersChanged.connect(self._on_passengers_changed)
        self.add_stop_btn.clicked.connect(self._add_stop)
        self.remove_stop_btn.clicked.connect(self._remove_selected_stop)

    def _label(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setStyleSheet("color: #6a6a73; font-size: 12px;")
        return lbl

    def _on_speed_changed(self, value: int):
        self.speed_value_label.setText(f"Avg speed: {value} mph")
        self.speedChanged.emit(value)

    def _on_distance_changed(self, value: int):
        self.stop_mile_spin.setRange(1, max(1, value - 1))
        kept = [mi for mi in self.charging_stops if mi < value]
        if kept != self.charging_stops:
            self.charging_stops = kept
            self._refresh_stops_list()
        self.distanceChanged.emit(value)

    def _on_passengers_changed(self, count: int):
        self.pax_label.setText(f"{count} passenger" + ("" if count == 1 else "s"))

    def _add_stop(self):
        value = self.stop_mile_spin.value()
        if 0 < value < self.distance_spin.value() and value not in self.charging_stops:
            self.charging_stops.append(value)
            self.charging_stops.sort()
            self._refresh_stops_list()

    def _remove_selected_stop(self):
        row = self.stops_list.currentRow()
        if row >= 0:
            del self.charging_stops[row]
            self._refresh_stops_list()

    def _refresh_stops_list(self):
        self.stops_list.clear()
        for mi in self.charging_stops:
            self.stops_list.addItem(f"{mi} mi")

    def get_ev_range(self) -> int:
        return self.vehicle_combo.currentData()

    def get_distance(self) -> int:
        return self.distance_spin.value()

    def get_speed(self) -> int:
        return self.speed_slider.value()

    def get_passengers(self) -> int:
        return self.seat_selector.passenger_count()

    def get_charging_stops(self) -> list[int]:
        return list(self.charging_stops)
