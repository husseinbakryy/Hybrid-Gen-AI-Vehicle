from typing import Any
from PyQt6.QtCore import QThread, pyqtSignal
import trip_logic


class LiveTripWorker(QThread):
    """Background worker thread managing the WebSocket connection for a live trip session."""

    updateReceived = pyqtSignal(object)
    connectionFailed = pyqtSignal(str)
    connectionClosed = pyqtSignal()

    def __init__(self, trip_config: dict, base_url: str = "ws://localhost:8000", parent=None):
        super().__init__(parent)
        self.trip_config = trip_config
        self.base_url = base_url
        self._ws: Any = None
        self._running = False

    def run(self):
        self._ws = trip_logic.connect_live_trip(self.trip_config, self.base_url, timeout=30.0)
        if self._ws is None:
            self.connectionFailed.emit(
                f"Could not connect to live trip server at {self.base_url}"
            )
            return

        self._running = True
        while self._running:
            try:
                raw = self._ws.recv()  # pyrefly: ignore [no-attribute]
            except Exception:
                break

            if not raw:
                continue

            update = trip_logic.parse_server_message(raw)
            self.updateReceived.emit(update)

            if update.message_type == "trip_end":
                self._running = False

        self.connectionClosed.emit()

    def send_action(self, action: str):
        if self._ws is not None:
            try:
                trip_logic.send_pedal_action(self._ws, action)
            except Exception:
                pass

    def send_multiplier(self, value: int):
        if self._ws is not None:
            try:
                trip_logic.send_time_multiplier(self._ws, value)
            except Exception:
                pass

    def send_voice_toggle(self, enabled: bool):
        if self._ws is not None:
            try:
                trip_logic.toggle_voice(self._ws, enabled)
            except Exception:
                pass

    def stop(self):
        self._running = False
        if self._ws is not None:
            try:
                trip_logic.stop_live_trip(self._ws)
            except Exception:
                pass
            try:
                self._ws.close()
            except Exception:
                pass
