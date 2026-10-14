"""
Persona tibial fitting utilities for KneeFit3D.

Available corrected research sizes:
A, B, C, D, E, F, G, H, J

Research/prototype use only.
The Persona STL files are research-scaled proxies,
not official OEM CAD.
"""

from pathlib import Path
import re

import numpy as np
import pandas as pd

from scipy.spatial import ConvexHull, cKDTree

try:
    from shapely.geometry import Polygon
except ImportError:
    Polygon = None

from .mesh_utils import load_mesh_mm, unit_vector


TIBIAL_SIZE_ORDER = {
    "A": 1,
    "B": 2,
    "C": 3,
    "D": 4,
    "E": 5,
    "F": 6,
    "G": 7,
    "H": 8,
    "J": 9,
}


def extract_tibial_size(path):
    """Extract A-J Persona tibial size from filename."""

    name = Path(path).stem

    match = re.search(
        r"Size_([A-J])_",
        name,
        flags=re.IGNORECASE
    )

    if match is None:
        return None

    return match.group(1).upper()


def discover_persona_tibial_implants(library_root):
    """Find corrected Persona tibial research STL files."""

    library_root = Path(library_root)

    rows = []

    for path in library_root.rglob("*.stl"):

        size = extract_tibial_size(path)

        if size not in TIBIAL_SIZE_ORDER:
            continue

        rows.append({
            "size": size,
            "size_order": TIBIAL_SIZE_ORDER[size],
            "path": path
        })

    return sorted(
        rows,
        key=lambda x: x["size_order"]
    )


def plane_basis(normal):
    """
    Construct orthonormal basis (u,v) lying in a plane.
    """

    n = unit_vector(normal)

    candidates = [
        np.array([1.0, 0.0, 0.0]),
        np.array([0.0, 1.0, 0.0]),
        np.array([0.0, 0.0, 1.0])
    ]

    ref = min(
        candidates,
        key=lambda a: abs(np.dot(a, n))
    )

    u = np.cross(n, ref)
    u = unit_vector(u)

    v = np.cross(n, u)
    v = unit_vector(v)

    return u, v


def project_to_plane(
    points,
    origin,
    normal
):
    """
    Project 3D points to 2D plane coordinates.
    """

    points = np.asarray(
        points,
        dtype=float
    )

    origin = np.asarray(
        origin,
        dtype=float
    )

    u, v = plane_basis(normal)

    q = points - origin

    xy = np.column_stack([
        q @ u,
        q @ v
    ])

    return xy, u, v


def convex_hull_polygon(points_2d):
    """
    Return convex hull vertices ordered around footprint.
    """

    points_2d = np.asarray(
        points_2d,
        dtype=float
    )

    hull = ConvexHull(
        points_2d
    )

    return points_2d[
        hull.vertices
    ]


def polygon_area(points_2d):
    """2D polygon area."""

    P = np.asarray(
        points_2d,
        dtype=float
    )

    x = P[:, 0]
    y = P[:, 1]

    return float(
        0.5
        *
        abs(
            np.dot(x, np.roll(y, 1))
            -
            np.dot(y, np.roll(x, 1))
        )
    )


def polygon_boundary_samples(
    polygon,
    n_per_edge=50
):
    """
    Sample polygon boundary for distance metrics.
    """

    polygon = np.asarray(
        polygon,
        dtype=float
    )

    pts = []

    for i in range(len(polygon)):

        a = polygon[i]
        b = polygon[(i + 1) % len(polygon)]

        t = np.linspace(
            0.0,
            1.0,
            n_per_edge,
            endpoint=False
        )[:, None]

        pts.append(
            a[None, :]
            +
            t * (b - a)[None, :]
        )

    return np.vstack(pts)


def footprint_metrics(
    bone_polygon,
    implant_polygon,
    percentile=95
):
    """
    Compute research geometric footprint metrics.

    Definitions
    -----------
    Coverage:
        intersection area / bone footprint area * 100

    Underhang:
        percentile distance from bone boundary to nearest
        implant boundary.

    Overhang:
        percentile distance from implant boundary to nearest
        bone boundary.

    RMSE:
        symmetric boundary-distance RMSE.

    These are research geometric metrics, not validated
    clinical thresholds.
    """

    bone_polygon = np.asarray(
        bone_polygon,
        dtype=float
    )

    implant_polygon = np.asarray(
        implant_polygon,
        dtype=float
    )

    bone_area = polygon_area(
        bone_polygon
    )

    implant_area = polygon_area(
        implant_polygon
    )

    coverage = np.nan

    if Polygon is not None:

        pb = Polygon(
            bone_polygon
        ).buffer(0)

        pi = Polygon(
            implant_polygon
        ).buffer(0)

        intersection = pb.intersection(
            pi
        ).area

        if bone_area > 0:
            coverage = (
                intersection
                /
                bone_area
                *
                100.0
            )

    bone_boundary = polygon_boundary_samples(
        bone_polygon
    )

    implant_boundary = polygon_boundary_samples(
        implant_polygon
    )

    tree_implant = cKDTree(
        implant_boundary
    )

    tree_bone = cKDTree(
        bone_boundary
    )

    d_bone_to_implant, _ = (
        tree_implant.query(
            bone_boundary
        )
    )

    d_implant_to_bone, _ = (
        tree_bone.query(
            implant_boundary
        )
    )

    underhang = float(
        np.percentile(
            d_bone_to_implant,
            percentile
        )
    )

    overhang = float(
        np.percentile(
            d_implant_to_bone,
            percentile
        )
    )

    symmetric = np.concatenate([
        d_bone_to_implant,
        d_implant_to_bone
    ])

    rmse = float(
        np.sqrt(
            np.mean(
                symmetric ** 2
            )
        )
    )

    return {
        "Coverage_pct": float(coverage),
        "Underhang_mm": underhang,
        "Overhang_mm": overhang,
        "Footprint_RMSE_mm": rmse,

        "Bone_Area_mm2": float(bone_area),
        "Implant_Area_mm2": float(implant_area)
    }


def implant_contact_footprint(
    implant_mesh,
    plane_normal=np.array([0.0, 0.0, 1.0]),
    low_fraction=0.05
):
    """
    Estimate implant tray contact footprint using vertices
    close to the lower planar side.

    For the corrected research Persona tray library, meshes
    are expected to already be oriented consistently.

    Returns Nx2 native footprint coordinates.
    """

    V = np.asarray(
        implant_mesh.vertices,
        dtype=float
    )

    n = unit_vector(
        plane_normal
    )

    coord = V @ n

    cmin = coord.min()
    cmax = coord.max()

    threshold = (
        cmin
        +
        low_fraction
        *
        (cmax - cmin)
    )

    pts = V[
        coord <= threshold
    ]

    if len(pts) < 10:
        raise ValueError(
            "Insufficient contact-footprint vertices."
        )

    xy, _, _ = project_to_plane(
        pts,
        origin=np.zeros(3),
        normal=n
    )

    return convex_hull_polygon(
        xy
    )


def translate_polygon(
    polygon,
    delta
):
    return (
        np.asarray(
            polygon,
            dtype=float
        )
        +
        np.asarray(
            delta,
            dtype=float
        )
    )


def center_align_polygon(
    implant_polygon,
    bone_polygon
):
    """
    Initial centroid alignment.
    """

    implant_polygon = np.asarray(
        implant_polygon,
        dtype=float
    )

    bone_polygon = np.asarray(
        bone_polygon,
        dtype=float
    )

    shift = (
        bone_polygon.mean(axis=0)
        -
        implant_polygon.mean(axis=0)
    )

    return translate_polygon(
        implant_polygon,
        shift
    ), shift


def evaluate_tibial_library(
    bone_polygon,
    library_root
):
    """
    Evaluate all Persona tibial corrected STL sizes against
    one tibial resection footprint.

    Assumes corrected implant STLs share the same native
    planar orientation.

    Returns
    -------
    pandas.DataFrame
    """

    implants = discover_persona_tibial_implants(
        library_root
    )

    rows = []

    for item in implants:

        mesh = load_mesh_mm(
            item["path"]
        )

        implant_poly = implant_contact_footprint(
            mesh
        )

        implant_poly, shift = center_align_polygon(
            implant_poly,
            bone_polygon
        )

        metrics = footprint_metrics(
            bone_polygon,
            implant_poly
        )

        rows.append({
            "Size": item["size"],

            **metrics,

            "Shift_X_mm": float(shift[0]),
            "Shift_Y_mm": float(shift[1]),

            "Implant_Path": str(item["path"])
        })

    return pd.DataFrame(
        rows
    )
