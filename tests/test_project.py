import json
from pathlib import Path

import pytest

from floodguard.project import (
    PROJECT_EXTENSION,
    SCHEMA_VERSION,
    Catchment,
    EngineeringProject,
    ProjectFormatError,
    ProjectValidationError,
    create_example_project,
    create_starter_project,
)
from floodguard.scenarios import default_scenarios


def test_starter_project_contains_valid_default_network():
    project = create_starter_project("Test Catchment", engineer="A. Engineer")
    assert project.metadata.name == "Test Catchment"
    assert project.metadata.engineer == "A. Engineer"
    assert [node.id for node in project.nodes] == ["J-01", "O-01"]
    assert [pipe.id for pipe in project.pipes] == ["P-01"]
    assert len(project.scenarios) == len(default_scenarios())
    project.validate()


def test_starter_project_does_not_share_catchment():
    catchment = Catchment(area_ha=2.0)
    project = create_starter_project("Test", catchment=catchment)
    project.catchment.area_ha = 7.0
    assert catchment.area_ha == 2.0


def test_project_round_trip_preserves_engineering_values(tmp_path):
    project = create_example_project()
    project.set_node_position("J-02", 42.5, -17.25)
    destination = tmp_path / "example.fgsproj"
    saved = project.save(destination)
    assert saved == destination
    loaded = EngineeringProject.load(saved)
    assert loaded.to_dict() == project.to_dict()
    assert loaded.schema_version == SCHEMA_VERSION
    assert loaded.find_pipe("P-02").diameter_m == pytest.approx(1.2)
    assert loaded.node_position("J-02") == pytest.approx((42.5, -17.25))


def test_save_adds_project_extension(tmp_path):
    project = create_starter_project("Extension test")
    saved = project.save(tmp_path / "catchment")
    assert saved.name == "catchment" + PROJECT_EXTENSION
    assert saved.exists()


def test_save_rejects_invalid_project(tmp_path):
    project = create_starter_project("Invalid test")
    project.pipes[0].slope_percent = 0.0
    with pytest.raises(ProjectValidationError):
        project.save(tmp_path / "invalid.fgsproj")


def test_load_rejects_invalid_json(tmp_path):
    source = tmp_path / "bad.fgsproj"
    source.write_text("{not json", encoding="utf-8")
    with pytest.raises(ProjectFormatError, match="invalid"):
        EngineeringProject.load(source)


def test_load_rejects_unsupported_schema(tmp_path):
    source = tmp_path / "future.fgsproj"
    source.write_text(
        json.dumps({"schema_version": 99, "project": {}}), encoding="utf-8"
    )
    with pytest.raises(ProjectFormatError, match="Unsupported"):
        EngineeringProject.load(source)


def test_load_rejects_missing_structure():
    with pytest.raises(ProjectFormatError):
        EngineeringProject.from_json(json.dumps({"schema_version": SCHEMA_VERSION}))


def test_add_and_remove_network_elements():
    project = create_starter_project("Network test")
    node = project.add_node("junction", 40.0, 20.0)
    assert node.id == "J-02"
    outfall = project.add_node("outfall", 100.0, 20.0)
    assert outfall.id == "O-02"
    pipe = project.add_pipe("J-02", "O-02")
    assert pipe.id == "P-02"
    assert project.pipe_ids_for_node("J-02") == ["P-02"]
    removed = project.remove_node("O-02")
    assert removed == 1
    assert project.find_node("O-02") is None
    assert project.find_pipe("P-02") is None
    project.validate()


def test_pipe_requires_distinct_existing_nodes():
    project = create_starter_project("Network test")
    with pytest.raises(ProjectValidationError, match="different"):
        project.add_pipe("J-01", "J-01")
    with pytest.raises(ProjectValidationError, match="does not exist"):
        project.add_pipe("J-01", "O-99")


def test_validate_reports_duplicate_node_ids_and_missing_pipe_nodes():
    project = create_starter_project("Validation test")
    project.nodes.append(
        project.nodes[0].__class__(
            id="J-01", name="Duplicate", kind="junction", x=0.0, y=0.0
        )
    )
    project.pipes[0].to_node_id = "O-99"
    with pytest.raises(ProjectValidationError) as error:
        project.validate()
    message = str(error.value)
    assert "unique" in message
    assert "missing end node" in message


def test_clone_is_independent():
    project = create_example_project()
    clone = project.clone()
    clone.pipes[0].diameter_m = 2.0
    assert project.pipes[0].diameter_m == pytest.approx(0.9)


def test_bundled_example_json_matches_generator() -> None:
    path = Path(__file__).resolve().parents[1] / "data" / "example_project.json"
    loaded = EngineeringProject.load(path)
    assert loaded.to_dict() == create_example_project().to_dict()
