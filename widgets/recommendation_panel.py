from PyQt6.QtWidgets import QFrame, QVBoxLayout, QLabel


class RecommendationPanel(QFrame):
    """AI-generated recommendation text - placeholder wording for now,
    will be replaced once the GenAI integration is wired in (see
    trip_logic.describe_segments)."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("card")
        layout = QVBoxLayout(self)
        title = QLabel("AI RECOMMENDATION")
        title.setStyleSheet("color: #8a8a93; font-size: 11px; letter-spacing: 1px;")
        layout.addWidget(title)
        self.text_label = QLabel("Set up your trip and hit start to get a recommendation.")
        self.text_label.setWordWrap(True)
        self.text_label.setStyleSheet("color: #c5c5cc; font-size: 13px;")
        layout.addWidget(self.text_label)

    def set_text(self, text: str):
        self.text_label.setText(text)

    def reset_text(self):
        self.text_label.setText("Set up your trip and hit start to get a recommendation.")
