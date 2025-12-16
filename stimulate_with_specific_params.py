"""
This script allows to stimulate with parameters found manually or through optimization.
"""

import threading
import time
import pickle

from pedal_worker import PedalWorker
from stim_worker import StimulationWorker
from common_types import StimParameters, MuscleMode

from pedal_communication import DataCollector, PedalDevice


PARAMETER_FILE_PATH = "muscle_data_20251216_112111.pkl"  # TOBECHANGED
RESULT_TYPE = "MANUAL"  # "MANUAL" or "OPTIMIZATION"  # TOBECHANGED


def start_stimulate(data_collector: DataCollector):

    # Load parameters from file
    with open(PARAMETER_FILE_PATH, "rb") as f:
        params_results = pickle.load(f)
    if RESULT_TYPE == "MANUAL":
        params = StimParameters(
            onset_deg_biceps_r=params_results["muscles_best_slider"]["Biceps Right"]["onset"],
            offset_deg_biceps_r=params_results["muscles_best_slider"]["Biceps Right"]["offset"],
            pulse_intensity_biceps_r=params_results["muscles_best_slider"]["Biceps Right"]["intensity"],
            onset_deg_triceps_r=params_results["muscles_best_slider"]["Triceps Right"]["onset"],
            offset_deg_triceps_r=params_results["muscles_best_slider"]["Triceps Right"]["offset"],
            pulse_intensity_triceps_r=params_results["muscles_best_slider"]["Triceps Right"]["intensity"],
            onset_deg_biceps_l=params_results["muscles_best_slider"]["Biceps Left"]["onset"],
            offset_deg_biceps_l=params_results["muscles_best_slider"]["Biceps Left"]["offset"],
            pulse_intensity_biceps_l=params_results["muscles_best_slider"]["Biceps Left"]["intensity"],
            onset_deg_triceps_l=params_results["muscles_best_slider"]["Triceps Left"]["onset"],
            offset_deg_triceps_l=params_results["muscles_best_slider"]["Triceps Left"]["offset"],
            pulse_intensity_triceps_l=params_results["muscles_best_slider"]["Triceps Left"]["intensity"],
            onset_deg_delt_post_r=params_results["muscles_best_slider"]["Posterior Deltoid Right"]["onset"],
            offset_deg_delt_post_r=params_results["muscles_best_slider"]["Posterior Deltoid Right"]["offset"],
            pulse_intensity_delt_post_r=params_results["muscles_best_slider"]["Posterior Deltoid Right"]["intensity"],
            onset_deg_delt_ant_r=params_results["muscles_best_slider"]["Anterior Deltoid Right"]["onset"],
            offset_deg_delt_ant_r=params_results["muscles_best_slider"]["Anterior Deltoid Right"]["offset"],
            pulse_intensity_delt_ant_r=params_results["muscles_best_slider"]["Anterior Deltoid Right"]["intensity"],
            onset_deg_delt_post_l=params_results["muscles_best_slider"]["Posterior Deltoid Left"]["onset"],
            offset_deg_delt_post_l=params_results["muscles_best_slider"]["Posterior Deltoid Left"]["offset"],
            pulse_intensity_delt_post_l=params_results["muscles_best_slider"]["Posterior Deltoid Left"]["intensity"],
            onset_deg_delt_ant_l=params_results["muscles_best_slider"]["Anterior Deltoid Left"]["onset"],
            offset_deg_delt_ant_l=params_results["muscles_best_slider"]["Anterior Deltoid Left"]["offset"],
            pulse_intensity_delt_ant_l=params_results["muscles_best_slider"]["Anterior Deltoid Left"]["intensity"],
        )
        stim_params = params.add_angles_offset()

    elif RESULT_TYPE == "OPTIMIZATION":
        print("TODO")
    else:
        raise ValueError(f"Unknown RESULT_TYPE: {RESULT_TYPE}")

    muscle_mode = MuscleMode.BOTH()

    # Shared stop flag
    stop_event = threading.Event()

    # Create pedal worker (third worker) that provides the crank angle
    worker_pedal = PedalWorker(
        stop_event=stop_event,
        data_collector=data_collector,
        # worker_plot=worker_plot,
    )

    # Create stimulation worker and connect callback.
    # We also pass a reference to the pedal_worker so that it can use
    # the angle coming from the pedal device instead of the NI-DAQ.
    worker_stim = StimulationWorker(
        worker_pedal=worker_pedal,
        muscle_mode=muscle_mode,
    )
    worker_stim.controller.apply_parameters(stim_params, really_change_stim_intensity=True)

    threading.Thread(target=worker_pedal.run, daemon=True).start()
    threading.Thread(target=worker_stim.run, daemon=True).start()

    # Run for 2 minutes
    duration = 2 * 60
    start_time = time.time()

    try:
        while time.time() - start_time < duration:
            time.sleep(1)  # Check every second
        print("Timer finished - stopping workers...")
    except KeyboardInterrupt:
        print("Interrupted by user...")
    finally:
        worker_pedal.stop()
        worker_stim.stop()


if __name__ == "__main__":


    # Connect to the device. If no real devices are available, one can run the script `mocked_device.py` to create a
    # local TCP mock device that simulates a real pedal device.
    device = PedalDevice()
    while not device.connect():
        time.sleep(0.1)

    data_collector = DataCollector(device)
    # data_collector.show_live([DataType.A0, DataType.A1, DataType.A2])

    # Initialize the data collection from the pedals and start the optimization
    data_collector.start()
    start_stimulate(data_collector)
    data_collector.stop()