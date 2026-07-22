"""
Modal popup for adding a new hybrid vehicle to the backend's vehicle
database via POST /api/vehicles. Only used from TripSetupForm's
"+ Add Vehicle" button.

powertrain_type is always "hybrid" here and is NOT a user-editable field -
this dashboard's vehicle dropdown is already filtered to
powertrain_type=hybrid only (fetch_vehicle_catalog's default), so a
vehicle saved here with any other powertrain_type would never appear in
this app's own dropdown anyway.
"""

import requests
from PyQt6.QtCore import QThread, pyqtSignal, Qt
from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit, QComboBox,
    QDoubleSpinBox, QPushButton, QWidget
)

from theme import Colors, Dashboard, Buttons
from widgets.card import Card


class _AddVehicleWorker(QThread):
    """Background worker so the POST doesn't block the UI thread - same
    pattern as RecommendationWorker/HealthWorker in main_window.py."""
    finished = pyqtSignal(bool, object)

    def __init__(self, payload):
        super().__init__()
        self.payload = payload

    def run(self):
        try:
            r = requests.post(
                "http://localhost:8000/api/vehicles",
                json=self.payload,
                timeout=10,
            )
        except requests.exceptions.RequestException:
            # No response was ever received (connection refused, timeout,
            # DNS failure, etc.) - there's no server error message to show.
            self.finished.emit(False, "Could not reach backend.")
            return

        try:
            r.raise_for_status()
        except requests.exceptions.HTTPError:
            # A response WAS received but with a 4xx/5xx status - surface
            # the backend's actual error detail (FastAPI's HTTPException
            # bodies look like {"detail": "..."}) rather than a generic message.
            message = f"Server error ({r.status_code})"
            try:
                body = r.json()
                if isinstance(body, dict) and body.get("detail"):
                    message = body["detail"]
            except Exception:
                pass
            self.finished.emit(False, message)
            return

        self.finished.emit(True, r.json())


class AddVehicleDialog(QDialog):
    """Popup form for submitting a new hybrid vehicle to the real backend.

    Emits vehicleAdded(display_name) on success - TripSetupForm connects
    this to refresh_vehicle_catalog() to repopulate and re-select the
    vehicle dropdown.
    """

    vehicleAdded = pyqtSignal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Add Vehicle")
        self.setMinimumSize(700, 640)
        # QDialog isn't covered by the app's global QSS (that only styles
        # QMainWindow), so without this the popup would show up with a
        # default light background against an otherwise all-dark app.
        self.setStyleSheet(f"background-color: {Colors.DASHBOARD.name()};")
        self._worker: _AddVehicleWorker | None = None
        self._make_submitted = ""
        self._model_submitted = ""

        layout = QVBoxLayout(self)
        layout.setContentsMargins(
            Dashboard.PADDING, Dashboard.PADDING, Dashboard.PADDING, Dashboard.PADDING
        )
        layout.setSpacing(Dashboard.SPACING)

        # In-dialog header
        header_layout = QHBoxLayout()
        header_title = QLabel("Add Vehicle")
        header_title.setObjectName("Title")
        header_layout.addWidget(header_title)
        header_layout.addStretch()
        layout.addLayout(header_layout)

        # Section 1: Vehicle Identity
        identity_card = Card("Vehicle Identity", Colors.RANGE_LEFT)

        self.make_edit = QLineEdit()
        self.model_edit = QLineEdit()
        self.make_edit.returnPressed.connect(self._on_save_clicked)
        self.model_edit.returnPressed.connect(self._on_save_clicked)

        row1 = self._make_row(
            self._make_field("Make", self.make_edit),
            self._make_field("Model", self.model_edit),
        )
        identity_card.add_layout(row1)

        self.body_type_combo = QComboBox()
        self.body_type_combo.addItems(["sedan", "suv", "hatchback"])

        # Informational only - not a real input field. See module docstring
        # for why powertrain_type is fixed to "hybrid" for this dialog.
        powertrain_val = QLabel("Hybrid (fixed)")
        powertrain_val.setStyleSheet(
            f"background-color: {Colors.CARD_HOVER.name()}; "
            f"color: {Colors.TEXT_DISABLED.name()}; "
            f"border: 1px solid {Colors.BORDER.name()}; "
            f"border-radius: 6px; padding: 4px 8px; font-size: 12px;"
        )
        powertrain_val.setFixedHeight(30)

        row2 = self._make_row(
            self._make_field("Body type", self.body_type_combo),
            self._make_field("Powertrain", powertrain_val),
        )
        identity_card.add_layout(row2)
        layout.addWidget(identity_card)

        # Section 2: Battery
        battery_card = Card("Battery", Colors.EV)

        self.battery_capacity_spin = QDoubleSpinBox()
        self.battery_capacity_spin.setRange(0.0, 100.0)
        self.battery_capacity_spin.setDecimals(1)
        self.battery_capacity_spin.setSingleStep(0.5)

        self.usable_battery_spin = QDoubleSpinBox()
        self.usable_battery_spin.setRange(0.0, 100.0)
        self.usable_battery_spin.setDecimals(1)
        self.usable_battery_spin.setSingleStep(0.5)

        battery_row = self._make_row(
            self._make_field("Battery capacity (kWh)", self.battery_capacity_spin),
            self._make_field("Usable battery (kWh)", self.usable_battery_spin),
        )
        battery_card.add_layout(battery_row)
        layout.addWidget(battery_card)

        # Section 3: Fuel & Mass
        fuel_card = Card("Fuel & Mass", Colors.GAS)

        self.fuel_tank_spin = QDoubleSpinBox()
        self.fuel_tank_spin.setRange(0.0, 100.0)
        self.fuel_tank_spin.setDecimals(1)
        self.fuel_tank_spin.setSingleStep(0.5)

        self.mass_spin = QDoubleSpinBox()
        self.mass_spin.setRange(500.0, 4000.0)
        self.mass_spin.setDecimals(1)
        self.mass_spin.setSingleStep(50.0)
        self.mass_spin.setValue(1500.0)

        fuel_row = self._make_row(
            self._make_field("Fuel tank (L)", self.fuel_tank_spin),
            self._make_field("Mass (kg)", self.mass_spin),
        )
        fuel_card.add_layout(fuel_row)
        layout.addWidget(fuel_card)

        # Section 4: Aerodynamics
        aero_card = Card("Aerodynamics", Colors.CO2)

        self.drag_coeff_spin = QDoubleSpinBox()
        self.drag_coeff_spin.setRange(0.15, 0.50)
        self.drag_coeff_spin.setDecimals(3)
        self.drag_coeff_spin.setSingleStep(0.01)
        self.drag_coeff_spin.setValue(0.28)

        self.frontal_area_spin = QDoubleSpinBox()
        self.frontal_area_spin.setRange(1.5, 4.0)
        self.frontal_area_spin.setDecimals(2)
        self.frontal_area_spin.setSingleStep(0.1)
        self.frontal_area_spin.setValue(2.3)

        aero_row = self._make_row(
            self._make_field("Drag coefficient", self.drag_coeff_spin),
            self._make_field("Frontal area (m2)", self.frontal_area_spin),
        )
        aero_card.add_layout(aero_row)
        layout.addWidget(aero_card)

        # Inline error message for validation/API failures - no native
        # QMessageBox popups, matching this app's established convention of
        # inline status messages (e.g. TripSetupForm.vehicle_label).
        self.error_label = QLabel("")
        self.error_label.setWordWrap(True)
        self.error_label.setStyleSheet(f"color: {Colors.TIME.name()}; font-size: 12px;")
        self.error_label.hide()
        layout.addWidget(self.error_label)

        btn_row = QHBoxLayout()
        self.save_btn = QPushButton("Save")
        self.save_btn.setObjectName("startBtn")
        self.save_btn.setMinimumHeight(Buttons.HEIGHT)
        self.save_btn.setDefault(True)
        self.save_btn.setAutoDefault(True)
        self.save_btn.setCursor(Qt.CursorShape.PointingHandCursor)

        self.cancel_btn = QPushButton("Cancel")
        self.cancel_btn.setObjectName("Secondary")
        self.cancel_btn.setMinimumHeight(Buttons.HEIGHT)
        self.cancel_btn.setCursor(Qt.CursorShape.PointingHandCursor)

        btn_row.addWidget(self.save_btn)
        btn_row.addWidget(self.cancel_btn)
        layout.addLayout(btn_row)

        self.save_btn.clicked.connect(self._on_save_clicked)
        self.cancel_btn.clicked.connect(self.reject)

    def _make_field(self, label_text: str, widget: QWidget) -> QWidget:
        container = QWidget()
        vbox = QVBoxLayout(container)
        vbox.setContentsMargins(0, 0, 0, 0)
        vbox.setSpacing(4)
        lbl = QLabel(label_text)
        lbl.setStyleSheet(f"color: {Colors.TEXT_DISABLED.name()}; font-size: 12px;")
        vbox.addWidget(lbl)
        vbox.addWidget(widget)
        return container

    def _make_row(self, field1: QWidget, field2: QWidget) -> QHBoxLayout:
        row = QHBoxLayout()
        row.setSpacing(Dashboard.SPACING)
        row.addWidget(field1, 1)
        row.addWidget(field2, 1)
        return row

    def _label(self, text: str) -> QLabel:
        # Duplicated from TripSetupForm._label() rather than importing a
        # private method across files - same styling convention though.
        lbl = QLabel(text)
        lbl.setStyleSheet(f"color: {Colors.TEXT_DISABLED.name()}; font-size: 12px;")
        return lbl

    def _show_error(self, message: str):
        self.error_label.setText(message)
        self.error_label.show()

    def _on_save_clicked(self, checked: bool = False):
        make = self.make_edit.text().strip()
        model = self.model_edit.text().strip()
        usable = self.usable_battery_spin.value()
        capacity = self.battery_capacity_spin.value()

        # Client-side validation happens BEFORE any network call.
        if not make or not model:
            self._show_error("Make and model are required.")
            return
        if usable > capacity:
            self._show_error("Usable battery cannot exceed battery capacity.")
            return

        self.error_label.hide()
        self.save_btn.setEnabled(False)
        self.cancel_btn.setEnabled(False)

        # Exactly the 10 confirmed request fields - no more, no less.
        payload = {
            "make": make,
            "model": model,
            "powertrain_type": "hybrid",
            "body_type": self.body_type_combo.currentText(),
            "battery_capacity_kwh": capacity,
            "usable_battery_kwh": usable,
            "fuel_tank_l": self.fuel_tank_spin.value(),
            "mass_kg": self.mass_spin.value(),
            "drag_coeff": self.drag_coeff_spin.value(),
            "frontal_area_m2": self.frontal_area_spin.value(),
        }

        self._make_submitted = make
        self._model_submitted = model

        self._worker = _AddVehicleWorker(payload)
        self._worker.finished.connect(self._on_save_result)
        self._worker.start()

    def _on_save_result(self, success: bool, data: object):
        self.save_btn.setEnabled(True)
        self.cancel_btn.setEnabled(True)

        if not success:
            # Do NOT close the dialog - let the user fix input and retry.
            self._show_error(str(data))
            return

        vehicle = data.get("vehicle", {}) if isinstance(data, dict) else {}
        display_name = vehicle.get("vehicle_name") or f"{self._make_submitted} {self._model_submitted}"
        self.vehicleAdded.emit(display_name)
        self.accept()


