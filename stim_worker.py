from __future__ import annotations

import logging
import threading
import time
from typing import Optional, TYPE_CHECKING

if TYPE_CHECKING:
    from pedal_worker import PedalWorker

from common_types import StimParameters, MuscleMode
from constants import STIMULATION_RANGE

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

    def __init__(self, worker_pedal: PedalWorker, muscle_mode: MuscleMode.BICEPS_TRICEPS | MuscleMode.DELTOIDS):

        self.worker_pedal = worker_pedal
        self.muscle_mode = muscle_mode

        # ----------------- Stimulator setup ----------------- #
        # Default intensity for each muscle (will be overridden by BO)
        self.intensity = {
            "biceps_r": 0,
            "triceps_r": 0,
            "biceps_l": 0,
            "triceps_l": 0,
            "delt_post_r": 0,
            "delt_ant_r": 0,
            "delt_post_l": 0,
            "delt_ant_l": 0,
        }

        # Pulse width for each muscle
        self.pulse_width = {
            "biceps_r": 300,
            "triceps_r": 300,
            "biceps_l": 300,
            "triceps_l": 300,
            "delt_post_r": 300,
            "delt_ant_r": 300,
            "delt_post_l": 300,
            "delt_ant_l": 300,
        }

        # Keeps track of if the stimulation is currently active for each muscle
        self.stimulation_state = {
            "biceps_r": False,
            "triceps_r": False,
            "biceps_l": False,
            "triceps_l": False,
            "delt_post_r": False,
            "delt_ant_r": False,
            "delt_post_l": False,
            "delt_ant_l": False,
        }

        # Default stimulation ranges in degrees (will be overridden by BO)
        self.stimulation_range = {key: STIMULATION_RANGE[key] for key in STIMULATION_RANGE.keys()}

        self.list_channels = [
            Ch(
                mode=Modes.SINGLE,
                no_channel=self.muscle_mode.channel_indices[i],
                amplitude=self.intensity[muscle_name],  # Intensity
                pulse_width=self.pulse_width[muscle_name],
                name=muscle_name,
                device_type=Device.Rehastim2,
            )
            for i, muscle_name in enumerate(self.muscle_mode.muscle_keys)
        ]

        # Create stimulator
        self.stimulator = St(port="COM3", show_log=False)
        self.stimulator.init_channel(
            stimulation_interval=20,
            list_channels=self.list_channels,
        )

        # Angle-related state (degrees)
        self._angle_lock = threading.Lock()
        self.angle = 0.0               # current estimated angle (deg)
        self.previous_angle = 0.0      # last integrated angle (deg)
        self.previous_speed = 0.0      # last speed (deg/s)
        self.previous_time = time.perf_counter()

        # ----------------- Start stimulation once ----------------- #
        self.stimulator.start_stimulation(upd_list_channels=self.list_channels)

    def apply_parameters(self, params: StimParameters, really_change_stim_intensity: bool) -> None:
        """
        Apply BO parameters to:
          - stimulation_range (onset/offset)
          - intensity per muscle
          - pulse_width per muscle
        """
        for muscle in self.muscle_mode.muscle_keys:
            onset = int(getattr(params, f"onset_deg_{muscle}"))
            offset = int(getattr(params, f"offset_deg_{muscle}"))
            intensity = int(getattr(params, f"pulse_intensity_{muscle}"))

            # Update angle range [onset, offset]
            self.stimulation_range[muscle] = [onset, offset]

            # Update intensity
            if really_change_stim_intensity:
                self.intensity[muscle] = intensity

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
        self.angle = self.worker_pedal.get_latest_estimated_angle()
        for i, muscle in enumerate(self.muscle_mode.muscle_keys):
            onset, offset = self.stimulation_range[muscle]
            is_stimulation_active = self.stimulation_state[muscle]
            channel = self.list_channels[i]

            if self.angle > 360.0 or self.angle < 0:
                raise RuntimeError("Error: this should not happen. The angle is out of range [0. 360].")

            # Range wraps around 360 (e.g., [220, 10])
            should_be_active = self.should_stimulation_be_active(onset, offset)
            # print(
            #     "muscle: ", key,
            #     "onset: ", onset,
            #     "offset: ", offset,
            #     "angle", self.angle,
            #     'is_active: ', is_stimulation_active,
            #     'should_be_active: ', should_be_active,
            # )

            if not is_stimulation_active and should_be_active:
                # Start stimulation
                self.stimulation_state[muscle] = True
                channel.set_amplitude(self.intensity[muscle])
                channel.set_pulse_width(self.pulse_width[muscle])
                should_activate_stim = True
            elif is_stimulation_active and not self.should_stimulation_be_active(onset, offset):
                # Stop stimulation
                self.stimulation_state[muscle] = False
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
        worker_pedal: PedalWorker,
        muscle_mode: MuscleMode.BICEPS_TRICEPS | MuscleMode.DELTOIDS,
    ):
        # Flag to stop the thread
        self._keep_running = True

        # Controller that runs continuously
        self.controller = HandCycling2(worker_pedal, muscle_mode)

        # Worker that provides pedal data
        self.worker_pedal = worker_pedal
        self.muscle_mode = muscle_mode

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

