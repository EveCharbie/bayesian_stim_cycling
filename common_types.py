from __future__ import annotations

from dataclasses import dataclass
from typing import List, Dict
from enum import Enum

from constants import STIMULATION_RANGE


@dataclass
class StimParameters:
    """
    Single BO sample of stimulation parameters:

      onset_deg / offset_deg / pulse_intensity / pulse_width
      for each muscle: biceps_r, triceps_r, biceps_l, triceps_l.
    """

    # Right biceps
    onset_deg_biceps_r: float
    offset_deg_biceps_r: float
    pulse_intensity_biceps_r: float

    # Right triceps
    onset_deg_triceps_r: float
    offset_deg_triceps_r: float
    pulse_intensity_triceps_r: float

    # Left biceps
    onset_deg_biceps_l: float
    offset_deg_biceps_l: float
    pulse_intensity_biceps_l: float

    # Left triceps
    onset_deg_triceps_l: float
    offset_deg_triceps_l: float
    pulse_intensity_triceps_l: float

    # Right posterior deltoid
    onset_deg_delt_post_r: float
    offset_deg_delt_post_r: float
    pulse_intensity_delt_post_r: float

    # Right deltoid anterior
    onset_deg_delt_ant_r: float
    offset_deg_delt_ant_r: float
    pulse_intensity_delt_ant_r: float

    # Left posterior deltoid
    onset_deg_delt_post_l: float
    offset_deg_delt_post_l: float
    pulse_intensity_delt_post_l: float

    # Left deltoid anterior
    onset_deg_delt_ant_l: float
    offset_deg_delt_ant_l: float
    pulse_intensity_delt_ant_l: float

    @classmethod
    def from_flat_vector(cls, x: List[float]) -> "StimParameters":
        """
        Convert 16D BO vector to StimParameters instance.
        Order must match the search space in bo_worker.py.
        """
        return cls(*x)

    @classmethod
    def from_dict(cls, param_dict: Dict[str, float]) -> "StimParameters":
        """
        Convert dictionary to StimParameters instance.
        """
        return cls(
            onset_deg_biceps_r=param_dict["onset_deg_biceps_r"],
            offset_deg_biceps_r=param_dict["offset_deg_biceps_r"],
            pulse_intensity_biceps_r=param_dict["pulse_intensity_biceps_r"],
            onset_deg_triceps_r=param_dict["onset_deg_triceps_r"],
            offset_deg_triceps_r=param_dict["offset_deg_triceps_r"],
            pulse_intensity_triceps_r=param_dict["pulse_intensity_triceps_r"],
            onset_deg_biceps_l=param_dict["onset_deg_biceps_l"],
            offset_deg_biceps_l=param_dict["offset_deg_biceps_l"],
            pulse_intensity_biceps_l=param_dict["pulse_intensity_biceps_l"],
            onset_deg_triceps_l=param_dict["onset_deg_triceps_l"],
            offset_deg_triceps_l=param_dict["offset_deg_triceps_l"],
            pulse_intensity_triceps_l=param_dict["pulse_intensity_triceps_l"],
            onset_deg_delt_post_r=param_dict["onset_deg_delt_post_r"],
            offset_deg_delt_post_r=param_dict["offset_deg_delt_post_r"],
            pulse_intensity_delt_post_r=param_dict["pulse_intensity_delt_post_r"],
            onset_deg_delt_ant_r=param_dict["onset_deg_delt_ant_r"],
            offset_deg_delt_ant_r=param_dict["offset_deg_delt_ant_r"],
            pulse_intensity_delt_ant_r=param_dict["pulse_intensity_delt_ant_r"],
            onset_deg_delt_post_l=param_dict["onset_deg_delt_post_l"],
            offset_deg_delt_post_l=param_dict["offset_deg_delt_post_l"],
            pulse_intensity_delt_post_l=param_dict["pulse_intensity_delt_post_l"],
            onset_deg_delt_ant_l=param_dict["onset_deg_delt_ant_l"],
            offset_deg_delt_ant_l=param_dict["offset_deg_delt_ant_l"],
            pulse_intensity_delt_ant_l=param_dict["pulse_intensity_delt_ant_l"],
        )

    def to_flat_vector(self) -> List[float]:
        """
        Convert back to a flat list if needed.
        """
        return [
            self.onset_deg_biceps_r,
            self.offset_deg_biceps_r,
            self.pulse_intensity_biceps_r,
            self.onset_deg_triceps_r,
            self.offset_deg_triceps_r,
            self.pulse_intensity_triceps_r,
            self.onset_deg_biceps_l,
            self.offset_deg_biceps_l,
            self.pulse_intensity_biceps_l,
            self.onset_deg_triceps_l,
            self.offset_deg_triceps_l,
            self.pulse_intensity_triceps_l,
            self.onset_deg_delt_post_r,
            self.offset_deg_delt_post_r,
            self.pulse_intensity_delt_post_r,
            self.onset_deg_delt_ant_r,
            self.offset_deg_delt_ant_r,
            self.pulse_intensity_delt_ant_r,
            self.onset_deg_delt_post_l,
            self.offset_deg_delt_post_l,
            self.pulse_intensity_delt_post_l,
            self.onset_deg_delt_ant_l,
            self.offset_deg_delt_ant_l,
            self.pulse_intensity_delt_ant_l,
        ]

    def add_angles_offset(self) -> StimParameters:
        """
        Return a new StimParameters instance with an offset added to all angle parameters.
        """
        def mod_angle(angle: float) -> float:
            """Ensure angle is within [0, 360) degrees."""
            if angle < 0:
                return angle + 360
            elif angle >= 360:
                return angle % 360
            else:
                return angle

        return StimParameters(
            onset_deg_biceps_r=mod_angle(self.onset_deg_biceps_r + STIMULATION_RANGE["biceps_r"][0]),
            offset_deg_biceps_r=mod_angle(self.offset_deg_biceps_r + STIMULATION_RANGE["biceps_r"][1]),
            pulse_intensity_biceps_r=self.pulse_intensity_biceps_r,
            onset_deg_triceps_r=mod_angle(self.onset_deg_triceps_r + STIMULATION_RANGE["triceps_r"][0]),
            offset_deg_triceps_r=mod_angle(self.offset_deg_triceps_r + STIMULATION_RANGE["triceps_r"][1]),
            pulse_intensity_triceps_r=self.pulse_intensity_triceps_r,
            onset_deg_biceps_l=mod_angle(self.onset_deg_biceps_l + STIMULATION_RANGE["biceps_l"][0]),
            offset_deg_biceps_l=mod_angle(self.offset_deg_biceps_l + STIMULATION_RANGE["biceps_l"][1]),
            pulse_intensity_biceps_l=self.pulse_intensity_biceps_l,
            onset_deg_triceps_l=mod_angle(self.onset_deg_triceps_l + STIMULATION_RANGE["triceps_l"][0]),
            offset_deg_triceps_l=mod_angle(self.offset_deg_triceps_l + STIMULATION_RANGE["triceps_l"][1]),
            pulse_intensity_triceps_l=self.pulse_intensity_triceps_l,
            onset_deg_delt_post_r=mod_angle(self.onset_deg_delt_post_r + STIMULATION_RANGE["delt_post_r"][0]),
            offset_deg_delt_post_r=mod_angle(self.offset_deg_delt_post_r + STIMULATION_RANGE["delt_post_r"][1]),
            pulse_intensity_delt_post_r=self.pulse_intensity_delt_post_r,
            onset_deg_delt_ant_r=mod_angle(self.onset_deg_delt_ant_r + STIMULATION_RANGE["delt_ant_r"][0]),
            offset_deg_delt_ant_r=mod_angle(self.offset_deg_delt_ant_r + STIMULATION_RANGE["delt_ant_r"][1]),
            pulse_intensity_delt_ant_r=self.pulse_intensity_delt_ant_r,
            onset_deg_delt_post_l=mod_angle(self.onset_deg_delt_post_l + STIMULATION_RANGE["delt_post_l"][0]),
            offset_deg_delt_post_l=mod_angle(self.offset_deg_delt_post_l + STIMULATION_RANGE["delt_post_l"][1]),
            pulse_intensity_delt_post_l=self.pulse_intensity_delt_post_l,
            onset_deg_delt_ant_l=mod_angle(self.onset_deg_delt_ant_l + STIMULATION_RANGE["delt_ant_l"][0]),
            offset_deg_delt_ant_l=mod_angle(self.offset_deg_delt_ant_l + STIMULATION_RANGE["delt_ant_l"][1]),
            pulse_intensity_delt_ant_l=self.pulse_intensity_delt_ant_l,
        )

class MuscleMode:

    class BICEPS_TRICEPS:
        def __init__(self):
            self.value = "biceps_triceps"
            self.muscle_keys = (
                "biceps_r",   # Channel 1
                "triceps_r",  # Channel 2
                "biceps_l",   # Channel 3
                "triceps_l",  # Channel 4
            )
            self.channel_indices = [1, 2, 3, 4]

    class DELTOIDS:
        def __init__(self):
            self.value = "deltoids"
            self.muscle_keys = (
                "delt_post_r",  # Channel 5
                "delt_ant_r",   # Channel 6
                "delt_post_l",  # Channel 7
                "delt_ant_l",   # Channel 8
            )
            self.channel_indices = [5, 6, 7, 8]

    class BOTH:
        def __init__(self):
            self.value = "both"
            self.muscle_keys = (
                "biceps_r",    # Channel 1
                "triceps_r",   # Channel 2
                "biceps_l",    # Channel 3
                "triceps_l",   # Channel 4
                "delt_post_r", # Channel 5
                "delt_ant_r",  # Channel 6
                "delt_post_l", # Channel 7
                "delt_ant_l",  # Channel 8
            )
            self.channel_indices = [1, 2, 3, 4, 5, 6, 7, 8]