from __future__ import annotations

import logging
import threading
from typing import Dict, List, Callable
import time
import pickle

import numpy as np
# from skopt import gp_minimize
from skopt.space import Real

from pedal_worker import PedalWorker
from stim_worker import StimulationWorker
from common_types import StimParameters
from live_plotter import LivePlotter
from constants import MUSCLE_KEYS, PARAMS_BOUNDS, CUTOFF_ANGLES
from bayesian_optimizer import BayesianOptimizer

from pedal_communication.data.data import DataType


class BayesianOptimizationWorker:
    """
    Thread that runs Bayesian optimization and requests trials from
    the stimulation worker via a queue.

    Stimulation is continuous; each BO evaluation is:
      - send new StimParameters
      - wait for cost from stim thread
    """

    def __init__(
        self,
        stop_event: threading.Event,
        worker_pedal: PedalWorker,
        worker_stim: StimulationWorker,
        nb_cycles_to_run: int = 5,
        nb_cycles_to_keep: int = 3,
        nb_initialization_cycles: int = 8,
        really_change_stim_intensity: bool = True,
        worker_plot: LivePlotter = None,
    ):
        # self.job_queue = job_queue
        self.stop_event = stop_event
        self.nb_cycles_to_run = nb_cycles_to_run
        self.nb_cycles_to_keep = nb_cycles_to_keep
        self.nb_initialization_cycles = nb_initialization_cycles

        # Flag to stop the thread
        self._keep_running = True

        # Worker that provides pedal data
        self.worker_pedal = worker_pedal

        # Worker that handles stimulation
        self.worker_stim = worker_stim

        # Worker that handles live plotting
        self.worker_plot = worker_plot

        self.space: dict[str, list[Real]] = {key: [] for key in MUSCLE_KEYS}
        self.build_search_space()

        # Store the iterations
        self.cost_dict: dict[str, list[float]] = {key: [] for key in MUSCLE_KEYS}
        self.parameter_list: list[StimParameters] = []
        self._result_lock = threading.Lock()
        self._result_available = threading.Condition(self._result_lock)

        self.best_result_dict: dict[str, float] = {key: None for key in MUSCLE_KEYS}  # will hold gp_minimize's result

        # Debugging flag to avoid large stim during tests
        self.really_change_stim_intensity = really_change_stim_intensity

        # cost functions for each muscle
        self.cost_function: dict[str, Callable] = {
            "biceps_r": self._biceps_r_cost,
            "triceps_r": self._triceps_r_cost,
            "biceps_l": self._biceps_l_cost,
            "triceps_l": self._triceps_l_cost,
        }

        # Logging
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        )
        self._logger = logging.getLogger("BayesianOptimizationWorker")

    def build_search_space(self):
        """
        Create skopt search space: 4 parameters × 4 muscles = 16 dimensions.
        """
        for muscle in MUSCLE_KEYS:
            for param_name in PARAMS_BOUNDS[muscle].keys():
                low, high = PARAMS_BOUNDS[muscle][param_name]
                dim_name = f"{param_name}_{muscle}"
                self.space[muscle].append(Real(low, high, name=dim_name))

    def get_num_cycles(self) -> int:
        """
        Count the number of complete cycles in the data collector buffer.
        Each cycle is defined as angle going from -90° to 270°.
        """
        angles = self.worker_pedal.data_collector.data.values[:, DataType.A18.value]
        num_cycles = 0
        for i in range(1, len(angles)):
            current_angle = angles[i]
            previous_angle = angles[i - 1]
            nb_rotations = current_angle // (2 * np.pi)
            if np.sign(current_angle - (nb_rotations * 2 * np.pi)) != np.sign(
                    previous_angle - (nb_rotations * 2 * np.pi)):
                num_cycles += 1
        return num_cycles

    def get_last_cycles_data(self) -> Dict[str, list[np.ndarray]]:
        """
        Extract the last nb_cycles from the data collector buffer.
        Each cycle is defined as angle going from 0° to 360°.
        TODO: this piece of code is very similar to the one in pedal_worker, refactor it.
        """
        times_vector = self.worker_pedal.data_collector.data.timestamp
        angles = self.worker_pedal.data_collector.data.values[:, DataType.A18.value]
        left_power = self.worker_pedal.data_collector.data.values[:, DataType.A36.value]
        right_power = self.worker_pedal.data_collector.data.values[:, DataType.A37.value]
        total_power = self.worker_pedal.data_collector.data.values[:, DataType.A38.value]

        last_cycles_data = {
            "times_vector": [],
            "angles": [],
            "left_power": [],
            "right_power": [],
            "total_power": [],
        }
        last_idx = len(angles) - 1
        cycles_identified = 0
        last_bound = None
        while last_idx > 0 and cycles_identified < self.nb_cycles_to_keep:
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
                    last_cycles_data["times_vector"].insert(0, times_vector[start_idx:end_idx])
                    last_cycles_data["angles"].insert(0, self.worker_pedal.rotated_angle(angles[start_idx:end_idx]))
                    last_cycles_data["left_power"].insert(0, left_power[start_idx:end_idx])
                    last_cycles_data["right_power"].insert(0, right_power[start_idx:end_idx])
                    last_cycles_data["total_power"].insert(0, total_power[start_idx:end_idx])
                    last_bound = last_idx

            cycles_identified = len(last_cycles_data["times_vector"])
            last_idx -= 1

        return last_cycles_data

    # def get_cost_value(self, last_cycles_data: Dict[str, list[np.ndarray]]) -> float:
    #     # Maximize power
    #     left_power = np.hstack(last_cycles_data["left_power"])
    #     right_power = np.hstack(last_cycles_data["right_power"])
    #     total_left_power = -np.sum(left_power ** 2)
    #     total_right_power = -np.sum(right_power ** 2)
    #
    #     # Minimize stimulation intensity
    #     right_intensity = (
    #             self.worker_stim.controller.intensity["biceps_r"] ** 2 +
    #             self.worker_stim.controller.intensity["triceps_r"] ** 2
    #     )
    #     left_intensity = (
    #             self.worker_stim.controller.intensity["biceps_l"] ** 2 +
    #             self.worker_stim.controller.intensity["triceps_l"] ** 2
    #     )
    #
    #     cost = total_left_power + total_right_power + 0.1 * (right_intensity + left_intensity)
    #     return float(cost)

    def _biceps_r_cost(self, last_cycles_data: Dict[str, list[np.ndarray]]) -> float:
        # Angles
        angles = np.hstack(last_cycles_data["angles"])
        if np.any(angles < 0) or np.any(angles > 2*np.pi):
            raise RuntimeError("Something went wrong with angle wrapping, angles should be in [0, 2pi]")

        lower_bound = np.radians(CUTOFF_ANGLES["right"][0])
        upper_bound = np.radians(CUTOFF_ANGLES["right"][1])
        angles_in_range_indices = np.where(
            np.logical_and(
                lower_bound < angles,
                angles < upper_bound,
            )
        )

        if len(angles_in_range_indices) > 0:
            angles_in_range_indices = angles_in_range_indices[0]
            # print("biceps r", angles_in_range_indices.shape[0], " / ", angles.shape[0])

        # Maximize power
        right_power = np.hstack(last_cycles_data["right_power"])[angles_in_range_indices]
        power = -np.sum(right_power ** 2)

        # Minimize stimulation intensity
        intensity = self.worker_stim.controller.intensity["biceps_r"] ** 2

        cost = power + 0.05 * intensity
        # print("biceps r cost:", cost)
        return float(cost)

    def _triceps_r_cost(self, last_cycles_data: Dict[str, list[np.ndarray]]) -> float:
        # Angles
        angles = np.hstack(last_cycles_data["angles"])
        if np.any(angles < 0) or np.any(angles > 2 * np.pi):
            raise RuntimeError("Something went wrong with angle wrapping, angles should be in [0, 2pi]")

        lower_bound = np.radians(CUTOFF_ANGLES["right"][1])
        upper_bound = np.radians(CUTOFF_ANGLES["right"][0])
        angles_in_range_indices = np.where(
            np.logical_not(
                np.logical_and(
                    angles < lower_bound,
                    upper_bound < angles,
                )
            )
        )

        if len(angles_in_range_indices) > 0:
            angles_in_range_indices = angles_in_range_indices[0]
            # print("triceps r", angles_in_range_indices.shape[0], " / ", angles.shape[0])

        # Maximize power
        right_power = np.hstack(last_cycles_data["right_power"])[angles_in_range_indices]
        power = -np.sum(right_power ** 2)

        # Minimize stimulation intensity
        intensity = self.worker_stim.controller.intensity["triceps_r"] ** 2

        cost = power + 0.05 * intensity
        # print("triceps r cost:", cost)
        return float(cost)

    def _biceps_l_cost(self, last_cycles_data: Dict[str, list[np.ndarray]]) -> float:
        # Angles
        angles = np.hstack(last_cycles_data["angles"])
        if np.any(angles < 0) or np.any(angles > 2 * np.pi):
            raise RuntimeError("Something went wrong with angle wrapping, angles should be in [0, 2pi]")
        lower_bound = np.radians(CUTOFF_ANGLES["left"][1])
        upper_bound = np.radians(CUTOFF_ANGLES["left"][0])
        angles_in_range_indices = np.where(
            np.logical_not(
                np.logical_and(
                    angles < lower_bound,
                    upper_bound < angles,
                )
            )
        )

        if len(angles_in_range_indices) > 0:
            angles_in_range_indices = angles_in_range_indices[0]
            # print("biceps l", angles_in_range_indices.shape[0], " / ", angles.shape[0])

        # Maximize power
        left_power = np.hstack(last_cycles_data["left_power"])[angles_in_range_indices]
        power = -np.sum(left_power ** 2)

        # Minimize stimulation intensity
        intensity = self.worker_stim.controller.intensity["biceps_l"] ** 2

        cost = power + 0.05 * intensity
        # print("biceps l cost:", cost)
        return float(cost)

    def _triceps_l_cost(self, last_cycles_data: Dict[str, list[np.ndarray]]) -> float:
        # Angles
        angles = np.hstack(last_cycles_data["angles"])
        if np.any(angles < 0) or np.any(angles > 2 * np.pi):
            raise RuntimeError("Something went wrong with angle wrapping, angles should be in [0, 2pi]")

        lower_bound = np.radians(CUTOFF_ANGLES["left"][0])
        upper_bound = np.radians(CUTOFF_ANGLES["left"][1])
        angles_in_range_indices = np.where(
            np.logical_and(
                lower_bound < angles,
                angles < upper_bound,
            )
        )
        if len(angles_in_range_indices) > 0:
            angles_in_range_indices = angles_in_range_indices[0]
            # print("triceps l", angles_in_range_indices.shape[0], " / ", angles.shape[0])

        # Maximize power
        left_power = np.hstack(last_cycles_data["left_power"])[angles_in_range_indices]
        power = -np.sum(left_power ** 2)

        # Minimize stimulation intensity
        intensity = self.worker_stim.controller.intensity["triceps_l"] ** 2

        cost = power + 0.05 * intensity
        # print("triceps l cost:", cost)
        return float(cost)

    # def _objective(self, x: List[float]) -> float:
    #     """
    #     Objective passed to gp_minimize.
    #     x is a flat vector of stimulation parameters.
    #     """
    #     # Get the current parameters
    #     params = StimParameters.from_flat_vector(x)
    #    parameters = params.add_angles_offset()
    #     print("[BO WORKER] Evaluating parameters:", parameters)
    #
    #    # Update the stimulation worker with new parameters
    #     self.worker_stim.controller.apply_parameters(parameters, self.really_change_stim_intensity)
    #     print("[BO WORKER] Applied new stimulation parameters.")
    #
    #     # Clear the data collector buffer to start fresh
    #     self.worker_pedal.data_collector.clear()
    #
    #     # Wait until a few cycles have been collected
    #     while self.get_num_cycles() < self.nb_cycles_to_run:
    #         time.sleep(0.1)
    #     print("[BO WORKER] Required number of cycles collected.")
    #
    #     # Get cost value
    #     last_cycles_data = self.get_last_cycles_data()
    #     cost = self.get_cost_value(last_cycles_data)
    #     print(f"[BO WORKER] Cost evaluated: {cost}")
    #
    #     # Update results and live plotter
    #     self.cost_list.append(cost)
    #     self.parameter_list.append(params)
    #     self.worker_plot.update_data(self.cost_list, self.parameter_list)
    #
    #     return cost

    def _make_an_interation(self, x: List[float]) -> list[float]:
        """
        Send the stimulation parameters to the subject, measure the cost, and return it.
        The parameters for all four muscles are tested at the same time.
        x is a flat vector of stimulation parameters.
        """
        # Get the current parameters
        params = StimParameters.from_flat_vector(x)
        parameters = params.add_angles_offset()
        self._logger.info(f"Evaluating parameters: {parameters}")

        # Update the stimulation worker with new parameters
        self.worker_stim.controller.apply_parameters(parameters, self.really_change_stim_intensity)
        self._logger.info(f"Applied new stimulation parameters.")

        # Clear the data collector buffer to start fresh
        self.worker_pedal.data_collector.clear()

        # Wait until a few cycles have been collected
        while self.get_num_cycles() < self.nb_cycles_to_run:
            time.sleep(0.1)
        self._logger.info(f"Required number of cycles collected.")

        # Get cost value
        last_cycles_data = self.get_last_cycles_data()
        cost_list = []
        for muscle in MUSCLE_KEYS:
            cost = self.cost_function[muscle](last_cycles_data)
            cost_list += [cost]

            # Update results and live plotter
            self.cost_dict[muscle].append(cost)
        self.parameter_list.append(params)
        if self.worker_plot is not None:
            self.worker_plot.update_data(self.cost_dict, self.parameter_list)

        return cost_list

    def save_results(self) -> None:
        """
        Save the BO results to a file.
        """
        results = {
            "best_params": [self.best_result_dict[muscle] for muscle in MUSCLE_KEYS],
            "best_cost": [self.best_result_dict[muscle] for muscle in MUSCLE_KEYS],
            "cost_list": self.cost_dict,
            "parameter_list": self.parameter_list,
        }
        with open("bo_results.pkl", "wb") as f:
            pickle.dump(results, f)
        self._logger.info(f"Results saved to bo_results.pkl.")

    def run(self) -> None:
        """
        Main BO routine. Runs in a separate thread.
        """
        self._logger.info(f"Starting Bayesian optimization with continuous stimulation...")


        # self.best_result = gp_minimize(
        #     func=self._objective,
        #     dimensions=self.space,
        #     n_calls=100,  # 6,
        #     n_initial_points=6,
        #     acq_func="PI",  # "LCB", "EI", "PI", "gp_hedge", "EIps", "PIps"
        #     kappa=5,  # *
        #     random_state=0,
        #     n_jobs=1,
        # )  # x0, y0, kappa[exploitation, exploration], xi [minimal improvement default 0.01]

        bayesian_optimizer = BayesianOptimizer(
            iteration_func=self._make_an_interation,
            xi=0.01,
            length_scale=1.0,
        )
        self.best_result_dict = bayesian_optimizer.optimize(
            n_iterations=75,
            nb_initialization_cycles=self.nb_initialization_cycles,
        )

        self._logger.info(f"Optimization finished.")
        self.save_results()
        self.worker_stim.stop()
