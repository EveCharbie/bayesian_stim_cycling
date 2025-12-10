

# Zero = left hand in front
STIMULATION_RANGE = {
    "biceps_r": [220 - 90, 10 - 90],
    "triceps_r": [20 - 90, 180 - 90],
    "biceps_l": [40 - 90, 190 - 90],
    "triceps_l": [200 - 90, 360 - 90],
}

MUSCLE_KEYS = (
    "biceps_r",   # Channel 1
    "triceps_r",  # Channel 2
    "biceps_l",   # Channel 3
    "triceps_l",  # Channel 4
)

PARAMS_BOUNDS = {
    "onset_deg": [-30.0, 30.0],
    "offset_deg": [-30.0, 30.0],
    "pulse_intensity": [5, 15],  # TODO: Change these values to really stim
    # "pulse_intensity": [30, 50],
}