"""
Vehicle, distance, speed, temperature, traffic, driving style, seats, and
other trip inputs - built on the Card base class. Public interface (signals,
getters) is unchanged for existing controls, so main_window.py needs no edits
for the trip planning flow.
"""

from PyQt6.QtWidgets import (
    QFrame, QHBoxLayout, QLabel, QComboBox, QDoubleSpinBox, QScrollArea,
    QSpinBox, QSlider, QVBoxLayout, QPushButton, QWidget
)
from PyQt6.QtCore import Qt, pyqtSignal

from widgets.card import Card
from widgets.car_seat_selector import CarSeatSelector
from theme import Colors


class TripSetupForm(Card):
    speedChanged = pyqtSignal(int)
    distanceChanged = pyqtSignal(int)

    def __init__(self, parent=None):
        super().__init__("Trip Setup", Colors.RANGE)
        self.setFixedWidth(260)

        self.scroll_area = QScrollArea()
        self.scroll_area.setFrameShape(QFrame.Shape.NoFrame)
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        self.scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.scroll_area.setStyleSheet(f"""
            QScrollBar:vertical {{
                background: transparent;
                width: 10px;
                margin: 0px;
            }}
            QScrollBar::handle:vertical {{
                background: {Colors.BORDER_ACTIVE.name()};
                min-height: 32px;
                border-radius: 5px;
            }}
            QScrollBar::handle:vertical:hover {{
                background: {Colors.BORDER.name()};
            }}
            QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{
                height: 0;
            }}
            QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{
                background: transparent;
            }}
        """)

        self.form_widget = QWidget()
        self.form_layout = QVBoxLayout(self.form_widget)
        # Reserve right-side space for the scrollbar so controls don't sit under it.
        # Viewport margins ensure the scrollbar occupies its own column rather than
        # floating over the content (some platforms/styles overlay scrollbars).
        self.form_layout.setContentsMargins(0, 0, 0, 0)
        self.form_layout.setSpacing(8)
        # Reserve explicit space in the viewport for the scrollbar track.
        self.scroll_area.setViewportMargins(0, 0, 12, 0)
        self.scroll_area.setWidget(self.form_widget)

        super().add_widget(self.scroll_area)

        self.vehicle_label = QLabel()
        self.vehicle_label.setStyleSheet(
            f"""
            QLabel {{
                color: {Colors.TEXT_DISABLED.name()};
                font-size: 12px;
            }}
            """
        )
        self.add_widget(self.vehicle_label)

        self.vehicle_combo = QComboBox()
        # Initially disabled until the app fetches the live catalog at startup.
        self.vehicle_combo.setEnabled(False)
        self.add_widget(self.vehicle_combo)

        # Own row below the combo rather than sharing one with it - vehicle
        # display names (e.g. "Terra Trail H (SUV - 61.0 km EV)") already
        # crowd this 260px-wide sidebar on their own.
        self.add_vehicle_btn = QPushButton("+ Add Vehicle")
        self.add_vehicle_btn.setObjectName("Secondary")
        self.add_widget(self.add_vehicle_btn)

        self._update_vehicle_label()

        self.add_widget(self._label("Distance (km)"))
        self.distance_spin = QSpinBox()
        self.distance_spin.setRange(1, 5000)
        self.distance_spin.setValue(65)
        self.add_widget(self.distance_spin)

        self.speed_value_label = self._label("Avg speed: 45 km/h")
        self.add_widget(self.speed_value_label)
        self.speed_slider = QSlider(Qt.Orientation.Horizontal)
        self.speed_slider.setRange(1, 120)
        self.speed_slider.setValue(45)
        self.add_widget(self.speed_slider)

        self.temp_value_label = self._label("Temperature: 20C")
        self.add_widget(self.temp_value_label)
        self.temp_slider = QSlider(Qt.Orientation.Horizontal)
        self.temp_slider.setRange(-10, 42)
        self.temp_slider.setValue(20)
        self.add_widget(self.temp_slider)

        self.add_widget(self._label("Weather"))
        self.weather_combo = QComboBox()
        self.weather_combo.addItems([
            "clear", "cloudy", "foggy", "heavy_rain", "light_rain",
            "snow", "windy",
        ])
        self.weather_combo.setCurrentText("clear")
        self.add_widget(self.weather_combo)

        self.humidity_value_label = self._label("Humidity: 50%")
        self.add_widget(self.humidity_value_label)
        self.humidity_slider = QSlider(Qt.Orientation.Horizontal)
        self.humidity_slider.setRange(0, 100)
        self.humidity_slider.setValue(50)
        self.add_widget(self.humidity_slider)

        self.wind_value_label = self._label("Wind speed: 10 km/h")
        self.add_widget(self.wind_value_label)
        self.wind_slider = QSlider(Qt.Orientation.Horizontal)
        self.wind_slider.setRange(0, 60)
        self.wind_slider.setValue(10)
        self.add_widget(self.wind_slider)

        self.add_widget(self._label("Trip purpose"))
        self.trip_purpose_combo = QComboBox()
        self.trip_purpose_combo.addItems([
            "airport", "business", "commute", "errand", "leisure",
            "road_trip", "school_run",
        ])
        self.trip_purpose_combo.setCurrentText("commute")
        self.add_widget(self.trip_purpose_combo)

        self.add_widget(self._label("Road type"))
        self.road_type_combo = QComboBox()
        self.road_type_combo.addItems(["arterial", "highway", "suburban", "urban"])
        self.road_type_combo.setCurrentText("urban")
        self.add_widget(self.road_type_combo)

        self.add_widget(self._label("Cargo (kg)"))
        self.cargo_spin = QDoubleSpinBox()
        self.cargo_spin.setRange(0.0, 200.0)
        self.cargo_spin.setSingleStep(0.5)
        self.cargo_spin.setDecimals(1)
        self.cargo_spin.setValue(0.0)
        self.add_widget(self.cargo_spin)

        self.add_widget(self._label("Traffic"))
        self.traffic_combo = QComboBox()
        self.traffic_combo.addItems(["Low", "Medium", "High"])
        self.traffic_combo.setCurrentText("Medium")
        self.add_widget(self.traffic_combo)

        self.add_widget(self._label("Driving style"))
        self.style_combo = QComboBox()
        self.style_combo.addItems(["Eco", "Normal", "Aggressive"])
        self.style_combo.setCurrentText("Normal")
        self.add_widget(self.style_combo)

        self.add_widget(self._label("Passengers"))
        self.seat_selector = CarSeatSelector()
        self.add_widget(self.seat_selector)

        self.pax_label = QLabel("1 passenger")
        self.pax_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.pax_label.setStyleSheet(
            f"color: {Colors.TEXT_DISABLED.name()}; font-size: 11px;"
        )
        self.add_widget(self.pax_label)

        self.add_stretch()

        self.speed_slider.valueChanged.connect(self._on_speed_changed)
        self.distance_spin.valueChanged.connect(self._on_distance_changed)
        self.temp_slider.valueChanged.connect(
            lambda v: self.temp_value_label.setText(f"Temperature: {v}C")
        )
        self.humidity_slider.valueChanged.connect(
            lambda v: self.humidity_value_label.setText(f"Humidity: {v}%")
        )
        self.wind_slider.valueChanged.connect(
            lambda v: self.wind_value_label.setText(f"Wind speed: {v} km/h")
        )
        self.seat_selector.passengersChanged.connect(self._on_passengers_changed)

        self.vehicle_combo.currentIndexChanged.connect(
            self._update_vehicle_label
        )

        self.add_vehicle_btn.clicked.connect(self._on_add_vehicle_clicked)

    def add_widget(self, widget):
        self.form_layout.addWidget(widget)

    def add_layout(self, layout):
        self.form_layout.addLayout(layout)

    def add_stretch(self):
        self.form_layout.addStretch()

    def _label(self, text: str) -> QLabel:
        lbl = QLabel(text)
        lbl.setStyleSheet(f"color: {Colors.TEXT_DISABLED.name()}; font-size: 12px;")
        return lbl

    def _on_add_vehicle_clicked(self):
        # Local import, same pattern as the trip_logic imports elsewhere in
        # this file - keeps the dialog as an optional/internal dependency
        # rather than a module-level import every caller of this file pays for.
        from widgets.add_vehicle_dialog import AddVehicleDialog

        dialog = AddVehicleDialog(self)
        dialog.vehicleAdded.connect(self.refresh_vehicle_catalog)
        dialog.exec()

    def refresh_vehicle_catalog(self, select_name: str = ""):
        """Re-fetch the live vehicle catalog (same hybrid-only default as
        fetch_vehicle_catalog()) and repopulate the dropdown - called after
        AddVehicleDialog successfully adds a new vehicle, selecting it by
        name if it's present in the refreshed list.

        NOTE: this duplicates the few fetch/populate lines already in
        main_window.py's startup code rather than sharing a helper - the
        failure-mode UX genuinely differs between the two call sites.
        Startup shows a "Backend unreachable" message and disables the
        combo on failure; here, a failed refresh right after a successful
        add just leaves the dropdown as-is rather than surprising the user
        by disabling a control they were just successfully using.
        """
        import trip_logic
        fetched = trip_logic.fetch_vehicle_catalog()
        if not fetched:
            return
        trip_logic.VEHICLE_CATALOG = fetched
        self.vehicle_combo.clear()
        for name in fetched.keys():
            self.vehicle_combo.addItem(name)
        self.vehicle_combo.setEnabled(True)
        if select_name in fetched:
            self.vehicle_combo.setCurrentText(select_name)
        self._update_vehicle_label()

    def _update_vehicle_label(self):
        vehicle = self.vehicle_combo.currentText()

        import trip_logic
        entry = trip_logic.VEHICLE_CATALOG.get(vehicle)
        body_type = entry.get("body_type") if entry else None
        if body_type:
            vehicle_type = "SUV" if body_type.lower() == "suv" else body_type.capitalize()
        else:
            vehicle_type = "Vehicle"

        self.vehicle_label.setText(
            f'Vehicle (<span style="color:{Colors.TEXT.name()}; font-weight:700;">{vehicle_type}</span>)'
        )

    def _on_speed_changed(self, value: int):
        self.speed_value_label.setText(f"Avg speed: {value} km/h")
        self.speedChanged.emit(value)

    def _on_distance_changed(self, value: int):
        self.distanceChanged.emit(value)

    def _on_passengers_changed(self, count: int):
        self.pax_label.setText(f"{count} passenger" + ("" if count == 1 else "s"))

    def get_ev_range(self) -> int:
        # Use the nominal per-vehicle EV ranges defined in VEHICLE_CATALOG or
        # fallback to NOMINAL_EV_RANGE_KM defined centrally in trip_logic
        # so the UI's time/range math has consistent inputs.
        try:
            import trip_logic
            sel = self.get_selected_vehicle()
            if not sel:
                return 0

            entry = trip_logic.VEHICLE_CATALOG.get(sel)
            if isinstance(entry, dict) and entry.get("ev_range_km") is not None:
                return int(round(float(entry["ev_range_km"])))

            val = trip_logic.NOMINAL_EV_RANGE_KM.get(sel)
            if val is not None:
                return val

            print(f"[trip_setup_form] Warning: no nominal EV range for '{sel}', defaulting to 0 km")
            return 0
        except Exception:
            # Defensive: never return None to caller
            return 0

    def get_selected_vehicle(self) -> str:
        return self.vehicle_combo.currentText()

    def get_distance(self) -> int:
        return self.distance_spin.value()

    def get_speed(self) -> int:
        return self.speed_slider.value()

    def get_passengers(self) -> int:
        return self.seat_selector.passenger_count()

    def get_temperature(self) -> int:
        return self.temp_slider.value()

    def get_weather(self) -> str:
        return self.weather_combo.currentText()

    def get_humidity(self) -> float:
        return self.humidity_slider.value() / 100.0

    def get_wind_speed(self) -> int:
        return self.wind_slider.value()

    def get_trip_purpose(self) -> str:
        return self.trip_purpose_combo.currentText()

    def get_road_type(self) -> str:
        return self.road_type_combo.currentText()

    def get_cargo_kg(self) -> float:
        return self.cargo_spin.value()

    def get_traffic(self) -> str:
        return self.traffic_combo.currentText()

    def get_style(self) -> str:
        return self.style_combo.currentText()

