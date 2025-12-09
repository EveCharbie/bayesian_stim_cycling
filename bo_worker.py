from __future__ import annotations

import threading
from typing import Dict, List
import time
import pickle

import numpy as np
from skopt import gp_minimize
from skopt.space import Real

from pedal_worker import PedalWorker
from stim_worker import StimulationWorker
from common_types import StimParameters
from live_plotter import LivePlotter
from constants import MUSCLE_KEYS, PARAMS_BOUNDS
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
        worker_plot: LivePlotter,
        nb_cycles_to_run: int = 5,
        nb_cycles_to_keep: int = 3,
        really_change_stim_intensity: bool = True,
    ):
        # self.job_queue = job_queue
        self.stop_event = stop_event
        self.nb_cycles_to_run = nb_cycles_to_run
        self.nb_cycles_to_keep = nb_cycles_to_keep

        # Flag to stop the thread
        self._keep_running = True

        # Worker that provides pedal data
        self.worker_pedal = worker_pedal

        # Worker that handles stimulation
        self.worker_stim = worker_stim

        # Worker that handles live plotting
        self.worker_plot = worker_plot

        self.space = None
        self.build_search_space()

        # Store the iterations
        self.cost_list: list[float] = []
        self.parameter_list: list[StimParameters] = []
        self._result_lock = threading.Lock()
        self._result_available = threading.Condition(self._result_lock)

        self.best_result = None  # will hold gp_minimize's result

        # Debugging flag to avoid large stim during tests
        self.really_change_stim_intensity = really_change_stim_intensity

    def build_search_space(self):
        """
        Create skopt search space: 4 parameters × 4 muscles = 16 dimensions.
        """
        space: List[Real] = []
        for muscle in MUSCLE_KEYS:
            for param_name in PARAMS_BOUNDS.keys():
                low, high = PARAMS_BOUNDS[param_name]
                dim_name = f"{param_name}_{muscle}"
                space.append(Real(low, high, name=dim_name))
        self.space = space

    def get_num_cycles(self) -> int:
        """
        Count the number of complete cycles in the data collector buffer.
        Each cycle is defined as angle going from 0° to 360°.
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
                    last_cycles_data["angles"].insert(0, angles[start_idx:end_idx])
                    last_cycles_data["left_power"].insert(0, left_power[start_idx:end_idx])
                    last_cycles_data["right_power"].insert(0, right_power[start_idx:end_idx])
                    last_cycles_data["total_power"].insert(0, total_power[start_idx:end_idx])
                    last_bound = last_idx

            cycles_identified = len(last_cycles_data["times_vector"])
            last_idx -= 1

        return last_cycles_data

    def get_cost_value(self, last_cycles_data: Dict[str, list[np.ndarray]]) -> float:
        # Maximize power
        left_power = np.hstack(last_cycles_data["left_power"])
        right_power = np.hstack(last_cycles_data["right_power"])
        total_left_power = -np.sum(left_power ** 2)
        total_right_power = -np.sum(right_power ** 2)

        # Minimize stimulation intensity
        right_intensity = self.worker_stim.controller.intensity["biceps_r"] ** 2
        #                    + self.worker_stim.controller.intensity["triceps_r"] ** 2)
        # left_intensity = self.worker_stim.controller.intensity["biceps_l"] ** 2 + \
        #                  self.worker_stim.controller.intensity["triceps_l"] ** 2

        cost = total_left_power + total_right_power + 0.1 * (right_intensity)
        return float(cost)

    def _objective(self, x: List[float]) -> float:
        """
        Objective passed to gp_minimize.
        x is a flat vector of stimulation parameters.
        """
        # Get the current parameters
        params = StimParameters.from_flat_vector(x)
        parameters = params.add_angles_offset()
        print("[BO WORKER] Evaluating parameters:", parameters)
        
        # Update the stimulation worker with new parameters
        self.worker_stim.controller.apply_parameters(parameters, self.really_change_stim_intensity)
        print("[BO WORKER] Applied new stimulation parameters.")
        
        # Clear the data collector buffer to start fresh
        self.worker_pedal.data_collector.clear()

        # Wait until a few cycles have been collected
        while self.get_num_cycles() < self.nb_cycles_to_run:
            time.sleep(0.1)
        print("[BO WORKER] Required number of cycles collected.")

        # Get cost value
        last_cycles_data = self.get_last_cycles_data()
        cost = self.get_cost_value(last_cycles_data)
        print(f"[BO WORKER] Cost evaluated: {cost}")

        # Update results and live plotter
        self.cost_list.append(cost)
        self.parameter_list.append(params)
        self.worker_plot.update_data(self.cost_list, self.parameter_list)

        return cost

    def save_results(self) -> None:
        """
        Save the BO results to a file.
        """
        results = {
            "best_result": self.best_result,
            "cost_list": self.cost_list,
            "parameter_list": self.parameter_list,
        }
        with open("bo_results.pkl", "wb") as f:
            pickle.dump(results, f)
        print("[BO WORKER] Results saved to bo_results.pkl.")

    def run(self) -> None:
        """
        Main BO routine. Runs in a separate thread.
        """
        print("[BO WORKER] Starting Bayesian optimization with continuous stimulation...")

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
            objective_func=self._objective,
            xi=0.01,
            length_scale=1.0,
        )
        self.best_result = bayesian_optimizer.optimize(
            n_iterations=20, 
            n_initial_steps=8, 
            verbose=True,
        )

        print("[BO WORKER] Optimization finished.")
        print("[BO WORKER] Best parameters (flat vector):", self.best_result.x)
        print("[BO WORKER] Best cost:", self.best_result.fun)

        self.save_results()
