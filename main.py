import sys
from PyQt6.QtWidgets import QApplication

from styles import DARK_STYLE
from main_window import MainWindow


def main():
    app = QApplication(sys.argv)
    app.setStyleSheet(DARK_STYLE)
    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
