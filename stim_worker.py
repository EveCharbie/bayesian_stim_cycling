from __future__ import annotations

import logging
import threading
import time
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from pedal_worker import PedalWorker

from common_types import StimParameters
from constants import STIMULATION_RANGE, MUSCLE_KEYS

from pysciencemode import Rehastim2 as St
from pysciencemode import Channel as Ch
from pysciencemode import Device, Modes


class HandCycling2:
    """
    Hardware controller for Rehastim2 and encoder.

    Stimulation is started once and kept running.
    Angle is read from a single NI-DAQ channel (e.g. Dev1/ai14).
    BO updates only the stimulation parameters.
    """

    def __init__(self, worker_pedal):

        self.worker_pedal = worker_pedal

        # ----------------- Stimulator setup ----------------- #
        # Default intensity for each muscle (will be overridden by BO)
        self.intensity = {
            "biceps_r": 10,
            "triceps_r": 10,
            "biceps_l": 10,
            "triceps_l": 10,
        }

        # Pulse width for each muscle
        self.pulse_width = {
            "biceps_r": 300,
            "triceps_r": 300,
            "biceps_l": 300,
            "triceps_l": 300,
        }

        # Keeps track of if the stimulation is currently active for each muscle
        self.stimulation_state = {
            "biceps_r": False,
            "triceps_r": False,
            "biceps_l": False,
            "triceps_l": False,
        }

        # Default stimulation ranges in degrees (will be overridden by BO)
        self.stimulation_range = {key: STIMULATION_RANGE[key] for key in STIMULATION_RANGE.keys()}

        self.list_channels = [
            Ch(
                mode=Modes.SINGLE,
                no_channel=i + 1,
                amplitude=self.intensity[muscle_name],  # Intensity
                pulse_width=self.pulse_width[muscle_name],
                name=MUSCLE_KEYS[i],
                device_type=Device.Rehastim2,
            )
            for i, muscle_name in enumerate(MUSCLE_KEYS)
        ]

        # Create stimulator
        self.stimulator = St(port="COM3", show_log=False)
        self.stimulator.init_channel(
            stimulation_interval=30,
            list_channels=self.list_channels,
        )

        # Angle-related state (degrees)
        self._angle_lock = threading.Lock()
        self.angle = 0.0               # current estimated angle (deg)
        self.previous_angle = 0.0      # last integrated angle (deg)
        self.previous_speed = 0.0      # last speed (deg/s)
        self.previous_time = time.perf_counter()

        # # (optional, for debugging)
        # self.sensix_angle = 0.0        # last real angle from pedal (deg)
        # self.sensix_speed = 0.0        # last real speed from pedal (deg/s)

        # ----------------- Start stimulation once ----------------- #
        self.stimulator.start_stimulation(upd_list_channels=self.list_channels)

    def apply_parameters(self, params: StimParameters, really_change_stim_intensity: bool) -> None:
        """
        Apply BO parameters to:
          - stimulation_range (onset/offset)
          - intensity per muscle
          - pulse_width per muscle
        """
        for muscle in MUSCLE_KEYS:
            onset = int(getattr(params, f"onset_deg_{muscle}"))
            offset = int(getattr(params, f"offset_deg_{muscle}"))
            intensity = int(getattr(params, f"pulse_intensity_{muscle}"))

            # Update angle range [onset, offset]
            self.stimulation_range[muscle] = [onset, offset]

            # Update intensity
            if really_change_stim_intensity:
                self.intensity[muscle] = intensity


    # # ---------- called when pedal worker has a new real sample ----------
    # def update_sensor(self, angle: float, speed: float) -> None:
    #     """
    #     Update the internal sensor state with a new real sample.
    #     Angle and speed are expected in degrees and degrees/second.
    #     """
    #     now = time.perf_counter()
    #     with self._angle_lock:
    #         self.sensix_angle = angle
    #         self.sensix_speed = speed
    #
    #         # reset integrator to measured state
    #         self.previous_angle = angle
    #         self.previous_speed = speed
    #         self.previous_time = now
    #         self.angle = angle
    #
    #         # print(angle, speed)

    # def calculate_angle(self) -> float:
    #     """
    #     Integrate the last known speed to get a high-rate angle estimate.
    #     """
    #     now = time.perf_counter()
    #     with self._angle_lock:
    #         dt = now - self.previous_time
    #         self.previous_time = now
    #
    #         self.previous_angle = (self.previous_angle + self.previous_speed * dt) % 360.0
    #         self.angle = self.previous_angle
    #         print("Calculated angle :", self.previous_angle)
    #         return self.angle

    def should_stimulation_be_active(self, onset: float, offset: float) -> bool:
        if onset < offset:
            # The range does not wrap around 0
            return (onset <= self.angle) and (self.angle <= offset)
        elif onset > offset:
            # The angle wraps around 0
            return not ((offset <= self.angle) and (self.angle <= onset))
        else:
            raise RuntimeError("The onset and offset have the same value.")

    def update_stimulation_for_current_angle(self) -> tuple[bool, bool]:
        """
        One pass of your original while-loop logic.

        Returns:
          True if amplitudes were updated and we should call start_stimulation().
        """
        should_activate_stim = False
        should_deactivate_stim = False
        self.angle = self.worker_pedal.get_latest_angle()
        for key in self.stimulation_range.keys():
            onset, offset = self.stimulation_range[key]
            is_stimulation_active = self.stimulation_state[key]
            ch_idx = MUSCLE_KEYS.index(key)
            channel = self.list_channels[ch_idx]

            if self.angle > 360.0 or self.angle < 0:
                raise RuntimeError("Error: this should not happen. The angle is out of range [0. 360].")

            # Range wraps around 360 (e.g., [220, 10])
            should_be_active = self.should_stimulation_be_active(onset, offset)
            print(
                "muscle: ", key,
                "onset: ", onset,
                "offset: ", offset,
                "angle", self.angle,
                'is_active: ', is_stimulation_active,
                'should_be_active: ', should_be_active,
            )

            if not is_stimulation_active and should_be_active:
                # Start stimulation
                self.stimulation_state[key] = True
                channel.set_amplitude(self.intensity[key])
                channel.set_pulse_width(self.pulse_width[key])
                should_activate_stim = True
            elif is_stimulation_active and not self.should_stimulation_be_active(onset, offset):
                # Stop stimulation
                self.stimulation_state[key] = False
                channel.set_amplitude(0.0)
                should_deactivate_stim = True
            else:
                continue

        return should_activate_stim, should_deactivate_stim


class StimulationWorker:
    """
    Thread that keeps stimulation running continuously using a while-loop structure.
    """

    def __init__(
        self,
        worker_pedal: Optional["PedalWorker"],
    ):
        # Flag to stop the thread
        self._keep_running = True

        # Controller that runs continuously
        self.controller = HandCycling2(worker_pedal)

        # Worker that provides pedal data
        self.worker_pedal = worker_pedal

        # Logger
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        )
        self._logger = logging.getLogger("StimlWorker")

    def run(self) -> None:

        try:
            while self._keep_running:
                should_activate_stim, should_deactivate_stim = self.controller.update_stimulation_for_current_angle()
                if should_deactivate_stim or should_activate_stim:
                    # Only call when intensity or pulse width changed
                    # Start is misleading, it should be called update
                    self.controller.stimulator.start_stimulation(
                        upd_list_channels=self.controller.list_channels
                    )
                time.sleep(0.001)
        finally:
            self._logger.info("Stopping StimWorker...")
            try:
                self.stop()
            except Exception as exc:
                self._logger.exception("Error while stopping StimWorker: %s", exc)
            self._logger.info("Stimulation worker stopped.")

    def stop(self):
        self.controller.stimulator.pause_stimulation()
        self.controller.stimulator.end_stimulation()
        self.controller.stimulator.disconnect()
        self._keep_running = False

