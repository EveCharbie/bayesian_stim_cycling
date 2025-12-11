import sys
import json
import logging
import pickle
from datetime import datetime
from Qt5.QtWidgets import (
    QApplication,
    QMainWindow,
    QVBoxLayout,
    QHBoxLayout,
    QCheckBox,
    QPushButton,
    QWidget,
    QGroupBox,
    QLabel,
    QLineEdit,
    QSpinBox,
    QComboBox,
    QFileDialog,
    QMessageBox,
    QStatusBar,
    QGridLayout,
    QRadioButton,
    QSlider,
    QFrame,
)
from PyQt5.QtCore import Qt, QTimer
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure

from constants import MUSCLE_KEYS, PARAMS_BOUNDS
from stim_worker import StimulationWorker
from common_types import StimParameters
from pedal_worker import PedalWorker


class MuscleSection(QGroupBox):
    """A section containing three sliders for a single muscle."""

    def __init__(self, muscle_name, parent=None):
        super().__init__(muscle_name, parent)
        self.muscle_name = muscle_name
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout()

        # Create sliders
        self.onset_slider = self.create_slider("Onset", 0, 100, 0)
        self.offset_slider = self.create_slider("Offset", 0, 100, 100)
        self.intensity_slider = self.create_slider("Intensity", 0, 100, 50)

        layout.addLayout(self.onset_slider['layout'])
        layout.addLayout(self.offset_slider['layout'])
        layout.addLayout(self.intensity_slider['layout'])

        self.setLayout(layout)

    def create_slider(self, name, min_val, max_val, default_val):
        """Create a labeled slider with value display."""
        layout = QHBoxLayout()

        # Label
        label = QLabel(f"{name}:")
        label.setFixedWidth(70)

        # Slider
        slider = QSlider(Qt.Horizontal)
        slider.setMinimum(min_val)
        slider.setMaximum(max_val)
        slider.setValue(default_val)

        # Value label
        value_label = QLabel(str(default_val))
        value_label.setFixedWidth(35)
        value_label.setAlignment(Qt.AlignRight | Qt.AlignVCenter)

        # Connect slider to update value label
        slider.valueChanged.connect(lambda v: value_label.setText(str(v)))

        layout.addWidget(label)
        layout.addWidget(slider)
        layout.addWidget(value_label)

        return {
            'layout': layout,
            'slider': slider,
            'value_label': value_label
        }

    def get_values(self):
        """Return current slider values."""
        return {
            'onset': self.onset_slider['slider'].value(),
            'offset': self.offset_slider['slider'].value(),
            'intensity': self.intensity_slider['slider'].value()
        }


class PlotCanvas(FigureCanvas):
    """Matplotlib canvas for the plot at the bottom."""

    def __init__(self, parent=None):
        self.fig = Figure(figsize=(10, 4), dpi=100)
        self.ax = self.fig.add_subplot(111)
        super().__init__(self.fig)
        self.setParent(parent)

        # Initial plot setup
        self.ax.set_xlabel('Cycle')
        self.ax.set_ylabel('Power')
        self.ax.grid(True, alpha=0.7)
        self.fig.tight_layout()


class Interface(QMainWindow):
    """Main application window."""

    def __init__(self, worker_stim: StimulationWorker, worker_pedal: PedalWorker):
        super().__init__()
        self.worker_stim = worker_stim
        self.worker_pedal = worker_pedal  # TODO: plot power !!

        # Store the parameters for each muscle
        self.parameters = {}
        for muscle in MUSCLE_KEYS:
            self.parameters[muscle] = {
                'onset': (PARAMS_BOUNDS["onset_deg"][0] + PARAMS_BOUNDS["onset_deg"][1]) / 2,
                'offset': (PARAMS_BOUNDS["offset_deg"][0] + PARAMS_BOUNDS["offset_deg"][1]) / 2,
                'intensity': (PARAMS_BOUNDS["pulse_intensity"][0] + PARAMS_BOUNDS["pulse_intensity"][1]) / 2
            }

        # create the main window
        self.setWindowTitle("Muscle Control GUI")
        self.setMinimumSize(900, 700)

        # Timer variables (7 minutes 30 seconds = 450 seconds)
        self.remaining_time = 7 * 60 + 30  # 450 seconds

        self.setup_ui()
        self.setup_timer()

    def set_param_value(self, muscle_key, param_name, value):
        # Set the parameter value for a given muscle
        self.parameters[muscle_key][param_name] = value
        params = StimParameters(
            self.parameters["biceps_r"]["onset"],
            self.parameters["biceps_r"]["offset"],
            self.parameters["biceps_r"]["intensity"],
            self.parameters["triceps_r"]["onset"],
            self.parameters["triceps_r"]["offset"],
            self.parameters["triceps_r"]["intensity"],
            self.parameters["biceps_l"]["onset"],
            self.parameters["biceps_l"]["offset"],
            self.parameters["biceps_l"]["intensity"],
            self.parameters["triceps_l"]["onset"],
            self.parameters["triceps_l"]["offset"],
            self.parameters["triceps_l"]["intensity"],
        )
        # Send the updated parameters to the stimulation worker
        self.worker_stim.controller.apply_parameters(params)

    def setup_ui(self):
        """Set up the main UI layout."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(15)
        main_layout.setContentsMargins(15, 15, 15, 15)

        # Timer display at the top
        self.timer_label = QLabel("07:30")
        self.timer_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(self.timer_label)

        # Muscle sections container
        muscles_layout = QHBoxLayout()
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
            section = MuscleSection(muscle_names[key])
            section.onset_slider["slider"].connect(lambda value: self.set_param_value(key, 'onset', value))
            self.muscle_sections[muscle_names[key]] = section
            muscles_layout.addWidget(section)

        main_layout.addLayout(muscles_layout)

        # Separator line
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        main_layout.addWidget(line)

        # Plot at the bottom
        self.plot_canvas = PlotCanvas(self)
        self.plot_canvas.setMinimumHeight(250)
        main_layout.addWidget(self.plot_canvas)

        # Set stretch factors
        main_layout.setStretch(0, 0)  # Timer - no stretch
        main_layout.setStretch(1, 1)  # Muscle sections - some stretch
        main_layout.setStretch(2, 0)  # Separator - no stretch
        main_layout.setStretch(3, 2)  # Plot - more stretch

    def setup_timer(self):
        """Set up the countdown timer."""
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_timer)
        self.timer.start(1000)  # Update every second

    def update_timer(self):
        """Update the countdown timer display."""
        if self.remaining_time > 0:
            self.remaining_time -= 1
            minutes = self.remaining_time // 60
            seconds = self.remaining_time % 60
            self.timer_label.setText(f"{minutes:02d}:{seconds:02d}")

            # Change color when time is running low
            if self.remaining_time <= 60:
                self.timer_label.setStyleSheet("""
                    QLabel {
                        font-size: 36px;
                        font-weight: bold;
                        color: #ffffff;
                        background-color: #e74c3c;
                        border-radius: 10px;
                        padding: 10px;
                    }
                """)
            elif self.remaining_time <= 120:
                self.timer_label.setStyleSheet("""
                    QLabel {
                        font-size: 36px;
                        font-weight: bold;
                        color: #f39c12;
                        background-color: #2c3e50;
                        border-radius: 10px;
                        padding: 10px;
                    }
                """)
        else:
            self.timer.stop()
            self.timer_label.setText("00:00")
            self.save_values()

    def save_values(self):
        """Save all slider values to a pickle file."""
        data = {
            'timestamp': datetime.now().isoformat(),
            'muscles': {}
        }

        for name, section in self.muscle_sections.items():
            data['muscles'][name] = section.get_values()

        filename = f"muscle_data_{datetime.now().strftime('%Y%m%d_%H%M%S')}.pkl"

        with open(filename, 'wb') as f:
            pickle.dump(data, f)

        print(f"Data saved to {filename}")
        print("Saved data:")
        for muscle, values in data['muscles'].items():
            print(f"  {muscle}: {values}")

        # Update timer label to show saved status
        self.timer_label.setText("SAVED!")
        self.timer_label.setStyleSheet("""
            QLabel {
                font-size: 36px;
                font-weight: bold;
                color: #ffffff;
                background-color: #27ae60;
                border-radius: 10px;
                padding: 10px;
            }
        """)

