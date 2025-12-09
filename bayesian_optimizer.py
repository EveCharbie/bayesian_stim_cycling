from typing import Callable
import numpy as np
from scipy.stats import norm
from scipy.optimize import minimize
from scipy.spatial.distance import cdist

from common_types import StimParameters
from constants import PARAMS_BOUNDS


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
            objective_func: Callable,
            xi: float = 0.01,
            length_scale: float = 1.0,
    ):
        """
        Parameters
        ----------
        objective_func: The function to minimize
        xi: Exploration parameter for Probability of Improvement. Higher values encourage exploration.
        length_scale: GP kernel length scale. Higher values lead to smoother functions.
        """
        self.objective_func = objective_func
        self.n_params = len(PARAMS_BOUNDS.keys())
        self.xi = xi
        self.gp = GaussianProcess(length_scale=length_scale)

        self.input_observed = np.empty((self.n_params, 0))
        self.output_observed = np.empty((1, 0))
        self.best_x = None
        self.best_y = np.inf

    def probability_of_improvement(self, x: np.ndarray) -> np.ndarray:
        """
        Calculate Probability of Improvement at x.
        PI(x) = Φ((f_best - μ(x) - ξ) / σ(x))
        """
        x = np.array(x).reshape(-1, self.n_params)
        mean, std = self.gp.predict(x)

        # Avoid division by zero
        std = np.maximum(std, 1e-10)

        # Calculate PI (for minimization)
        z = (self.best_y - mean - self.xi) / std
        pi = norm.cdf(z)

        return pi

    def _acquisition_to_minimize(self, x):
        """Negative PI for minimization."""
        return -self.probability_of_improvement(x.reshape(1, -1))[0]

    def suggest_next_point(self, n_restarts: int = 10):
        """
        Find the point that maximizes PI.

        Parameters
        ----------
        n_restarts: Number of random restarts for optimization
        """
        best_x: float = None
        best_acquisition: float = np.inf

        # Multi-start optimization
        for _ in range(n_restarts):
            # Random starting point
            x0 = np.random.uniform(
                self.bounds[:, 0],
                self.bounds[:, 1]
            )

            result = minimize(
                self._acquisition_to_minimize,
                x0=x0,
                bounds=self.bounds,
                method='L-BFGS-B'
            )

            if result.fun < best_acquisition:
                best_acquisition = result.fun
                best_x = result.x

        return best_x

    def initialize(self, n_initial_steps: int):
        """
        Initialize predefined samples with random onset and offset, but with incremental intensity so that the
        participant slowly gets habituated to the stimulation.

        Parameters
            n_initial_steps: Number of initial random samples
        """
        intensity_increment = (PARAMS_BOUNDS["pulse_intensity"][1] - PARAMS_BOUNDS["pulse_intensity"][0]) / n_initial_steps

        for i_init in range(n_initial_steps):
            # Random angles
            onset_this_time = np.random.uniform(
                PARAMS_BOUNDS["onset_deg"][0],
                PARAMS_BOUNDS["onset_deg"][1],
            )
            offset_this_time = np.random.uniform(
                PARAMS_BOUNDS["offset_deg"][0],
                PARAMS_BOUNDS["offset_deg"][1],
            )

            # Incremental intensity
            intensity_this_time = PARAMS_BOUNDS["pulse_intensity"][0] + i_init * intensity_increment

            stim_params = StimParameters(
                    onset_deg_biceps_r=onset_this_time,
                    offset_deg_biceps_r=offset_this_time,
                    pulse_intensity_biceps_r=intensity_this_time,
                )
            y = self.objective_func(stim_params)
            x = stim_params.to_flat_vector()

            self.input_observed = np.vstack((self.input_observed, x))
            self.output_observed = np.vstack((self.output_observed, y))

            if y < self.best_y:
                self.best_y = y
                self.best_x = x.copy()

        self.gp.fit(self.input_observed, self.output_observed)

    def optimize(self, n_iterations: int = 20, n_initial_steps: int = 8, verbose: bool = True):
        """
        Run the Bayesian Optimization loop.

        Parameters:
            n_iterations: Number of optimization iterations
            n_initial_steps: Number of initial incremental steps to evaluate before starting the optimization.
            verbose: Print progress
        """
        # Initialize with random samples
        if verbose:
            print("[BO OPTIM] Initializing with random samples...")
        self.initialize(n_initial_steps)

        if verbose:
            print(f"[BO OPTIM] Initial best: {self.best_y:.6f}")
            print(f"[BO OPTIM] Initial best params: {self.best_x}")
            print("[BO OPTIM] \nStarting optimization...")

        # Main optimization loop
        for i_iter in range(n_iterations):
            # Find next point to evaluate
            next_x = self.suggest_next_point()

            # Evaluate objective function
            next_y = self.objective_func(next_x)

            # Update observations
            self.input_observed = np.vstack((self.input_observed, next_x))
            self.output_observed = np.vstack((self.output_observed, next_y))

            # Update best
            if next_y < self.best_y:
                self.best_y = next_y
                self.best_x = next_x.copy()

            # Refit GP
            self.gp.fit(self.input_observed, self.output_observed)

            if verbose:
                print(f"[BO OPTIM] Iteration {i_iter + 1}/{n_iterations}: "
                      f"y = {next_y:.6f}, best = {self.best_y:.6f}")

        return self.best_x, self.best_y

