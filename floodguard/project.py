"""Versioned engineering project model and JSON persistence."""

from __future__ import annotations

import json
import math
import os
from dataclasses import asdict, dataclass, field
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from floodguard import __version__
from floodguard.hydraulics import calculate_pipe_capacity
from floodguard.scenarios import Scenario, default_scenarios, evaluate_scenario
from floodguard.validation import (
    ValidationError,
    require_finite,
    validate_catchment_area,
    validate_manning_n,
    validate_pipe_diameter,
    validate_rainfall_intensity,
    validate_runoff_coefficient,
    validate_slope_percent,
)

SCHEMA_VERSION = 1
PROJECT_EXTENSION = ".fgsproj"
PROJECT_FILE_FILTER = "FloodGuard Studio Project (*.fgsproj);;JSON files (*.json)"
APP_NAME = "FloodGuard Studio"
VALID_NODE_KINDS = ("junction", "outfall")


class ProjectError(Exception):
    """Base exception for project persistence and model errors."""


class ProjectFormatError(ProjectError):
    """Raised when a project file has an unsupported or malformed structure."""


class ProjectValidationError(ProjectError):
    """Raised when project engineering values are invalid."""


def utc_now_iso() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def _as_str(value: Any, field_name: str, *, allow_empty: bool = True) -> str:
    if value is None:
        text = ""
    elif isinstance(value, str):
        text = value.strip()
    else:
        raise ProjectFormatError(f"'{field_name}' must be a string.")
    if not allow_empty and not text:
        raise ProjectFormatError(f"'{field_name}' must not be empty.")
    return text


def _as_float(value: Any, field_name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ProjectFormatError(f"'{field_name}' must be numeric.")
    number = float(value)
    if not math.isfinite(number):
        raise ProjectFormatError(f"'{field_name}' must be finite.")
    return number


def _as_mapping(value: Any, field_name: str) -> dict[str, Any]:
    if not isinstance(value, dict):
        raise ProjectFormatError(f"'{field_name}' must be a JSON object.")
    return value


def _as_list(value: Any, field_name: str) -> list[Any]:
    if not isinstance(value, list):
        raise ProjectFormatError(f"'{field_name}' must be a JSON array.")
    return value


@dataclass
class ProjectMetadata:
    name: str
    project_number: str = ""
    client: str = ""
    location: str = ""
    engineer: str = ""
    description: str = ""
    created_at: str = field(default_factory=utc_now_iso)
    modified_at: str = field(default_factory=utc_now_iso)

    def touch(self) -> None:
        self.modified_at = utc_now_iso()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ProjectMetadata:
        data = _as_mapping(data, "metadata")
        return cls(
            name=_as_str(data.get("name"), "metadata.name", allow_empty=False),
            project_number=_as_str(
                data.get("project_number"), "metadata.project_number"
            ),
            client=_as_str(data.get("client"), "metadata.client"),
            location=_as_str(data.get("location"), "metadata.location"),
            engineer=_as_str(data.get("engineer"), "metadata.engineer"),
            description=_as_str(data.get("description"), "metadata.description"),
            created_at=_as_str(data.get("created_at"), "metadata.created_at")
            or utc_now_iso(),
            modified_at=_as_str(data.get("modified_at"), "metadata.modified_at")
            or utc_now_iso(),
        )


@dataclass
class Catchment:
    area_ha: float = 5.0
    rainfall_intensity_mm_h: float = 90.0
    runoff_coefficient: float = 0.75
    notes: str = ""

    def validate(self) -> None:
        validate_catchment_area(self.area_ha)
        validate_rainfall_intensity(self.rainfall_intensity_mm_h)
        validate_runoff_coefficient(self.runoff_coefficient)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    def clone(self) -> Catchment:
        return Catchment(**asdict(self))

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Catchment:
        data = _as_mapping(data, "catchment")
        return cls(
            area_ha=_as_float(data.get("area_ha"), "catchment.area_ha"),
            rainfall_intensity_mm_h=_as_float(
                data.get("rainfall_intensity_mm_h"),
                "catchment.rainfall_intensity_mm_h",
            ),
            runoff_coefficient=_as_float(
                data.get("runoff_coefficient"), "catchment.runoff_coefficient"
            ),
            notes=_as_str(data.get("notes"), "catchment.notes"),
        )


@dataclass
class Node:
    id: str
    name: str
    kind: str
    x: float
    y: float
    invert_elevation_m: float = 0.0
    notes: str = ""

    @property
    def display_kind(self) -> str:
        return self.kind.capitalize()

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Node:
        data = _as_mapping(data, "node")
        return cls(
            id=_as_str(data.get("id"), "node.id", allow_empty=False),
            name=_as_str(data.get("name"), "node.name", allow_empty=False),
            kind=_as_str(data.get("kind"), "node.kind", allow_empty=False).lower(),
            x=_as_float(data.get("x"), "node.x"),
            y=_as_float(data.get("y"), "node.y"),
            invert_elevation_m=_as_float(
                data.get("invert_elevation_m", 0.0), "node.invert_elevation_m"
            ),
            notes=_as_str(data.get("notes"), "node.notes"),
        )


@dataclass
class Pipe:
    id: str
    name: str
    from_node_id: str
    to_node_id: str
    diameter_m: float = 1.0
    length_m: float = 100.0
    slope_percent: float = 0.5
    manning_n: float = 0.013
    material: str = "Concrete"
    notes: str = ""

    def validate(self) -> None:
        validate_pipe_diameter(self.diameter_m)
        validate_manning_n(self.manning_n)
        validate_slope_percent(self.slope_percent)
        length = require_finite(self.length_m, "Pipe length", "m")
        if length <= 0.0:
            raise ValidationError("Pipe length must be greater than 0 m.")
        calculate_pipe_capacity(self.diameter_m, self.manning_n, self.slope_percent)

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Pipe:
        data = _as_mapping(data, "pipe")
        return cls(
            id=_as_str(data.get("id"), "pipe.id", allow_empty=False),
            name=_as_str(data.get("name"), "pipe.name", allow_empty=False),
            from_node_id=_as_str(
                data.get("from_node_id"), "pipe.from_node_id", allow_empty=False
            ),
            to_node_id=_as_str(
                data.get("to_node_id"), "pipe.to_node_id", allow_empty=False
            ),
            diameter_m=_as_float(data.get("diameter_m"), "pipe.diameter_m"),
            length_m=_as_float(data.get("length_m"), "pipe.length_m"),
            slope_percent=_as_float(data.get("slope_percent"), "pipe.slope_percent"),
            manning_n=_as_float(data.get("manning_n"), "pipe.manning_n"),
            material=_as_str(data.get("material"), "pipe.material"),
            notes=_as_str(data.get("notes"), "pipe.notes"),
        )


def _scenario_to_dict(scenario: Scenario) -> dict[str, Any]:
    return asdict(scenario)


def _scenario_from_dict(data: dict[str, Any]) -> Scenario:
    data = _as_mapping(data, "scenario")
    return Scenario(
        name=_as_str(data.get("name"), "scenario.name", allow_empty=False),
        catchment_area_ha=_as_float(
            data.get("catchment_area_ha"), "scenario.catchment_area_ha"
        ),
        runoff_coefficient=_as_float(
            data.get("runoff_coefficient"), "scenario.runoff_coefficient"
        ),
        rainfall_intensity_mm_h=_as_float(
            data.get("rainfall_intensity_mm_h"),
            "scenario.rainfall_intensity_mm_h",
        ),
        pipe_diameter_m=_as_float(
            data.get("pipe_diameter_m"), "scenario.pipe_diameter_m"
        ),
        manning_n=_as_float(data.get("manning_n"), "scenario.manning_n"),
        slope_percent=_as_float(data.get("slope_percent"), "scenario.slope_percent"),
        description=_as_str(data.get("description"), "scenario.description"),
    )


@dataclass
class EngineeringProject:
    metadata: ProjectMetadata
    catchment: Catchment = field(default_factory=Catchment)
    nodes: list[Node] = field(default_factory=list)
    pipes: list[Pipe] = field(default_factory=list)
    scenarios: list[Scenario] = field(default_factory=lambda: list(default_scenarios()))
    schema_version: int = SCHEMA_VERSION
    software_version: str = __version__

    def find_node(self, node_id: str) -> Node | None:
        return next((node for node in self.nodes if node.id == node_id), None)

    def find_pipe(self, pipe_id: str) -> Pipe | None:
        return next((pipe for pipe in self.pipes if pipe.id == pipe_id), None)

    def require_node(self, node_id: str) -> Node:
        node = self.find_node(node_id)
        if node is None:
            raise ProjectValidationError(f"Node '{node_id}' does not exist.")
        return node

    def require_pipe(self, pipe_id: str) -> Pipe:
        pipe = self.find_pipe(pipe_id)
        if pipe is None:
            raise ProjectValidationError(f"Pipe '{pipe_id}' does not exist.")
        return pipe

    def _next_id(self, prefix: str, existing_ids: list[str]) -> str:
        highest = 0
        marker = f"{prefix}-"
        for identifier in existing_ids:
            if identifier.startswith(marker):
                try:
                    highest = max(highest, int(identifier.split("-")[-1]))
                except ValueError:
                    continue
        return f"{marker}{highest + 1:02d}"

    def add_node(self, kind: str, x: float, y: float) -> Node:
        kind = kind.lower()
        if kind not in VALID_NODE_KINDS:
            raise ProjectValidationError("Node type must be 'junction' or 'outfall'.")
        prefix = "J" if kind == "junction" else "O"
        node_id = self._next_id(prefix, [node.id for node in self.nodes])
        label = "Junction" if kind == "junction" else "Outfall"
        index = sum(1 for node in self.nodes if node.kind == kind) + 1
        node = Node(
            id=node_id,
            name=f"{label} {index}",
            kind=kind,
            x=float(x),
            y=float(y),
            invert_elevation_m=0.0,
        )
        self.nodes.append(node)
        return node

    def pipe_ids_for_node(self, node_id: str) -> list[str]:
        return [
            pipe.id
            for pipe in self.pipes
            if pipe.from_node_id == node_id or pipe.to_node_id == node_id
        ]

    def add_pipe(self, from_node_id: str, to_node_id: str) -> Pipe:
        self.require_node(from_node_id)
        self.require_node(to_node_id)
        if from_node_id == to_node_id:
            raise ProjectValidationError("A pipe must connect two different nodes.")
        pipe_id = self._next_id("P", [pipe.id for pipe in self.pipes])
        pipe = Pipe(
            id=pipe_id,
            name=f"Pipe {pipe_id}",
            from_node_id=from_node_id,
            to_node_id=to_node_id,
        )
        self.pipes.append(pipe)
        return pipe

    def remove_node(self, node_id: str) -> int:
        self.require_node(node_id)
        removed_pipes = self.pipe_ids_for_node(node_id)
        self.pipes = [pipe for pipe in self.pipes if pipe.id not in removed_pipes]
        self.nodes = [node for node in self.nodes if node.id != node_id]
        return len(removed_pipes)

    def remove_pipe(self, pipe_id: str) -> None:
        self.require_pipe(pipe_id)
        self.pipes = [pipe for pipe in self.pipes if pipe.id != pipe_id]

    def node_position(self, node_id: str) -> tuple[float, float]:
        node = self.require_node(node_id)
        return node.x, node.y

    def set_node_position(self, node_id: str, x: float, y: float) -> None:
        node = self.require_node(node_id)
        node.x = float(x)
        node.y = float(y)

    def validate(self) -> None:
        errors: list[str] = []
        if not self.metadata.name.strip():
            errors.append("Project name must not be empty.")
        try:
            self.catchment.validate()
        except ValidationError as error:
            errors.append(f"Catchment: {error}")

        node_ids = [node.id for node in self.nodes]
        if len(node_ids) != len(set(node_ids)):
            errors.append("Node identifiers must be unique.")
        for node in self.nodes:
            if not node.id.strip() or not node.name.strip():
                errors.append("Every node requires a non-empty identifier and name.")
            if node.kind not in VALID_NODE_KINDS:
                errors.append(f"Node '{node.name}' has unsupported type '{node.kind}'.")
            try:
                require_finite(node.x, "Node x-coordinate")
                require_finite(node.y, "Node y-coordinate")
                require_finite(node.invert_elevation_m, "Node invert elevation")
            except ValidationError as error:
                errors.append(f"Node '{node.name}': {error}")

        pipe_ids = [pipe.id for pipe in self.pipes]
        if len(pipe_ids) != len(set(pipe_ids)):
            errors.append("Pipe identifiers must be unique.")
        valid_nodes = set(node_ids)
        for pipe in self.pipes:
            if not pipe.id.strip() or not pipe.name.strip():
                errors.append("Every pipe requires a non-empty identifier and name.")
            if pipe.from_node_id not in valid_nodes:
                errors.append(
                    f"Pipe '{pipe.name}' references missing start node "
                    f"'{pipe.from_node_id}'."
                )
            if pipe.to_node_id not in valid_nodes:
                errors.append(
                    f"Pipe '{pipe.name}' references missing end node "
                    f"'{pipe.to_node_id}'."
                )
            if pipe.from_node_id == pipe.to_node_id:
                errors.append(f"Pipe '{pipe.name}' must connect two different nodes.")
            try:
                pipe.validate()
            except ValidationError as error:
                errors.append(f"Pipe '{pipe.name}': {error}")

        scenario_names: set[str] = set()
        for scenario in self.scenarios:
            if not scenario.name.strip():
                errors.append("Every scenario requires a name.")
            if scenario.name in scenario_names:
                errors.append(f"Scenario name '{scenario.name}' is duplicated.")
            scenario_names.add(scenario.name)
            try:
                evaluate_scenario(scenario)
            except ValidationError as error:
                errors.append(f"Scenario '{scenario.name}': {error}")

        if errors:
            raise ProjectValidationError("\n".join(errors))

    def touch(self) -> None:
        self.metadata.touch()

    def to_dict(self) -> dict[str, Any]:
        return {
            "schema_version": self.schema_version,
            "application": {"name": APP_NAME, "version": self.software_version},
            "project": {
                "metadata": self.metadata.to_dict(),
                "catchment": self.catchment.to_dict(),
                "network": {
                    "nodes": [node.to_dict() for node in self.nodes],
                    "pipes": [pipe.to_dict() for pipe in self.pipes],
                },
                "scenarios": [_scenario_to_dict(item) for item in self.scenarios],
            },
        }

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), indent=2, ensure_ascii=False) + "\n"

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> EngineeringProject:
        data = _as_mapping(data, "project file")
        version = data.get("schema_version")
        if not isinstance(version, int):
            raise ProjectFormatError(
                "Project file must define an integer schema_version."
            )
        if version != SCHEMA_VERSION:
            raise ProjectFormatError(
                f"Unsupported project schema version {version}. "
                f"This build supports version {SCHEMA_VERSION}."
            )
        application = _as_mapping(data.get("application", {}), "application")
        project_data = _as_mapping(data.get("project"), "project")
        metadata = ProjectMetadata.from_dict(
            _as_mapping(project_data.get("metadata"), "project.metadata")
        )
        catchment = Catchment.from_dict(
            _as_mapping(project_data.get("catchment"), "project.catchment")
        )
        network = _as_mapping(project_data.get("network"), "project.network")
        nodes = [
            Node.from_dict(item)
            for item in _as_list(network.get("nodes"), "project.network.nodes")
        ]
        pipes = [
            Pipe.from_dict(item)
            for item in _as_list(network.get("pipes"), "project.network.pipes")
        ]
        scenarios = [
            _scenario_from_dict(item)
            for item in _as_list(project_data.get("scenarios", []), "project.scenarios")
        ]
        project = cls(
            metadata=metadata,
            catchment=catchment,
            nodes=nodes,
            pipes=pipes,
            scenarios=scenarios,
            schema_version=version,
            software_version=_as_str(application.get("version"), "application.version")
            or __version__,
        )
        project.validate()
        return project

    @classmethod
    def from_json(cls, text: str) -> EngineeringProject:
        try:
            data = json.loads(text)
        except json.JSONDecodeError as error:
            raise ProjectFormatError(f"Project JSON is invalid: {error}") from error
        return cls.from_dict(data)

    def save(self, path: str | Path) -> Path:
        self.validate()
        destination = Path(path)
        if destination.suffix.lower() != PROJECT_EXTENSION:
            destination = destination.with_suffix(PROJECT_EXTENSION)
        destination.parent.mkdir(parents=True, exist_ok=True)
        temporary = destination.with_suffix(destination.suffix + ".tmp")
        temporary.write_text(self.to_json(), encoding="utf-8")
        os.replace(temporary, destination)
        return destination

    @classmethod
    def load(cls, path: str | Path) -> EngineeringProject:
        source = Path(path)
        try:
            text = source.read_text(encoding="utf-8")
        except OSError as error:
            raise ProjectFormatError(f"Could not read project file: {error}") from error
        return cls.from_json(text)

    def clone(self) -> EngineeringProject:
        return EngineeringProject.from_dict(self.to_dict())


def create_starter_project(
    name: str,
    engineer: str = "",
    location: str = "",
    description: str = "",
    catchment: Catchment | None = None,
) -> EngineeringProject:
    """Create a new project with a minimal junction-to-outfall reach."""
    project = EngineeringProject(
        metadata=ProjectMetadata(
            name=name.strip() or "Untitled Project",
            engineer=engineer,
            location=location,
            description=description,
        ),
        catchment=catchment.clone()
        if hasattr(catchment, "clone")
        else (catchment or Catchment()),
    )
    project.nodes = [
        Node(id="J-01", name="Junction 1", kind="junction", x=-180.0, y=0.0),
        Node(id="O-01", name="Outfall 1", kind="outfall", x=180.0, y=0.0),
    ]
    project.pipes = [
        Pipe(
            id="P-01",
            name="Pipe P-01",
            from_node_id="J-01",
            to_node_id="O-01",
            diameter_m=1.0,
            length_m=100.0,
            slope_percent=0.5,
            manning_n=0.013,
            material="Concrete",
        )
    ]
    project.scenarios = list(default_scenarios())
    return project


def create_example_project() -> EngineeringProject:
    """Create the bundled illustrative demonstration project."""
    project = EngineeringProject(
        metadata=ProjectMetadata(
            name="Riverside Demonstration Catchment",
            project_number="FGS-DEMO-001",
            client="Portfolio demonstration",
            location="Illustrative urban catchment",
            engineer="Civil Engineering Portfolio",
            description=(
                "Example project supplied with FloodGuard Studio. Network geometry, "
                "rainfall and asset values are illustrative and are not observed "
                "site measurements."
            ),
            created_at="2026-10-26T09:00:00+00:00",
            modified_at="2026-10-26T09:00:00+00:00",
        ),
        catchment=Catchment(
            area_ha=5.0,
            rainfall_intensity_mm_h=90.0,
            runoff_coefficient=0.75,
            notes=(
                "Illustrative small urban catchment. A real assessment requires local "
                "IDF data, verified land use and survey information."
            ),
        ),
        nodes=[
            Node("J-01", "Junction 1", "junction", -300.0, -80.0, 10.20),
            Node("J-02", "Junction 2", "junction", -20.0, 90.0, 8.65),
            Node("O-01", "Outfall 1", "outfall", 300.0, -40.0, 6.90),
        ],
        pipes=[
            Pipe(
                "P-01",
                "Reach J1-J2",
                "J-01",
                "J-02",
                diameter_m=0.9,
                length_m=120.0,
                slope_percent=0.60,
                manning_n=0.013,
                material="Concrete",
                notes="Illustrative upstream reach.",
            ),
            Pipe(
                "P-02",
                "Reach J2-O1",
                "J-02",
                "O-01",
                diameter_m=1.2,
                length_m=160.0,
                slope_percent=0.45,
                manning_n=0.013,
                material="Concrete",
                notes="Illustrative downstream reach.",
            ),
        ],
        scenarios=list(default_scenarios()),
    )
    return project
