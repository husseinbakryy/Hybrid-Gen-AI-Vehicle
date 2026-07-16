"""Global stylesheet for the app - dark 'cockpit' theme."""

DARK_STYLE = """
QMainWindow { background-color: #0a0a0d; }
QLabel { color: #e8e8ec; }
QFrame#card {
    background-color: #131318;
    border: 1px solid #2a2a30;
    border-radius: 12px;
}
QFrame#statTile {
    background-color: #1c1c22;
    border-radius: 8px;
}
QPushButton {
    background-color: transparent;
    color: #8a8a93;
    border: 1px solid #333;
    border-radius: 6px;
    padding: 8px;
}
QPushButton:hover { background-color: #1c1c22; }
QPushButton#startBtn {
    background-color: #00d9c0;
    color: #04342c;
    border: none;
    font-weight: 600;
}
QPushButton#startBtn:hover { background-color: #1fe8d0; }
QComboBox, QSpinBox {
    background-color: #1c1c22;
    color: #e8e8ec;
    border: 1px solid #333;
    border-radius: 4px;
    padding: 4px;
}
QSlider::groove:horizontal {
    height: 4px;
    background: #1c1c22;
    border-radius: 2px;
}
QSlider::handle:horizontal {
    background: #00d9c0;
    width: 14px;
    height: 14px;
    margin: -6px 0;
    border-radius: 7px;
}
"""
