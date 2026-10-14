"""
KneeFit3D cutting interface.

The actual five-cut and tibial resection geometry originates
from the baseline GitHub TKA virtual cutting workflow.

This module does NOT recreate manufacturer-specific Persona
cutting geometry.

Research/prototype use only.
"""

from pathlib import Path


SIZE_CODES = [
    "S1", "S2", "S3", "S4",
    "M1", "M2", "M3", "M4",
    "L1", "L2", "L3", "L4"
]


def get_original_size_folder(
    library_root,
    size
):
    """
    Resolve original GitHub size folder.
    """

    size = str(size).upper()

    if size not in SIZE_CODES:
        raise ValueError(
            f"Unknown implant size: {size}"
        )

    root = Path(
        library_root
    )

    matches = list(
        root.rglob(size)
    )

    directories = [
        p
        for p in matches
        if p.is_dir()
        and p.name.upper() == size
    ]

    if not directories:
        raise FileNotFoundError(
            f"Size folder {size} not found under {root}"
        )

    return directories[0]


def get_femoral_component(
    library_root,
    size,
    side="Left"
):
    """
    Return corresponding femoral implant STL for a selected
    original GitHub size.
    """

    folder = get_original_size_folder(
        library_root,
        size
    )

    expected = (
        f"Implant(Femoral){side}_{size}.stl"
    )

    path = folder / expected

    if not path.exists():
        raise FileNotFoundError(path)

    return path


def get_femoral_cutting_block(
    library_root,
    size
):
    """
    Get corresponding femoral cutting block for selected size.
    """

    folder = get_original_size_folder(
        library_root,
        size
    )

    candidates = list(
        folder.glob(
            f"CuttingBlockFemoral*_{size}.stl"
        )
    )

    candidates = [
        p
        for p in candidates
        if "shell" not in p.name.lower()
    ]

    if not candidates:
        raise FileNotFoundError(
            f"Femoral cutting block for {size} not found."
        )

    return candidates[0]


def get_tibial_cutting_block(
    library_root,
    size
):
    """
    Return baseline tibial cutting block paired with the
    original size library.

    Note:
    final KneeFit3D tibial implant selection may use Persona
    research trays, while cutting remains baseline research
    geometry.
    """

    folder = get_original_size_folder(
        library_root,
        size
    )

    candidates = list(
        folder.glob(
            f"CuttingBlockTibia*_{size}.stl"
        )
    )

    candidates = [
        p
        for p in candidates
        if "shell" not in p.name.lower()
    ]

    if not candidates:
        raise FileNotFoundError(
            f"Tibial cutting block for {size} not found."
        )

    return candidates[0]


def get_baseline_tibial_plate(
    library_root,
    size
):
    """
    Optional original GitHub tibial plate reference.
    """

    folder = get_original_size_folder(
        library_root,
        size
    )

    candidates = list(
        folder.glob(
            f"Tibial_Plate*_{size}.stl"
        )
    )

    if not candidates:
        raise FileNotFoundError(
            f"Tibial plate for {size} not found."
        )

    return candidates[0]
