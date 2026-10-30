"""CSV and PDF generation for FloodGuard Studio assessment results."""

from __future__ import annotations

from datetime import datetime
from io import BytesIO
from xml.sax.saxutils import escape

import pandas as pd
from reportlab.lib import colors
from reportlab.lib.enums import TA_LEFT
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import mm
from reportlab.platypus import (
    PageBreak,
    Paragraph,
    SimpleDocTemplate,
    Spacer,
    Table,
    TableStyle,
)

from floodguard.analysis import PipeAnalysis, ProjectAnalysis
from floodguard.hydraulics import CapacityAssessment, HydraulicResult
from floodguard.project import EngineeringProject
from floodguard.runoff import RunoffResult
from floodguard.scenarios import ScenarioResult

NAVY = colors.HexColor("#0B3C5D")
MUTED_BLUE = colors.HexColor("#3E6B89")
PALE_BLUE = colors.HexColor("#E8EEF5")
NEUTRAL = colors.HexColor("#5B6770")
INK = colors.HexColor("#1F2933")
AMBER = colors.HexColor("#B7791F")
RED = colors.HexColor("#B42318")
GREEN = colors.HexColor("#2E7D5B")

DISCLAIMER = (
    "FloodGuard Studio is a preliminary engineering screening and educational tool. "
    "It applies simplified rainfall-runoff and uniform-flow equations to user-supplied "
    "inputs and screens individual pipes independently. It does not perform network-wide "
    "hydraulic routing, predict flood depth or extent, or establish structural safety. "
    "It must not be used as the sole basis for design, permitting or public-safety decisions."
)


PIPE_RESULT_COLUMNS = [
    "Pipe",
    "ID",
    "From node",
    "To node",
    "Diameter (m)",
    "Length (m)",
    "Slope (%)",
    "Manning n",
    "Full-flow capacity (m3/s)",
    "Full-flow velocity (m/s)",
    "Peak runoff (m3/s)",
    "Capacity utilisation (%)",
    "Classification",
]

RESULT_COLUMNS = [
    "Scenario",
    "Catchment area (ha)",
    "Runoff coefficient",
    "Rainfall intensity (mm/h)",
    "Pipe diameter (m)",
    "Manning n",
    "Slope (%)",
    "Peak runoff (m3/s)",
    "Peak runoff (L/s)",
    "Pipe capacity (m3/s)",
    "Full-flow velocity (m/s)",
    "Capacity utilisation (%)",
    "Classification",
    "Description",
]


def scenario_results_to_dataframe(results: list[ScenarioResult]) -> pd.DataFrame:
    """Convert scenario results into a tidy comparison table."""
    records = []
    for result in results:
        records.append(
            {
                "Scenario": result.name,
                "Catchment area (ha)": result.scenario.catchment_area_ha,
                "Runoff coefficient": result.scenario.runoff_coefficient,
                "Rainfall intensity (mm/h)": result.scenario.rainfall_intensity_mm_h,
                "Pipe diameter (m)": result.scenario.pipe_diameter_m,
                "Manning n": result.scenario.manning_n,
                "Slope (%)": result.scenario.slope_percent,
                "Peak runoff (m3/s)": result.runoff.peak_runoff_m3_s,
                "Peak runoff (L/s)": result.runoff.peak_runoff_l_s,
                "Pipe capacity (m3/s)": result.hydraulics.capacity_m3_s,
                "Full-flow velocity (m/s)": result.hydraulics.full_flow_velocity_m_s,
                "Capacity utilisation (%)": result.assessment.utilisation_percent,
                "Classification": result.assessment.classification,
                "Description": result.description,
            }
        )
    return pd.DataFrame(records, columns=RESULT_COLUMNS)


def build_scenario_csv(results: list[ScenarioResult]) -> bytes:
    """Return scenario results as UTF-8 CSV bytes."""
    dataframe = scenario_results_to_dataframe(results)
    return dataframe.to_csv(index=False).encode("utf-8-sig")


def _fmt(value: float, digits: int = 4) -> str:
    return f"{value:,.{digits}f}"


def _p(text: str, style: ParagraphStyle) -> Paragraph:
    return Paragraph(text, style)


def _pdf_styles() -> dict[str, ParagraphStyle]:
    base = getSampleStyleSheet()
    return {
        "title": ParagraphStyle(
            "FGTitle",
            parent=base["Title"],
            fontName="Helvetica-Bold",
            fontSize=24,
            leading=28,
            textColor=NAVY,
            alignment=TA_LEFT,
            spaceAfter=4,
        ),
        "subtitle": ParagraphStyle(
            "FGSubtitle",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=11,
            leading=15,
            textColor=MUTED_BLUE,
            spaceAfter=2,
        ),
        "meta": ParagraphStyle(
            "FGMeta",
            parent=base["Normal"],
            fontName="Helvetica",
            fontSize=8.5,
            leading=12,
            textColor=NEUTRAL,
        ),
        "h1": ParagraphStyle(
            "FGH1",
            parent=base["Heading1"],
            fontName="Helvetica-Bold",
            fontSize=13,
            leading=17,
            textColor=NAVY,
            spaceBefore=12,
            spaceAfter=6,
        ),
        "body": ParagraphStyle(
            "FGBody",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=9,
            leading=13,
            textColor=INK,
            spaceAfter=5,
        ),
        "small": ParagraphStyle(
            "FGSmall",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=8,
            leading=11,
            textColor=NEUTRAL,
            spaceAfter=3,
        ),
        "bullet": ParagraphStyle(
            "FGBullet",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=8.5,
            leading=12,
            textColor=INK,
            leftIndent=11,
            bulletIndent=2,
            spaceAfter=3,
        ),
        "cell": ParagraphStyle(
            "FGCell",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=7.2,
            leading=9,
            textColor=INK,
        ),
        "cell_header": ParagraphStyle(
            "FGCellHeader",
            parent=base["BodyText"],
            fontName="Helvetica-Bold",
            fontSize=7.2,
            leading=9,
            textColor=colors.white,
        ),
        "disclaimer": ParagraphStyle(
            "FGDisclaimer",
            parent=base["BodyText"],
            fontName="Helvetica",
            fontSize=8.2,
            leading=11.5,
            textColor=INK,
        ),
    }


def _data_table(
    header: list[str],
    rows: list[list[str]],
    styles: dict[str, ParagraphStyle],
    widths: list[float] | None = None,
) -> Table:
    data = [[_p(escape(text), styles["cell_header"]) for text in header]]
    data.extend(
        [[_p(escape(str(text)), styles["cell"]) for text in row] for row in rows]
    )
    table = Table(data, colWidths=widths, repeatRows=1, hAlign="LEFT")
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), NAVY),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#B8C4CE")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, PALE_BLUE]),
                ("LEFTPADDING", (0, 0), (-1, -1), 4),
                ("RIGHTPADDING", (0, 0), (-1, -1), 4),
                ("TOPPADDING", (0, 0), (-1, -1), 3),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3),
            ]
        )
    )
    return table


def _key_value_table(
    rows: list[tuple[str, str]], styles: dict[str, ParagraphStyle]
) -> Table:
    data = [
        [
            _p(escape(label), styles["cell_header"]),
            _p(escape(value), styles["cell"]),
        ]
        for label, value in rows
    ]
    table = Table(data, colWidths=[70 * mm, 105 * mm], hAlign="LEFT")
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (0, -1), NAVY),
                ("BACKGROUND", (1, 0), (1, -1), colors.white),
                ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#B8C4CE")),
                ("VALIGN", (0, 0), (-1, -1), "TOP"),
                ("LEFTPADDING", (0, 0), (-1, -1), 5),
                ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                ("TOPPADDING", (0, 0), (-1, -1), 3.5),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 3.5),
            ]
        )
    )
    return table


def _page_footer(canvas, document) -> None:
    canvas.saveState()
    canvas.setStrokeColor(colors.HexColor("#CBD5DF"))
    canvas.setLineWidth(0.5)
    canvas.line(20 * mm, 15 * mm, 190 * mm, 15 * mm)
    canvas.setFont("Helvetica", 7.5)
    canvas.setFillColor(NEUTRAL)
    canvas.drawString(
        20 * mm, 10 * mm, "FloodGuard Studio | Preliminary engineering screening"
    )
    canvas.drawRightString(190 * mm, 10 * mm, f"Page {document.page}")
    canvas.restoreState()


def build_pdf_report(
    runoff: RunoffResult,
    hydraulics: HydraulicResult,
    assessment: CapacityAssessment,
    scenario_results: list[ScenarioResult] | None = None,
    generated_at: datetime | None = None,
) -> bytes:
    """Build a PDF engineering summary from actual calculated results."""
    generated = (generated_at or datetime.now()).strftime("%d %B %Y, %H:%M")
    buffer = BytesIO()
    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=20 * mm,
        rightMargin=20 * mm,
        topMargin=17 * mm,
        bottomMargin=20 * mm,
        title="FloodGuard Studio Engineering Report",
        author="FloodGuard Studio",
        subject="Preliminary urban drainage capacity and rainfall scenario assessment",
    )
    styles = _pdf_styles()
    story: list[object] = []

    story.append(_p("FloodGuard Studio", styles["title"]))
    story.append(
        _p(
            "Urban Drainage Capacity and Rainfall Scenario Assessment",
            styles["subtitle"],
        )
    )
    story.append(_p(f"Report generated: {escape(generated)}", styles["meta"]))
    story.append(Spacer(1, 7))

    disclaimer_box = Table(
        [[_p(f"<b>Important notice.</b> {escape(DISCLAIMER)}", styles["disclaimer"])]],
        colWidths=[170 * mm],
        hAlign="LEFT",
    )
    disclaimer_box.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FFF7E6")),
                ("BOX", (0, 0), (-1, -1), 0.8, AMBER),
                ("LEFTPADDING", (0, 0), (-1, -1), 7),
                ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.append(disclaimer_box)

    story.append(_p("1. Engineering inputs", styles["h1"]))
    story.append(
        _key_value_table(
            [
                ("Catchment area", f"{_fmt(runoff.catchment_area_ha, 3)} ha"),
                (
                    "Rainfall intensity",
                    f"{_fmt(runoff.rainfall_intensity_mm_h, 2)} mm/h",
                ),
                ("Runoff coefficient", f"{_fmt(runoff.runoff_coefficient, 3)} (-)"),
                ("Pipe internal diameter", f"{_fmt(hydraulics.diameter_m, 3)} m"),
                (
                    "Manning roughness coefficient",
                    f"{_fmt(hydraulics.manning_n, 4)} (-)",
                ),
                (
                    "Pipe slope",
                    f"{_fmt(hydraulics.slope_percent, 3)}% ({_fmt(hydraulics.slope_fraction, 5)} m/m)",
                ),
            ],
            styles,
        )
    )

    story.append(_p("2. Rational Method runoff estimate", styles["h1"]))
    story.append(
        _p(
            "Q = (1/360) x C x I x A, with I in mm/h and A in hectares, gives Q in m3/s.",
            styles["body"],
        )
    )
    story.append(
        _key_value_table(
            [
                ("Estimated peak runoff", f"{_fmt(runoff.peak_runoff_m3_s, 4)} m3/s"),
                ("Estimated peak runoff", f"{_fmt(runoff.peak_runoff_l_s, 2)} L/s"),
                (
                    "Substitution",
                    (
                        f"(1/360) x {_fmt(runoff.runoff_coefficient, 3)} x "
                        f"{_fmt(runoff.rainfall_intensity_mm_h, 2)} x "
                        f"{_fmt(runoff.catchment_area_ha, 3)}"
                    ),
                ),
            ],
            styles,
        )
    )

    story.append(_p("3. Manning full-flow capacity estimate", styles["h1"]))
    story.append(
        _p(
            "Q = (1/n) x A x R^(2/3) x S^(1/2), with a full circular section and "
            "the hydraulic energy slope assumed equal to the pipe slope.",
            styles["body"],
        )
    )
    story.append(
        _key_value_table(
            [
                (
                    "Cross-sectional area",
                    f"{_fmt(hydraulics.cross_section_area_m2, 5)} m2",
                ),
                ("Wetted perimeter", f"{_fmt(hydraulics.wetted_perimeter_m, 5)} m"),
                ("Hydraulic radius", f"{_fmt(hydraulics.hydraulic_radius_m, 5)} m"),
                (
                    "Estimated full-flow capacity",
                    f"{_fmt(hydraulics.capacity_m3_s, 4)} m3/s",
                ),
                (
                    "Estimated full-flow capacity",
                    f"{_fmt(hydraulics.capacity_l_s, 2)} L/s",
                ),
                (
                    "Estimated mean velocity at full flow",
                    f"{_fmt(hydraulics.full_flow_velocity_m_s, 3)} m/s",
                ),
            ],
            styles,
        )
    )

    story.append(_p("4. Capacity utilisation assessment", styles["h1"]))
    story.append(
        _key_value_table(
            [
                ("Capacity utilisation", f"{_fmt(assessment.utilisation_percent, 1)}%"),
                ("Screening classification", assessment.classification),
                (
                    "Illustrative thresholds",
                    "Within < 80%; Approaching 80% to 100%; Exceeds > 100%",
                ),
            ],
            styles,
        )
    )
    story.append(Spacer(1, 5))
    story.append(
        _p(
            "The classification is a software screening indicator, not a universal "
            "design criterion. A result below 100% does not establish flood-free "
            "performance, and a result above 100% requires detailed engineering review.",
            styles["body"],
        )
    )

    if scenario_results:
        story.append(PageBreak())
        story.append(_p("5. Scenario comparison", styles["h1"]))
        story.append(
            _p(
                "Scenario inputs are illustrative demonstrations, not observed rainfall "
                "records. All values below were recalculated from the current table.",
                styles["body"],
            )
        )
        scenario_dataframe = scenario_results_to_dataframe(scenario_results)
        display_columns = [
            "Scenario",
            "Rainfall intensity (mm/h)",
            "Pipe diameter (m)",
            "Peak runoff (m3/s)",
            "Pipe capacity (m3/s)",
            "Capacity utilisation (%)",
            "Classification",
        ]
        header = display_columns
        rows: list[list[str]] = []
        for _, row in scenario_dataframe[display_columns].iterrows():
            rows.append(
                [
                    str(row["Scenario"]),
                    _fmt(float(row["Rainfall intensity (mm/h)"]), 1),
                    _fmt(float(row["Pipe diameter (m)"]), 2),
                    _fmt(float(row["Peak runoff (m3/s)"]), 4),
                    _fmt(float(row["Pipe capacity (m3/s)"]), 4),
                    _fmt(float(row["Capacity utilisation (%)"]), 1),
                    str(row["Classification"]),
                ]
            )
        story.append(
            _data_table(
                header,
                rows,
                styles,
                widths=[35 * mm, 19 * mm, 15 * mm, 21 * mm, 21 * mm, 24 * mm, 30 * mm],
            )
        )
        story.append(
            _p(
                "Built-in scenarios are illustrative configurations and should not be "
                "interpreted as measured Nigerian rainfall or verified asset data.",
                styles["small"],
            )
        )

    story.append(_p("6. Methodology and assumptions", styles["h1"]))
    assumptions = [
        (
            "The Rational Method is a simplified peak-flow estimator appropriate only for "
            "suitable small catchments after professional judgement."
        ),
        (
            "Rainfall intensity is treated as a single design value. Its duration, return "
            "period and local intensity-duration-frequency basis must be selected separately."
        ),
        (
            "Runoff is calculated as a peak rate only; no hydrograph, volume, depth or "
            "flood extent is produced."
        ),
        "The pipe is assumed circular, flowing full, with steady and uniform flow.",
        "The specified pipe slope is assumed to approximate the hydraulic energy slope.",
        (
            "Inlet losses, outlet control, surcharge, backwater effects, sediment, blockage "
            "and network routing are not modelled."
        ),
        (
            "The 80% and 100% utilisation thresholds are illustrative screening indicators, "
            "not universal design standards."
        ),
    ]
    for statement in assumptions:
        story.append(_p(f"&bull; {escape(statement)}", styles["bullet"]))

    story.append(_p("7. Limitations and recommended further checks", styles["h1"]))
    limitations = [
        (
            "Confirm the design storm duration, return period and intensity using a local "
            "intensity-duration-frequency source and the relevant authority requirements."
        ),
        (
            "Verify catchment delineation, land use, runoff coefficient and any time-of-"
            "concentration or routing assumptions."
        ),
        (
            "Perform detailed hydraulic analysis including inlet and outlet conditions, "
            "part-full flow, surcharge, backwater and blockages."
        ),
        (
            "Check pipe material, structural loading, cover, bedding, access, erosion and "
            "constructability requirements."
        ),
        "Assess climate-change allowances, maintenance and whole-life performance.",
    ]
    for statement in limitations:
        story.append(_p(f"&bull; {escape(statement)}", styles["bullet"]))

    story.append(Spacer(1, 8))
    story.append(
        _p(
            "The results in this report depend entirely on the user-supplied inputs and "
            "the simplified equations described above. Independent engineering review is "
            "required before any design or operational decision.",
            styles["small"],
        )
    )

    document.build(story, onFirstPage=_page_footer, onLaterPages=_page_footer)
    return buffer.getvalue()


def build_pipe_results_csv(analysis: ProjectAnalysis) -> bytes:
    """Return independent pipe screening results as UTF-8 CSV bytes."""
    records = []
    for item in analysis.pipes:
        pipe = item.pipe
        records.append(
            {
                "Pipe": pipe.name,
                "ID": pipe.id,
                "From node": pipe.from_node_id,
                "To node": pipe.to_node_id,
                "Diameter (m)": pipe.diameter_m,
                "Length (m)": pipe.length_m,
                "Slope (%)": pipe.slope_percent,
                "Manning n": pipe.manning_n,
                "Full-flow capacity (m3/s)": item.hydraulics.capacity_m3_s,
                "Full-flow velocity (m/s)": item.hydraulics.full_flow_velocity_m_s,
                "Peak runoff (m3/s)": analysis.runoff.peak_runoff_m3_s,
                "Capacity utilisation (%)": item.assessment.utilisation_percent,
                "Classification": item.assessment.classification,
            }
        )
    return (
        pd.DataFrame(records, columns=PIPE_RESULT_COLUMNS)
        .to_csv(index=False)
        .encode("utf-8-sig")
    )


def _selected_pipe_table(
    selected: PipeAnalysis, styles: dict[str, ParagraphStyle]
) -> Table:
    pipe = selected.pipe
    return _key_value_table(
        [
            ("Pipe", f"{pipe.name} ({pipe.id})"),
            ("Connected nodes", f"{pipe.from_node_id} to {pipe.to_node_id}"),
            ("Internal diameter", f"{_fmt(pipe.diameter_m, 3)} m"),
            ("Length", f"{_fmt(pipe.length_m, 2)} m"),
            ("Slope", f"{_fmt(pipe.slope_percent, 3)}%"),
            ("Manning roughness coefficient", f"{_fmt(pipe.manning_n, 4)} (-)"),
            (
                "Estimated full-flow capacity",
                f"{_fmt(selected.hydraulics.capacity_m3_s, 4)} m3/s",
            ),
            (
                "Full-flow velocity",
                f"{_fmt(selected.hydraulics.full_flow_velocity_m_s, 3)} m/s",
            ),
            (
                "Capacity utilisation",
                f"{_fmt(selected.assessment.utilisation_percent, 1)}%",
            ),
            ("Screening classification", selected.assessment.classification),
        ],
        styles,
    )


def build_studio_pdf_report(
    project: EngineeringProject,
    analysis: ProjectAnalysis,
    generated_at: datetime | None = None,
) -> bytes:
    """Build a project-level PDF report from saved inputs and actual results."""
    generated = (generated_at or datetime.now()).strftime("%d %B %Y, %H:%M")
    buffer = BytesIO()
    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        leftMargin=20 * mm,
        rightMargin=20 * mm,
        topMargin=17 * mm,
        bottomMargin=20 * mm,
        title=f"FloodGuard Studio Report - {project.metadata.name}",
        author="FloodGuard Studio",
        subject="Preliminary project-level drainage screening assessment",
    )
    styles = _pdf_styles()
    story: list[object] = []

    story.append(_p("FloodGuard Studio", styles["title"]))
    story.append(_p(escape(project.metadata.name), styles["subtitle"]))
    story.append(
        _p(
            "Project-level preliminary drainage screening report",
            styles["subtitle"],
        )
    )
    story.append(
        _p(
            f"Project number: {escape(project.metadata.project_number or 'Not specified')} "
            f"| Report generated: {escape(generated)}",
            styles["meta"],
        )
    )
    story.append(Spacer(1, 7))

    disclaimer_box = Table(
        [[_p(f"<b>Important notice.</b> {escape(DISCLAIMER)}", styles["disclaimer"])]],
        colWidths=[170 * mm],
        hAlign="LEFT",
    )
    disclaimer_box.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, -1), colors.HexColor("#FFF7E6")),
                ("BOX", (0, 0), (-1, -1), 0.8, AMBER),
                ("LEFTPADDING", (0, 0), (-1, -1), 7),
                ("RIGHTPADDING", (0, 0), (-1, -1), 7),
                ("TOPPADDING", (0, 0), (-1, -1), 6),
                ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
            ]
        )
    )
    story.append(disclaimer_box)

    story.append(_p("1. Project information", styles["h1"]))
    story.append(
        _key_value_table(
            [
                ("Project", project.metadata.name),
                ("Project number", project.metadata.project_number or "Not specified"),
                ("Client", project.metadata.client or "Not specified"),
                ("Location", project.metadata.location or "Not specified"),
                ("Engineer / author", project.metadata.engineer or "Not specified"),
                ("Description", project.metadata.description or "Not specified"),
                (
                    "Network elements",
                    f"{len(project.nodes)} nodes, {len(project.pipes)} pipes",
                ),
                ("Saved scenarios", str(len(project.scenarios))),
            ],
            styles,
        )
    )

    story.append(_p("2. Scope and methodology", styles["h1"]))
    story.append(
        _p(
            "Peak runoff is estimated with the Rational Method, Q = (1/360) x C x I x A. "
            "Each pipe is screened independently using Manning's equation for steady, "
            "uniform, full circular flow: Q = (1/n) x A x R^(2/3) x S^(1/2).",
            styles["body"],
        )
    )
    story.append(
        _p(
            "This report does not contain a network hydraulic simulation. No routed flows, "
            "part-full depths, backwater levels, surcharge, flooding or time-varying results "
            "are calculated or implied.",
            styles["body"],
        )
    )

    story.append(_p("3. Catchment and design rainfall", styles["h1"]))
    story.append(
        _key_value_table(
            [
                ("Catchment area", f"{_fmt(project.catchment.area_ha, 3)} ha"),
                (
                    "Design rainfall intensity",
                    f"{_fmt(project.catchment.rainfall_intensity_mm_h, 2)} mm/h",
                ),
                (
                    "Runoff coefficient",
                    f"{_fmt(project.catchment.runoff_coefficient, 3)} (-)",
                ),
                (
                    "Estimated peak runoff",
                    f"{_fmt(analysis.runoff.peak_runoff_m3_s, 4)} m3/s",
                ),
                (
                    "Estimated peak runoff",
                    f"{_fmt(analysis.runoff.peak_runoff_l_s, 2)} L/s",
                ),
            ],
            styles,
        )
    )
    if project.catchment.notes:
        story.append(_p(escape(project.catchment.notes), styles["small"]))

    story.append(_p("4. Drainage network", styles["h1"]))
    if project.nodes:
        story.append(
            _data_table(
                ["ID", "Name", "Type", "X", "Y", "Invert (m)"],
                [
                    [
                        node.id,
                        node.name,
                        node.display_kind,
                        _fmt(node.x, 1),
                        _fmt(node.y, 1),
                        _fmt(node.invert_elevation_m, 3),
                    ]
                    for node in project.nodes
                ],
                styles,
                widths=[18 * mm, 44 * mm, 25 * mm, 27 * mm, 27 * mm, 29 * mm],
            )
        )
        story.append(Spacer(1, 6))
    else:
        story.append(_p("No network nodes are defined.", styles["body"]))

    if project.pipes:
        story.append(
            _data_table(
                [
                    "Pipe",
                    "From",
                    "To",
                    "D (m)",
                    "L (m)",
                    "n",
                    "S (%)",
                    "Capacity (m3/s)",
                    "Util. (%)",
                    "Status",
                ],
                [
                    [
                        pipe.name,
                        pipe.from_node_id,
                        pipe.to_node_id,
                        _fmt(pipe.diameter_m, 2),
                        _fmt(pipe.length_m, 1),
                        _fmt(pipe.manning_n, 3),
                        _fmt(pipe.slope_percent, 2),
                        _fmt(item.hydraulics.capacity_m3_s, 3),
                        _fmt(item.assessment.utilisation_percent, 1),
                        item.assessment.classification,
                    ]
                    for item in analysis.pipes
                    for pipe in [item.pipe]
                ],
                styles,
                widths=[
                    21 * mm,
                    13 * mm,
                    13 * mm,
                    12 * mm,
                    13 * mm,
                    11 * mm,
                    11 * mm,
                    22 * mm,
                    16 * mm,
                    38 * mm,
                ],
            )
        )
        story.append(
            _p(
                "Utilisation compares the same project-wide peak runoff estimate with each "
                "pipe's independent full-flow capacity. It is a screening indicator only.",
                styles["small"],
            )
        )

    if analysis.selected_pipe is not None:
        story.append(PageBreak())
        story.append(_p("5. Selected pipe screening detail", styles["h1"]))
        story.append(_selected_pipe_table(analysis.selected_pipe, styles))
        story.append(
            _p(
                "The selected-pipe result uses the current project catchment and rainfall "
                "inputs. It does not represent routed flow arriving from upstream pipes.",
                styles["small"],
            )
        )

    story.append(_p("6. Pipe screening summary", styles["h1"]))
    if analysis.pipes:
        story.append(
            _data_table(
                [
                    "Pipe",
                    "Peak runoff (m3/s)",
                    "Capacity (m3/s)",
                    "Utilisation (%)",
                    "Classification",
                ],
                [
                    [
                        item.pipe.name,
                        _fmt(analysis.runoff.peak_runoff_m3_s, 4),
                        _fmt(item.hydraulics.capacity_m3_s, 4),
                        _fmt(item.assessment.utilisation_percent, 1),
                        item.assessment.classification,
                    ]
                    for item in analysis.pipes
                ],
                styles,
                widths=[40 * mm, 32 * mm, 32 * mm, 30 * mm, 36 * mm],
            )
        )
    else:
        story.append(_p("No pipe screening results are available.", styles["body"]))

    if analysis.scenario_results:
        story.append(_p("7. Scenario comparison", styles["h1"]))
        scenario_dataframe = scenario_results_to_dataframe(
            list(analysis.scenario_results)
        )
        display_columns = [
            "Scenario",
            "Rainfall intensity (mm/h)",
            "Pipe diameter (m)",
            "Peak runoff (m3/s)",
            "Pipe capacity (m3/s)",
            "Capacity utilisation (%)",
            "Classification",
        ]
        rows = [
            [
                str(row["Scenario"]),
                _fmt(float(row["Rainfall intensity (mm/h)"]), 1),
                _fmt(float(row["Pipe diameter (m)"]), 2),
                _fmt(float(row["Peak runoff (m3/s)"]), 4),
                _fmt(float(row["Pipe capacity (m3/s)"]), 4),
                _fmt(float(row["Capacity utilisation (%)"]), 1),
                str(row["Classification"]),
            ]
            for _, row in scenario_dataframe[display_columns].iterrows()
        ]
        story.append(
            _data_table(
                display_columns,
                rows,
                styles,
                widths=[35 * mm, 19 * mm, 15 * mm, 21 * mm, 21 * mm, 24 * mm, 30 * mm],
            )
        )
        story.append(
            _p(
                "Scenarios are user-defined what-if configurations. Built-in scenarios are "
                "illustrative and are not observed rainfall or verified asset data.",
                styles["small"],
            )
        )

    story.append(_p("8. Assumptions, limitations and next steps", styles["h1"]))
    for statement in [
        "The Rational Method is a simplified peak-flow estimator requiring professional judgement.",
        "Rainfall intensity, duration and return period must be confirmed from a local design source.",
        "No hydrograph, runoff volume, flood depth, flood extent or network routing is produced.",
        "Each pipe is assumed circular, flowing full, with steady uniform flow.",
        "The entered pipe slope is assumed to represent the hydraulic energy slope.",
        "Inlet and outlet losses, surcharge, backwater, blockage, sediment and construction constraints are not modelled.",
        "The 80% and 100% utilisation thresholds are illustrative screening bands, not universal design standards.",
        "Detailed hydraulic modelling, survey verification and independent engineering review are required before design.",
        "If network-wide performance is required, develop and verify a separate SWMM or equivalent model; it is not provided by this version.",
    ]:
        story.append(_p(f"&bull; {escape(statement)}", styles["bullet"]))

    story.append(Spacer(1, 8))
    story.append(
        _p(
            "This report depends on the saved project inputs and the simplified equations "
            "described above. It is not a substitute for site investigation, detailed design "
            "or statutory approval.",
            styles["small"],
        )
    )

    document.build(story, onFirstPage=_page_footer, onLaterPages=_page_footer)
    return buffer.getvalue()
