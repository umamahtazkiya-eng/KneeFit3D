"""
General KneeFit3D fitting helpers.

Research/prototype use only.
"""

import numpy as np

from .mesh_utils import mesh_center


def center_mesh_xy(
    implant_mesh,
    target_center,
    axes=(0, 1)
):
    """
    Center implant bounding box over target AP/ML center.

    Does not modify Z / resection depth.
    """

    out = implant_mesh.copy()

    c = mesh_center(
        out
    )

    target = np.asarray(
        target_center,
        dtype=float
    )

    shift = np.zeros(3)

    for i, axis in enumerate(axes):
        shift[axis] = (
            target[i]
            -
            c[axis]
        )

    out.apply_translation(
        shift
    )

    return out, shift


def place_on_plane(
    implant_mesh,
    implant_reference_point,
    target_plane_origin,
    axis=2
):
    """
    Translate implant so one reference coordinate matches
    the target resection plane coordinate.

    Current GitHub-preprocessed bone frame:
      X = AP
      Y = ML
      Z = proximal/distal
    """

    out = implant_mesh.copy()

    ref = np.asarray(
        implant_reference_point,
        dtype=float
    )

    target = np.asarray(
        target_plane_origin,
        dtype=float
    )

    shift = np.zeros(3)

    shift[axis] = (
        target[axis]
        -
        ref[axis]
    )

    out.apply_translation(
        shift
    )

    return out, shift
