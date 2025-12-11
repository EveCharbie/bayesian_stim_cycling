"""
This script allows to start stimulation with a specific intensity.
It should be used to determine what is the motor threshold and 8 on a borg scale for each subject.

biceps_r = [, ]
triceps_r = [, ]
biceps_l = [, ]
triceps_l = [, ]
"""
import threading
import time
import sys

from PyQt6.QtWidgets import (
    QApplication,
    QMainWindow,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QWidget,
    QGroupBox,
    QLabel,
    QSlider,
)
from PyQt6.QtCore import Qt

from pedal_worker import PedalWorker
from stim_worker import StimulationWorker
from common_types import StimParameters
from constants import STIMULATION_RANGE, MUSCLE_KEYS

from pedal_communication import DataCollector, PedalDevice


class MuscleSection(QGroupBox):
    """A section containing three sliders for a single muscle."""

    def __init__(self, muscle_key: str, muscle_name: str, parent=None):
        super().__init__(muscle_name, parent)
        self.muscle_key = muscle_key
        self.muscle_name = muscle_name
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout()

        # Create all three sliders
        self.intensity_slider = self.create_slider(
            name="Intensity",
        )
        layout.addLayout(self.intensity_slider['layout'])
        self.setLayout(layout)

    def create_slider(self, name, min_val=0, max_val=80, default_val=0, increments: float = 2):
        """Create a labeled slider with value display."""
        layout = QHBoxLayout()

        # Scale factor for precision (internal: scaled, display: actual)
        scale = 1 / increments

        # Label
        label = QLabel(f"{name}:")
        label.setFixedWidth(70)

        # Minus button
        minus_btn = QPushButton("-")
        minus_btn.setFixedWidth(20)
        minus_btn.setFixedHeight(20)

        # Slider (scaled for precision)
        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setMinimum(int(min_val * scale))
        slider.setMaximum(int(max_val * scale))
        slider.setValue(int(default_val * scale))

        # Plus button
        plus_btn = QPushButton("+")
        plus_btn.setFixedWidth(20)
        plus_btn.setFixedHeight(20)

        # Value label (shows decimal value)
        value_label = QLabel(f"{default_val:.1f}")
        value_label.setFixedWidth(40)
        value_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        # Connect slider to update value label
        slider.valueChanged.connect(
            lambda v: value_label.setText(f"{v / scale:.1f}")
        )

        # Connect buttons
        minus_btn.clicked.connect(lambda: slider.setValue(slider.value() - 1))
        plus_btn.clicked.connect(lambda: slider.setValue(slider.value() + 1))

        # Assemble layout
        layout.addWidget(label)
        layout.addWidget(minus_btn)
        layout.addWidget(slider)
        layout.addWidget(plus_btn)
        layout.addWidget(value_label)

        return {
            'layout': layout,
            'slider': slider,
            'value_label': value_label,
            'scale': scale,
            'minus_btn': minus_btn,
            'plus_btn': plus_btn
        }

    def get_values(self):
        """Return current slider values."""
        scale = self.intensity_slider['scale']
        return {
            'intensity': self.intensity_slider['slider'].value() / scale
        }


class Interface(QMainWindow):
    """Main application window."""

    def __init__(self, worker_stim: StimulationWorker):
        super().__init__(parent=None)
        self.worker_stim = worker_stim

        # Store the parameters for each muscle
        self.parameters = {}
        for muscle in MUSCLE_KEYS:
            self.parameters[muscle] = {
                'intensity': 0
            }

        # create the main window
        self.setWindowTitle("Muscle Control GUI")
        self.setMinimumSize(900, 800)

        self.setup_ui()

    def set_param_value(self, muscle_key, param_name, value):
        # Set the parameter value for a given muscle
        self.parameters[muscle_key][param_name] = value
        params = StimParameters(
            onset_deg_biceps_r=STIMULATION_RANGE["biceps_r"][0],
            offset_deg_biceps_r=STIMULATION_RANGE["biceps_r"][1],
            pulse_intensity_biceps_r=self.parameters["biceps_r"]["intensity"],
            onset_deg_triceps_r=STIMULATION_RANGE["triceps_r"][0],
            offset_deg_triceps_r=STIMULATION_RANGE["triceps_r"][1],
            pulse_intensity_triceps_r=self.parameters["triceps_r"]["intensity"],
            onset_deg_biceps_l=STIMULATION_RANGE["biceps_l"][0],
            offset_deg_biceps_l=STIMULATION_RANGE["biceps_l"][1],
            pulse_intensity_biceps_l=self.parameters["biceps_l"]["intensity"],
            onset_deg_triceps_l=STIMULATION_RANGE["triceps_l"][0],
            offset_deg_triceps_l=STIMULATION_RANGE["triceps_l"][1],
            pulse_intensity_triceps_l=self.parameters["triceps_l"]["intensity"],
        )
        # Send the updated parameters to the stimulation worker
        self.worker_stim.controller.apply_parameters(params)

    def setup_ui(self):
        """Set up the main UI layout."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(5)
        main_layout.setContentsMargins(15, 15, 15, 15)

        # Muscle sections container
        muscles_layout = QVBoxLayout()
        muscles_layout.setSpacing(10)

        # Create four muscle sections
        self.muscle_sections = {}
        muscle_names = {
            "biceps_r": "Biceps Right",
            "triceps_r": "Triceps Right",
            "biceps_l": "Biceps Left",
            "triceps_l": "Triceps Left",
        }

        for key in muscle_names:
            section = MuscleSection(key, muscle_names[key])

            # Fix lambda capture by using default argument
            section.intensity_slider["slider"].valueChanged.connect(
                lambda value, k=key, s=section: self.set_param_value(k, 'intensity',
                                                                     value / s.intensity_slider['scale'])
            )

            self.muscle_sections[muscle_names[key]] = section
            muscles_layout.addWidget(section)

        main_layout.addLayout(muscles_layout)


def start_stimulate(data_collector: DataCollector):

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
    )
    # worker_stim.controller.apply_parameters(
    #     StimParameters(
    #         onset_deg_biceps_r=STIMULATION_RANGE["biceps_r"][0],
    #         offset_deg_biceps_r=STIMULATION_RANGE["biceps_r"][1],
    #         pulse_intensity_biceps_r=biceps_r_intensity,
    #         onset_deg_triceps_r=STIMULATION_RANGE["triceps_r"][0],
    #         offset_deg_triceps_r=STIMULATION_RANGE["triceps_r"][1],
    #         pulse_intensity_triceps_r=triceps_r_intensity,
    #         onset_deg_biceps_l=STIMULATION_RANGE["biceps_l"][0],
    #         offset_deg_biceps_l=STIMULATION_RANGE["biceps_l"][1],
    #         pulse_intensity_biceps_l=biceps_l_intensity,
    #         onset_deg_triceps_l=STIMULATION_RANGE["triceps_l"][0],
    #         offset_deg_triceps_l=STIMULATION_RANGE["triceps_l"][1],
    #         pulse_intensity_triceps_l=triceps_l_intensity,
    #     ),
    #     really_change_stim_intensity=True,
    # )

    # Create a GUI so that the subject/experimentator can interact with the stimulation parameters
    app = QApplication(sys.argv)
    interface = Interface(worker_stim=None)
    interface.show()

    threading.Thread(target=worker_pedal.run, daemon=True).start()
    threading.Thread(target=worker_stim.run, daemon=True).start()

    # Start the GUI
    sys.exit(app.exec())

    # Keep main thread alive
    try:
        while True:
            time.sleep(5)
    except KeyboardInterrupt:
        worker_pedal.stop()
        worker_stim.stop()

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