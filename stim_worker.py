from __future__ import annotations

import threading
import queue
import time
from typing import Optional, Dict, Callable, List, TYPE_CHECKING

if TYPE_CHECKING:
    from pedal_worker import PedalWorker

import numpy as np
import nidaqmx

from pedal_communication import DataCollector, DataType

from pysciencemode import Rehastim2 as St
from pysciencemode import Channel as Ch
from pysciencemode import Device, Modes

from common_types import StimJob, StimResult, StimParameters


class HandCycling2:
    """
    Hardware controller for Rehastim2 and encoder.

    Stimulation is started once and kept running.
    Angle is read from a single NI-DAQ channel (e.g. Dev1/ai14).
    BO updates only the stimulation parameters.
    """

    MUSCLE_KEYS = ["biceps_r", "triceps_r", "biceps_l", "triceps_l"]

    def __init__(self, worker_pedal):

        self.worker_pedal = worker_pedal

        # ----------------- Stimulator setup ----------------- #
        channel_muscle_name = [
            "biceps_r",
            # "triceps_r",
            # "biceps_l",
            # "triceps_l",
        ]

        # Default intensity for each muscle (will be overridden by BO)
        self.intensity = {
            "biceps_r": 10,
            # "triceps_r": 10,
            # "biceps_l": 10,
            # "triceps_l": 10,
        }

        # Default pulse width for each muscle (will be overridden by BO)
        self.pulse_width = {
            "biceps_r": 100,
            # "triceps_r": 100,
            # "biceps_l": 100,
            # "triceps_l": 100,
        }

        self.channel_number = {
            "biceps_r": 1,
            # "triceps_r": 2,
            # "biceps_l": 3,
            # "triceps_l": 4,
        }

        self.stimulation_state = {
            "biceps_r": False,
            # "triceps_r": False,
            # "biceps_l": False,
            # "triceps_l": False,
        }

        # Default stimulation ranges in degrees (will be overridden by BO)
        # zero = main gauche devant
        self.stimulation_range = {
            "biceps_r": [220.0, 10.0],
            # "triceps_r": [20.0, 180.0],
            # "biceps_l": [40.0, 190.0],
            # "triceps_l": [200.0, 360.0],
        }

        self.list_channels = [
            Ch(
                mode=Modes.SINGLE,
                no_channel=i + 1,
                amplitude=self.intensity[muscle_name],  # Intensity
                pulse_width=350,
                name=channel_muscle_name[i],
                device_type=Device.Rehastim2,
            )
            for i, muscle_name in enumerate(channel_muscle_name)
        ]

        # Create stimulator
        self.stimulator = St(port="COM3", show_log=False)
        self.stimulator.init_channel(
            stimulation_interval=30,
            list_channels=self.list_channels,
        )

        # Condition flags for wrap-around
        # self.stim_condition: Dict[str, int] = {}
        # self._update_stim_condition()

        # Angle-related state (degrees)
        self._angle_lock = threading.Lock()
        self.angle = 0.0               # current estimated angle (deg)
        self.previous_angle = 0.0      # last integrated angle (deg)
        self.previous_speed = 0.0      # last speed (deg/s)
        self.previous_time = time.perf_counter()

        # (optional, for debugging)
        self.sensix_angle = 0.0        # last real angle from pedal (deg)
        self.sensix_speed = 0.0        # last real speed from pedal (deg/s)

        # ----------------- Start stimulation once ----------------- #
        self.stimulator.start_stimulation(upd_list_channels=self.list_channels)


    # ------------ Apply parameters from BO (called only when BO updates) ------------ #
    # def _update_stim_condition(self):
    #     for key in self.stimulation_range.keys():
    #         self.stim_condition[key] = (
    #             1 if self.stimulation_range[key][0] < self.stimulation_range[key][1] else 0
    #         )

    def apply_parameters(self, params: StimParameters) -> None:
        """
        Apply BO parameters to:
          - stimulation_range (onset/offset)
          - intensity per muscle
          - pulse_width per muscle
        """
        for muscle in self.MUSCLE_KEYS:
            onset = int(getattr(params, f"onset_deg_{muscle}"))
            offset = int(getattr(params, f"offset_deg_{muscle}"))
            intensity = int(getattr(params, f"pulse_intensity_{muscle}"))
            pulse_width = int(getattr(params, f"pulse_width_{muscle}"))

            # Update angle range [onset, offset]
            self.stimulation_range[muscle] = [onset, offset]

            # Update intensity & pulse width
            self.intensity[muscle] = intensity

            # Update pulse width
            self.pulse_width[muscle] = pulse_width

        # # Recompute condition flags
        # self._update_stim_condition()

    # ---------- called when pedal worker has a new real sample ----------
    def update_sensor(self, angle: float, speed: float) -> None:
        """
        Update the internal sensor state with a new real sample.
        Angle and speed are expected in degrees and degrees/second.
        """
        now = time.perf_counter()
        with self._angle_lock:
            self.sensix_angle = angle
            self.sensix_speed = speed

            # reset integrator to measured state
            self.previous_angle = angle
            self.previous_speed = speed
            self.previous_time = now
            self.angle = angle

            # print(angle, speed)

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

    # ----------------- Stimulation update ----------------- #
    def should_stimulation_be_active(self, onset: float, offset: float) -> bool:
        if onset < offset:
            # The range does not wrap around 0
            return (onset <= self.angle) and (self.angle <= offset)
        elif onset > offset:
            # The angle wraps around 0
            return not ((onset >= self.angle) and (self.angle >= offset))
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
            # cond = self.stim_condition[key]
            is_stimulation_active = self.stimulation_state[key]
            ch_idx = self.channel_number[key] - 1
            channel = self.list_channels[ch_idx]

            if self.angle > 360.0 or self.angle < 0:
                raise RuntimeError("EEEEEEEEEEEEEEror")

            # Range wraps around 360 (e.g., [220, 10])
            should_be_active = self.should_stimulation_be_active(onset, offset)
            print(
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
    Thread that:
      - keeps stimulation running continuously using a while-loop structure
      - whenever a new StimJob arrives, it:
          * applies the new parameters ONCE
          * collects data for an evaluation window (eval_duration_s)
          * computes a cost
          * sends StimResult back via callback

    Stimulation NEVER stops; only parameters and evaluation windows change.
    """

    def __init__(
        self,
        worker_pedal: Optional["PedalWorker"],
        # job_queue: "queue.Queue[Optional[StimJob]]",
        # stop_event: threading.Event,
        # result_callback: Callable[[StimResult], None],
        # data_collector: DataCollector = None,
        # eval_duration_s: float = 2.0,
        # name: str = "StimulationWorker",
    ):
        self._keep_running = True

        # self.job_queue = job_queue
        # self.stop_event = stop_event
        # self.result_callback = result_callback
        # self.data_collector = data_collector
        # self.eval_duration_s = eval_duration_s

        # Controller that runs continuously
        self.controller = HandCycling2(worker_pedal)

        # State for current BO evaluation
        self.current_job: Optional[StimJob] = None
        self.eval_start_time: Optional[float] = None
        # self.eval_buffer: List[Dict] = []

        # Worker that provides pedal data
        self.worker_pedal = worker_pedal
        # if self.worker_pedal is not None:
        #     # Register to receive real pedal samples
        #     self.worker_pedal.register_callback(self.handle_pedal_update)

    # def handle_pedal_update(self, angle: float, speed: float, power: float) -> None:
    #     """
    #     Very lightweight: just update the controller's sensor state.
    #     """
    #     self.controller.update_sensor(angle, speed)
    #     # self._last_power = power # If power in the cost

    def run(self) -> None:
        while self._keep_running:

            # Clear the data collector buffer
            # self.worker_pedal.data_collector.clear()
            # Apply parameters immediately and stimulation continues with new params
            # self.controller.apply_parameters(job.params)

            should_activate_stim, should_deactivate_stim = self.controller.update_stimulation_for_current_angle()
            if should_deactivate_stim or should_activate_stim:
                # Only call when intensity or pulse width changed
                # Start is misleading, it should be called update
                self.controller.stimulator.start_stimulation(
                    upd_list_channels=self.controller.list_channels
                )

            # if self.current_job is not None:
            #     # self.eval_buffer.append(measurement)
            #
            #     elapsed = time.time() - self.eval_start_time
            #     if elapsed >= self.eval_duration_s:
            #         self._finish_current_evaluation()

            time.sleep(0.001)

    def stop(self):
        self.controller.stimulator.pause_stimulation()
        self._keep_running = False


    # def _start_new_evaluation(self, job: StimJob) -> None:
    #     """
    #     Called when BO sends a new parameter set.
    #     """
    #     print(f"[StimulationWorker] Starting evaluation of job {job.job_id}")
    #     self.current_bo_job = job
    #     self.bo_eval_start_time = time.time()
    #     # self.eval_buffer = []
    #
    #     # Apply parameters immediately and stimulation continues with new params
    #     self.controller.apply_parameters(job.params)

    # def _finish_current_evaluation(self) -> None:
    #     """
    #     Compute cost from buffered data and report back to BO.
    #    """
    #     assert self.current_bo_job is not None
    #     job = self.current_bo_job
    #
    #     cost = self._compute_cost_from_buffer()
    #     # extra_data = {
    #     #     "num_samples": len(self.eval_buffer),
    #     # }
    #
    #     print(f"[StimulationWorker] Finished evaluation of job {job.job_id}")
    #     result = StimResult(job_id=job.job_id, cost=cost) # , extra_data=extra_data)
    #     self.result_callback(result)
    #
    #     # Keep stimulation running with last parameters, just end evaluation
    #     self.current_bo_job = None
    #     self.bo_eval_start_time = None
    #     # self.eval_buffer = []

    # # TODO: Replace this with a real cost function.
    # def _compute_cost_from_buffer(self) -> float:
    #    """
    #    Compute a scalar cost from the collected data during eval_duration_s.
    #    For now, it uses a dummy example based on angle variance.
    #    """
    #    def get_last_cycles_data(nb_cycles: int = 3) -> List[Dict]:
    #         """
    #         Extract the last nb_cycles from the data collector buffer.
    #         Each cycle is defined as angle going from 0° to 360°.
    #         """
    #         times_vector = self.data_collector.data.timestamp
    #         angles = self.data_collector.data.values[:, DataType.A18]
    #         left_power = self.data_collector.data.values[:, DataType.A36]
    #         right_power = self.data_collector.data.values[:, DataType.A37]
    #         total_power = self.data_collector.data.values[:, DataType.A38]
    #
    #         last_cycles_data = {
    #             "times_vector": [],
    #             "angles": [],
    #             "left_power": [],
    #             "right_power": [],
    #             "total_power": [],
    #         }
    #         last_idx = len(angles) - 1
    #         cycles_collected = 0
    #         last_bound = None
    #         while last_idx > 0 and cycles_collected < nb_cycles:
    #             current_angle = angles[last_idx]
    #             previous_angle = angles[last_idx - 1]
    #             nb_rotations = current_angle // (2 * np.pi)
    #             if np.sign(current_angle - (nb_rotations * 2 * np.pi)) != np.sign(previous_angle - (nb_rotations * 2 * np.pi)):
    #                 if last_bound is None:
    #                     # The end of the last cycle was detected
    #                     last_bound = last_idx
    #                 else:
    #                     # The beginning of this cycle was detected, extract data for this cycle
    #                     start_idx = last_idx
    #                     end_idx = last_bound
    #                     last_cycles_data["times_vector"].insert(0, times_vector[start_idx:end_idx])
    #                     last_cycles_data["angles"].insert(0, angles[start_idx:end_idx])
    #                     last_cycles_data["left_power"].insert(0, left_power[start_idx:end_idx])
    #                     last_cycles_data["right_power"].insert(0, right_power[start_idx:end_idx])
    #                     last_cycles_data["total_power"].insert(0, total_power[start_idx:end_idx])
    #                     last_bound = last_idx
    #
    #             cycles_collected = len(last_cycles_data["times_vector"])
    #             last_idx -= 1
    #
    #         return last_cycles_data

    #     def get_cost_value(last_cycles_data: Dict[str, list[np.ndarray]]) -> float:
    #
    #         # Maximize power
    #         left_power = np.hstack(last_cycles_data["left_power"])
    #         right_power = np.hstack(last_cycles_data["right_power"])
    #         total_left_power = -np.sum(left_power ** 2)
    #         total_right_power = -np.sum(right_power ** 2)
    #
    #         # Minimize stimulation intensity
    #         right_intensity = self.controller.intensity["biceps_r"]** 2 + self.controller.intensity["triceps_r"]** 2
    #         left_intensity = self.controller.intensity["biceps_l"]** 2 + self.controller.intensity["triceps_l"]** 2
    #
    #         cost = total_left_power + total_right_power + 0.1 * (right_intensity + left_intensity)
    #         return float(cost)
    #
    #     last_cycles_data = get_last_cycles_data()
    #     cost = get_cost_value(last_cycles_data)
    #
    #     return cost
