"""
AI-generated recommendation text - placeholder wording for now (see
trip_logic.describe_segments), now built on the Card base class.
"""

from PyQt6.QtWidgets import QLabel

from widgets.card import Card
from theme import Colors

DEFAULT_TEXT = "Set up your trip and hit start to get a recommendation."


class RecommendationPanel(Card):
    def __init__(self, parent=None):
        super().__init__("AI Recommendation", Colors.AI)

        self.text_label = QLabel(DEFAULT_TEXT)
        self.text_label.setWordWrap(True)
        self.text_label.setStyleSheet(
            f"color: {Colors.TEXT_SECONDARY.name()}; font-size: 13px;"
        )
        self.add_widget(self.text_label)

    def set_text(self, text: str):
        self.text_label.setText(text)

    def reset_text(self):
        self.text_label.setText(DEFAULT_TEXT)