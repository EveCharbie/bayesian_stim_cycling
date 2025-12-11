import pickle
from datetime import datetime
from PyQt6.QtWidgets import (
    QMainWindow,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QWidget,
    QGroupBox,
    QLabel,
    QSlider,
    QFrame,
)
from PyQt6.QtCore import Qt, QTimer
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import numpy as np

from constants import MUSCLE_KEYS, PARAMS_BOUNDS, STIMULATION_RANGE
from stim_worker import StimulationWorker
from common_types import StimParameters
from pedal_worker import PedalWorker

from pedal_communication import DataType


class MuscleSection(QGroupBox):
    """A section containing three sliders for a single muscle."""

    def __init__(self, muscle_key: str, muscle_name: str, parent=None):
        super().__init__(muscle_name, parent)
        self.muscle_key = muscle_key
        self.muscle_name = muscle_name
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout()

        # Create sliders
        # STIMULATION_RANGE[self.muscle_key][0]
        self.onset_slider = self.create_slider(
            name="Onset",
            min_val=PARAMS_BOUNDS[self.muscle_name]["onset_deg"][0],
            max_val=PARAMS_BOUNDS[self.muscle_name]["onset_deg"][1],
            default_val=0,
            increments=0.5,
        )
        self.offset_slider = self.create_slider(
            name="Offset",
            min_val=PARAMS_BOUNDS[self.muscle_name]["offset_deg"][0],
            max_val=PARAMS_BOUNDS[self.muscle_name]["offset_deg"][1],
            default_val=0,
            increments=0.5,
        )
        self.intensity_slider = self.create_slider(
            name="Intensity",
            min_val=PARAMS_BOUNDS[self.muscle_name]["pulse_intensity"][0],
            max_val=PARAMS_BOUNDS[self.muscle_name]["pulse_intensity"][1],
            default_val=(PARAMS_BOUNDS[self.muscle_name]["pulse_intensity"][0] + PARAMS_BOUNDS[self.muscle_name]["pulse_intensity"][1]) / 2,
            increments=2,
        )

        layout.addLayout(self.onset_slider['layout'])
        layout.addLayout(self.offset_slider['layout'])
        layout.addLayout(self.intensity_slider['layout'])

        self.setLayout(layout)

    def create_slider(self, name, min_val, max_val, default_val, increments: float = 0.5):
        """Create a labeled slider with value display."""
        layout = QHBoxLayout()

        # Scale factor for 0.5 precision (internal: 0-200, display: 0.0-100.0)
        scale = 1/increments

        # Label
        label = QLabel(f"{name}:")
        label.setFixedWidth(70)

        # Minus button
        minus_btn = QPushButton("-")
        minus_btn.setFixedWidth(20)
        minus_btn.setFixedHeight(20)

        # Slider (scaled for 0.5 precision)
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
        plus_btn.setFixedWidth(20)
        plus_btn.setFixedHeight(20)
        value_label.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)

        # Connect slider to update value label
        slider.valueChanged.connect(
            lambda v: value_label.setText(f"{v / scale:.1f}")
        )

        # Connect buttons
        minus_btn.clicked.connect(lambda: slider.setValue(slider.value() - 1))
        plus_btn.clicked.connect(lambda: slider.setValue(slider.value() + 1))

        # Enable auto-repeat to allow holding the button
        minus_btn.setAutoRepeat(True)
        minus_btn.setAutoRepeatInterval(50)  # Repeat every 50ms while held
        minus_btn.setAutoRepeatDelay(300)  # Start repeating after 300ms

        plus_btn.setAutoRepeat(True)
        plus_btn.setAutoRepeatInterval(50)
        plus_btn.setAutoRepeatDelay(300)

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
        scale = self.onset_slider['scale']
        return {
            'onset': self.onset_slider['slider'].value() / scale,
            'offset': self.offset_slider['slider'].value() / scale,
            'intensity': self.intensity_slider['slider'].value() / scale
        }


class PlotCanvas(FigureCanvas):
    """Matplotlib canvas for the plot at the bottom."""

    def __init__(self, worker_pedal: PedalWorker, side: str, parent = None):
        self.worker_pedal = worker_pedal
        self.side = side

        # Data to plot
        self.power_list = []

        # Initialize figure
        self.fig = Figure(figsize=(10, 4), dpi=100)
        self.ax = self.fig.add_subplot(111)
        super().__init__(self.fig)
        self.setParent(parent)

        # Initial plot setup
        self.ax.set_xlabel('Time [s]')
        self.ax.set_ylabel(f'Power {side} [W]')
        self.ax.grid(True, alpha=0.7)
        self.fig.tight_layout()

    def setup_live_plot(self):
        """Set up timer for live data updates."""
        self.plot_timer = QTimer(self)
        self.plot_timer.timeout.connect(self.update_live_plot)
        self.plot_timer.start(10)  # 10ms = 100 Hz

    def update_live_plot(self):
        """Called every 10ms to update plot with new data."""
        last_cycle_data = self.worker_pedal.get_last_cycle_data()
        if self.side == "Left":
            power = np.nanmean(np.abs(last_cycle_data["left_power"]))
        elif self.side == "Right":
            power = np.nanmean(np.abs(last_cycle_data["right_power"]))
        else:
            raise ValueError(f"Unknown side: {self.side}")
        self.power_list += [power]

        # Keep only the last 50 cycles
        if len(self.power_list) > 50:
            power_to_plot = self.power_list[-50:]

        self.ax.cla()
        self.ax.step(np.arange(self.power_to_plot.shape[0]), self.power_to_plot, color='blue')
        self.ax.relim()
        self.ax.autoscale_view()
        self.ax.set_xlabel('Cycles')
        self.ax.set_ylabel(f'Power {self.side} [W]')
        self.ax.grid(True, alpha=0.7)
        self.fig.tight_layout()
        self.draw()

class Interface(QMainWindow):
    """Main application window."""

    def __init__(self, worker_stim: StimulationWorker, worker_pedal: PedalWorker):
        super().__init__(parent=None)
        self.worker_stim = worker_stim
        self.worker_pedal = worker_pedal

        # Store the parameters for each muscle
        self.parameters = {}
        for muscle in MUSCLE_KEYS:
            self.parameters[muscle] = {
                'onset': (PARAMS_BOUNDS[muscle]["onset_deg"][0] + PARAMS_BOUNDS[muscle]["onset_deg"][1]) / 2,
                'offset': (PARAMS_BOUNDS[muscle]["offset_deg"][0] + PARAMS_BOUNDS[muscle]["offset_deg"][1]) / 2,
                'intensity': (PARAMS_BOUNDS[muscle]["pulse_intensity"][0] + PARAMS_BOUNDS[muscle]["pulse_intensity"][1]) / 2
            }

        # create the main window
        self.setWindowTitle("Muscle Control GUI")
        self.setMinimumSize(900, 800)

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
        # self.worker_stim.controller.apply_parameters(params)

    def setup_ui(self):
        """Set up the main UI layout."""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout(central_widget)
        main_layout.setSpacing(5)
        main_layout.setContentsMargins(15, 15, 15, 15)

        # Timer display at the top
        self.timer_label = QLabel("07:30")
        self.timer_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        main_layout.addWidget(self.timer_label)

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
            section.onset_slider["slider"].valueChanged.connect(
                lambda value: self.set_param_value(key, 'onset', value / section.onset_slider['scale'])
            )
            self.muscle_sections[muscle_names[key]] = section
            muscles_layout.addWidget(section)

        main_layout.addLayout(muscles_layout)

        # Separator line
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        main_layout.addWidget(line)

        # Plot  sections container
        plot_layout = QVBoxLayout()
        plot_layout.setSpacing(5)
        self.plot_canvas = {
            "Left": PlotCanvas(self.worker_pedal, parent=None, side="left"),
            "Right": PlotCanvas(self.worker_pedal, parent=None, side="Right"),
        }
        self.plot_canvas["Left"].setMinimumHeight(150)
        self.plot_canvas["Right"].setMinimumHeight(150)
        plot_layout.addWidget(self.plot_canvas["Left"])
        plot_layout.addWidget(self.plot_canvas["Right"])
        main_layout.addLayout(plot_layout)

        # Set stretch factors
        main_layout.setStretch(0, 0)  # Timer - no stretch
        main_layout.setStretch(1, 0)  # Muscle sections - no stretch (stays at top)
        main_layout.setStretch(2, 0)  # Separator - no stretch
        main_layout.setStretch(3, 0)  # Plot - takes all remaining space

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
            self.timer_label.setStyleSheet("""
                QLabel {
                    font-size: 36px;
                    font-weight: bold;
                    color: #ffffff;
                    background-color: #144c3c;
                }
            """)

            # Change color when time is running low
            if self.remaining_time <= 60:
                self.timer_label.setStyleSheet("""
                    QLabel {
                        font-size: 36px;
                        font-weight: bold;
                        color: #ffffff;
                        background-color: #e74c3c;
                    }
                """)
            elif self.remaining_time <= 120:
                self.timer_label.setStyleSheet("""
                    QLabel {
                        font-size: 36px;
                        font-weight: bold;
                        color: #f39c12;
                        background-color: #2c3e50;
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
            }
        """)

