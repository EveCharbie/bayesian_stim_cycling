from pathlib import Path
import threading
import time

import numpy as np
import matplotlib

matplotlib.use("TkAgg")  # or 'Qt5Agg'
import matplotlib.pyplot as plt

from common_types import StimParameters
from constants import PARAMS_BOUNDS, MUSCLE_KEYS


class LivePlotter:
    """Separate class to handle live plotting in a thread"""

    def __init__(self):
        self.fig = None
        self.axs = None
        self.thread = None
        # Flag to stop the thread
        self._keep_running = True
        self.lock = threading.Lock()

        # Data to plot
        self.costs = None
        self.parameters = None

    def stop(self):
        """Stop the plotting thread"""
        self._keep_running = False
        if self.thread:
            self.thread.join()

    def update_data(self, cost_list: list[float], parameter_list: list[StimParameters]):
        """Thread-safe data update"""
        with self.lock:
            self.costs = np.array(cost_list)
            parameters_array = np.empty((0, len(PARAMS_BOUNDS.keys())))
            for param in parameter_list:
                parameters_array = np.vstack((parameters_array, param.to_flat_vector()))
            self.parameters = parameters_array

    def _initialize_plots(self):
        """Initialize the plot window"""
        n_muscles = len(MUSCLE_KEYS)
        self.fig, self.axs = plt.subplots(n_muscles, 3, figsize=(12, 8))
        plt.ion()

        for i_muscle in range(n_muscles):
            self.axs[i_muscle, 0].set_title("Onset")
            self.axs[i_muscle, 1].set_title("Offset")
            self.axs[i_muscle, 2].set_title("Intensity")

    def run(self):
        """Main plotting loop"""
        self._initialize_plots()

        while self._keep_running:
            with self.lock:
                self._update_plots()

            self.fig.canvas.draw()
            self.fig.canvas.flush_events()
            plt.pause(0.1)

        plt.ioff()

    def _update_plots(self) -> None:
        """Update all plots with current data"""

        if self.costs is None or self.parameters is None:
            # Wait for data to be collected
            time.sleep(0.1)
            return
        else:
            # Clear all axes
            for ax in self.axs.flat:
                ax.cla()

            colors = np.arange(100)[:len(self.costs)]
            # print(self.costs)
            # print(self.parameters)

            i_param = 0
            n_muscles = len(MUSCLE_KEYS)
            for i_muscle in range(n_muscles):
                self.axs[i_muscle, 0].scatter(self.parameters[:, i_param], self.costs, c=colors, cmap="viridis")
                self.axs[i_muscle, 0].plot(self.parameters[-1, i_param], self.costs[-1], "kx")
                self.axs[i_muscle, 0].set_title("Onset")
                # self.axs[i_muscle, 0].set_xlim(STIMULATION_RANGE["biceps_r"][0] + PARAMS_BOUNDS["onset_deg"][0], STIMULATION_RANGE["biceps_r"][0] + PARAMS_BOUNDS["onset_deg"][1])
                self.axs[i_muscle, 0].set_xlim(PARAMS_BOUNDS["onset_deg"][0], PARAMS_BOUNDS["onset_deg"][1])
                i_param += 1

                self.axs[i_muscle, 1].scatter(self.parameters[:, i_param], self.costs, c=colors, cmap="viridis")
                self.axs[i_muscle, 1].plot(self.parameters[-1, i_param], self.costs[-1], "kx")
                self.axs[i_muscle, 1].set_title("Offset")
                # self.axs[i_muscle, 1].set_xlim(STIMULATION_RANGE["biceps_r"][1] + PARAMS_BOUNDS["offset_deg"][0], STIMULATION_RANGE["biceps_r"][1] + PARAMS_BOUNDS["offset_deg"][1])
                self.axs[i_muscle, 1].set_xlim(PARAMS_BOUNDS["offset_deg"][0], PARAMS_BOUNDS["offset_deg"][1])
                i_param += 1

                self.axs[i_muscle, 2].scatter(self.parameters[:, i_param], self.costs, c=colors, cmap="viridis")
                self.axs[i_muscle, 2].plot(self.parameters[-1, i_param], self.costs[-1], "kx")
                self.axs[i_muscle, 2].set_title("Intensity")
                self.axs[i_muscle, 2].set_xlim(PARAMS_BOUNDS["pulse_intensity"][0], PARAMS_BOUNDS["pulse_intensity"][1])
                i_param += 1

            time.sleep(0.1)
            return


    def save_figure(self):
        """Save the current figure"""
        if self.fig:
            current_path = Path(__file__).parent
            spline_fig_path = f"{current_path}/figures/results.png"
            self.fig.savefig(spline_fig_path)
