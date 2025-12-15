

# Zero = left hand in front
STIMULATION_RANGE = {
    "biceps_r": [130, 280],  # [220 - 90, 10 - 90 + 360],
    "triceps_r": [290, 90],  # [20 - 90 + 360, 180 - 90],
    "biceps_l": [310, 100],  # [40 - 90 + 360, 190 - 90],
    "triceps_l": [110, 270],  # [200 - 90, 360 - 90],
    "delt_post_r": [130, 280],  # [220 - 90, 10 - 90 + 360],
    "delt_ant_r": [290, 90],  # [20 - 90 + 360, 180 - 90],
    "delt_post_l": [310, 100],  # [40 - 90 + 360, 190 - 90],
    "delt_ant_l": [110, 270],  # [200 - 90, 360 - 90],
}
CUTOFF_ANGLES = {
    "right": [110, 285],  # In degrees (biceps_r is in this range)
    "left": [105, 290],   # In degrees (triceps_l is in this range)
}

PARAMS_BOUNDS = {
    "biceps_r":{
        "onset_deg": [-30.0, 30.0],
        "offset_deg": [-30.0, 30.0],
        # "pulse_intensity": [30, 50],  # TODO: Change these values to really stim
        "pulse_intensity": [5, 15],
    },
    "triceps_r": {
        "onset_deg": [-30.0, 30.0],
        "offset_deg": [-30.0, 30.0],
        # "pulse_intensity": [30, 60],  # TODO: Change these values to really stim
        "pulse_intensity": [5, 15],
    },
    "biceps_l": {
        "onset_deg": [-30.0, 30.0],
        "offset_deg": [-30.0, 30.0],
        # "pulse_intensity": [30, 67],  # TODO: Change these values to really stim
        "pulse_intensity": [5, 15],
    },
    "triceps_l": {
        "onset_deg": [-30.0, 30.0],
        "offset_deg": [-30.0, 30.0],
        # "pulse_intensity": [30, 58],  # TODO: Change these values to really stim
        "pulse_intensity": [5, 15],
    },
    "delt_post_r": {
        "onset_deg": [-30.0, 30.0],
        "offset_deg": [-30.0, 30.0],
        # "pulse_intensity": [30, 50],  # TODO: Change these values to really stim
        "pulse_intensity": [5, 15],
    },
    "delt_ant_r": {
        "onset_deg": [-30.0, 30.0],
        "offset_deg": [-30.0, 30.0],
        # "pulse_intensity": [30, 60],  # TODO: Change these values to really stim
        "pulse_intensity": [5, 15],
    },
    "delt_post_l": {
        "onset_deg": [-30.0, 30.0],
        "offset_deg": [-30.0, 30.0],
        # "pulse_intensity": [30, 67],  # TODO: Change these values to really stim
        "pulse_intensity": [5, 15],
    },
    "delt_ant_l": {
        "onset_deg": [-30.0, 30.0],
        "offset_deg": [-30.0, 30.0],
        # "pulse_intensity": [30, 58],  # TODO: Change these values to really stim
        "pulse_intensity": [5, 15],
    },
}