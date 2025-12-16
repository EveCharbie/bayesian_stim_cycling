from __future__ import annotations

import threading
import time
import logging
import sys

from PyQt6.QtWidgets import QApplication

from stim_worker import StimulationWorker
from pedal_worker import PedalWorker
from interface import Interface
from common_types import MuscleMode

from pedal_communication import PedalDevice, DataCollector


def start_stimulation_optimization(data_collector: DataCollector) -> None:

    muscle_mode = MuscleMode.BOTH()  # This cannot be changed here !

    # Shared stop flag
    stop_event = threading.Event()

    # Create pedal worker (worker) that provides the crank angle
    worker_pedal = PedalWorker(
        stop_event=stop_event,
        data_collector=data_collector,
        worker_plot=None,
    )

    # Create stimulation worker and connect callback.
    # We also pass a reference to the pedal_worker so that it can use
    # the angle coming from the pedal device instead of the NI-DAQ.
    worker_stim = StimulationWorker(
        worker_pedal=worker_pedal,
        muscle_mode=muscle_mode,
    )

    threading.Thread(target=worker_pedal.run, daemon=True).start()
    threading.Thread(target=worker_stim.run, daemon=True).start()

    # Create a GUI so that the subject/experimentator can interact with the stimulation parameters
    app = QApplication(sys.argv)
    interface = Interface(worker_stim=worker_stim, worker_pedal=worker_pedal, muscle_mode=muscle_mode)
    interface.show()

    # This blocks until GUI closes
    exit_code = app.exec()

    sys.exit(exit_code)


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