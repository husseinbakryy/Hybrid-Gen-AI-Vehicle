import sys
from PyQt6.QtWidgets import QApplication, QMainWindow
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPalette, QColor

from styles import DARK_STYLE
from dashboard_container import DashboardContainer


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Hybrid Trip Planner")
        self.setCentralWidget(DashboardContainer())

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            if self.isFullScreen():
                self.showNormal()
            else:
                self.showFullScreen()
        else:
            super().keyPressEvent(event)


def _apply_dark_palette(app: QApplication) -> None:
    """
    Force a dark system palette so that text is always white on dark
    backgrounds regardless of the user's Windows theme (light vs dark mode).
    Without this, Qt inherits the system palette which on Windows light-mode
    machines gives black text, making it invisible on dark widget backgrounds.
    """
    palette = QPalette()
    white = QColor("#f5f7fb")
    muted = QColor("#9aa4b2")
    bg = QColor("#0c111b")
    card = QColor("#141926")
    highlight = QColor("#4da3ff")

    palette.setColor(QPalette.ColorRole.Window, bg)
    palette.setColor(QPalette.ColorRole.WindowText, white)
    palette.setColor(QPalette.ColorRole.Base, card)
    palette.setColor(QPalette.ColorRole.AlternateBase, bg)
    palette.setColor(QPalette.ColorRole.ToolTipBase, bg)
    palette.setColor(QPalette.ColorRole.ToolTipText, white)
    palette.setColor(QPalette.ColorRole.Text, white)
    palette.setColor(QPalette.ColorRole.Button, card)
    palette.setColor(QPalette.ColorRole.ButtonText, white)
    palette.setColor(QPalette.ColorRole.BrightText, white)
    palette.setColor(QPalette.ColorRole.Link, highlight)
    palette.setColor(QPalette.ColorRole.Highlight, highlight)
    palette.setColor(QPalette.ColorRole.HighlightedText, QColor("#000000"))
    palette.setColor(QPalette.ColorRole.PlaceholderText, muted)
    app.setPalette(palette)


def main():
    # Ensure consistent layout across different Windows DPI settings.
    # PassThrough lets Qt use the exact DPI scale factor (e.g. 1.25x, 1.5x)
    # instead of rounding it, which prevents widgets from appearing too large
    # or too small on screens with non-standard DPI relative to the dev machine.
    QApplication.setHighDpiScaleFactorRoundingPolicy(
        Qt.HighDpiScaleFactorRoundingPolicy.PassThrough
    )
    app = QApplication(sys.argv)
    _apply_dark_palette(app)   # must be before setStyleSheet
    app.setStyleSheet(DARK_STYLE)

    window = MainWindow()
    window.showFullScreen()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
