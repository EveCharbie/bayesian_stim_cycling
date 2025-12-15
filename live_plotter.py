from pathlib import Path
import threading
import time

import numpy as np
import matplotlib

matplotlib.use("TkAgg")  # or 'Qt5Agg'
import matplotlib.pyplot as plt

from common_types import StimParameters, MuscleMode
from constants import PARAMS_BOUNDS, STIMULATION_RANGE


class LivePlotter:
    """Separate class to handle live plotting in a thread"""

    def __init__(self, muscle_mode:MuscleMode.BICEPS_TRICEPS | MuscleMode.DELTOIDS):

        self.muscle_mode =muscle_mode

        self.fig_optim = None
        self.axs_optim = None
        self.fig_power = None
        self.axs_power = None
        self.thread = None
        # Flag to stop the thread
        self._keep_running = True
        self._lock = threading.Lock()

        # Data to plot
        self.costs: dict[str, list[float]] = {muscle: [] for muscle in self.muscle_mode.muscle_keys}
        self.parameters: list[StimParameters] = []
        self.angles = []
        self.left_powers = []
        self.right_powers = []

    def stop(self):
        """Stop the plotting thread"""
        self._keep_running = False
        if self.thread:
            self.thread.join()

    def update_data(self, cost_dict: dict[str, list[float]], parameter_list: list[StimParameters]):
        """Thread-safe data update"""
        with self._lock:
            for muscle in self.muscle_mode.muscle_keys:
                self.costs[muscle] = np.array(cost_dict[muscle])
            parameters_array = np.empty((0, len(PARAMS_BOUNDS["biceps_r"].keys()) * len(self.muscle_mode.muscle_keys)))
            for param in parameter_list:
                parameters_array = np.vstack((parameters_array, param.to_flat_vector()))
            self.parameters = parameters_array

    def add_pedal_data_points(self, angle: float, left_power: float, right_power: float):
        """Add new pedal data points"""
        with self._lock:
            self.angles.append(angle)
            self.left_powers.append(left_power)
            self.right_powers.append(right_power)

    def _initialize_plots(self):
        """Initialize the plot window"""
        n_muscles = len(self.muscle_mode.muscle_keys)
        self.fig_optim, self.axs_optim = plt.subplots(n_muscles, 3, figsize=(12, 8))
        plt.ion()

        for i_muscle in range(n_muscles):
            self.axs_optim[i_muscle, 0].set_title("Onset")
            self.axs_optim[i_muscle, 1].set_title("Offset")
            self.axs_optim[i_muscle, 2].set_title("Intensity")

        self.fig_power, self.axs_power = plt.subplots(1, 2, figsize=(8, 4), subplot_kw={'projection': 'polar'})
        plt.ion()

        self.axs_power[0].set_title("Left Power")
        self.axs_power[1].set_title("Right Power")

    def run(self):
        """Main plotting loop"""
        self._initialize_plots()

        while self._keep_running:
            with self._lock:
                self._update_plots()

            self.fig_optim.canvas.draw()
            self.fig_optim.canvas.flush_events()
            self.fig_power.canvas.draw()
            self.fig_power.canvas.flush_events()
            plt.pause(0.1)

        plt.ioff()

    def _update_plots(self) -> None:
        """Update all plots with current data"""

        if len(self.costs[self.muscle_mode.muscle_keys[0]]) == 0 or len(self.parameters) == 0:
            # Wait for data to be collected
            time.sleep(0.05)
        else:
            # Clear all axes
            for ax in self.axs_optim.flat:
                ax.cla()

            colors = np.arange(100)[:len(self.costs[self.muscle_mode.muscle_keys[0]])]
            # print(self.costs)
            # print(self.parameters)

            i_param = 0
            for i_muscle, muscle in enumerate(self.muscle_mode.muscle_keys):
                self.axs_optim[i_muscle, 0].scatter(self.parameters[:, i_param], self.costs[muscle], c=colors, cmap="viridis")
                self.axs_optim[i_muscle, 0].plot(self.parameters[-1, i_param], self.costs[muscle][-1], "kx")
                self.axs_optim[i_muscle, 0].set_title("Onset")
                # self.axs_optim[i_muscle, 0].set_xlim(STIMULATION_RANGE["biceps_r"][0] + PARAMS_BOUNDS["onset_deg"][0], STIMULATION_RANGE["biceps_r"][0] + PARAMS_BOUNDS["onset_deg"][1])
                self.axs_optim[i_muscle, 0].set_xlim(PARAMS_BOUNDS[muscle]["onset_deg"][0], PARAMS_BOUNDS[muscle]["onset_deg"][1])
                i_param += 1

                self.axs_optim[i_muscle, 1].scatter(self.parameters[:, i_param], self.costs[muscle], c=colors, cmap="viridis")
                self.axs_optim[i_muscle, 1].plot(self.parameters[-1, i_param], self.costs[muscle][-1], "kx")
                self.axs_optim[i_muscle, 1].set_title("Offset")
                # self.axs_optim[i_muscle, 1].set_xlim(STIMULATION_RANGE["biceps_r"][1] + PARAMS_BOUNDS["offset_deg"][0], STIMULATION_RANGE["biceps_r"][1] + PARAMS_BOUNDS["offset_deg"][1])
                self.axs_optim[i_muscle, 1].set_xlim(PARAMS_BOUNDS[muscle]["offset_deg"][0], PARAMS_BOUNDS[muscle]["offset_deg"][1])
                i_param += 1

                self.axs_optim[i_muscle, 2].scatter(self.parameters[:, i_param], self.costs[muscle], c=colors, cmap="viridis")
                self.axs_optim[i_muscle, 2].plot(self.parameters[-1, i_param], self.costs[muscle][-1], "kx")
                self.axs_optim[i_muscle, 2].set_title("Intensity")
                self.axs_optim[i_muscle, 2].set_xlim(PARAMS_BOUNDS[muscle]["pulse_intensity"][0], PARAMS_BOUNDS[muscle]["pulse_intensity"][1])
                i_param += 1
            self.fig_optim.tight_layout()
            time.sleep(0.1)

        if len(self.angles) == 0 or len(self.left_powers) == 0 or len(self.right_powers) == 0:
            # Wait for data to be collected
            time.sleep(0.1)
        else:
            # Clear all axes
            for ax in self.axs_power:
                ax.cla()

            # Add the ranges for stimulation
            self.axs_power[1].fill_between(
                np.linspace(
                    np.radians(STIMULATION_RANGE[self.muscle_mode.muscle_keys[0]][0]),
                    np.radians(STIMULATION_RANGE[self.muscle_mode.muscle_keys[0]][1]),
                    10
                ),
                0,  # Fill from radius 0
                1000000,  # To radius 1
                color='m',
                alpha=0.3,
            )
            self.axs_power[1].fill_between(
                np.linspace(
                    np.radians(STIMULATION_RANGE[self.muscle_mode.muscle_keys[1]][0]),
                    2 * np.pi,
                    10),
                0,  # Fill from radius 0
                1000000,  # To radius 1
                color='c',
                alpha=0.3,
            )
            self.axs_power[1].fill_between(
                np.linspace(
                    0,
                    np.radians(STIMULATION_RANGE[self.muscle_mode.muscle_keys[1]][1]),
                    10
                ),
                0,  # Fill from radius 0
                1000000,  # To radius 1
                color='c',
                alpha=0.3,
            )
            self.axs_power[0].fill_between(
                np.linspace(
                    np.radians(STIMULATION_RANGE[self.muscle_mode.muscle_keys[2]][0]),
                    2 * np.pi,
                    10
                ),
                0,  # Fill from radius 0
                1000000,  # To radius 1
                color='m',
                alpha=0.3,
                label='Biceps'
            )
            self.axs_power[0].fill_between(
                np.linspace(
                    0,
                    np.radians(STIMULATION_RANGE[self.muscle_mode.muscle_keys[2]][1]),
                    10
                ),
                0,  # Fill from radius 0
                1000000,  # To radius 1
                color='m',
                alpha=0.3,
            )
            self.axs_power[0].fill_between(
                np.linspace(
                    np.radians(STIMULATION_RANGE[self.muscle_mode.muscle_keys[3]][0]),
                    np.radians(STIMULATION_RANGE[self.muscle_mode.muscle_keys[3]][1]),
                    10
                ),
                0,  # Fill from radius 0
                1000000,  # To radius 1
                color='c',
                alpha=0.3,
                label='Triceps'
            )
            self.axs_power[0].plot(np.array([105, 105]) * np.pi / 180, [0, 1e6], 'k--', label='Power split')
            self.axs_power[0].plot(np.array([290, 290]) * np.pi / 180, [0, 1e6], 'k--')
            self.axs_power[1].plot(np.array([110, 110]) * np.pi / 180, [0, 1e6], 'k--')
            self.axs_power[1].plot(np.array([285, 285]) * np.pi / 180, [0, 1e6], 'k--')

            # Add the power vs angle plots
            angles_rad = np.radians(self.angles)
            self.axs_power[0].plot(angles_rad, self.left_powers, 'tab:red')
            self.axs_power[1].plot(angles_rad, self.right_powers, 'tab:red')

            # Fix the limits of the polar plots
            self.axs_power[0].set_ylim(0, max(self.left_powers) * 1.1)
            self.axs_power[1].set_ylim(0, max(self.right_powers) * 1.1)
            self.axs_power[0].legend()
            self.axs_power[0].set_title("Left Power")
            self.axs_power[1].set_title("Right Power")

            time.sleep(0.1)


    def save_figure(self):
        """Save the current figure"""
        if self.fig_optim:
            current_path = Path(__file__).parent
            spline_fig_path = f"{current_path}/figures/results.png"
            self.fig_optim.savefig(spline_fig_path)
