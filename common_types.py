from __future__ import annotations

from dataclasses import dataclass
from typing import List, Dict
from enum import Enum

from constants import STIMULATION_RANGE


class StimParameters:

    def __init__(
            self,
            onset_deg_biceps_r: float = 0,
            offset_deg_biceps_r: float = 0,
            pulse_intensity_biceps_r: float = 0,
            onset_deg_triceps_r: float = 0,
            offset_deg_triceps_r: float = 0,
            pulse_intensity_triceps_r: float = 0,
            onset_deg_biceps_l: float = 0,
            offset_deg_biceps_l: float = 0,
            pulse_intensity_biceps_l: float = 0,
            onset_deg_triceps_l: float = 0,
            offset_deg_triceps_l: float = 0,
            pulse_intensity_triceps_l: float = 0,
            onset_deg_delt_post_r: float = 0,
            offset_deg_delt_post_r: float = 0,
            pulse_intensity_delt_post_r: float = 0,
            onset_deg_delt_ant_r: float = 0,
            offset_deg_delt_ant_r: float = 0,
            pulse_intensity_delt_ant_r: float = 0,
            onset_deg_delt_post_l: float = 0,
            offset_deg_delt_post_l: float = 0,
            pulse_intensity_delt_post_l: float = 0,
            onset_deg_delt_ant_l: float = 0,
            offset_deg_delt_ant_l: float = 0,
            pulse_intensity_delt_ant_l: float = 0,
        ):

            # Right biceps
            self.onset_deg_biceps_r = onset_deg_biceps_r
            self.offset_deg_biceps_r = offset_deg_biceps_r
            self.pulse_intensity_biceps_r = pulse_intensity_biceps_r

            # Right triceps
            self.onset_deg_triceps_r = onset_deg_triceps_r
            self.offset_deg_triceps_r = offset_deg_triceps_r
            self.pulse_intensity_triceps_r = pulse_intensity_triceps_r

            # Left biceps
            self.onset_deg_biceps_l = onset_deg_biceps_l
            self.offset_deg_biceps_l = offset_deg_biceps_l
            self.pulse_intensity_biceps_l = pulse_intensity_biceps_l

            # Left triceps
            self.onset_deg_triceps_l = onset_deg_triceps_l
            self.offset_deg_triceps_l = offset_deg_triceps_l
            self.pulse_intensity_triceps_l = pulse_intensity_triceps_l

            # Right posterior deltoid
            self.onset_deg_delt_post_r = onset_deg_delt_post_r
            self.offset_deg_delt_post_r = offset_deg_delt_post_r
            self.pulse_intensity_delt_post_r = pulse_intensity_delt_post_r

            # Right deltoid anterior
            self.onset_deg_delt_ant_r = onset_deg_delt_ant_r
            self.offset_deg_delt_ant_r = offset_deg_delt_ant_r
            self.pulse_intensity_delt_ant_r = pulse_intensity_delt_ant_r

            # Left posterior deltoid
            self.onset_deg_delt_post_l = onset_deg_delt_post_l
            self.offset_deg_delt_post_l = offset_deg_delt_post_l
            self.pulse_intensity_delt_post_l = pulse_intensity_delt_post_l

            # Left deltoid anterior
            self.onset_deg_delt_ant_l = onset_deg_delt_ant_l
            self.offset_deg_delt_ant_l = offset_deg_delt_ant_l
            self.pulse_intensity_delt_ant_l = pulse_intensity_delt_ant_l

    @classmethod
    def from_flat_vector(self, x: List[float], muscle_mode: MuscleMode) -> "StimParameters":
        """
        Convert 16D BO vector to StimParameters instance.
        Order must match the search space in bo_worker.py.
        """
        if isinstance(muscle_mode, MuscleMode.BICEPS_TRICEPS):
            return StimParameters(
                onset_deg_biceps_r=x[0],
                offset_deg_biceps_r=x[1],
                pulse_intensity_biceps_r=x[2],
                onset_deg_triceps_r=x[3],
                offset_deg_triceps_r=x[4],
                pulse_intensity_triceps_r=x[5],
                onset_deg_biceps_l=x[6],
                offset_deg_biceps_l=x[7],
                pulse_intensity_biceps_l=x[8],
                onset_deg_triceps_l=x[9],
                offset_deg_triceps_l=x[10],
                pulse_intensity_triceps_l=x[11],
            )
        elif isinstance(muscle_mode, MuscleMode.DELTOIDS):
            return StimParameters(
                onset_deg_delt_post_r=x[0],
                offset_deg_delt_post_r=x[1],
                pulse_intensity_delt_post_r=x[2],
                onset_deg_delt_ant_r=x[3],
                offset_deg_delt_ant_r=x[4],
                pulse_intensity_delt_ant_r=x[5],
                onset_deg_delt_post_l=x[6],
                offset_deg_delt_post_l=x[7],
                pulse_intensity_delt_post_l=x[8],
                onset_deg_delt_ant_l=x[9],
                offset_deg_delt_ant_l=x[10],
                pulse_intensity_delt_ant_l=x[11],
            )
        elif isinstance(muscle_mode, MuscleMode.BOTH):
            return StimParameters(
                onset_deg_biceps_r=x[0],
                offset_deg_biceps_r=x[1],
                pulse_intensity_biceps_r=x[2],
                onset_deg_triceps_r=x[3],
                offset_deg_triceps_r=x[4],
                pulse_intensity_triceps_r=x[5],
                onset_deg_biceps_l=x[6],
                offset_deg_biceps_l=x[7],
                pulse_intensity_biceps_l=x[8],
                onset_deg_triceps_l=x[9],
                offset_deg_triceps_l=x[10],
                pulse_intensity_triceps_l=x[11],
                onset_deg_delt_post_r=x[12],
                offset_deg_delt_post_r=x[13],
                pulse_intensity_delt_post_r=x[14],
                onset_deg_delt_ant_r=x[15],
                offset_deg_delt_ant_r=x[16],
                pulse_intensity_delt_ant_r=x[17],
                onset_deg_delt_post_l=x[18],
                offset_deg_delt_post_l=x[19],
                pulse_intensity_delt_post_l=x[20],
                onset_deg_delt_ant_l=x[21],
                offset_deg_delt_ant_l=x[22],
                pulse_intensity_delt_ant_l=x[23],
            )
        else:
            raise ValueError(f"Invalid muscle mode : {muscle_mode}")

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