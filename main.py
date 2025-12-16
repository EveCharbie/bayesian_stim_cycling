"""
This code should be run in `run` not `debug` (memory access issues).
"""

from __future__ import annotations

import threading
import time
import logging

from bo_worker import BayesianOptimizationWorker
from stim_worker import StimulationWorker
from pedal_worker import PedalWorker
from live_plotter import LivePlotter
from common_types import MuscleMode

from pedal_communication import PedalDevice, DataCollector

MUSCLE_MODE = MuscleMode.BICEPS_TRICEPS()  # TOBECHANGED

def start_stimulation_optimization(data_collector: DataCollector) -> None:

    # Shared stop flag
    stop_event = threading.Event()

    # Create a thread to plot the results in real time
    # worker_plot = LivePlotter(muscle_mode=MUSCLE_MODE)

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
        muscle_mode=MUSCLE_MODE,
    )

    # Create Bayesian optimization worker
    worker_bo = BayesianOptimizationWorker(
        stop_event=stop_event,
        worker_pedal=worker_pedal,
        worker_stim=worker_stim,
        muscle_mode=MUSCLE_MODE,
        nb_init_intensity_increasing_steps=3,  #TOBECHANGED: 5 is a good value to increase stim intensity gradually
        n_iterations=5,  #TOBECHANGED: 30/type -> 7:30
        really_change_stim_intensity=True,  # This is just a debugging flag to avoid having large stim during tests
        # worker_plot=worker_plot,
    )

    threading.Thread(target=worker_pedal.run, daemon=True).start()
    threading.Thread(target=worker_stim.run, daemon=True).start()
    time.sleep(0.1)  # Give some time to start pedal and stim workers
    threading.Thread(target=worker_bo.run, daemon=True).start()
    # threading.Thread(target=worker_plot.run, daemon=True).start()

    # Keep main thread alive
    try:
        while True:
            time.sleep(5)
    except KeyboardInterrupt:
        worker_pedal.stop()
        worker_stim.stop()


if __name__ == "__main__":

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(name)s: %(message)s")

    # Connect to the device. If no real devices are available, one can run the script `mocked_device.py` to create a
    # local TCP mock device that simulates a real pedal device.
    device = PedalDevice()
    while not device.connect():
        time.sleep(0.1)

    data_collector = DataCollector(device)
    # data_collector.show_live([DataType.A0, DataType.A1, DataType.A2])

    # Initialize the data collection from the pedals and start the optimization
    data_collector.start()
    start_stimulation_optimization(data_collector)
    data_collector.stop()
