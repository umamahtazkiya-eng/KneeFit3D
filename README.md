# KneeFit3D

**KneeFit3D** is a research prototype for patient-specific knee 3D reconstruction, virtual bone resection, implant sizing, and virtual TKA fitting.

> **Important:** This repository is for research and prototype development only. It is not validated for clinical diagnosis, implant ordering, surgical navigation, or patient treatment.

---

# 1. Current Production Strategy

## Femoral Component

The current femoral pipeline uses the original GitHub TKA implant library:

```text
S1 S2 S3 S4
M1 M2 M3 M4
L1 L2 L3 L4
```

These components are paired with the original baseline cutting geometry and cutting blocks.

The Persona femoral research STL library is retained only for research/reference purposes and is not used in the current production femoral seating pipeline.

Reason: the available Persona femoral proxy meshes reproduce the target external AP/ML dimensions, but their bone-facing geometry does not reproduce the original five-cut interface.

## Tibial Component

The tibial fitting pipeline uses the corrected Persona tibial research proxy library:

```text
A B C D E F G H J
```

All candidate sizes are evaluated for each input tibial resection. Do not hard-code Size E.

Size E was the preferred candidate only for one development example.

---

# 2. Repository Structure

```text
KneeFit3D/
├── README.md
├── requirements.txt
├── src/
│   ├── __init__.py
│   ├── mesh_utils.py
│   ├── femoral_sizing.py
│   ├── tibial_sizing.py
│   ├── ranking.py
│   ├── fitting.py
│   └── cutting.py
├── configs/
│   └── fitting_config.yaml
└── data/
    ├── implants/
    │   ├── github_original/
    │   │   └── 12_size_range/
    │   └── persona/
    │       ├── femoral/
    │       └── tibial/
    ├── metadata/
    └── size_charts/
```

---

# 3. Coordinate Convention

The current baseline/preprocessed bone coordinate system is:

```text
X = AP  (Anterior–Posterior)
Y = ML  (Medial–Lateral)
Z = Proximal–Distal
```

Backend developers should not assume that arbitrary STL files already follow this coordinate system. Bone preprocessing and orientation must occur before sizing or fitting.

---

# 4. Backend Pipeline

```text
AP + LAT X-ray
        ↓
3D Reconstruction
        ↓
Bone Mesh
        ↓
Mesh Preprocessing / Coordinate Alignment
        ↓
        ├──────────────────────────────┐
        │                              │
      FEMUR                          TIBIA
        │                              │
Measure distal AP/ML             Tibial resection
        │                              │
Original TKA library             Resection footprint
S1–L4 screening                       │
        │                        Evaluate Persona A–J
Select femoral size                    │
        │                        Coverage
Load matching implant            Underhang
+ cutting block                  Overhang
        │                        Footprint RMSE
Virtual fitting                        │
        │                        Risk-aware ranking
        │                              │
        └──────────────┬───────────────┘
                       ↓
                Backend JSON result
                       ↓
                  Web frontend
```

---

# 5. Python Modules

## `src/mesh_utils.py`

General mesh helpers:

```text
load_mesh_mm()
unit_vector()
transform_mesh()
mesh_center()
measure_distal_envelope()
```

## `src/femoral_sizing.py`

Discovers and ranks the original 12-size femoral implant library.

Available sizes:

```text
S1–S4
M1–M4
L1–L4
```

The current dimensional screening uses AP and ML mismatch.

For each candidate:

```text
AP_Diff = Implant_AP - Bone_AP
ML_Diff = Implant_ML - Bone_ML
```

and:

```text
Dim_RMSE = sqrt((AP_Diff² + ML_Diff²) / 2)
```

Lower `Dim_RMSE_mm` indicates better dimensional agreement.

Primary functions:

```python
rank_femoral_implants(...)
select_best_femoral_implant(...)
```

Do not hard-code M3.

## `src/tibial_sizing.py`

Evaluates corrected Persona tibial research STL sizes against the tibial resection footprint.

Current metrics:

- Coverage
- Underhang
- Overhang
- Footprint RMSE

## `src/ranking.py`

Implements the current risk-aware tibial ranking strategy.

Priority:

```text
1. Overhang risk band
2. Underhang
3. Footprint RMSE
4. Coverage
```

Current research overhang bands:

```text
Preferred:               overhang <= 3.0 mm
Acceptable-Compromise:   3.0 mm < overhang <= 5.0 mm
High-overhang:           overhang > 5.0 mm
```

These are research heuristics, not clinically validated thresholds.

Within the same overhang band, the current research score uses:

```text
Overhang : 0.45
Underhang: 0.25
RMSE     : 0.20
Coverage : 0.10
```

Weights are stored in `configs/fitting_config.yaml`.

## `src/cutting.py`

Resolves the corresponding implant and cutting-block assets.

Important: `cutting.py` does not yet reproduce the full Blender boolean bone-cutting workflow in pure Python.

The actual cutting execution still originates from the original virtual TKA / Blender workflow.

---

# 6. Femoral Implant Library

Original femoral components are stored in:

```text
data/implants/github_original/12_size_range/
```

Use the femoral implant and matching femoral cutting block belonging to the selected size.

---

# 7. Tibial Fitting

Corrected Persona tibial meshes are stored in:

```text
data/implants/persona/tibial/
```

Coverage is defined as:

```text
Coverage = intersection area / bone footprint area × 100%
```

Lower underhang, lower overhang, and lower footprint RMSE are generally preferred.

---

# 8. Development Example

For one development case:

```text
Persona Tibial Size E
Coverage       ≈ 95.44 %
Underhang      ≈ 2.41 mm
Overhang       ≈ 2.36 mm
Footprint RMSE ≈ 1.32 mm
```

This is an example only. Do not hard-code Size E.

---

# 9. Basic Backend Usage

```python
from src.mesh_utils import load_mesh_mm, measure_distal_envelope
from src.femoral_sizing import select_best_femoral_implant
from src.ranking import select_best_tibial_implant
```

Example femoral sizing:

```python
femur = load_mesh_mm('patient_femur.stl')

dims = measure_distal_envelope(
    femur,
    distal_fraction=0.25
)

best_femur, femur_ranking = select_best_femoral_implant(
    bone_ap_mm=dims['AP_mm'],
    bone_ml_mm=dims['ML_mm'],
    library_root='data/implants/github_original/12_size_range',
    side='Left'
)
```

---

# 10. Recommended Backend JSON

```json
{
  "femur": {
    "library": "github_original",
    "selected_size": "M3",
    "implant_file": "Implant(Femoral)Left_M3.stl"
  },
  "tibia": {
    "library": "persona_corrected_research",
    "selected_size": "E",
    "metrics": {
      "coverage_pct": 95.44,
      "underhang_mm": 2.41,
      "overhang_mm": 2.36,
      "footprint_rmse_mm": 1.32
    }
  }
}
```

All values above are development examples and must not be hard-coded.

---

# 11. Persona Geometry Disclaimer

The Persona STL files in this repository are research proxy geometries and are not official Zimmer Biomet OEM CAD files.

Persona femoral meshes are retained for research/reference only.

Persona tibial meshes are used for research footprint fitting and ranking.

---

# 12. Backend Rules

```text
DO:
✓ calculate implant size for every patient
✓ load thresholds and weights from config
✓ preserve millimetre units
✓ preserve AP/ML/PD coordinate convention
✓ return complete ranking metrics when needed

DO NOT:
✗ hard-code M3
✗ hard-code tibial Size E
✗ assume Persona STL is official OEM CAD
✗ interpret research thresholds as clinical limits
✗ assume arbitrary STL orientation is already correct
✗ assume cutting.py already performs Blender boolean cutting
```

---

# 13. Installation

```bash
pip install -r requirements.txt
```

Main dependencies:

```text
numpy
pandas
scipy
trimesh
shapely
PyYAML
```

---

# 14. Backend Team — Start Here

Read these files first:

```text
src/mesh_utils.py
src/femoral_sizing.py
src/tibial_sizing.py
src/ranking.py
src/cutting.py
configs/fitting_config.yaml
```

Recommended implementation sequence:

```text
1. Load reconstructed bone STL
2. Normalize coordinate system and units
3. Measure bone geometry
4. Run implant sizing
5. Resolve implant/cutting assets
6. Run tibial footprint evaluation
7. Run ranking
8. Return selected components + metrics
9. Send STL paths to the 3D viewer
```

Implant-selection logic should remain in the backend Python modules and should not be duplicated independently in the frontend.
