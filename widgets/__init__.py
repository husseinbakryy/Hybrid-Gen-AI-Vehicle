"""Widget package - re-exports so other files can do
`from widgets import Speedometer, TripProgressPanel, ...`
"""

from widgets.speedometer import Speedometer
from widgets.segmented_mode_bar import SegmentedModeBar
from widgets.trip_progress_panel import TripProgressPanel
from widgets.car_seat_selector import CarSeatSelector
from widgets.trip_setup_form import TripSetupForm
from widgets.stat_cards_panel import StatCardsPanel
from widgets.recommendation_panel import RecommendationPanel

__all__ = [
    "Speedometer",
    "SegmentedModeBar",
    "TripProgressPanel",
    "CarSeatSelector",
    "TripSetupForm",
    "StatCardsPanel",
    "RecommendationPanel",
]
