

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

def angular_distance(angle1, angle2):
    """Returns the shortest angular distance from angle1 to angle2."""
    diff = (angle2 - angle1) % 360
    if diff > 180:
        diff -= 360
    return diff

def smaller_than_angle(angle1, angle2):
    """Returns True if angle1 comes before angle2 in the shortest direction around the circle."""
    return 0 <= angular_distance(angle1, angle2) <= 180

def mean_angle(angle1, angle2):
    """Returns the mean angle between two angles, taking the shortest path."""
    diff = angular_distance(angle1, angle2)
    return (angle1 + diff / 2) % 360

def wrap_angle(angle):
    """Wraps an angle to the range [0, 360)."""
    return angle % 360


def get_bounds_for_muscle(muscle1_name, muscle2_name, default_min_angle=30, default_max_angle=30):
    global STIMULATION_RANGE

    # Check overlap between muscle1's onset and muscle2's offset
    muscle1_onset_min = wrap_angle(STIMULATION_RANGE[muscle1_name][0] - default_min_angle)
    muscle2_offset_max = wrap_angle(STIMULATION_RANGE[muscle2_name][1] + default_max_angle)

    if smaller_than_angle(muscle1_onset_min, muscle2_offset_max):
        # They overlap, find the midpoint
        m_angle = mean_angle(STIMULATION_RANGE[muscle1_name][0], STIMULATION_RANGE[muscle2_name][1])
        # Calculate the distance from base angles to midpoint
        muscle1_min_onset = angular_distance(STIMULATION_RANGE[muscle1_name][0], m_angle)
        muscle2_max_offset = angular_distance(m_angle, STIMULATION_RANGE[muscle2_name][1])
    else:
        # No overlap, use default ranges
        muscle1_min_onset = -default_min_angle
        muscle2_max_offset = default_max_angle

    muscle1_max_onset = default_max_angle
    muscle2_min_offset = -default_min_angle

    # Check overlap between muscle2's onset and muscle1's offset
    muscle2_onset_min = wrap_angle(STIMULATION_RANGE[muscle2_name][0] - default_min_angle)
    muscle1_offset_max = wrap_angle(STIMULATION_RANGE[muscle1_name][1] + default_max_angle)

    if smaller_than_angle(muscle2_onset_min, muscle1_offset_max):
        # They overlap, find the midpoint
        m_angle = mean_angle(STIMULATION_RANGE[muscle2_name][0], STIMULATION_RANGE[muscle1_name][1])
        # Calculate the distance from base angles to midpoint
        muscle2_min_onset = angular_distance(STIMULATION_RANGE[muscle2_name][0], m_angle)
        muscle1_max_offset = angular_distance(m_angle, STIMULATION_RANGE[muscle1_name][1])
    else:
        # No overlap, use default ranges
        muscle2_min_onset = -default_min_angle
        muscle1_max_offset = default_max_angle

    muscle2_max_onset = default_max_angle
    muscle1_min_offset = -default_min_angle

    return (
        muscle1_min_onset,
        muscle1_max_onset,
        muscle1_min_offset,
        muscle1_max_offset,
        muscle2_min_onset,
        muscle2_max_onset,
        muscle2_min_offset,
        muscle2_max_offset,
    )

def set_param_bounds():
    global STIMULATION_RANGE

    (
        biceps_r_min_onset,
        biceps_r_max_onset,
        biceps_r_min_offset,
        biceps_r_max_offset,
        triceps_r_min_onset,
        triceps_r_max_onset,
        triceps_r_min_offset,
        triceps_r_max_offset,
    ) = get_bounds_for_muscle("biceps_r", "triceps_r", default_min_angle=30, default_max_angle=30)

    (
        biceps_l_min_onset,
        biceps_l_max_onset,
        biceps_l_min_offset,
        biceps_l_max_offset,
        triceps_l_min_onset,
        triceps_l_max_onset,
        triceps_l_min_offset,
        triceps_l_max_offset,
    ) = get_bounds_for_muscle("biceps_l", "triceps_l", default_min_angle=30, default_max_angle=30)

    (
        delt_post_r_min_onset,
        delt_post_r_max_onset,
        delt_post_r_min_offset,
        delt_post_r_max_offset,
        delt_ant_r_min_onset,
        delt_ant_r_max_onset,
        delt_ant_r_min_offset,
        delt_ant_r_max_offset,
    ) = get_bounds_for_muscle("delt_post_r", "delt_ant_r", default_min_angle=30, default_max_angle=30)

    (
        delt_post_l_min_onset,
        delt_post_l_max_onset,
        delt_post_l_min_offset,
        delt_post_l_max_offset,
        delt_ant_l_min_onset,
        delt_ant_l_max_onset,
        delt_ant_l_min_offset,
        delt_ant_l_max_offset,
    ) = get_bounds_for_muscle("delt_post_l", "delt_ant_l", default_min_angle=30, default_max_angle=30)


    PARAMS_BOUNDS = {
        "biceps_r":{
            "onset_deg": [biceps_r_min_onset, biceps_r_max_onset],
            "offset_deg": [biceps_r_min_offset, biceps_r_max_offset],
            # "pulse_intensity": [30, 50],  # TODO: Change these values to really stim
            "pulse_intensity": [5, 15],
        },
        "triceps_r": {
            "onset_deg": [triceps_r_min_onset, triceps_r_max_onset],
            "offset_deg": [triceps_r_min_offset, triceps_r_max_offset],
            # "pulse_intensity": [30, 60],  # TODO: Change these values to really stim
            "pulse_intensity": [5, 15],
        },
        "biceps_l": {
            "onset_deg": [biceps_l_min_onset, biceps_l_max_onset],
            "offset_deg": [biceps_l_min_offset, biceps_l_max_offset],
            # "pulse_intensity": [30, 67],  # TODO: Change these values to really stim
            "pulse_intensity": [5, 15],
        },
        "triceps_l": {
            "onset_deg": [triceps_l_min_onset, triceps_l_max_onset],
            "offset_deg": [triceps_l_min_offset, triceps_l_max_offset],
            # "pulse_intensity": [30, 58],  # TODO: Change these values to really stim
            "pulse_intensity": [5, 15],
        },
        "delt_post_r": {
            "onset_deg": [delt_post_r_min_onset, delt_post_r_max_onset],
            "offset_deg": [delt_post_r_min_offset, delt_post_r_max_offset],
            # "pulse_intensity": [30, 50],  # TODO: Change these values to really stim
            "pulse_intensity": [5, 15],
        },
        "delt_ant_r": {
            "onset_deg": [delt_ant_r_min_onset, delt_ant_r_max_onset],
            "offset_deg": [delt_ant_r_min_offset, delt_ant_r_max_offset],
            # "pulse_intensity": [30, 60],  # TODO: Change these values to really stim
            "pulse_intensity": [5, 15],
        },
        "delt_post_l": {
            "onset_deg": [delt_ant_l_min_onset, delt_ant_l_max_onset],
            "offset_deg": [delt_ant_l_min_offset, delt_ant_l_max_offset],
            # "pulse_intensity": [30, 67],  # TODO: Change these values to really stim
            "pulse_intensity": [5, 15],
        },
        "delt_ant_l": {
            "onset_deg": [delt_ant_l_min_onset, delt_ant_l_max_onset],
            "offset_deg": [delt_ant_l_min_offset, delt_ant_l_max_offset],
            # "pulse_intensity": [30, 58],  # TODO: Change these values to really stim
            "pulse_intensity": [5, 15],
        },
    }
    return PARAMS_BOUNDS

PARAMS_BOUNDS = set_param_bounds()