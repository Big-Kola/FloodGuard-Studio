# FloodGuard Studio — Engineering Methods and Limitations

## 1. Purpose and scope

FloodGuard Studio is a **preliminary engineering screening and educational tool**. It
connects three simplified calculations:

1. an estimated peak stormwater runoff rate from the Rational Method;
2. an estimated full-flow capacity for a circular pipe from Manning's equation; and
3. a capacity-utilisation ratio used to flag configurations for further review.

The tool is deliberately narrow. It does **not** calculate runoff volume, a runoff
hydrograph, flood depth, flood extent, structural safety, or actual drainage-system
performance. It does not verify compliance with any design standard or authority
requirement. Every result depends on user-supplied inputs and the assumptions below.

## 2. Rational Method

### 2.1 Equation

The Rational Method is commonly written as:

```text
Q = C · i · A
```

where:

- `Q` = peak runoff rate (m³/s);
- `C` = dimensionless runoff coefficient (0 to 1);
- `i` = rainfall intensity (m/s); and
- `A` = catchment area (m²).

FloodGuard Studio accepts rainfall intensity in millimetres per hour and area in
hectares. Converting those inputs to SI units:

```text
i [m/s]  = I [mm/h] / 1000 / 3600
A [m²]   = A [ha] × 10,000
```

Therefore:

```text
Q = C × (I / 1000 / 3600) × (A × 10,000)
  = C × I × A × (10,000 / 3,600,000)
  = C × I × A / 360
```

The implementation uses the exact conversion factor `1/360`, represented in Python as
`1.0 / 360.0` and displayed as `0.0027777778` where appropriate:

```text
Q [m³/s] = (1/360) × C × I [mm/h] × A [ha]
```

The factor is a unit conversion, not an empirical calibration coefficient.

### 2.2 Required inputs

| Input | Symbol | Unit | Accepted range |
|---|---|---|---|
| Catchment area | A | ha | > 0 |
| Rainfall intensity | I | mm/h | ≥ 0 |
| Runoff coefficient | C | dimensionless | 0 ≤ C ≤ 1 |

All numeric inputs must be finite. Boolean values, strings, missing values, NaN and
positive or negative infinity are rejected.

### 2.3 Interpretation of rainfall intensity

`I` is a **design rainfall intensity**. The user must choose it for a specific:

- rainfall duration;
- return period or design event;
- local intensity-duration-frequency (IDF) relationship; and
- climate or authority assumption.

Entering an intensity does not by itself establish a return period. The choice of
duration should be consistent with the catchment response time and the design method in
use. Where the time of concentration is not explicitly calculated, the user is
responsible for demonstrating that the selected duration is appropriate.

### 2.4 Assumptions and limitations

The Rational Method is a simplified peak-flow approximation. Its use in FloodGuard Studio
assumes:

- the catchment is small enough for the method to be defensible;
- rainfall intensity is uniform over the catchment and the design duration;
- the runoff coefficient is a single representative value;
- the peak runoff occurs when the contributing area is fully active;
- storage, routing, infiltration variation, antecedent moisture and snow/groundwater
  effects are not explicitly represented; and
- land-use, slope and soil information have been used to select a defensible `C`.

The method does not produce a hydrograph, runoff volume, flood depth or flood extent. It
should not be used for large, complex, strongly heterogeneous or storage-dominated
catchments without a more appropriate hydrological method.

## 3. Manning's equation for full-flow pipe capacity

### 3.1 Equation

For steady, uniform flow in SI units:

```text
Q = (1/n) · A · R^(2/3) · S^(1/2)
```

where:

- `Q` = estimated flow capacity (m³/s);
- `n` = Manning roughness coefficient (dimensionless, empirical);
- `A` = cross-sectional flow area (m²);
- `R` = hydraulic radius (m), equal to area divided by wetted perimeter; and
- `S` = hydraulic energy slope (m/m).

For a circular pipe flowing full with internal diameter `D`:

```text
A = πD² / 4
P = πD
R = A / P = D / 4
```

FloodGuard Studio assumes the hydraulic energy slope equals the specified pipe slope. It
accepts slope as a percentage and converts it before calculation:

```text
S [m/m] = slope [%] / 100
```

For example, `0.5%` becomes `0.005 m/m`, not `0.5 m/m`. This distinction is tested
explicitly.

### 3.2 Required inputs

| Input | Symbol | Unit | Accepted range |
|---|---|---|---|
| Internal pipe diameter | D | m | > 0 |
| Manning roughness coefficient | n | dimensionless | > 0 |
| Pipe slope | S | % | > 0 |

All numeric inputs must be finite. A zero or negative slope is rejected because the
simplified uniform-flow model requires a positive energy gradient.

### 3.3 Assumptions and limitations

The capacity result assumes:

- a circular pipe flowing full;
- steady, uniform flow;
- the specified pipe slope approximates the hydraulic energy slope;
- a single representative Manning roughness coefficient;
- no inlet loss, outlet control, surcharge, backwater, blockage, sediment transport or
  network routing; and
- no verification against local design standards, velocity criteria or structural
  requirements.

Real drainage systems commonly operate part-full, experience inlet and outlet control,
and may surcharge. The full-flow capacity calculated here is therefore an estimate for
screening, not a prediction of actual system performance or flood risk.

## 4. Capacity utilisation and classification

Capacity utilisation is:

```text
Utilisation [%] = (Estimated peak runoff / Estimated full-flow capacity) × 100
```

The calculation requires a positive estimated capacity and a non-negative runoff value.

FloodGuard Studio applies three illustrative bands:

| Utilisation | Classification |
|---|---|
| `< 80%` | Within calculated capacity |
| `80%` to `100%` inclusive | Approaching calculated capacity |
| `> 100%` | Calculated demand exceeds capacity |

The exact boundaries are tested: 80% is in the approaching band, 100% is in the
approaching band, and any value above 100% is in the exceedance band.

These thresholds are **software screening indicators**, not universal engineering design
requirements. Local standards, consequence of failure, blockage risk, climate allowances
and asset criticality may justify different criteria. A result below 100% does not
establish that a system is safe, flood-free or compliant. A result above 100% is a flag
for further assessment, not a prediction of flood depth or extent.

## 5. Worked reference calculations

### 5.1 Test case A — Rational Method

Inputs:

- `A = 5 ha`
- `I = 90 mm/h`
- `C = 0.75`

Using the SI conversion:

```text
Q = 0.75 × (90 / 1000 / 3600) × (5 × 10,000)
  = 0.75 × 0.000025 × 50,000
  = 0.9375 m³/s
```

Using the implemented factor:

```text
Q = (1/360) × 0.75 × 90 × 5
  = 0.9375 m³/s
  = 937.5 L/s
```

### 5.2 Test case B — Manning full-flow capacity

Inputs:

- `D = 1.0 m`
- `n = 0.013`
- slope = `0.5%`, so `S = 0.005 m/m`

Geometry:

```text
A = π(1.0)² / 4       = 0.7853981634 m²
P = π(1.0)            = 3.1415926536 m
R = A / P = D / 4     = 0.25 m
```

Manning:

```text
R^(2/3)  = 0.25^(2/3)   = 0.3968502630
S^(1/2)  = 0.005^(1/2)  = 0.0707106781

Q = (1 / 0.013) × 0.7853981634 × 0.3968502630 × 0.0707106781
  ≈ 1.6953454447 m³/s
```

Mean full-flow velocity:

```text
V = Q / A = 1.6953454447 / 0.7853981634 ≈ 2.1585808621 m/s
```

### 5.3 Utilisation

Comparing the reference runoff with the reference capacity:

```text
Utilisation = 0.9375 / 1.6953454447 × 100 ≈ 55.30%
```

This falls in the "Within calculated capacity" band. It does not, by itself, demonstrate
design compliance or flood-free operation.

## 6. Desktop application and project files

FloodGuard Studio is a native PySide6 desktop application. It does not start an internal
web server, browser session or cloud service. The interface, charts, reports and project
files are all handled in the local process.

Projects are stored as human-readable JSON with the `.fgsproj` extension. Schema version
`1` records:

- application name and version;
- project metadata (name, number, client, location, engineer, description and dates);
- catchment area, design rainfall intensity, runoff coefficient and notes;
- schematic node coordinates, node types and invert levels;
- pipe endpoints, diameter, length, slope, Manning `n`, material and notes; and
- saved scenario definitions.

On load, the complete file is parsed and checked before the interface accepts it.
Structural errors, unsupported schema versions, unknown node types, broken pipe
connectivity, duplicate identifiers, duplicate scenario names and invalid engineering
values are rejected. A project is validated again before saving. Saves write a temporary
file and atomically replace the destination so an interrupted write does not silently
produce a partial project.

The interactive calculations, scenario table and report exports all use the same core
functions. Running the background analysis task does not implement a second calculation
path. Node X/Y coordinates are schematic drawing positions only, not survey coordinates.
Node invert elevations are stored as project data but are not used by the current
screening equations because no network hydraulic model is implemented.

Application preferences are stored separately from engineering projects and are limited
to local directories, new-project defaults, delete-confirmation and scope-note display
settings. No preference contains an engineering result.

## 7. Verification approach

The automated pytest suite includes independent reference calculations and boundary
tests. It checks:

- the Rational Method reference result of `0.9375 m³/s`;
- the direct SI unit conversion that produces the same result;
- the Manning reference result of approximately `1.695345 m³/s`;
- full-pipe area, wetted perimeter and hydraulic radius;
- capacity divided by area for mean velocity;
- correct percent-to-m/m slope conversion and the consequence of confusing the two;
- zero runoff coefficient and zero rainfall intensity;
- negative or zero catchment area;
- invalid diameter, roughness and slope;
- runoff coefficient outside 0 to 1;
- non-finite and non-numeric inputs;
- exact 80% and 100% classification boundaries;
- scenario evaluation against the underlying engineering functions;
- CSV generation and PDF generation.

Run the suite with:

```powershell
python -m pytest -q
```

The same suite runs in GitHub Actions on Python 3.11 and 3.12. It also includes
headless Qt tests for application startup, page navigation, interactive asset selection,
network editing, undo/redo, catchment recalculation, project round trips and report
generation. The reference values are derived from the equations and unit conversions
documented above; they are not copied from unverified software output. No claim of
validation against measured field data is made.

## 8. Why this application does not calculate flood extent or depth

A peak-flow estimate is not a flood map. Calculating flood depth or extent requires at
minimum:

- a representation of channel, pipe and surface geometry;
- a stage-discharge or hydraulic relationship;
- flow routing and continuity through the drainage network;
- boundary conditions at inlets, outlets, rivers, tides or pumps;
- floodplain topography and surface flow paths; and
- calibration or verification data.

FloodGuard Studio calculates one peak runoff rate and one full-flow pipe capacity. It does
not solve a network hydraulic model, a surface-flow model or a stage relationship.
Consequently it cannot output flood depth, flood extent, damage or safety consequences.

## 9. Additional data and modelling needed for real-world assessment

A real drainage assessment would typically require:

- verified topographic survey, pipe invert levels and internal dimensions;
- a connected drainage network with node and link data;
- inlet and outlet geometry and control levels;
- outfall water levels and receiving-water boundary conditions;
- local IDF curves, design storm temporal patterns and climate-change allowances;
- land use, soil, imperviousness and connectivity data for runoff estimation;
- pipe material, age, condition, roughness and blockage/maintenance information;
- part-full flow, surcharge, backwater and network routing analysis;
- sediment, debris and erosion considerations;
- floodplain topography and surface flood pathways;
- structural, constructability and whole-life considerations; and
- review against the applicable local standards and authority requirements.

## 10. References

- ASCE (1992). *Design and Construction of Urban Stormwater Management Systems*.
  ASCE Manuals and Reports on Engineering Practice No. 77.
- Chow, V. T. (1959). *Open-Channel Hydraulics*. McGraw-Hill.
- Chow, V. T., Maidment, D. R., & Mays, L. W. (1988). *Applied Hydrology*. McGraw-Hill.
- CIRIA (2015). *The SUDS Manual*, C753.
- Federal Highway Administration (2009). *Urban Drainage Design Manual*, Hydraulic
  Engineering Circular No. 22, 3rd edition (FHWA-NHI-10-009).
- Manning, R. (1891). On the flow of water in open channels and pipes. *Transactions of
  the Institution of Civil Engineers of Ireland*, 20, 161–207.
- USDA Natural Resources Conservation Service (1986). *Urban Hydrology for Small
  Watersheds*, Technical Release 55.

These references identify the engineering basis of the methods. Their inclusion does not
imply that FloodGuard Studio has been validated, approved or certified against them.

## 11. Professional disclaimer

FloodGuard Studio is provided for education, preliminary screening and portfolio
demonstration. It must not be used as the sole basis for drainage design, flood-risk
assessment, permitting, construction or emergency planning. Users are responsible for
verifying all inputs, selecting appropriate methods, checking local requirements and
obtaining review by a qualified engineer.
