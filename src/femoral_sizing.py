"""
Femoral sizing for KneeFit3D.

Current production decision:
--------------------------------
Femoral virtual fitting uses the ORIGINAL GitHub TKA implant
library:

S1-S4
M1-M4
L1-L4

The Persona femoral proxy library is retained in the repository
for research/reference, but is not used by the main femoral
fitting pipeline because its available research geometry does
not reproduce the baseline five-cut bone-facing geometry.

Research/prototype use only.
"""

from pathlib import Path
import re

import numpy as np
import pandas as pd

from .mesh_utils import load_mesh_mm


SIZE_ORDER = {
    "S1": 1,
    "S2": 2,
    "S3": 3,
    "S4": 4,

    "M1": 5,
    "M2": 6,
    "M3": 7,
    "M4": 8,

    "L1": 9,
    "L2": 10,
    "L3": 11,
    "L4": 12,
}


def extract_size_code(path):
    """
    Extract S1...L4 from path or filename.
    """
    text = str(path)

    match = re.search(
        r"(?<![A-Za-z0-9])([SML][1-4])(?![A-Za-z0-9])",
        text,
        flags=re.IGNORECASE
    )

    if match is None:
        return None

    return match.group(1).upper()


def discover_femoral_implants(
    library_root,
    side="Left"
):
    """
    Find all original GitHub femoral implants.

    Expected examples:
      Implant(Femoral)Left_M3.stl
      Implant(Femoral)Right_L1.stl
    """

    library_root = Path(library_root)

    pattern_side = str(side).lower()

    rows = []

    for path in library_root.rglob("*.stl"):

        name = path.name.lower()

        if "implant(femoral)" not in name:
            continue

        if pattern_side not in name:
            continue

        size = extract_size_code(path)

        if size is None:
            continue

        rows.append({
            "size": size,
            "size_order": SIZE_ORDER[size],
            "side": side,
            "path": path
        })

    rows = sorted(
        rows,
        key=lambda x: x["size_order"]
    )

    return rows


def measure_femoral_implant(mesh):
    """
    For the original GitHub implant coordinate system:

      X ~= AP
      Y ~= ML
      Z = component depth

    Returns overall AP and ML dimensions.
    """

    ext = np.asarray(
        mesh.extents,
        dtype=float
    )

    return {
        "AP_mm": float(ext[0]),
        "ML_mm": float(ext[1]),
        "Depth_mm": float(ext[2])
    }


def dimensional_rmse(
    bone_ap_mm,
    bone_ml_mm,
    implant_ap_mm,
    implant_ml_mm
):
    """
    AP/ML dimensional mismatch.

    Lower = better.
    """

    return float(
        np.sqrt(
            (
                (implant_ap_mm - bone_ap_mm) ** 2
                +
                (implant_ml_mm - bone_ml_mm) ** 2
            ) / 2.0
        )
    )


def rank_femoral_implants(
    bone_ap_mm,
    bone_ml_mm,
    library_root,
    side="Left"
):
    """
    Rank all original GitHub femoral implant sizes.

    This is a dimensional screening/ranking stage.
    Seating compatibility remains governed by the paired
    original GitHub cutting geometry.

    Returns
    -------
    pandas.DataFrame
    """

    implants = discover_femoral_implants(
        library_root,
        side=side
    )

    if len(implants) == 0:
        raise FileNotFoundError(
            f"No femoral implant STL found under {library_root}"
        )

    rows = []

    for item in implants:

        mesh = load_mesh_mm(
            item["path"]
        )

        dims = measure_femoral_implant(
            mesh
        )

        ap_diff = (
            dims["AP_mm"]
            -
            bone_ap_mm
        )

        ml_diff = (
            dims["ML_mm"]
            -
            bone_ml_mm
        )

        rmse = dimensional_rmse(
            bone_ap_mm,
            bone_ml_mm,
            dims["AP_mm"],
            dims["ML_mm"]
        )

        rows.append({
            "Size": item["size"],
            "Side": side,

            "Implant_AP_mm": dims["AP_mm"],
            "Implant_ML_mm": dims["ML_mm"],

            "Bone_AP_mm": float(bone_ap_mm),
            "Bone_ML_mm": float(bone_ml_mm),

            "AP_Diff_mm": float(ap_diff),
            "ML_Diff_mm": float(ml_diff),

            "Dim_RMSE_mm": float(rmse),

            "Implant_Path": str(item["path"])
        })

    df = pd.DataFrame(rows)

    df = df.sort_values(
        [
            "Dim_RMSE_mm",
            "Size"
        ]
    ).reset_index(drop=True)

    df.insert(
        0,
        "Rank",
        np.arange(1, len(df) + 1)
    )

    return df


def select_best_femoral_implant(
    bone_ap_mm,
    bone_ml_mm,
    library_root,
    side="Left"
):
    """
    Return best dimensional candidate + complete ranking.
    """

    ranking = rank_femoral_implants(
        bone_ap_mm=bone_ap_mm,
        bone_ml_mm=bone_ml_mm,
        library_root=library_root,
        side=side
    )

    best = ranking.iloc[0].to_dict()

    return best, ranking
