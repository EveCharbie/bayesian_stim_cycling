from typing import Callable
import logging

import numpy as np
from scipy.stats import norm
from scipy.optimize import minimize
from scipy.spatial.distance import cdist

from common_types import MuscleMode
from constants import PARAMS_BOUNDS


class OptimizationResults:
    """Class mocking the optimization results from scipy."""

    def __init__(self, best_x: np.ndarray, best_y: float):
        self.best_x = best_x
        self.best_y = best_y

    @property
    def x(self) -> np.ndarray:
        return self.best_x

    @property
    def fun(self) -> float:
        return self.best_y

class GaussianProcess:
    """
    Simple Gaussian Process.
    It uses a Radial Basis Function kernel to estimate the covariance.
    """

    def __init__(self, length_scale: float = 1.0, noise: float = 1e-6):
        """
        Parameters
        ----------
        length_scale: Kernel length scale. It controls how quickly the correlation decays with distance.
        noise: Noise level added to the diagonal of the covariance matrix for numerical stability. 
        """
        self.length_scale = length_scale
        self.noise = noise
        self.input_training_data = None
        self.output_training_data = None
        self.K_inv = None

    def rbf_kernel(self, x_1: np.ndarray, x_2: np.ndarray) -> np.ndarray:
        """Radial Basis Function (squared exponential) kernel."""
        dists = cdist(x_1, x_2, metric='sqeuclidean')
        return np.exp(-0.5 * dists / (self.length_scale ** 2))

    def fit(self, input_data: np.ndarray, output_data: np.ndarray) -> None:
        """Fit the GP to training data."""
        self.input_training_data = np.array(input_data)
        self.output_training_data = np.array(output_data).flatten()

        K = self.rbf_kernel(self.input_training_data, self.input_training_data)
        K += self.noise * np.eye(len(self.input_training_data))

        self.K_inv = np.linalg.inv(K)

    def predict(self, test_data: np.ndarray) -> tuple[np.ndarray, np.ndarray]:
        """Predict mean and standard deviation at X."""
        test_data = np.array(test_data)
        if test_data.ndim == 1:
            test_data = test_data.reshape(1, -1)

        K_star = self.rbf_kernel(test_data, self.input_training_data)
        K_star_star = self.rbf_kernel(test_data, test_data)

        # Mean prediction
        mean = K_star @ self.K_inv @ self.output_training_data

        # Variance prediction
        var = K_star_star - K_star @ self.K_inv @ K_star.T
        std = np.sqrt(np.maximum(np.diag(var), 1e-10))

        return mean, std


class BayesianOptimizer:
    """Bayesian Optimization using Probability of Improvement."""

    def __init__(
            self,
            iteration_func: Callable,
            muscle_mode: MuscleMode.BICEPS_TRICEPS | MuscleMode.DELTOIDS,
            xi: float = 0.01,
            length_scale: float = 1.0,
    ):
        """
        Parameters
        ----------
        iteration_func: The function to minimize
        xi: Exploration parameter for Probability of Improvement. Higher values encourage exploration.
        length_scale: GP kernel length scale. Higher values lead to smoother functions.
        """
        self.iteration_func = iteration_func
        self.muscle_mode = muscle_mode
        self.n_params = 3
        self.xi = xi
        self.gp = {key: GaussianProcess(length_scale=length_scale) for key in self.muscle_mode.muscle_keys}

        self.input_observed = {key: np.empty((0, self.n_params)) for key in self.muscle_mode.muscle_keys}
        self.output_observed = {key: np.empty((0, 1)) for key in self.muscle_mode.muscle_keys}
        self.best_x = {key: np.empty((0, 1)) for key in self.muscle_mode.muscle_keys}
        self.best_y = {key: np.inf for key in self.muscle_mode.muscle_keys}

        # Logging
        logging.basicConfig(
            level=logging.INFO,
            format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        )
        self._logger = logging.getLogger("BO OPTIM")

    def bounds(self, muscle: str) -> np.ndarray:
        """Get parameter bounds as a numpy array."""
        return np.array([PARAMS_BOUNDS[muscle][key] for key in PARAMS_BOUNDS[muscle].keys()])  # shape (n_params, 2)

    def probability_of_improvement(self, x: np.ndarray, muscle: str) -> np.ndarray:
        """
        Calculate Probability of Improvement at x.
        PI(x) = Φ((f_best - μ(x) - ξ) / σ(x))
        """
        x = np.array(x).reshape(-1, self.n_params)
        mean, std = self.gp[muscle].predict(x)

        # Avoid division by zero
        std = np.maximum(std, 1e-10)

        # Calculate PI (for minimization)
        z = (self.best_y[muscle] - mean - self.xi) / std
        pi = norm.cdf(z)

        return pi

    def _acquisition_to_minimize(self, x: np.ndarray, muscle: str) -> float:
        """Negative PI for minimization."""
        return -self.probability_of_improvement(x.reshape(1, -1), muscle)[0]

    def suggest_next_point(self, n_restarts: int = 10) -> np.ndarray:
        """
        Find the point that maximizes PI.

        Parameters
        ----------
        n_restarts: Number of random restarts for optimization
        """
        next_x = []
        for muscle in self.muscle_mode.muscle_keys:
            best_x: list[float] = None
            best_acquisition: float = np.inf

            # Multi-start optimization
            for _ in range(n_restarts):
                # Random starting point
                x0 = np.random.uniform(
                    self.bounds(muscle)[:, 0],
                    self.bounds(muscle)[:, 1]
                )

                result = minimize(
                    lambda x: self._acquisition_to_minimize(x, muscle),
                    x0=x0,
                    bounds=self.bounds(muscle),
                    method='L-BFGS-B',
                )

                if result.fun < best_acquisition:
                    best_acquisition = result.fun
                    best_x = result.x

            next_x += best_x.tolist()
        return next_x

    def initialize(self, nb_initialization_cycles: int):
        """
        Initialize predefined samples with random onset and offset, but with incremental intensity so that the
        participant slowly gets habituated to the stimulation.

        Parameters
            nb_initialization_cycles: Number of initial random samples
        """
        for i_init in range(nb_initialization_cycles):
            # Get the initial parameters to test
            x = []
            x_all = []
            for muscle in self.muscle_mode.muscle_keys:
                intensity_increment = (PARAMS_BOUNDS[muscle]["pulse_intensity"][1] - PARAMS_BOUNDS[muscle]["pulse_intensity"][0]) / (
                            nb_initialization_cycles - 1)

                # Random angles
                onset_this_time = np.random.uniform(
                    PARAMS_BOUNDS[muscle]["onset_deg"][0],
                    PARAMS_BOUNDS[muscle]["onset_deg"][1],
                )
                offset_this_time = np.random.uniform(
                    PARAMS_BOUNDS[muscle]["offset_deg"][0],
                    PARAMS_BOUNDS[muscle]["offset_deg"][1],
                )

                # Incremental intensity
                intensity_this_time = PARAMS_BOUNDS[muscle]["pulse_intensity"][0] + i_init * intensity_increment

                x += [[onset_this_time, offset_this_time, intensity_this_time]]
                x_all += [onset_this_time, offset_this_time, intensity_this_time]

            cost_list = self.iteration_func(x_all)
            for i_muscle, muscle in enumerate(self.muscle_mode.muscle_keys):
                y = np.array(cost_list[i_muscle]).reshape(1, 1)

                self.input_observed[muscle] = np.vstack((self.input_observed[muscle], np.array(x[i_muscle]).reshape(1, 3)))
                self.output_observed[muscle] = np.vstack((self.output_observed[muscle], y))

                if y < self.best_y[muscle]:
                    self.best_y[muscle] = float(y)
                    self.best_x[muscle] = x[i_muscle].copy()

        for muscle in self.muscle_mode.muscle_keys:
            self.gp[muscle].fit(self.input_observed[muscle], self.output_observed[muscle])

    def optimize(self, n_iterations: int = 20, nb_initialization_cycles: int = 8) -> dict[str, OptimizationResults]:
        """
        Run the Bayesian Optimization loop.

        Parameters:
            n_iterations: Number of optimization iterations
            nb_initialization_cycles: Number of initial incremental steps to evaluate before starting the optimization.
        """
        # Initialize with random samples
        self._logger.info(f"Initializing with random samples...")
        self.initialize(nb_initialization_cycles)

        # Main optimization loop
        for i_iter in range(n_iterations):
            # Find next point to evaluate
            next_x = self.suggest_next_point()

            # Evaluate objective function
            next_y = self.iteration_func(next_x)

            # Update observations
            for i_muscle, muscle in enumerate(self.muscle_mode.muscle_keys):
                parameters_this_muscle = np.array(next_x[i_muscle * 3:(i_muscle + 1) * 3]).reshape(1, 3)
                self.input_observed[muscle] = np.vstack((self.input_observed[muscle], parameters_this_muscle))
                self.output_observed[muscle] = np.vstack((self.output_observed[muscle], next_y[i_muscle]))

                # Update best
                if next_y[i_muscle] < self.best_y[muscle]:
                    self.best_y[muscle] = next_y[i_muscle]
                    self.best_x[muscle] = parameters_this_muscle

                # Refit GP
                self.gp[muscle].fit(self.input_observed[muscle], self.output_observed[muscle])

                self._logger.info(f"[BO OPTIM] Iteration {i_iter + 1}/{n_iterations}: "
                                  f"y = {next_y[i_muscle]}, best = {self.best_y[muscle]}")

        return {muscle: OptimizationResults(self.best_x[muscle], self.best_y[muscle]) for muscle in self.muscle_mode.muscle_keys}

