from __future__ import annotations

import logging
import threading
import time
from typing import Tuple, Callable, Optional
import math

from live_plotter import LivePlotter

from pedal_communication import PedalDevice, DataCollector, DataType


class PedalWorker:
    """
    Background worker that continuously reads angle / speed / power
    from the pedal device.

    In addition to providing get_latest_* accessors, it can push new
    samples to a callback whenever the real angle changes.
    """

    def __init__(
            self,
            stop_event: threading.Event,
            data_collector: DataCollector,
            worker_plot: LivePlotter | None = None,
    ) -> None:

        # Flag to stop the thread
        self._keep_running = True

        self.stop_event = stop_event

        self.data_collector = data_collector
        self.worker_plot = worker_plot

        # Shared state (protected by _lock)
        self._lock = threading.Lock()
        self._angle: float = 0.0
        self._speed: float = 0.0
        self._left_power: float = 0.0
        self._right_power: float = 0.0

        # Optional consumer callback: (angle, speed, power) -> None
        self._callback: Optional[Callable[[float, float, float], None]] = None

        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        )
        self._logger = logging.getLogger("PedalWorker")

        # ---- Connect to pedal device ----
        self._logger.info("Connecting to pedal device...")
        self.device = PedalDevice()
        while not self.device.connect():
            if self.stop_event.is_set():
                self._logger.warning("Stop requested before pedal connected.")
                return
            time.sleep(0.1)
        self._logger.info("Pedal device connected.")

    def get_latest_angle(self) -> float:
        """Return the most recent pedal angle (in degrees)."""
        with self._lock:
            return self._angle

    def get_latest_values(self) -> Tuple[float, float, float, float]:
        """Return (angle, speed, power) for the most recent sample."""
        with self._lock:
            return self._angle, self._speed, self._left_power, self._right_power

    @staticmethod
    def wait():
        time.sleep(0.05)
        print("None -- sleep 0.05")

    def run(self) -> None:
        self._logger.info("Pedal worker loop started.")
        prev_angle = None
        prev_speed = None

        try:
            while self._keep_running:
                data = getattr(self.data_collector, "data", None)
                if data is None or getattr(data, "empty", False):
                    self.wait()
                    continue

                values = data.values
                if values.size == 0:
                    self.wait()
                else:

                    # angle -> col 18, speed -> col 35, right power -> col 38
                    angle = math.degrees(float(values[-1, DataType.A18.value])) % 360
                    speed = math.degrees(float(values[-1, DataType.A35.value]))
                    left_power = float(values[-1, DataType.A36.value])
                    right_power = float(values[-1, DataType.A37.value])

                    changed = (angle != prev_angle) or (speed != prev_speed) or (left_power != self._left_power) or (right_power != self._right_power)
                    if changed:
                        prev_angle = angle
                        prev_speed = speed
                        # print("angle: ", angle)

                        # Update shared state
                        with self._lock:
                            self._angle = angle
                            self._speed = speed
                            self._left_power = left_power
                            self._right_power = right_power
                            if self.worker_plot is not None:
                                self.worker_plot.add_pedal_data_points(angle - 90, left_power, right_power)

                    time.sleep(0.005)

        finally:
            self._logger.info("Stopping DataCollector...")
            try:
                self.data_collector.stop()
            except Exception as exc:
                self._logger.exception("Error while stopping DataCollector: %s", exc)

            try:
                close = getattr(self.device, "close", None)
                if callable(close):
                    close()
            except Exception as exc:
                self._logger.exception("Error while closing pedal device: %s", exc)

            self._logger.info("Pedal worker stopped.")

    def stop(self):
        self._keep_running = False
