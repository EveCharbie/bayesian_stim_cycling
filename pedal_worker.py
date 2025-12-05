from __future__ import annotations

import logging
import threading
import time
from typing import Tuple, Callable, Optional
import math

from pedal_communication import PedalDevice, DataCollector


class PedalWorker(threading.Thread):
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
            name: str = "PedalWorker",
    ) -> None:
        super().__init__(name=name, daemon=True)
        self.stop_event = stop_event
        self._keep_running = True
        self.data_collector = data_collector

        # Shared state (protected by _lock)
        self._lock = threading.Lock()
        self._angle: float = 0.0
        self._speed: float = 0.0
        self._power: float = 0.0

        # Optional consumer callback: (angle, speed, power) -> None
        self._callback: Optional[Callable[[float, float, float], None]] = None

        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        )
        self._logger = logging.getLogger(name)

        # ---- Connect to pedal device ----
        self._logger.info("Connecting to pedal device...")
        self.device = PedalDevice()
        while not self.device.connect():
            if self.stop_event.is_set():
                self._logger.warning("Stop requested before pedal connected.")
                return
            time.sleep(0.1)
        self._logger.info("Pedal device connected.")

        # ---- Start data collector ----
        # todo: move outside ?
        # self.data_collector = DataCollector(self.device)
        # self.data_collector.start()
        # self._logger.info("DataCollector started.")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    def register_callback(self, cb: Callable[[float, float, float], None]) -> None:
        """
        Called (by StimulationWorker) to receive new real samples.

        The callback is invoked from the PedalWorker thread, so it must be
        lightweight and non-blocking.
        """
        self._callback = cb

    def get_latest_angle(self) -> float:
        """Return the most recent pedal angle (in degrees)."""
        with self._lock:
            return self._angle

    def get_latest_values(self) -> Tuple[float, float, float]:
        """Return (angle, speed, power) for the most recent sample."""
        with self._lock:
            return self._angle, self._speed, self._power

    # ------------------------------------------------------------------
    # Thread loop
    # ------------------------------------------------------------------
    def wait(self):
        time.sleep(0.005)
        print("None -- sleep 0.005")

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

                # angle -> col 18, speed -> col 35, power -> col 38
                angle = math.degrees(float(values[-1, 18])) % 360
                speed = math.degrees(float(values[-1, 35]))

                power = 0.0
                try:
                    power = float(values[-1, 38])
                except IndexError:
                    pass

                changed = (angle != prev_angle) or (speed != prev_speed)
                if changed:
                    prev_angle = angle
                    prev_speed = speed
                    print("angle: ", angle)

                # Update shared state
                with self._lock:
                    self._angle = angle
                    self._speed = speed
                    self._power = power

                # Push to consumer if there is a new sample
                if changed and self._callback is not None:
                    try:
                        self._callback(angle, speed, power)
                    except Exception:
                        self._logger.exception("Error in pedal callback")

                time.sleep(0.005)  # you can tune this

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
