

# Zero = left hand in front
STIMULATION_RANGE = {
    "biceps_r": [220.0, 10.0],
    # "triceps_r": [20.0, 180.0],
    # "biceps_l": [40.0, 190.0],
    # "triceps_l": [200.0, 360.0],
}

MUSCLE_KEYS = (
    "biceps_r",
    # "triceps_r",
    # "biceps_l",
    # "triceps_l",
)

PARAMS_BOUNDS = {
    "onset_deg": [-40.0, 40.0],
    "offset_deg": [-40.0, 40.0],
    "pulse_intensity": [1.0, 7.0],
    "pulse_width": [100.0, 500.0],
}