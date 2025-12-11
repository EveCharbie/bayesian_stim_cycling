

# Zero = left hand in front
STIMULATION_RANGE = {
    "biceps_r": [180, 330],  # [220 - 90, 10 - 90 + 360],
    "triceps_r": [290, 90],  # [20 - 90 + 360, 180 - 90],
    "biceps_l": [310, 100],  # [40 - 90 + 360, 190 - 90],
    "triceps_l": [110, 270]  # [200 - 90, 360 - 90],
    # "biceps_r": [130, 280],  # [220 - 90, 10 - 90 + 360],
    # "triceps_r": [290, 90],  # [20 - 90 + 360, 180 - 90],
    # "biceps_l": [310, 100],  # [40 - 90 + 360, 190 - 90],
    # "triceps_l": [110, 270]  # [200 - 90, 360 - 90],
    # "delt_post_r": [220 - 90, 10 - 90 + 360],
    # "delt_ant_r": [20 - 90 + 360, 180 - 90],
    # "delt_post_l": [40 - 90 + 360, 190 - 90],
    # "delt_ant_l": [200 - 90, 360 - 90],
}
CUTOFF_ANGLES = {
    "right": [110, 285],  # In degrees (biceps_r is in this range)
    "left": [105, 290],   # In degrees (triceps_l is in this range)
}

MUSCLE_KEYS = (
    "biceps_r",   # Channel 1
    "triceps_r",  # Channel 2
    "biceps_l",   # Channel 3
    "triceps_l",  # Channel 4
)

PARAMS_BOUNDS = {
    "biceps_r":{
        "onset_deg": [-30.0, 30.0],
        "offset_deg": [-30.0, 30.0],
        # "pulse_intensity": [30, 50],  # TODO: Change these values to really stim
        "pulse_intensity": [10, 20],
    },
    "triceps_r": {
        "onset_deg": [-30.0, 30.0],
        "offset_deg": [-30.0, 30.0],
        # "pulse_intensity": [30, 60],  # TODO: Change these values to really stim
        "pulse_intensity": [10, 30],
    },
    "biceps_l": {
        "onset_deg": [-30.0, 30.0],
        "offset_deg": [-30.0, 30.0],
        # "pulse_intensity": [30, 67],  # TODO: Change these values to really stim
        "pulse_intensity": [10, 35],
    },
    "triceps_l": {
        "onset_deg": [-30.0, 30.0],
        "offset_deg": [-30.0, 30.0],
        # "pulse_intensity": [30, 58],  # TODO: Change these values to really stim
        "pulse_intensity": [10, 28],
    },
}