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
    QStyleOptionSlider,
    QStyle,
    QApplication,
)
from PyQt6.QtGui import QPainter, QColor, QPen, QPolygon
from PyQt6.QtCore import Qt, QTimer, QPoint

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import numpy as np

from constants import PARAMS_BOUNDS, STIMULATION_RANGE
from stim_worker import StimulationWorker
from common_types import StimParameters, MuscleMode
from pedal_worker import PedalWorker


class MarkedSlider(QSlider):
    """QSlider with a visual marker for the best value."""

    def __init__(self, orientation):
        super().__init__(orientation)
        self.best_value = None

    def set_best_value(self, value):
        """Set the position of the best value marker."""
        self.best_value = value
        self.update()  # Trigger repaint

    def clear_best_value(self):
        """Remove the best value marker."""
        self.best_value = None
        self.update()

    def paintEvent(self, event):
        """Override paint to draw the marker."""
        # First draw the normal slider
        super().paintEvent(event)

        # Then draw our custom marker if set
        if self.best_value is None:
            return

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Calculate position of the marker
        slider_min = self.minimum()
        slider_max = self.maximum()
        slider_range = slider_max - slider_min

        if slider_range == 0:
            painter.end()
            return

        # Get slider geometry using proper QStyleOptionSlider
        opt = QStyleOptionSlider()
        self.initStyleOption(opt)

        groove_rect = self.style().subControlRect(
            QStyle.ComplexControl.CC_Slider,
            opt,
            QStyle.SubControl.SC_SliderGroove,
            self
        )

        # Calculate pixel position
        value_ratio = (self.best_value - slider_min) / slider_range

        if self.orientation() == Qt.Orientation.Horizontal:
            x_pos = groove_rect.x() + int(groove_rect.width() * value_ratio)
            y_top = groove_rect.y()
            y_bottom = groove_rect.y() + groove_rect.height()

            # Draw a vertical line at the best value position
            pen = QPen(QColor(255, 215, 0), 3)  # Gold color
            painter.setPen(pen)
            painter.drawLine(x_pos, y_top - 5, x_pos, y_bottom + 5)

            # Draw small triangles at top and bottom
            painter.setBrush(QColor(255, 215, 0))
            painter.setPen(Qt.PenStyle.NoPen)

            # Top triangle
            points_top = QPolygon([
                QPoint(x_pos, y_top - 5),
                QPoint(x_pos - 4, y_top - 10),
                QPoint(x_pos + 4, y_top - 10)
            ])
            painter.drawPolygon(points_top)

            # Bottom triangle
            points_bottom = QPolygon([
                QPoint(x_pos, y_bottom + 5),
                QPoint(x_pos - 4, y_bottom + 10),
                QPoint(x_pos + 4, y_bottom + 10)
            ])
            painter.drawPolygon(points_bottom)

        painter.end()


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
            min_val=PARAMS_BOUNDS[self.muscle_key]["onset_deg"][0],
            max_val=PARAMS_BOUNDS[self.muscle_key]["onset_deg"][1],
            default_val=0,
            increments=0.5,
        )
        self.offset_slider = self.create_slider(
            name="Offset",
            min_val=PARAMS_BOUNDS[self.muscle_key]["offset_deg"][0],
            max_val=PARAMS_BOUNDS[self.muscle_key]["offset_deg"][1],
            default_val=0,
            increments=0.5,
        )
        self.intensity_slider = self.create_slider(
            name="Intensity",
            min_val=0,  # PARAMS_BOUNDS[self.muscle_key]["pulse_intensity"][0],
            max_val=PARAMS_BOUNDS[self.muscle_key]["pulse_intensity"][1],
            default_val=0,  # (PARAMS_BOUNDS[self.muscle_key]["pulse_intensity"][0] + PARAMS_BOUNDS[self.muscle_key]["pulse_intensity"][1]) / 2,
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
        slider = MarkedSlider(Qt.Orientation.Horizontal)
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
        def increment_slider():
            current = slider.value()
            slider.setValue(current + 1)

        def decrement_slider():
            current = slider.value()
            slider.setValue(current - 1)

        minus_btn.clicked.connect(decrement_slider)
        plus_btn.clicked.connect(increment_slider)

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

    def set_best_values(self, onset, offset, intensity):
        """Mark the best parameter values on all sliders."""
        self.onset_slider['slider'].set_best_value(int(onset * self.onset_slider['scale']))
        self.offset_slider['slider'].set_best_value(int(offset * self.offset_slider['scale']))
        self.intensity_slider['slider'].set_best_value(int(intensity * self.intensity_slider['scale']))

    def get_best_values(self):
        """Return slider best values."""
        return {
            'onset': self.onset_slider['slider'].best_value / self.onset_slider['scale'],
            'offset': self.offset_slider['slider'].best_value / self.offset_slider['scale'],
            'intensity': self.intensity_slider['slider'].best_value / self.intensity_slider['scale']
        }

    def clear_best_values(self):
        """Remove best value markers from all sliders."""
        self.onset_slider['slider'].clear_best_value()
        self.offset_slider['slider'].clear_best_value()
        self.intensity_slider['slider'].clear_best_value()

    def get_values(self):
        """Return current slider values."""
        return {
            'onset': self.onset_slider['slider'].value() / self.onset_slider['scale'],
            'offset': self.offset_slider['slider'].value() / self.offset_slider['scale'],
            'intensity': self.intensity_slider['slider'].value() / self.intensity_slider['scale']
        }


class PlotCanvas(FigureCanvas):
    """Matplotlib canvas for the plot at the bottom."""

    def __init__(self, worker_pedal: PedalWorker, side: str, muscle_sections: dict, parent = None):

        self.worker_pedal = worker_pedal
        self.side = side
        # TODO: muscle_sections should be independent from the plot update, but the power computation should e placed somewhere else for that.
        self.muscle_sections = muscle_sections

        # Data to plot
        self.power_list = []

        # Initialize figure
        self.fig = Figure(figsize=(10, 4), dpi=100)
        self.ax = self.fig.add_subplot(111)
        super().__init__(self.fig)
        self.setParent(parent)

        # Initial plot setup
        self.ax.set_xlabel('Cycles')
        self.ax.set_ylabel(f'Power {side} [W]')
        self.ax.grid(True, alpha=0.7)
        self.fig.tight_layout()
        self.setup_live_plot()

    def setup_live_plot(self):
        """Set up timer for live data updates."""

        self.plot_timer = QTimer(self)
        self.plot_timer.timeout.connect(self.update_live_plot)
        self.plot_timer.start(50)  # 50ms = 20 Hz

    def update_live_plot(self):
        """Called every 10ms to update plot with new data."""
        last_cycle_data = self.worker_pedal.get_last_cycle_data()
        nb_cycles = len(last_cycle_data["times_vector"])

        if nb_cycles == 0:
            return
        else:
            if self.side == "Left":
                power = np.nanmean(np.abs(last_cycle_data["left_power"][-1]))
            elif self.side == "Right":
                power = np.nanmean(np.abs(last_cycle_data["right_power"][-1]))
            else:
                raise ValueError(f"Unknown side: {self.side}")

            if len(self.power_list) == 0:
                self.power_list += [power]
            elif power == self.power_list[-1]:
                return
            else:
                self.power_list += [power]

            # Keep only the last 50 cycles
            nb_cycles_to_show = 50
            if len(self.power_list) > nb_cycles_to_show:
                power_to_plot = self.power_list[-nb_cycles_to_show:]
            else:
                power_to_plot = self.power_list

            self.ax.cla()
            self.ax.step(np.arange(len(power_to_plot)), power_to_plot, color='blue')
            self.ax.relim()
            self.ax.autoscale_view()
            self.ax.set_xlabel('Cycles')
            self.ax.set_ylabel(f'Power {self.side} [W]')
            self.ax.grid(True, alpha=0.7)
            self.fig.tight_layout()
            self.draw()


            # Update the marker on the slide bar if a new max power is reached
            if power >= max(self.power_list):
                self.update_best_markers()

    def update_best_markers(self):
        """Update the best value markers on relevant muscle sections."""
        for muscle_name, section in self.muscle_sections.items():
            # Only update markers for muscles on the same side
            if (self.side == "Left" and muscle_name.endswith("Left")) or \
               (self.side == "Right" and muscle_name.endswith("Right")):
                values = section.get_values()
                section.set_best_values(
                    onset=values['onset'],
                    offset=values['offset'],
                    intensity=values['intensity']
                )

class Interface(QMainWindow):
    """Main application window."""

    def __init__(
            self,
            worker_stim: StimulationWorker,
            worker_pedal: PedalWorker,
            muscle_mode: MuscleMode.BOTH
    ):
        super().__init__(parent=None)
        self.worker_stim = worker_stim
        self.worker_pedal = worker_pedal
        if not isinstance(muscle_mode, MuscleMode.BOTH):
            raise ValueError("muscle_mode must be MuscleMode.BOTH for this interface.")
        self.muscle_mode = muscle_mode

        # Store the parameters for each muscle
        self.parameters = {}
        for muscle in self.muscle_mode.muscle_keys:
            self.parameters[muscle] = {
                'onset': 0,
                'offset': 0,
                'intensity': 0,
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
            self.parameters["delt_post_r"]["onset"],
            self.parameters["delt_post_r"]["offset"],
            self.parameters["delt_post_r"]["intensity"],
            self.parameters["delt_ant_r"]["onset"],
            self.parameters["delt_ant_r"]["offset"],
            self.parameters["delt_ant_r"]["intensity"],
            self.parameters["delt_post_l"]["onset"],
            self.parameters["delt_post_l"]["offset"],
            self.parameters["delt_post_l"]["intensity"],
            self.parameters["delt_ant_l"]["onset"],
            self.parameters["delt_ant_l"]["offset"],
            self.parameters["delt_ant_l"]["intensity"],
        )
        params_to_send = params.add_angles_offset()

        # Send the updated parameters to the stimulation worker
        try:
            self.worker_stim.controller.apply_parameters(params_to_send, really_change_stim_intensity=True)
        except Exception as e:
            print(f"Error applying parameters to stimulator: {e}")

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
        muscles_layout = QHBoxLayout()
        left_sub_muscles_layout = QVBoxLayout()
        left_sub_muscles_layout.setSpacing(10)
        right_sub_muscles_layout = QVBoxLayout()
        right_sub_muscles_layout.setSpacing(10)
        muscles_layout.addLayout(left_sub_muscles_layout)
        muscles_layout.addLayout(right_sub_muscles_layout)

        # Create four muscle sections
        self.muscle_sections = {}
        muscle_names = {
            "biceps_r": "Biceps Right",
            "triceps_r": "Triceps Right",
            "biceps_l": "Biceps Left",
            "triceps_l": "Triceps Left",
            "delt_post_r": "Posterior Deltoid Right",
            "delt_ant_r": "Anterior Deltoid Right",
            "delt_post_l": "Posterior Deltoid Left",
            "delt_ant_l": "Anterior Deltoid Left",
        }

        for muscle in muscle_names:
            section = MuscleSection(muscle, muscle_names[muscle])

            section.onset_slider["slider"].valueChanged.connect(
                lambda value, m=muscle, s=section: self.set_param_value(m, 'onset', value / s.onset_slider['scale'])
            )
            section.offset_slider["slider"].valueChanged.connect(
                lambda value, m=muscle, s=section: self.set_param_value(m, 'offset', value / s.offset_slider['scale'])
            )
            section.intensity_slider["slider"].valueChanged.connect(
                lambda value, m=muscle, s=section: self.set_param_value(m, 'intensity',
                                                                        value / s.intensity_slider['scale'])
            )

            self.muscle_sections[muscle_names[muscle]] = section
            if muscle.endswith("_l"):
                left_sub_muscles_layout.addWidget(section)
            elif muscle.endswith("_r"):
                right_sub_muscles_layout.addWidget(section)
            else:
                raise ValueError(f"The muscle key {muscle} should have ended with _l or _r.")

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
            "Left": PlotCanvas(self.worker_pedal, parent=self, side="Left", muscle_sections=self.muscle_sections),
            "Right": PlotCanvas(self.worker_pedal, parent=self, side="Right", muscle_sections=self.muscle_sections),
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
            'muscles': {},
            'muscles_best_slider': {}
        }

        for name, section in self.muscle_sections.items():
            data['muscles'][name] = section.get_values()
            data['muscles_best_slider'][name] = section.get_values()

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

        # Stop the stimulation and pedal workers
        self.stop_event.set()
        self.worker_pedal.stop()
        self.worker_stim.stop()

        # Close the GUI
        self.close()

        # Quit the application
        QApplication.quit()

