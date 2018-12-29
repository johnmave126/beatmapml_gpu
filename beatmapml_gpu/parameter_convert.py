from slider.mod import circle_radius
import numpy as np
import math

from .structs import *

__all__ = [
    'calc_cs_propotion',
    'calc_dimension',
    'MAX_PLAYFIELD'
]
MAX_PLAYFIELD = np.array([512, 384])


def calc_cs_propotion(cs: float) -> float:
    """Calculate the relative radius of a circle for a given circle size

        Args:
            cs (float): The circle size raw value.

        Returns:
            The relative radius of a circle. A float between 0 and 1,
            meaning the ratio between the raius and the playfield width.
    """
    return circle_radius(cs) / 512


def calc_dimension(width):
    MAX_CS_RADIUS_RATIO = calc_cs_propotion(2)
    MAX_CS_RADIUS = math.floor(
        width * MAX_CS_RADIUS_RATIO / (1 + 2 * MAX_CS_RADIUS_RATIO))
    field_width = width - 2 * MAX_CS_RADIUS
    field_height = math.floor(field_width * 3 / 4)
    height = field_height + 2 * MAX_CS_RADIUS
    return (Dimension(width, height),
            Rect(MAX_CS_RADIUS,
                 MAX_CS_RADIUS,
                 MAX_CS_RADIUS + field_width,
                 MAX_CS_RADIUS + field_height))
