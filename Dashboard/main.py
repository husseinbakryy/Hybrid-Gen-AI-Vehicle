import sys
from PyQt6.QtWidgets import QApplication, QMainWindow
from PyQt6.QtCore import Qt

from styles import DARK_STYLE
from dashboard_container import DashboardContainer


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Hybrid Trip Planner")
        self.setCentralWidget(DashboardContainer())

    def keyPressEvent(self, event):
        # Escape toggles fullscreen <-> normal window - handy while
        # developing/testing so you're not stuck in fullscreen every run.
        # Remove this if you want fullscreen to be locked for the demo.
        if event.key() == Qt.Key.Key_Escape:
            if self.isFullScreen():
                self.showNormal()
            else:
                self.showFullScreen()
        else:
            super().keyPressEvent(event)


def main():
    app = QApplication(sys.argv)
    app.setStyleSheet(DARK_STYLE)

    window = MainWindow()
    window.showFullScreen()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
