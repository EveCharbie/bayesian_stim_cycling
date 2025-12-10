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

from pedal_communication import PedalDevice, DataCollector


def start_stimulation_optimization(data_collector: DataCollector) -> None:

    # Shared stop flag
    stop_event = threading.Event()

    # Create a thread to plot the results in real time
    worker_plot = LivePlotter()

    # Create pedal worker (third worker) that provides the crank angle
    worker_pedal = PedalWorker(
        stop_event=stop_event,
        data_collector=data_collector,
        worker_plot=worker_plot,
    )

    # Create stimulation worker and connect callback.
    # We also pass a reference to the pedal_worker so that it can use
    # the angle coming from the pedal device instead of the NI-DAQ.
    # worker_stim = StimulationWorker(
    #     worker_pedal=worker_pedal,
    # )

    # Create Bayesian optimization worker
    # worker_bo = BayesianOptimizationWorker(
    #     stop_event=stop_event,
    #     worker_pedal=worker_pedal,
    #     worker_stim=worker_stim,
    #     worker_plot=worker_plot,
    #     nb_initialization_cycles=2,
    #     really_change_stim_intensity=True,  # This is just a debugging flag to avoid having large stim during tests
    # )

    threading.Thread(target=worker_pedal.run, daemon=True).start()
    # threading.Thread(target=worker_stim.run, daemon=True).start()
    time.sleep(0.1)  # Give some time to start pedal and stim workers
    # threading.Thread(target=worker_bo.run, daemon=True).start()
    threading.Thread(target=worker_plot.run, daemon=True).start()

    # Keep main thread alive
    try:
        while True:
            time.sleep(5)
    except KeyboardInterrupt:
        worker_pedal.stop()
        # worker_stim.stop()

    # try:
    #     # Wait for BO to finish
    #     bo_worker.join()
    # except KeyboardInterrupt:
    #     print("[Main] KeyboardInterrupt detected, stopping...")
    # finally:
    #     # Signal all threads to stop
    #     stop_event.set()

    #     # Quit stimulation worker (sentinel for the job queue)
    #     job_queue.put(None)

    #     # Join workers
    #     stim_worker.join()
    #     pedal_worker.join()

    #     print("[Main] All threads stopped.")

    #     if bo_worker.best_result is not None:
    #         print("[Main] Best x:", bo_worker.best_result.x)
    #         print("[Main] Best cost:", bo_worker.best_result.fun)


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
