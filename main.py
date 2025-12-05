from __future__ import annotations

import threading
import queue
import time
import logging

from pedal_communication import PedalDevice, DataType, DataCollector

from bo_worker import BayesianOptimizationWorker, build_search_space
from stim_worker import StimulationWorker
from pedal_worker import PedalWorker
from common_types import StimJob


def start_stimulation_optimization(data_collector: DataCollector) -> None:

    # Shared queue and stop flag
    job_queue: "queue.Queue[StimJob | None]" = queue.Queue()
    stop_event = threading.Event()

    # # Build BO search space
    # space = build_search_space()

    # Create Bayesian optimization worker
    # bo_worker = BayesianOptimizationWorker(
    #     job_queue=job_queue,
    #     stop_event=stop_event,
    #     space=space,
    #     data_collector=data_collector,
    # )

    # Create pedal worker (third worker) that provides the crank angle
    pedal_worker = PedalWorker(
        stop_event=stop_event,
        data_collector=data_collector,
    )

    # Create stimulation worker and connect callback.
    # We also pass a reference to the pedal_worker so that it can use
    # the angle coming from the pedal device instead of the NI-DAQ.
    # stim_worker = StimulationWorker(
    #     job_queue=job_queue,
    #     stop_event=stop_event,
    #     result_callback=bo_worker.handle_result,
    #     eval_duration_s=10.0,  # seconds per cost fun evaluation
    #     data_collector=data_collector,
    #     pedal_worker=pedal_worker,
    # )

    threading.Thread(target=pedal_worker.run, daemon=True).start()
    # stim_worker.start()
    # bo_worker.start()

    # Keep main thread alive
    try:
        while True:
            time.sleep(5)
    except KeyboardInterrupt:
        pedal_worker.stop()

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
