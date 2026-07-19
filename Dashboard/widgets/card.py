"""
Reusable dashboard card with a colored left accent strip.

NOTE: deliberately has NO QGraphicsDropShadowEffect (add_shadow) - that's
the exact thing that caused the hover-disappearing bug earlier. If we want
a shadow/glow back later, it needs to be painted manually (paintEvent)
rather than via QGraphicsEffect.
"""

from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import QWidget, QFrame, QLabel, QVBoxLayout, QHBoxLayout

from theme import Cards


class Card(QFrame):
    def __init__(self, title: str, accent_color):
        super().__init__()

        self.setObjectName("Card")

        root_layout = QHBoxLayout(self)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        self.accent = QFrame()
        self.accent.setFixedWidth(Cards.ACCENT_WIDTH)
        self.accent.setStyleSheet(
            f"""
            background:{accent_color.name()};
            border-top-left-radius:{Cards.RADIUS}px;
            border-bottom-left-radius:{Cards.RADIUS}px;
            """
        )
        root_layout.addWidget(self.accent)

        container = QWidget()
        self.content_layout = QVBoxLayout(container)
        self.content_layout.setContentsMargins(
            Cards.PADDING, Cards.PADDING, Cards.PADDING, Cards.PADDING
        )
        self.content_layout.setSpacing(Cards.CONTENT_SPACING)

        self.title = QLabel(title.upper())
        self.title.setObjectName("SectionTitle")
        self.title.setAlignment(Qt.AlignmentFlag.AlignLeft)

        self.header_row = QHBoxLayout()
        self.header_row.addWidget(self.title)
        self.header_row.addStretch()
        self.content_layout.addLayout(self.header_row)

        root_layout.addWidget(container)

    def add_header_widget(self, widget):
        self.header_row.addWidget(widget)

    def set_accent_color(self, color):
        self.accent.setStyleSheet(
            f"""
            background:{color.name()};
            border-top-left-radius:{Cards.RADIUS}px;
            border-bottom-left-radius:{Cards.RADIUS}px;
            """
        )

    def add_widget(self, widget):
        self.content_layout.addWidget(widget)

    def add_layout(self, layout):
        self.content_layout.addLayout(layout)

    def add_spacing(self, value):
        self.content_layout.addSpacing(value)

    def add_stretch(self):
        self.content_layout.addStretch()