import random
from PyQt6.QtWidgets import QWidget, QGridLayout, QVBoxLayout
from PyQt6.QtCore import QTimer

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

        speedo_card = Card("Speed", Colors.EV)
        self.speedometer = Speedometer()
        speedo_card.add_widget(self.speedometer)

        self.progress_panel = TripProgressPanel()
        self.stat_cards = StatCardsPanel()
        self.recommendation = RecommendationPanel()

        # Bottom group: everything except the speedometer, stacked together
        bottom_group = QVBoxLayout()
        bottom_group.addWidget(self.progress_panel)
        bottom_group.addWidget(self.stat_cards)
        bottom_group.addWidget(self.recommendation)
        bottom_group.addStretch()

        self.trip_form = TripSetupForm()

        outer.addWidget(self.header, 0, 0, 1, 2)
        outer.addWidget(speedo_card, 1, 0)
        outer.addLayout(bottom_group, 2, 0)
        # Trip Setup spans both rows on the right - a persistent sidebar
        # while the speedometer + bottom group stack up on the left
        outer.addWidget(self.trip_form, 1, 1, 2, 1)

        # Give the speedometer row more room than the bottom group row
        outer.setRowStretch(1, 1)
        outer.setRowStretch(2, 2)

        self.trip_form.speedChanged.connect(self.speedometer.setSpeed)
        self.trip_form.distanceChanged.connect(
            lambda v: self.progress_panel.dist_label.setText(f"{v} mi")
        )
        self.speedometer.setSpeed(self.trip_form.get_speed())

        self.progress_panel.startClicked.connect(self._start_trip)
        self.progress_panel.resetClicked.connect(self._reset_trip)

        self.trip_timer = QTimer(self)
        self.trip_timer.timeout.connect(self._tick_trip)
        self._trip_progress = 0.0

    def _start_trip(self):
        self._trip_progress = 0.0
        self._run_dist = self.trip_form.get_distance()
        self._run_speed = self.trip_form.get_speed()
        ev_range = self.trip_form.get_ev_range()
        pax = self.trip_form.get_passengers()
        load_factor = 1 + 0.02 * (pax - 1)
        self._run_stops = self.trip_form.get_charging_stops()

        # --- All the actual trip-planning math lives in trip_logic.py ---
        self._run_segments = trip_logic.compute_mode_segments(
            self._run_dist, ev_range / load_factor, self._run_stops
        )

        self.progress_panel.set_plan(self._run_segments, self._run_stops, self._run_dist)
        self.stat_cards.reset_stats()
        self.recommendation.reset_text()
        self.trip_timer.start(100)

    def _reset_trip(self):
        self.trip_timer.stop()
        self.progress_panel.reset_display()
        self.stat_cards.reset_stats()
        self.recommendation.reset_text()
        self.speedometer.setSpeed(self.trip_form.get_speed())

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
            return f"charging stop at {round(next_stop)} mi"
        other_mode = "Gas" if mode == "Electric" else "Electric"
        return f"switch to {other_mode} at {round(next_switch)} mi"

    def _tick_trip(self):
        self._trip_progress += 2.0
        finished = self._trip_progress >= 100
        if finished:
            self._trip_progress = 100
            self.trip_timer.stop()

        miles = (self._trip_progress / 100) * self._run_dist
        self.progress_panel.mile_label.setText(f"{round(miles)} mi")
        self.progress_panel.mode_bar.set_traveled(miles)
        self.progress_panel.next_event_label.setText(self._next_event_text(miles))

        seg_start, seg_end, mode = self._segment_at(miles)
        self.progress_panel.set_mode(mode)
        if mode == "Electric":
            seg_len = max(0.01, seg_end - seg_start)
            batt = max(0, 100 - ((miles - seg_start) / seg_len) * 100)
            self.progress_panel.set_battery(batt)
        else:
            self.progress_panel.set_battery(0)
            total_gas = sum(e - s for s, e, m in self._run_segments if m == "Gas")
            gas_so_far = self._cumulative_gas_before(miles)
            fuel_pct = 100 - (gas_so_far / total_gas) * 40 if total_gas > 0 else 100
            self.progress_panel.set_fuel(max(0, fuel_pct))

        self.speedometer.setSpeed(self._run_speed + random.uniform(-3, 3))

        if finished:
            self._finish_trip()

    def _finish_trip(self):
        # --- Again, all the actual math lives in trip_logic.py ---
        stats = trip_logic.compute_trip_stats(
            self._run_segments, self._run_stops, self._run_dist, self._run_speed
        )
        self.stat_cards.set_stats(
            stats["cost"], f"{stats['hh']}h {stats['mm']}m", stats["co2"], stats["range_left"]
        )
        text = trip_logic.describe_segments(
            self._run_segments, self._run_stops, stats["cost"], stats["hh"], stats["mm"]
        )
        self.recommendation.set_text(text)