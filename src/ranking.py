"""
KneeFit3D implant ranking logic.

Tibial ranking philosophy
-------------------------
Risk-aware hierarchical ranking:

1. Overhang risk band
2. Underhang
3. Footprint RMSE
4. Coverage

Overhang receives stronger priority because the current
research workflow treats excessive overhang as less desirable
than mild undercoverage.

Thresholds and weights are RESEARCH HEURISTICS.
They are not validated clinical limits.
"""

import numpy as np
import pandas as pd


DEFAULT_TIBIAL_CONFIG = {
    # research-only thresholds
    "overhang_preferred_max_mm": 3.0,
    "overhang_compromise_max_mm": 5.0,

    # within-band scoring weights
    "weight_overhang": 0.45,
    "weight_underhang": 0.25,
    "weight_rmse": 0.20,
    "weight_coverage": 0.10
}


def minmax(series):
    x = np.asarray(
        series,
        dtype=float
    )

    lo = np.nanmin(x)
    hi = np.nanmax(x)

    if hi - lo < 1e-12:
        return np.zeros_like(x)

    return (
        x - lo
    ) / (
        hi - lo
    )


def overhang_risk_band(
    overhang_mm,
    preferred_max=3.0,
    compromise_max=5.0
):
    """
    Lower risk band is better.

    0 = Preferred range
    1 = Acceptable-compromise range
    2 = High-overhang / reject range
    """

    if overhang_mm <= preferred_max:
        return 0

    if overhang_mm <= compromise_max:
        return 1

    return 2


def rank_tibial_implants(
    results,
    config=None
):
    """
    Rank tibial implant candidates.

    Expected columns:
      Size
      Overhang_mm
      Underhang_mm
      Footprint_RMSE_mm
      Coverage_pct

    Method
    ------
    First:
        classify by overhang risk band.

    Then within the same band:
        weighted geometric score.

    Lower score = better.
    """

    if config is None:
        config = DEFAULT_TIBIAL_CONFIG.copy()

    df = results.copy()

    required = [
        "Size",
        "Overhang_mm",
        "Underhang_mm",
        "Footprint_RMSE_mm",
        "Coverage_pct"
    ]

    missing = [
        c
        for c in required
        if c not in df.columns
    ]

    if missing:
        raise ValueError(
            f"Missing ranking columns: {missing}"
        )

    df["Overhang_Risk_Band"] = (
        df["Overhang_mm"]
        .apply(
            lambda x:
            overhang_risk_band(
                x,
                preferred_max=config[
                    "overhang_preferred_max_mm"
                ],
                compromise_max=config[
                    "overhang_compromise_max_mm"
                ]
            )
        )
    )

    df["Norm_Overhang"] = minmax(
        df["Overhang_mm"]
    )

    df["Norm_Underhang"] = minmax(
        df["Underhang_mm"]
    )

    df["Norm_RMSE"] = minmax(
        df["Footprint_RMSE_mm"]
    )

    # coverage higher = better,
    # therefore convert to penalty
    coverage_penalty = (
        100.0
        -
        df["Coverage_pct"].astype(float)
    )

    df["Norm_Coverage_Penalty"] = minmax(
        coverage_penalty
    )

    df["Within_Band_Score"] = (

        config["weight_overhang"]
        *
        df["Norm_Overhang"]

        +

        config["weight_underhang"]
        *
        df["Norm_Underhang"]

        +

        config["weight_rmse"]
        *
        df["Norm_RMSE"]

        +

        config["weight_coverage"]
        *
        df["Norm_Coverage_Penalty"]
    )

    # hierarchy:
    # risk band first,
    # composite score second
    df = df.sort_values(
        [
            "Overhang_Risk_Band",
            "Within_Band_Score",
            "Underhang_mm",
            "Footprint_RMSE_mm",
            "Coverage_pct"
        ],
        ascending=[
            True,
            True,
            True,
            True,
            False
        ]
    ).reset_index(
        drop=True
    )

    df.insert(
        0,
        "Rank",
        np.arange(
            1,
            len(df) + 1
        )
    )

    def category(row):

        if row["Rank"] == 1:
            return "Preferred"

        if row["Overhang_Risk_Band"] <= 1:
            return "Acceptable-Compromise"

        return "Reject"

    df["Recommendation"] = df.apply(
        category,
        axis=1
    )

    return df


def select_best_tibial_implant(
    results,
    config=None
):
    """
    Return preferred candidate + ranked dataframe.
    """

    ranked = rank_tibial_implants(
        results,
        config=config
    )

    best = ranked.iloc[0].to_dict()

    return best, ranked
