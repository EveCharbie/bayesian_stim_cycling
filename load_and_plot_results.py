import pickle
import numpy as np
import matplotlib.pyplot as plt

from common_types import StimParameters
from constants import PARAMS_BOUNDS, MUSCLE_KEYS

def load_results(file_path: str):
    with open(file_path, 'rb') as f:
        results = pickle.load(f)
    cost_list = results['cost_list']
    parameters_list = results['parameter_list']
    return cost_list, parameters_list

def plot_results(cost_list, parameters_list):

    colors = np.arange(100)[:len(cost_list["biceps_r"])]
    n_muscles = len(MUSCLE_KEYS)
    fig_optim, axs_optim = plt.subplots(n_muscles, 3, figsize=(12, 8))

    for i_iter in range(len(cost_list["biceps_r"])):
        parameters = parameters_list[i_iter].to_flat_vector()
        i_param = 0
        for i_muscle, muscle in enumerate(MUSCLE_KEYS):
            cost = cost_list[muscle][i_iter]
            axs_optim[i_muscle, 0].set_title("Onset")
            axs_optim[i_muscle, 1].set_title("Offset")
            axs_optim[i_muscle, 2].set_title("Intensity")

            axs_optim[i_muscle, 0].scatter(parameters[i_param], cost, c=colors[i_iter],
                                                cmap="viridis", vmin=colors[0], vmax=colors[-1])
            axs_optim[i_muscle, 0].set_title("Onset")
            axs_optim[i_muscle, 0].set_xlim(PARAMS_BOUNDS[muscle]["onset_deg"][0],
                                                 PARAMS_BOUNDS[muscle]["onset_deg"][1])
            i_param += 1
    
            axs_optim[i_muscle, 1].scatter(parameters[i_param], cost, c=colors[i_iter],
                                                cmap="viridis", vmin=colors[0], vmax=colors[-1])
            axs_optim[i_muscle, 1].set_title("Offset")
            axs_optim[i_muscle, 1].set_xlim(PARAMS_BOUNDS[muscle]["offset_deg"][0],
                                                 PARAMS_BOUNDS[muscle]["offset_deg"][1])
            i_param += 1
    
            axs_optim[i_muscle, 2].scatter(parameters[i_param], cost, c=colors[i_iter],
                                                cmap="viridis", vmin=colors[0], vmax=colors[-1])
            axs_optim[i_muscle, 2].set_title("Intensity")
            axs_optim[i_muscle, 2].set_xlim(PARAMS_BOUNDS[muscle]["pulse_intensity"][0],
                                                 PARAMS_BOUNDS[muscle]["pulse_intensity"][1])
            i_param += 1
        fig_optim.tight_layout()


if __name__ == "__main__":
    costs_list, parameters_list = load_results("bo_results.pkl")
    plot_results(costs_list, parameters_list)
    plt.show()