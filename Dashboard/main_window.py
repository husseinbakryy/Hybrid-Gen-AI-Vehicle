import random
from PyQt6.QtWidgets import QWidget, QGridLayout, QVBoxLayout, QFrame
from PyQt6.QtCore import QTimer, QThread, pyqtSignal, QObject
import requests

from widgets import (
    Speedometer, TripProgressPanel, TripSetupForm, StatCardsPanel, RecommendationPanel,
    Header
)
from widgets.card import Card
from theme import Colors
import trip_logic


class DashboardView(QWidget):
    """All the actual dashboard content (speedometer, panels, form). Used
    to be the QMainWindow's central widget directly - now it gets nested
    inside DashboardContainer's floating panel instead. Nothing about its
    internal behavior changed, just what it's a child of."""

    def __init__(self):
        super().__init__()

        outer = QGridLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(12)

        self.header = Header()

        # Build widgets
        self.speedometer = Speedometer()

        self.progress_panel = TripProgressPanel()
        self.stat_cards = StatCardsPanel()
        self.recommendation = RecommendationPanel()

        # Left column: merged card containing Recommendation (left) and
        # Speedometer (right), followed by the progress panel and stat cards.
        # The merged card replaces the previous separate Speed and Recommendation
        # cards so both appear together without introducing any scroll area.
        merged_card = Card("Speed & Recommendation", Colors.EV)
        merged_inner = QWidget()
        merged_layout = QGridLayout(merged_inner)
        merged_layout.setContentsMargins(0, 0, 0, 0)
        merged_layout.setSpacing(12)
        # Make both halves share available width equally
        merged_layout.setColumnStretch(0, 1)
        merged_layout.setColumnStretch(1, 1)
        # Recommendation on the left
        merged_layout.addWidget(self.recommendation, 0, 0)
        # Speedometer on the right
        merged_layout.addWidget(self.speedometer, 0, 1)
        merged_card.add_widget(merged_inner)

        left_widget = QWidget()
        left_layout = QVBoxLayout(left_widget)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(12)
        left_layout.addWidget(merged_card)
        left_layout.addWidget(self.progress_panel)
        left_layout.addWidget(self.stat_cards)
        left_layout.addStretch()

        self.trip_form = TripSetupForm()

        # At startup, attempt a one-time fetch of the live vehicle catalog from
        # the teammate backend. If successful populate the vehicle dropdown.
        try:
            fetched = trip_logic.fetch_vehicle_catalog()
            if fetched:
                trip_logic.VEHICLE_CATALOG = fetched
                # Repopulate the vehicle combo with the fetched display names
                self.trip_form.vehicle_combo.clear()
                for name in fetched.keys():
                    self.trip_form.vehicle_combo.addItem(name)
                self.trip_form.vehicle_combo.setEnabled(True)
                self.trip_form._update_vehicle_label()
            else:
                # Empty catalog -> backend unreachable at startup; clear and disable
                self.trip_form.vehicle_combo.clear()
                self.trip_form.vehicle_combo.setEnabled(False)
                self.trip_form.vehicle_label.setText(
                    "Backend unreachable — vehicle list unavailable"
                )
        except Exception:
            # Unexpected error shouldn't block startup
            self.trip_form.vehicle_combo.clear()
            self.trip_form.vehicle_combo.setEnabled(False)
            self.trip_form.vehicle_label.setText(
                "Backend unreachable — vehicle list unavailable"
            )

        # Health-check state and timer. The Start button is enabled only when
        # the last health check succeeded and a vehicle is selected.
        self._health_ok = False
        self._health_thread: QThread | None = None
        self.health_timer = QTimer(self)
        self.health_timer.setInterval(5000)  # poll every 5 seconds
        self.health_timer.timeout.connect(self._start_health_check)
        self.health_timer.start()

        # Initially disable Start until health check succeeds and vehicle chosen
        self.progress_panel.start_btn.setEnabled(False)
        self.trip_form.vehicle_combo.currentIndexChanged.connect(
            lambda: self._update_start_enabled()
        )

        outer.addWidget(self.header, 0, 0, 1, 2)
        # Left column (merged card + stacked panels) - fixed layout, no scroll area
        outer.addWidget(left_widget, 1, 0, 2, 1)
        # Trip Setup spans both rows on the right - a persistent sidebar
        # while the merged left column stacks up on the left
        outer.addWidget(self.trip_form, 1, 1, 2, 1)

        # Give the speedometer row more room than the bottom group row
        outer.setRowStretch(1, 1)
        outer.setRowStretch(2, 2)

        # Connect form updates
        self.trip_form.speedChanged.connect(self.speedometer.setSpeed)
        self.trip_form.distanceChanged.connect(
            lambda v: self.progress_panel.dist_label.setText(f"{v} km")
        )
        self.speedometer.setSpeed(self.trip_form.get_speed())

        self.progress_panel.startClicked.connect(self._start_trip)
        self.progress_panel.resetClicked.connect(self._reset_trip)

        # Trip timer kept for legacy API but not used for animation when backend is live
        self.trip_timer = QTimer(self)
        self.trip_timer.timeout.connect(self._tick_trip)
        self._trip_progress = 0.0

    def _start_health_check(self):
        # Spawn a short-lived thread to perform the health check without
        # blocking the UI. If a check is already running, skip starting another.
        if self._health_thread is not None and self._health_thread.isRunning():
            return

        class HealthWorker(QThread):
            result = pyqtSignal(bool)

            def run(self_inner):
                try:
                    r = requests.get("http://localhost:8000/health", timeout=2.5)
                    ok = r.status_code == 200
                except Exception:
                    ok = False
                self_inner.result.emit(ok)

        worker = HealthWorker()
        worker.result.connect(self._on_health_result)
        self._health_thread = worker
        worker.start()

    def _on_health_result(self, ok: bool):
        self._health_ok = ok
        if not ok:
            # Show inline status using the vehicle_label as requested
            self.trip_form.vehicle_label.setText("Backend unreachable — vehicle list unavailable")
            self.trip_form.vehicle_combo.setEnabled(False)
        else:
            # Clear any inline error message if catalog exists
            if trip_logic.VEHICLE_CATALOG:
                self.trip_form.vehicle_label.setText("")
                self.trip_form.vehicle_combo.setEnabled(True)
        self._update_start_enabled()

    def _update_start_enabled(self):
        """Enable or disable the Start button based on recent health checks
        and whether a vehicle is selected. This method must NOT modify layout
        or reparent widgets — it only toggles interactivity."""
        has_vehicle = bool(self.trip_form.get_selected_vehicle())
        self.progress_panel.start_btn.setEnabled(self._health_ok and has_vehicle)


        self.trip_timer = QTimer(self)
        self.trip_timer.timeout.connect(self._tick_trip)
        self._trip_progress = 0.0

    def _start_trip(self):
        # Build the payload dict using current live form values. This uses
        # trip_logic.build_trip_payload which will validate the selected
        # vehicle against the live VEHICLE_CATALOG. Any validation error is
        # surfaced inline rather than crashing the app.
        try:
            payload = trip_logic.build_trip_payload(
                vehicle=self.trip_form.get_selected_vehicle(),
                weather=self.trip_form.get_weather(),
                temp=self.trip_form.get_temperature(),
                humidity=self.trip_form.get_humidity(),
                wind=self.trip_form.get_wind_speed(),
                trip_purpose=self.trip_form.get_trip_purpose(),
                road_type=self.trip_form.get_road_type(),
                traffic=self.trip_form.get_traffic(),
                distance=self.trip_form.get_distance(),
                passengers=self.trip_form.get_passengers(),
                cargo=self.trip_form.get_cargo_kg(),
                style=self.trip_form.get_style(),
            )
        except Exception as exc:
            # Show error inline and abort start
            self.recommendation.set_text(f"Error building payload: {exc}")
            return

        print("\n========== TRIP PAYLOAD ==========")
        import json
        print(json.dumps(payload, indent=2))
        print("===================================\n")

        # Keep computing local segments for the Time/Range Left math, but do
        # NOT start any animation or set the segmented plan for the UI.
        self._run_dist = self.trip_form.get_distance()
        self._run_speed = self.trip_form.get_speed()
        ev_range = self.trip_form.get_ev_range()
        pax = self.trip_form.get_passengers()
        load_factor = 1 + 0.02 * (pax - 1)
        self._run_stops = []

        self._run_segments = trip_logic.compute_mode_segments(
            self._run_dist,
            ev_range / load_factor if load_factor else 0,
            self._run_stops,
            self.trip_form.get_temperature(),
            self.trip_form.get_traffic(),
            self.trip_form.get_style(),
        )

        # Reset visual stat/state placeholders and show a loading state in the
        # recommendation panel while we fetch the backend recommendation.
        self.stat_cards.reset_stats()
        self.recommendation.set_text("Getting recommendation...")
        self.progress_panel.start_btn.setEnabled(False)

        # Background worker to post the payload and fetch recommendation
        class RecommendationWorker(QThread):
            finished = pyqtSignal(bool, object)

            def __init__(self, payload):
                super().__init__()
                self.payload = payload

            def run(self_inner):
                try:
                    r = requests.post(
                        "http://localhost:8000/api/trip/recommendation",
                        json=self_inner.payload,
                        timeout=30,
                    )
                    r.raise_for_status()
                    data = r.json()
                    self_inner.finished.emit(True, data)
                except Exception as exc:
                    self_inner.finished.emit(False, str(exc))

        self._rec_thread = RecommendationWorker(payload)
        self._rec_thread.finished.connect(self._on_recommendation_result)
        self._rec_thread.start()

    def _reset_trip(self):
        self.trip_timer.stop()
        self.progress_panel.reset_display()
        self.stat_cards.reset_stats()
        self.recommendation.reset_text()
        self.speedometer.setSpeed(self.trip_form.get_speed())

    def _on_recommendation_result(self, success: bool, data: object):
        # This runs in the main thread via the QThread signal connection.
        if not success:
            # Show inline error message and keep Start disabled until the
            # next successful health check per requirements.
            self.recommendation.set_text(f"Recommendation request failed: {data}")
            # Do not re-enable Start here; wait for health check to re-enable.
            return

        # Parse response safely: expected shape per spec, but be tolerant to
        # alternative backend shapes.
        resp = data if isinstance(data, dict) else {}

        # Try multiple locations for ML output (some backends may differ)
        ml_raw = None
        if 'ml_output' in resp and isinstance(resp['ml_output'], dict):
            ml = resp['ml_output']
            if isinstance(ml.get('raw'), dict):
                ml_raw = ml['raw']
            else:
                # Some backends use ml_output.raw vs ml_results; try top-level
                ml_raw = ml
        elif 'ml_results' in resp and isinstance(resp['ml_results'], dict):
            ml_raw = resp['ml_results']
        elif 'ml_results' in resp:
            ml_raw = resp.get('ml_results')
        else:
            ml_raw = {}

        genai = resp.get('genai_recommendation') or resp.get('genai') or resp.get('ai_advice') or {}

        # Extract numeric fields with safe defaults
        recommended_mode = None
        if isinstance(ml_raw, dict):
            recommended_mode = ml_raw.get('recommended_mode')
            fuel_used = ml_raw.get('fuel_used_l', 0.0)
            battery_used = ml_raw.get('battery_used_kwh', 0.0)
            co2 = ml_raw.get('co2_emissions_kg', ml_raw.get('co2', 0.0))
            cost = ml_raw.get('trip_cost_usd', ml_raw.get('cost', 0.0))
        else:
            recommended_mode = None
            fuel_used = 0.0
            battery_used = 0.0
            co2 = 0.0
            cost = 0.0

        def _to_float(x):
            try:
                return float(x)
            except Exception:
                return 0.0

        # Compute local Time and Range Left using the same local math as before
        stats = trip_logic.compute_trip_stats(
            self._run_segments,
            self._run_stops,
            self._run_dist,
            self._run_speed,
            self.trip_form.get_temperature(),
            self.trip_form.get_traffic(),
            self.trip_form.get_style(),
        )
        time_str = f"{stats['hh']}h {stats['mm']}m"
        range_left = stats['range_left']

        # Update stat tiles: use ml values for cost/co2/fuel/battery, local for time/range
        try:
            self.stat_cards.set_extended_stats(
                _to_float(cost),
                time_str,
                _to_float(co2),
                _to_float(range_left),
                _to_float(fuel_used),
                _to_float(battery_used),
            )
        except Exception:
            # Fallback: set what we can
            self.stat_cards.set_stats(_to_float(cost), time_str, _to_float(co2), _to_float(range_left))

        # Update mode badge/bar to show single recommended mode
        if recommended_mode:
            self.progress_panel.mode_bar.set_recommended_mode(recommended_mode)
            # Also update the textual badge shown in the header area
            if recommended_mode == 'ev':
                self.progress_panel.set_mode('Electric')
            elif recommended_mode == 'hybrid':
                self.progress_panel.set_mode('Hybrid')
            else:
                self.progress_panel.set_mode('Gas')
        else:
            # No recommendation mode provided; clear badge but keep segmented off
            self.progress_panel.mode_bar.set_recommended_mode(None)
            self.progress_panel.set_mode('Ready')

        # Update recommendation panel with genai summary and optional actions
        summary = None
        actions = None
        if isinstance(genai, dict):
            summary = genai.get('summary')
            actions = genai.get('actions')
        if summary:
            text = summary
            if actions and isinstance(actions, list) and len(actions) > 0:
                # Truncate the actions list to 6 items to avoid overflowing the
                # fixed recommendation area in the merged card. This is a
                # deliberate UX choice: the summary is preserved, actions are
                # limited to keep the layout compact (front-end truncation only).
                text += "\n\nActions:\n" + "\n".join(f"• {a}" for a in actions[:6])
            self.recommendation.set_text(text)
        else:
            # Fallback to the local describe_segments string
            text = trip_logic.describe_segments(
                self._run_segments, self._run_stops, stats.get('cost', 0.0), stats['hh'], stats['mm']
            )
            self.recommendation.set_text(text)

        # Re-enable Start when health check is OK and vehicle remains selected
        self._update_start_enabled()

    def _segment_at(self, miles: float) -> list:
        for seg in self._run_segments:
            if seg[0] <= miles < seg[1]:
                return seg
        return self._run_segments[-1]

    def _cumulative_gas_before(self, miles: float) -> float:
        total = 0.0
        for start, end, mode in self._run_segments:
            if mode != "Gas" or miles <= start:
                continue
            total += min(miles, end) - start
        return total

    def _next_event_text(self, miles: float) -> str:
        next_stop = next((s for s in self._run_stops if s > miles), None)
        seg_start, seg_end, mode = self._segment_at(miles)
        next_switch = seg_end if seg_end < self._run_dist else None
        if next_stop is None and next_switch is None:
            return "no more events"
        if next_stop is not None and (next_switch is None or next_stop <= next_switch):
            return f"charging stop at {round(next_stop)} km"
        other_mode = "Gas" if mode == "Electric" else "Electric"
        return f"switch to {other_mode} at {round(next_switch)} km"

    def _tick_trip(self):
        self._trip_progress += 2.0
        finished = self._trip_progress >= 100
        if finished:
            self._trip_progress = 100
            self.trip_timer.stop()

        kilometers = (self._trip_progress / 100) * self._run_dist
        self.progress_panel.mile_label.setText(f"{round(kilometers)} km")
        self.progress_panel.mode_bar.set_traveled(kilometers)
        self.progress_panel.next_event_label.setText(self._next_event_text(kilometers))

        seg_start, seg_end, mode = self._segment_at(kilometers)
        self.progress_panel.set_mode(mode)
        if mode == "Electric":
            seg_len = max(0.01, seg_end - seg_start)
            batt = max(0, 100 - ((kilometers - seg_start) / seg_len) * 100)
            self.progress_panel.set_battery(batt)
        else:
            self.progress_panel.set_battery(0)
            total_gas = sum(e - s for s, e, m in self._run_segments if m == "Gas")
            gas_so_far = self._cumulative_gas_before(kilometers)
            fuel_pct = 100 - (gas_so_far / total_gas) * 40 if total_gas > 0 else 100
            self.progress_panel.set_fuel(max(0, fuel_pct))

        self.speedometer.setSpeed(self._run_speed + random.uniform(-3, 3))

        if finished:
            self._finish_trip()

    def _finish_trip(self):
        # --- Again, all the actual math lives in trip_logic.py ---
        stats = trip_logic.compute_trip_stats(
            self._run_segments,
            self._run_stops,
            self._run_dist,
            self._run_speed,
            self.trip_form.get_temperature(),
            self.trip_form.get_traffic(),
            self.trip_form.get_style(),
        )
        self.stat_cards.set_stats(
            stats["cost"], f"{stats['hh']}h {stats['mm']}m", stats["co2"], stats["range_left"]
        )
        text = trip_logic.describe_segments(
            self._run_segments, self._run_stops, stats["cost"], stats["hh"], stats["mm"]
        )
        self.recommendation.set_text(text)