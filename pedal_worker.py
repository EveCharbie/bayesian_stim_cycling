from __future__ import annotations

import logging
import threading
import time
from typing import Tuple, Callable, Optional
import math
import numpy as np

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

        # States for the estimation of the angle by integrating speed (higher frequency than 50 Hz)
        self._previous_angle: float = 0
        self._previous_speed: float = 0
        self._previous_time: float = 0
        self._angle_estimate: float = 0

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

    def update_sensor(self, angle: float, speed: float) -> None:
        """
        Update the internal sensor state with a new real sample.
        Angle and speed are expected in degrees and degrees/s.
        """
        now = time.perf_counter()
        with self._lock:
            # reset integrator to measured state
            self._previous_angle = angle
            self._previous_speed = speed
            self._previous_time = now
            self._angle_estimate = angle
        # print("Measured angle :", self._previous_angle)

    def calculate_angle(self) -> None:
        """
        Integrate the last known speed to get a high-rate angle estimate.
        """
        now = time.perf_counter()
        with self._lock:
            dt = now - self._previous_time
            self._angle_estimate = (self._previous_angle + self._previous_speed * dt) % 360.0
            # print("Calculated angle :", self._angle_estimate)

    def get_latest_values(self) -> Tuple[float, float, float, float]:
        """Return (angle, speed, power) for the most recent sample."""
        with self._lock:
            return self._angle, self._speed, self._left_power, self._right_power

    def get_latest_estimated_angle(self) -> float:
        """Return the most recent estimated angle (in degrees)."""
        with self._lock:
            return self._angle_estimate

    @staticmethod
    def rotated_angle(angles: np.ndarray) -> np.ndarray:
        """Shift the angle by -90 degrees and then wrap it to [0, 360] degrees."""
        rotated_angles = np.zeros_like(angles)
        for i_frame in range(angles.shape[0]):
            shifted_angle = angles[i_frame] - np.pi/2  # Shift by -90 degrees
            rotated_angles[i_frame] = shifted_angle % (2 * np.pi)  # Wrap to [0, 2π]
        return rotated_angles

    def get_last_cycle_data(self) -> dict[str, list[np.ndarray]]:
        """
        Extract the last nb_cycles from the data collector buffer.
        Each cycle is defined as angle going from 0° to 360°.
        """
        with self._lock:
            times_vector = self.data_collector.data.timestamp.copy()
            angles = self.data_collector.data.values[:, DataType.A18.value].copy()
            left_power = self.data_collector.data.values[:, DataType.A36.value].copy()
            right_power = self.data_collector.data.values[:, DataType.A37.value].copy()
            total_power = self.data_collector.data.values[:, DataType.A38.value].copy()

        last_cycle_data = {
            "times_vector": [],
            "angles": [],
            "left_power": [],
            "right_power": [],
            "total_power": [],
        }
        last_idx = len(angles) - 1
        last_bound = None
        while last_idx > 0:
            current_angle = angles[last_idx]
            previous_angle = angles[last_idx - 1]
            nb_rotations = current_angle // (2 * np.pi)
            if np.sign(current_angle - (nb_rotations * 2 * np.pi)) != np.sign(
                    previous_angle - (nb_rotations * 2 * np.pi)):
                if last_bound is None:
                    # The end of the last cycle was detected
                    last_bound = last_idx
                else:
                    # The beginning of this cycle was detected, extract data for this cycle
                    start_idx = last_idx
                    end_idx = last_bound
                    last_cycle_data["times_vector"].insert(0, times_vector[start_idx:end_idx])
                    last_cycle_data["angles"].insert(0, self.rotated_angle(angles[start_idx:end_idx]))
                    last_cycle_data["left_power"].insert(0, left_power[start_idx:end_idx])
                    last_cycle_data["right_power"].insert(0, right_power[start_idx:end_idx])
                    last_cycle_data["total_power"].insert(0, total_power[start_idx:end_idx])
                    last_bound = last_idx

            last_idx -= 1

        return last_cycle_data

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
                        self.update_sensor(angle, speed)
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

                    else:
                        self.calculate_angle()
                    time.sleep(0.001)

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
