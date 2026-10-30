# Portfolio Material

## CV entry

**FloodGuard Studio — Offline Urban Drainage Screening Desktop Application** |
Python, PySide6, NumPy/Pandas, ReportLab, pytest-qt, PyInstaller, GitHub Actions

- Built a native engineering desktop application that estimates peak stormwater runoff
  with the Rational Method and circular-pipe full-flow capacity with Manning's equation.
- Implemented a versioned `.fgsproj` project model with schema validation, atomic saves,
  an interactive QGraphics network editor, editable properties, undo/redo, scenario
  comparison, pyqtgraph charts and PDF/CSV reporting.
- Verified engineering references, persistence and headless Qt interaction workflows
  with a 149-test pytest suite using the offscreen Qt platform.
- Configured cross-version GitHub Actions checks for formatting, lint, compilation,
  imports and tests on Python 3.11 and 3.12, plus a reproducible PyInstaller build script
  for Windows.
- Documented equations, SI conversions, assumptions, model limits and professional scope
  with reproducible screenshots and public reference calculations.

## Short portfolio description

FloodGuard Studio is a preliminary stormwater screening application built as a native
Python/PySide6 desktop tool. It connects design rainfall, catchment runoff, circular pipe
capacity and capacity utilisation in one transparent workflow, with a schematic network
editor, project files, scenario comparisons, interactive charts and exportable engineering
reports. The calculations are separated from the interface and covered by automated
reference, boundary and headless GUI tests. The project is explicitly limited to
educational and preliminary screening use: it does not route a drainage network, model
part-full or surcharge conditions, calculate flood depth or extent, or certify a design.

## Engineering and software focus

The project demonstrates:

- applied hydrology and hydraulics using the Rational Method and Manning's equation;
- explicit separation between calculation core, persistence and presentation;
- validated project schemas and defensive handling of engineering inputs;
- native desktop interaction design with Qt Widgets and QGraphicsView;
- automated testing of both calculation results and interactive workflows;
- reproducible local reporting and offline operation; and
- clear communication of engineering assumptions and professional limitations.

## Accurate scope statement

FloodGuard Studio is a portfolio prototype, not a commercial or validated engineering
product. It performs simplified peak-flow and independent full-flow pipe capacity
screening, scenario comparisons and report generation. It does not provide flood
forecasting, flood depth or extent mapping, sensor integration, real-time monitoring,
machine learning, a validated digital twin or evidence of reduced flooding. Any use
beyond education and preliminary screening requires additional data, detailed hydraulic
modelling and review by a qualified engineer.
