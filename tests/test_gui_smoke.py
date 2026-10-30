"""Headless smoke and interaction tests for the Qt desktop shell."""

from __future__ import annotations

import pytest
from PySide6.QtWidgets import QFileDialog, QLabel, QMessageBox

from floodguard.project import EngineeringProject, create_example_project
from gui.main_window import NAV_ITEMS, MainWindow
from gui.state import AppSettings


@pytest.fixture
def window(qtbot, tmp_path, monkeypatch):
    monkeypatch.setenv("XDG_CONFIG_HOME", str(tmp_path / "config"))
    settings = AppSettings(
        default_project_directory=str(tmp_path / "projects"),
        default_reports_directory=str(tmp_path / "reports"),
    )
    main = MainWindow(settings=settings)
    monkeypatch.setattr(main, "_maybe_save_changes", lambda: True)
    qtbot.addWidget(main)
    main.resize(1480, 930)
    main.show()
    qtbot.wait(40)
    yield main
    main.dirty = False
    main.close()


def test_window_starts_with_analysed_starter_project(window):
    assert window.project is not None
    assert len(window.project.nodes) == 2
    assert len(window.project.pipes) == 1
    assert window.analysis is not None
    assert window.analysis.runoff.peak_runoff_m3_s == pytest.approx(0.9375)
    assert window.analysis.pipes[0].assessment.utilisation_percent == pytest.approx(
        55.298, abs=0.01
    )
    assert window.pages.count() == len(NAV_ITEMS)


def test_all_workspace_pages_navigate(window):
    for key, _ in NAV_ITEMS:
        window.navigate(key)
        assert window.pages.currentWidget() is window.page_map[key]
        assert window._page_key == key


def test_network_selection_updates_properties_and_hydraulics(window):
    window.navigate("network")
    window.network.scene.clearSelection()
    window.network.scene.pipe_items["P-01"].setSelected(True)
    window.network.scene.selectionChanged.emit()

    assert window._selection_kind == "pipe"
    assert window._selection_id == "P-01"
    assert window.properties._selection_kind == "pipe"
    assert window.properties._selection_id == "P-01"
    assert window.hydraulics._current_id == "P-01"


def test_add_node_selects_asset_and_undo_redo_restore_network(window):
    original_count = len(window.project.nodes)
    window.navigate("network")
    window.network.add_junction()

    assert len(window.project.nodes) == original_count + 1
    node = window.project.nodes[-1]
    assert window.dirty
    assert window._selection_kind == "node"
    assert window._selection_id == node.id
    assert window.properties._selection_id == node.id
    assert window.undo_action.isEnabled()

    window.undo()
    assert len(window.project.nodes) == original_count
    assert window.redo_action.isEnabled()

    window.redo()
    assert len(window.project.nodes) == original_count + 1


def test_connect_pipe_updates_selection_and_analysis(window):
    window.navigate("network")
    original_count = len(window.project.pipes)
    window.network.connect_button.setChecked(True)
    window.network._node_clicked("J-01")
    window.network._node_clicked("O-01")

    assert len(window.project.pipes) == original_count + 1
    pipe = window.project.pipes[-1]
    assert window._selection_kind == "pipe"
    assert window._selection_id == pipe.id
    assert window.analysis is not None
    assert window.analysis.pipe_result(pipe.id) is not None
    assert window.properties._selection_kind == "pipe"


def test_hydrology_apply_recalculates_and_supports_undo(window):
    window.navigate("hydrology")
    window.hydrology.rainfall.setValue(135.0)
    window.hydrology._apply()

    assert window.project.catchment.rainfall_intensity_mm_h == 135.0
    assert window.analysis is not None
    assert window.analysis.runoff.peak_runoff_m3_s == pytest.approx(1.40625)
    assert window.dirty

    window.undo()
    assert window.project.catchment.rainfall_intensity_mm_h == 90.0
    assert window.analysis is not None
    assert window.analysis.runoff.peak_runoff_m3_s == pytest.approx(0.9375)


def test_load_example_and_reduce_scenarios_without_stale_page_state(window):
    window.load_example()
    assert len(window.project.nodes) == 3
    assert len(window.project.pipes) == 2
    assert len(window.project.scenarios) == 3
    assert window.analysis is not None
    assert len(window.analysis.scenario_results) == 3
    assert window.scenarios.table.rowCount() == 3

    window._select_pipe("P-02")
    assert window.analysis.selected_pipe is not None
    assert window.analysis.selected_pipe.pipe.id == "P-02"
    assert window.dashboard.selected_pipe.text() == "Reach J2-O1"
    assert window.dashboard.utilisation_metric.value.text() == "35.8"

    example = create_example_project()
    example.scenarios = example.scenarios[:1]
    window._set_project(example, path=None, dirty=False, reset_undo=True)

    assert len(window.project.scenarios) == 1
    assert window.analysis is not None
    assert len(window.analysis.scenario_results) == 1
    assert window.scenarios.table.rowCount() == 1
    assert window._scenario_name == example.scenarios[0].name


def test_project_save_load_round_trip_through_window(window, tmp_path):
    window.project.metadata.name = "GUI Round Trip"
    window.project.catchment.area_ha = 7.5
    window.dirty = False
    path = window.project.save(tmp_path / "gui-round-trip.fgsproj")

    loaded = EngineeringProject.load(path)
    assert loaded.metadata.name == "GUI Round Trip"
    assert loaded.catchment.area_ha == 7.5
    assert loaded.to_dict() == window.project.to_dict()

    window._set_project(loaded, path=path, dirty=False, reset_undo=True)
    assert window.current_path == path
    assert window.top_project.text() == "GUI Round Trip"


def test_settings_reject_empty_folders(window, monkeypatch):
    warnings: list[tuple] = []
    monkeypatch.setattr(
        QMessageBox,
        "warning",
        lambda *args, **kwargs: warnings.append(args),
    )
    original = window.settings.default_project_directory
    window.navigate("settings")
    window.settings_page.projects_dir.setText("")
    window.settings_page._save()

    assert warnings
    assert window.settings.default_project_directory == original


def test_scope_reminders_follow_preference(window):
    hidden = AppSettings(
        default_project_directory=window.settings.default_project_directory,
        default_reports_directory=window.settings.default_reports_directory,
        show_scope_notes=False,
    )
    window._settings_changed(hidden)
    window.navigate("dashboard")
    assert window.dashboard.scope_banner.isHidden()
    assert window.hydrology.scope.isHidden()
    assert window.hydraulics.scope.isHidden()
    assert window.scenarios.scope_banner.isHidden()
    assert window.reports.scope_banner.isHidden()

    visible = AppSettings(
        default_project_directory=window.settings.default_project_directory,
        default_reports_directory=window.settings.default_reports_directory,
        show_scope_notes=True,
    )
    window._settings_changed(visible)
    assert not window.dashboard.scope_banner.isHidden()
    assert not window.reports.scope_banner.isHidden()


def test_properties_report_actual_save_state(window, tmp_path):
    window.navigate("dashboard")
    texts = [item.text() for item in window.properties.findChildren(QLabel)]
    assert "New unsaved project" in texts
    assert "Saved: " not in " ".join(texts)

    path = window.project.save(tmp_path / "saved-project.fgsproj")
    window.current_path = path
    window.dirty = False
    window._refresh_properties()

    texts = [item.text() for item in window.properties.findChildren(QLabel)]
    assert f"Saved: {path.name}" in texts

    window.dirty = True
    window._refresh_properties()
    texts = [item.text() for item in window.properties.findChildren(QLabel)]
    assert "Unsaved changes" in texts


def test_save_project_refreshes_save_state_indicator(window, tmp_path):
    window.navigate("dashboard")
    window.current_path = tmp_path / "indicator.fgsproj"
    window.dirty = True
    assert window.save_project()

    texts = [item.text() for item in window.properties.findChildren(QLabel)]
    assert "Saved: indicator.fgsproj" in texts
    assert "Unsaved changes" not in texts


def test_report_export_creates_missing_default_directory(window, tmp_path, monkeypatch):
    target = tmp_path / "new-reports-folder"
    assert not target.exists()
    window.reports.set_default_directory(str(target))
    monkeypatch.setattr(
        QFileDialog,
        "getSaveFileName",
        lambda *args, **kwargs: ("", ""),
    )

    window.reports.export_pdf()

    assert target.is_dir()


def test_bundled_report_generation_from_window_analysis(window, tmp_path):
    from floodguard.reporting import build_studio_pdf_report

    assert window.analysis is not None
    destination = tmp_path / "gui-report.pdf"
    destination.write_bytes(build_studio_pdf_report(window.project, window.analysis))
    assert destination.read_bytes().startswith(b"%PDF")
    assert destination.stat().st_size > 1000
