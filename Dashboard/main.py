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
        if event.key() == Qt.Key.Key_Escape:
            if self.isFullScreen():
                self.showNormal()
            else:
                self.showFullScreen()
        else:
            super().keyPressEvent(event)


def main():
    app = QApplication(sys.argv)
    # Force Qt's own cross-platform Fusion style so widget rendering
    # (especially text color in QComboBox, QLineEdit, QDoubleSpinBox) is
    # consistent across all machines regardless of their OS theme. Without
    # this, "windowsvista" or other native styles may ignore stylesheet
    # color rules and pull text colors from the system palette instead.
    app.setStyle("Fusion")
    app.setStyleSheet(DARK_STYLE)

    window = MainWindow()
    window.showFullScreen()

    sys.exit(app.exec())


if __name__ == "__main__":
    main()
