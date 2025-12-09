from __future__ import annotations

from dataclasses import dataclass
from typing import List, Optional, Dict

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
    pulse_width_biceps_r: float

    # # Right triceps
    # onset_deg_triceps_r: float
    # offset_deg_triceps_r: float
    # pulse_intensity_triceps_r: float
    # pulse_width_triceps_r: float

    # # Left biceps
    # onset_deg_biceps_l: float
    # offset_deg_biceps_l: float
    # pulse_intensity_biceps_l: float
    # pulse_width_biceps_l: float

    # # Left triceps
    # onset_deg_triceps_l: float
    # offset_deg_triceps_l: float
    # pulse_intensity_triceps_l: float
    # pulse_width_triceps_l: float

    @classmethod
    def from_flat_vector(cls, x: List[float]) -> "StimParameters":
        """
        Convert 16D BO vector to StimParameters instance.
        Order must match the search space in bo_worker.py.
        """
        return cls(*x)

    def to_flat_vector(self) -> List[float]:
        """
        Convert back to a flat list if needed.
        """
        return [
            self.onset_deg_biceps_r,
            self.offset_deg_biceps_r,
            self.pulse_intensity_biceps_r,
            self.pulse_width_biceps_r,
            # self.onset_deg_triceps_r,
            # self.offset_deg_triceps_r,
            # self.pulse_intensity_triceps_r,
            # self.pulse_width_triceps_r,
            # self.onset_deg_biceps_l,
            # self.offset_deg_biceps_l,
            # self.pulse_intensity_biceps_l,
            # self.pulse_width_biceps_l,
            # self.onset_deg_triceps_l,
            # self.offset_deg_triceps_l,
            # self.pulse_intensity_triceps_l,
            # self.pulse_width_triceps_l,
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
            pulse_width_biceps_r=self.pulse_width_biceps_r,
            # onset_deg_triceps_r=mod_angle(self.onset_deg_triceps_r + STIMULATION_RANGE["triceps_r"][0]),
            # offset_deg_triceps_r=mod_angle(self.offset_deg_triceps_r + STIMULATION_RANGE["triceps_r"][1]),
            # pulse_intensity_triceps_r=self.pulse_intensity_triceps_r,
            # pulse_width_triceps_r=self.pulse_width_triceps_r,
            # onset_deg_biceps_l=mod_angle(self.onset_deg_biceps_l + STIMULATION_RANGE["biceps_l"][0]),
            # offset_deg_biceps_l=mod_angle(self.offset_deg_biceps_l + STIMULATION_RANGE["biceps_l"][1]),
            # pulse_intensity_biceps_l=self.pulse_intensity_biceps_l,
            # pulse_width_biceps_l=self.pulse_width_biceps_l,
            # onset_deg_triceps_l=mod_angle(self.onset_deg_triceps_l + STIMULATION_RANGE["triceps_l"][0]),
            # offset_deg_triceps_l=mod_angle(self.offset_deg_triceps_l + STIMULATION_RANGE["triceps_l"][1]),
            # pulse_intensity_triceps_l=self.pulse_intensity_triceps_l,
            # pulse_width_triceps_l=self.pulse_width_triceps_l,
        )