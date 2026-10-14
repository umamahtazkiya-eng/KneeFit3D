"""
KneeFit3D mesh utilities.

Research/prototype use only.
"""

from pathlib import Path
import numpy as np
import trimesh


def load_mesh_mm(path):
    """
    Load STL as trimesh and convert meter-scale geometries
    to millimetres when required.

    Parameters
    ----------
    path : str or Path

    Returns
    -------
    trimesh.Trimesh
    """
    path = Path(path)

    mesh = trimesh.load(
        str(path),
        force="mesh",
        process=False
    ).copy()

    if np.max(mesh.extents) < 1.0:
        mesh.apply_scale(1000.0)

    return mesh


def unit_vector(v):
    """Return normalized vector."""
    v = np.asarray(v, dtype=float)

    n = np.linalg.norm(v)

    if n < 1e-12:
        raise ValueError("Zero-length vector.")

    return v / n


def transform_mesh(mesh, rotation=None, translation=None):
    """
    Apply rigid transformation to a mesh.

    Parameters
    ----------
    rotation : (3,3) ndarray or None
    translation : (3,) ndarray or None
    """
    out = mesh.copy()

    V = np.asarray(out.vertices, dtype=float)

    if rotation is not None:
        R = np.asarray(rotation, dtype=float)
        V = V @ R.T

    if translation is not None:
        t = np.asarray(translation, dtype=float)
        V = V + t

    out.vertices = V

    return out


def mesh_center(mesh):
    """Bounding-box center."""
    return (
        np.asarray(mesh.bounds[0], dtype=float)
        +
        np.asarray(mesh.bounds[1], dtype=float)
    ) / 2.0


def measure_distal_envelope(
    mesh,
    distal_fraction=0.25,
    ap_axis=0,
    ml_axis=1,
    pd_axis=2,
    distal_at_min=True,
    robust_percentiles=None
):
    """
    Measure distal femoral AP/ML envelope.

    Assumption for current KneeFit3D preprocessing:
      X = AP
      Y = ML
      Z = proximal-distal

    Parameters
    ----------
    mesh : trimesh.Trimesh
    distal_fraction : float
        Fraction of distal bone included.
    distal_at_min : bool
        Current GitHub-preprocessed femur has distal end at low Z.
    robust_percentiles : tuple(float,float) or None
        Example: (1,99). If None, raw min/max are used.

    Returns
    -------
    dict
    """

    V = np.asarray(mesh.vertices, dtype=float)

    z = V[:, pd_axis]

    z_min = z.min()
    z_max = z.max()

    length = z_max - z_min

    if distal_at_min:
        threshold = z_min + distal_fraction * length
        roi = V[z <= threshold]
    else:
        threshold = z_max - distal_fraction * length
        roi = V[z >= threshold]

    if len(roi) == 0:
        raise ValueError("Distal ROI contains no vertices.")

    if robust_percentiles is None:
        ap_min = roi[:, ap_axis].min()
        ap_max = roi[:, ap_axis].max()

        ml_min = roi[:, ml_axis].min()
        ml_max = roi[:, ml_axis].max()

    else:
        lo, hi = robust_percentiles

        ap_min, ap_max = np.percentile(
            roi[:, ap_axis],
            [lo, hi]
        )

        ml_min, ml_max = np.percentile(
            roi[:, ml_axis],
            [lo, hi]
        )

    return {
        "AP_mm": float(ap_max - ap_min),
        "ML_mm": float(ml_max - ml_min),

        "AP_min_mm": float(ap_min),
        "AP_max_mm": float(ap_max),

        "ML_min_mm": float(ml_min),
        "ML_max_mm": float(ml_max),

        "distal_fraction": float(distal_fraction),
        "n_vertices": int(len(roi))
    }
