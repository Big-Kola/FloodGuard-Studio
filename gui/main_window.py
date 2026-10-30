"""FloodGuard Studio main desktop window."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from PySide6.QtCore import QSettings, QSize, Qt
from PySide6.QtGui import QAction, QCloseEvent, QColor, QIcon, QKeySequence
from PySide6.QtWidgets import (
    QFileDialog,
    QFrame,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QMainWindow,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSplitter,
    QStackedWidget,
    QTabWidget,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from floodguard import __version__ as APP_VERSION
from floodguard.analysis import ProjectAnalysis, analyse_project
from floodguard.paths import ensure_directory
from floodguard.project import (
    APP_NAME,
    PROJECT_EXTENSION,
    PROJECT_FILE_FILTER,
    Catchment,
    EngineeringProject,
    ProjectError,
    create_example_project,
    create_starter_project,
)
from gui.dialogs import NewProjectDialog
from gui.icons import action_icon, nav_icon
from gui.pages.dashboard import DashboardPage
from gui.pages.hydraulics import HydraulicsPage
from gui.pages.hydrology import HydrologyPage
from gui.pages.network import NetworkPage
from gui.pages.reports import ReportsPage
from gui.pages.scenarios import ScenariosPage
from gui.pages.settings import SettingsPage
from gui.properties import PropertiesPanel
from gui.state import AppSettings
from gui.theme import COLORS
from gui.widgets import label
from gui.workers import AnalysisWorker

NAV_ITEMS = [
    ("dashboard", "Dashboard"),
    ("network", "Drainage Network"),
    ("hydrology", "Rainfall & Hydrology"),
    ("hydraulics", "Hydraulic Analysis"),
    ("scenarios", "Scenario Comparison"),
    ("reports", "Engineering Reports"),
    ("settings", "Settings"),
]


class MainWindow(QMainWindow):
    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        settings: AppSettings | None = None,
    ) -> None:
        super().__init__(parent)
        self.settings = settings or AppSettings.load()
        self.project: EngineeringProject | None = None
        self.analysis: ProjectAnalysis | None = None
        self.current_path: Path | None = None
        self.dirty = False
        self._selection_kind = ""
        self._selection_id = ""
        self._scenario_name = ""
        self._page_key = "dashboard"
        self._undo_stack: list[dict] = []
        self._redo_stack: list[dict] = []
        self._analysis_generation = 0
        self._worker: AnalysisWorker | None = None
        self._initializing = True

        self.setObjectName("MainWindow")
        self.setMinimumSize(1180, 740)
        self.resize(1480, 930)
        self._build_actions()
        self._build_ui()
        self._create_pages()
        self._connect_pages()
        self._restore_window_state()
        self._start_initial_project()
        self._initializing = False

    def _build_actions(self) -> None:
        self.new_action = QAction("New Project", self)
        self.new_action.setShortcut(QKeySequence.StandardKey.New)
        self.new_action.triggered.connect(self.new_project)
        self.open_action = QAction("Open Project", self)
        self.open_action.setShortcut(QKeySequence.StandardKey.Open)
        self.open_action.triggered.connect(self.open_project)
        self.save_action = QAction("Save Project", self)
        self.save_action.setShortcut(QKeySequence.StandardKey.Save)
        self.save_action.triggered.connect(self.save_project)
        self.save_as_action = QAction("Save Project As", self)
        self.save_as_action.setShortcut(QKeySequence.StandardKey.SaveAs)
        self.save_as_action.triggered.connect(self.save_project_as)
        self.run_action = QAction("Run Analysis", self)
        self.run_action.setShortcut(QKeySequence("F5"))
        self.run_action.triggered.connect(self.run_analysis)
        self.export_action = QAction("Export Report", self)
        self.export_action.setShortcut(QKeySequence("Ctrl+E"))
        self.export_action.triggered.connect(self.export_report)
        self.undo_action = QAction("Undo", self)
        self.undo_action.setShortcut(QKeySequence.StandardKey.Undo)
        self.undo_action.triggered.connect(self.undo)
        self.redo_action = QAction("Redo", self)
        self.redo_action.setShortcut(QKeySequence.StandardKey.Redo)
        self.redo_action.triggered.connect(self.redo)
        self.quit_action = QAction("Exit", self)
        self.quit_action.setShortcut(QKeySequence.StandardKey.Quit)
        self.quit_action.triggered.connect(self.close)
        for action in (
            self.new_action,
            self.open_action,
            self.save_action,
            self.save_as_action,
            self.run_action,
            self.export_action,
            self.undo_action,
            self.redo_action,
            self.quit_action,
        ):
            self.addAction(action)
        self._update_action_state()

    def _build_ui(self) -> None:
        root = QWidget()
        root.setObjectName("AppRoot")
        self.setCentralWidget(root)
        layout = QHBoxLayout(root)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)

        sidebar = QFrame()
        sidebar.setObjectName("Sidebar")
        sidebar.setFixedWidth(220)
        sidebar_layout = QVBoxLayout(sidebar)
        sidebar_layout.setContentsMargins(0, 0, 0, 0)
        sidebar_layout.setSpacing(0)

        brand = QWidget()
        brand_layout = QHBoxLayout(brand)
        brand_layout.setContentsMargins(18, 18, 14, 14)
        brand_layout.setSpacing(10)
        mark = QLabel("FG")
        mark.setObjectName("BrandMark")
        mark.setFixedSize(38, 38)
        mark.setAlignment(Qt.AlignmentFlag.AlignCenter)
        brand_layout.addWidget(mark)
        brand_text = QVBoxLayout()
        brand_text.setSpacing(0)
        brand_text.addWidget(label("FLOODGUARD", "BrandName"))
        brand_text.addWidget(label("STUDIO  |  DESKTOP", "BrandSub"))
        brand_layout.addLayout(brand_text)
        brand_layout.addStretch(1)
        sidebar_layout.addWidget(brand)

        self.nav = QListWidget()
        self.nav.setObjectName("Nav")
        self.nav.setIconSize(QSize(16, 16))
        self.nav.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.nav.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        for key, title in NAV_ITEMS:
            item = QListWidgetItem(nav_icon(key), title)
            item.setData(Qt.ItemDataRole.UserRole, key)
            item.setSizeHint(QSize(0, 42))
            self.nav.addItem(item)
        self.nav.currentRowChanged.connect(self._nav_changed)
        sidebar_layout.addWidget(self.nav, 1)

        project_card = QFrame()
        project_card.setObjectName("Card")
        project_card.setStyleSheet(
            f"QFrame#Card {{ background: {COLORS['surface']}; border: 1px solid "
            f"{COLORS['border_soft']}; border-radius: 9px; }}"
        )
        card_layout = QVBoxLayout(project_card)
        card_layout.setContentsMargins(12, 10, 12, 10)
        card_layout.setSpacing(3)
        card_layout.addWidget(label("ACTIVE PROJECT", "CardTitle"))
        self.nav_project = label("Untitled Project", "Muted", wrap=True)
        card_layout.addWidget(self.nav_project)
        self.nav_file = label("Unsaved project", "Faint", wrap=True)
        card_layout.addWidget(self.nav_file)
        card_margin = QWidget()
        margin_layout = QVBoxLayout(card_margin)
        margin_layout.setContentsMargins(12, 8, 12, 8)
        margin_layout.addWidget(project_card)
        sidebar_layout.addWidget(card_margin)

        version = label(f"v{APP_VERSION}  |  Offline screening", "Faint")
        version.setContentsMargins(18, 0, 18, 14)
        sidebar_layout.addWidget(version)
        layout.addWidget(sidebar)

        workspace = QWidget()
        workspace_layout = QHBoxLayout(workspace)
        workspace_layout.setContentsMargins(0, 0, 0, 0)
        workspace_layout.setSpacing(0)

        centre = QWidget()
        centre_layout = QVBoxLayout(centre)
        centre_layout.setContentsMargins(0, 0, 0, 0)
        centre_layout.setSpacing(0)
        centre_layout.addWidget(self._build_topbar())

        splitter = QSplitter(Qt.Orientation.Vertical)
        splitter.setChildrenCollapsible(False)
        self.pages = QStackedWidget()
        splitter.addWidget(self.pages)
        splitter.addWidget(self._build_bottom_panel())
        splitter.setStretchFactor(0, 5)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([690, 160])
        centre_layout.addWidget(splitter, 1)
        workspace_layout.addWidget(centre, 1)

        self.properties = PropertiesPanel()
        workspace_layout.addWidget(self.properties)
        layout.addWidget(workspace, 1)

        self.statusBar().showMessage("Ready", 5000)
        self.scope_status = QLabel(
            "  Independent pipe screening  |  no network solver  "
        )
        self.scope_status.setStyleSheet(
            f"color: {COLORS['text_faint']}; font-size: 9px;"
        )
        self.statusBar().addPermanentWidget(self.scope_status)

    def _build_topbar(self) -> QWidget:
        topbar = QFrame()
        topbar.setObjectName("Topbar")
        topbar.setFixedHeight(64)
        layout = QHBoxLayout(topbar)
        layout.setContentsMargins(20, 10, 16, 10)
        layout.setSpacing(8)
        titles = QVBoxLayout()
        titles.setSpacing(1)
        self.top_project = label("Untitled Project", "SectionTitle")
        self.top_path = label("Unsaved project", "Faint")
        titles.addWidget(self.top_project)
        titles.addWidget(self.top_path)
        layout.addLayout(titles)
        layout.addStretch(1)

        self.new_button = QPushButton("New")
        self.new_button.setIcon(action_icon("new", COLORS["text"]))
        self.new_button.clicked.connect(self.new_project)
        self.open_button = QPushButton("Open")
        self.open_button.setIcon(action_icon("open", COLORS["accent"]))
        self.open_button.clicked.connect(self.open_project)
        self.save_button = QPushButton("Save")
        self.save_button.setIcon(action_icon("save", COLORS["accent"]))
        self.save_button.clicked.connect(self.save_project)
        layout.addWidget(self.new_button)
        layout.addWidget(self.open_button)
        layout.addWidget(self.save_button)

        self.undo_button = QToolButton()
        self.undo_button.setIcon(action_icon("undo", COLORS["text_muted"]))
        self.undo_button.setToolTip("Undo (Ctrl+Z)")
        self.undo_button.clicked.connect(self.undo)
        self.redo_button = QToolButton()
        self.redo_button.setIcon(action_icon("redo", COLORS["text_muted"]))
        self.redo_button.setToolTip("Redo (Ctrl+Y)")
        self.redo_button.clicked.connect(self.redo)
        layout.addWidget(self.undo_button)
        layout.addWidget(self.redo_button)

        separator = QFrame()
        separator.setFixedSize(1, 26)
        separator.setStyleSheet(f"background: {COLORS['border']};")
        layout.addSpacing(4)
        layout.addWidget(separator)
        layout.addSpacing(4)

        self.run_button = QPushButton("Run Analysis")
        self.run_button.setObjectName("PrimaryButton")
        self.run_button.setIcon(action_icon("run", COLORS["button_text"]))
        self.run_button.clicked.connect(self.run_analysis)
        self.export_button = QPushButton("Export Report")
        self.export_button.setIcon(action_icon("export", COLORS["accent"]))
        self.export_button.clicked.connect(self.export_report)
        layout.addWidget(self.run_button)
        layout.addWidget(self.export_button)
        return topbar

    def _build_bottom_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(14, 4, 14, 6)
        self.bottom_tabs = QTabWidget()
        self.bottom_tabs.setDocumentMode(True)
        flags = QWidget()
        flags_layout = QVBoxLayout(flags)
        flags_layout.setContentsMargins(8, 7, 8, 7)
        self.flags_list = QListWidget()
        self.flags_list.setStyleSheet(
            "QListWidget { border: none; background: transparent; }"
        )
        flags_layout.addWidget(self.flags_list)
        self.bottom_tabs.addTab(flags, "Screening Flags")
        logs = QWidget()
        logs_layout = QVBoxLayout(logs)
        logs_layout.setContentsMargins(8, 7, 8, 7)
        self.log_view = QPlainTextEdit()
        self.log_view.setReadOnly(True)
        self.log_view.setMaximumBlockCount(400)
        self.log_view.setStyleSheet(
            "QPlainTextEdit { border: none; background: transparent; font-size: 9px; }"
        )
        logs_layout.addWidget(self.log_view)
        self.bottom_tabs.addTab(logs, "Analysis Log")
        layout.addWidget(self.bottom_tabs)
        return panel

    def _create_pages(self) -> None:
        self.dashboard = DashboardPage()
        self.network = NetworkPage()
        self.hydrology = HydrologyPage()
        self.hydraulics = HydraulicsPage()
        self.scenarios = ScenariosPage()
        self.reports = ReportsPage()
        self.settings_page = SettingsPage()
        self.page_map = {
            "dashboard": self.dashboard,
            "network": self.network,
            "hydrology": self.hydrology,
            "hydraulics": self.hydraulics,
            "scenarios": self.scenarios,
            "reports": self.reports,
            "settings": self.settings_page,
        }
        for page in self.page_map.values():
            self.pages.addWidget(page)

    def _connect_pages(self) -> None:
        self.dashboard.run_requested.connect(self.run_analysis)
        self.dashboard.save_requested.connect(self.save_project)
        self.dashboard.navigate_requested.connect(self.navigate)
        self.dashboard.example_requested.connect(self.load_example)

        self.network.before_change.connect(self._record_undo)
        self.network.project_changed.connect(self._project_changed)
        self.network.element_selected.connect(self._network_selected)
        self.network.delete_requested.connect(self._delete_element)
        self.network.status_message.connect(self._status)

        self.hydrology.before_change.connect(self._record_undo)
        self.hydrology.project_changed.connect(self._project_changed)
        self.hydrology.status_message.connect(self._status)

        self.hydraulics.pipe_selected.connect(self._select_pipe)
        self.hydraulics.navigate_requested.connect(self.navigate)

        self.scenarios.before_change.connect(self._record_undo)
        self.scenarios.project_changed.connect(self._project_changed)
        self.scenarios.status_message.connect(self._status)
        self.scenarios.scenario_selected.connect(self._scenario_selected)

        self.reports.status_message.connect(self._status)
        self.settings_page.settings_changed.connect(self._settings_changed)
        self.settings_page.status_message.connect(self._status)

        self.properties.before_change.connect(self._record_undo)
        self.properties.project_changed.connect(self._project_changed)
        self.properties.delete_requested.connect(self._delete_element)
        self.properties.navigate_requested.connect(self.navigate)
        self.properties.status_message.connect(self._status)

    def _restore_window_state(self) -> None:
        settings = QSettings("FloodGuard", "FloodGuard Studio")
        geometry = settings.value("window/geometry")
        if geometry is not None:
            self.restoreGeometry(geometry)
        state = settings.value("window/state")
        if state is not None:
            self.restoreState(state)

    def _start_initial_project(self) -> None:
        catchment = Catchment(
            area_ha=self.settings.default_area_ha,
            rainfall_intensity_mm_h=self.settings.default_rainfall_intensity_mm_h,
            runoff_coefficient=self.settings.default_runoff_coefficient,
        )
        project = create_starter_project("Untitled Project", catchment=catchment)
        self._set_project(project, path=None, dirty=False, reset_undo=True)
        self.settings_page.set_settings(self.settings)
        self.reports.set_default_directory(self.settings.default_reports_directory)
        self.scenarios.set_confirm_delete(self.settings.confirm_delete)
        self._apply_scope_setting()
        self._log(f"FloodGuard Studio {APP_VERSION} started.")
        self.navigate("dashboard")

    def _set_project(
        self,
        project: EngineeringProject,
        *,
        path: Path | None,
        dirty: bool,
        reset_undo: bool = False,
    ) -> None:
        self.project = project
        self.current_path = path
        self.dirty = dirty
        self._scenario_name = project.scenarios[0].name if project.scenarios else ""
        if reset_undo:
            self._undo_stack.clear()
            self._redo_stack.clear()
            self._update_undo_buttons()
        self._analysis_generation += 1
        self.analysis = None
        self._refresh_all_pages()
        self._analyse_sync(report_errors=True)
        self.network.request_fit()
        self._update_project_labels()
        self._update_action_state()
        self._refresh_properties()

    def _analyse_sync(self, report_errors: bool = False) -> bool:
        if self.project is None:
            self.analysis = None
            return False
        try:
            analysis = analyse_project(
                self.project,
                selected_pipe_id=self._selection_id
                if self._selection_kind == "pipe"
                else None,
            )
        except Exception as error:  # noqa: BLE001 - surfaced in the UI
            self.analysis = None
            self._status(f"Analysis failed: {error}")
            if report_errors:
                QMessageBox.critical(self, "Analysis failed", str(error))
            return False
        self.analysis = analysis
        self._set_analysis(analysis)
        return True

    def _set_analysis(self, analysis: ProjectAnalysis) -> None:
        self.analysis = analysis
        self.dashboard.set_analysis(analysis)
        self.network.set_analysis(analysis)
        self.hydrology.set_analysis(analysis)
        self.hydraulics.set_analysis(analysis)
        self.scenarios.set_analysis(analysis)
        self.reports.set_analysis(analysis)
        selected_scenario = self.scenarios.selected_scenario()
        self._scenario_name = (
            selected_scenario.name if selected_scenario is not None else ""
        )
        self._fill_flags(analysis)
        self._refresh_properties()

    def _refresh_all_pages(self) -> None:
        if self.project is None:
            return
        selected_kind = self._selection_kind
        selected_id = self._selection_id
        if selected_kind == "node" and self.project.find_node(selected_id) is None:
            selected_kind, selected_id = "", ""
        if selected_kind == "pipe" and self.project.find_pipe(selected_id) is None:
            selected_kind = "pipe"
            selected_id = self.project.pipes[0].id if self.project.pipes else ""
            if not selected_id:
                selected_kind = ""
        self._selection_kind = selected_kind
        self._selection_id = selected_id

        self.dashboard.set_project(self.project)
        self.network.set_project(
            self.project,
            selected_kind=selected_kind,
            selected_id=selected_id,
        )
        self.hydrology.set_project(self.project)
        pipe_id = (
            selected_id
            if selected_kind == "pipe"
            else (
                self.analysis.selected_pipe.pipe.id
                if self.analysis and self.analysis.selected_pipe
                else ""
            )
        )
        self.hydraulics.set_project(self.project, selected_pipe_id=pipe_id)
        self.scenarios.set_project(self.project)
        self.reports.set_project(self.project)
        if self.analysis is not None:
            self.dashboard.set_analysis(self.analysis)
            self.network.set_analysis(self.analysis)
            self.hydrology.set_analysis(self.analysis)
            self.hydraulics.set_analysis(self.analysis)
            self.scenarios.set_analysis(self.analysis)
            self.reports.set_analysis(self.analysis)
            selected_scenario = self.scenarios.selected_scenario()
            self._scenario_name = (
                selected_scenario.name if selected_scenario is not None else ""
            )
            self._fill_flags(self.analysis)

    def _project_changed(self) -> None:
        if self.project is None or self._initializing:
            return
        self.project.touch()
        self.dirty = True
        self._analysis_generation += 1
        self._analyse_sync(report_errors=False)
        self._refresh_all_pages()
        self._update_project_labels()
        self._update_action_state()
        self._refresh_properties()

    def _update_project_labels(self) -> None:
        if self.project is None:
            return
        name = self.project.metadata.name
        marker = " *" if self.dirty else ""
        self.setWindowTitle(f"{APP_NAME} | {name}{marker}")
        self.top_project.setText(name)
        if self.current_path is not None:
            path_text = str(self.current_path)
            self.top_path.setText(path_text)
            self.top_path.setToolTip(path_text)
            self.nav_file.setText(self.current_path.name)
            self.nav_file.setToolTip(path_text)
        else:
            self.top_path.setText("Unsaved project")
            self.nav_file.setText("Unsaved project")
        self.nav_project.setText(name)
        state = (
            "Unsaved changes"
            if self.dirty
            else ("Saved locally" if self.current_path else "New unsaved project")
        )
        if self.current_path is not None:
            self.nav_file.setText(f"{self.current_path.name}\n{state}")
        else:
            self.nav_file.setText(state)

    def _update_action_state(self) -> None:
        enabled = self.project is not None
        for action in (
            self.save_action,
            self.save_as_action,
            self.run_action,
            self.export_action,
        ):
            if action is not None:
                action.setEnabled(enabled)
        if hasattr(self, "save_button"):
            self.save_button.setEnabled(enabled)
            self.run_button.setEnabled(enabled)
            self.export_button.setEnabled(enabled)
        if hasattr(self, "undo_action"):
            self.undo_action.setEnabled(bool(self._undo_stack))
            self.redo_action.setEnabled(bool(self._redo_stack))
        if hasattr(self, "undo_button"):
            self.undo_button.setEnabled(bool(self._undo_stack))
            self.redo_button.setEnabled(bool(self._redo_stack))

    def _update_undo_buttons(self) -> None:
        if hasattr(self, "undo_button"):
            self.undo_button.setEnabled(bool(self._undo_stack))
            self.redo_button.setEnabled(bool(self._redo_stack))
            self.undo_action.setEnabled(bool(self._undo_stack))
            self.redo_action.setEnabled(bool(self._redo_stack))

    def _record_undo(self) -> None:
        if self.project is None or self._initializing:
            return
        self._undo_stack.append(self.project.to_dict())
        if len(self._undo_stack) > 60:
            self._undo_stack.pop(0)
        self._redo_stack.clear()
        self._update_undo_buttons()

    def undo(self) -> None:
        if not self._undo_stack or self.project is None:
            return
        self._redo_stack.append(self.project.to_dict())
        data = self._undo_stack.pop()
        try:
            project = EngineeringProject.from_dict(data)
        except ProjectError as error:
            self._status(f"Could not undo: {error}")
            return
        self.project = project
        self.dirty = True
        self._analysis_generation += 1
        self.analysis = None
        self._refresh_all_pages()
        self._analyse_sync(report_errors=False)
        self._update_project_labels()
        self._update_undo_buttons()
        self._status("Undo applied.")

    def redo(self) -> None:
        if not self._redo_stack or self.project is None:
            return
        self._undo_stack.append(self.project.to_dict())
        data = self._redo_stack.pop()
        try:
            project = EngineeringProject.from_dict(data)
        except ProjectError as error:
            self._status(f"Could not redo: {error}")
            return
        self.project = project
        self.dirty = True
        self._analysis_generation += 1
        self.analysis = None
        self._refresh_all_pages()
        self._analyse_sync(report_errors=False)
        self._update_project_labels()
        self._update_undo_buttons()
        self._status("Redo applied.")

    def _nav_changed(self, row: int) -> None:
        if not hasattr(self, "page_map"):
            return
        if row < 0 or row >= len(NAV_ITEMS):
            return
        self._show_page(NAV_ITEMS[row][0])

    def navigate(self, key: str) -> None:
        keys = [item[0] for item in NAV_ITEMS]
        if key not in keys:
            return
        row = keys.index(key)
        if self.nav.currentRow() != row:
            self.nav.setCurrentRow(row)
        else:
            self._show_page(key)

    def _show_page(self, key: str) -> None:
        page = self.page_map.get(key)
        if page is None:
            return
        self._page_key = key
        self.pages.setCurrentWidget(page)
        if key == "network" and self.network.needs_fit:
            self.network.fit_view()
        if key == "hydraulics" and self.analysis is not None:
            if self._selection_kind == "pipe" and self._selection_id:
                self.hydraulics.set_selected_pipe(self._selection_id)
            elif self.analysis.selected_pipe is not None:
                self.hydraulics.set_selected_pipe(self.analysis.selected_pipe.pipe.id)
        self._refresh_properties()

    def _refresh_properties(self) -> None:
        scenario_name = self._scenario_name
        self.properties.set_context(
            self._page_key,
            self.project,
            self.analysis,
            self._selection_kind,
            scenario_name if self._page_key == "scenarios" else self._selection_id,
            current_path=self.current_path,
            dirty=self.dirty,
        )

    def _network_selected(self, kind: str, element_id: str) -> None:
        if not kind:
            self._selection_kind = ""
            self._selection_id = ""
        else:
            self._selection_kind = kind
            self._selection_id = element_id
        if kind == "pipe" and self.hydraulics is not None:
            self.hydraulics.set_selected_pipe(element_id)
            if (
                self.analysis is not None
                and self.analysis.selected_pipe is not None
                and self.analysis.selected_pipe.pipe.id != element_id
            ):
                self._analysis_generation += 1
                self._analyse_sync(report_errors=False)
        self._refresh_properties()

    def _select_pipe(self, pipe_id: str) -> None:
        if self.project is None or self.project.find_pipe(pipe_id) is None:
            return
        self._selection_kind = "pipe"
        self._selection_id = pipe_id
        self.network.set_selected_element("pipe", pipe_id)
        self.hydraulics.set_selected_pipe(pipe_id)
        if (
            self.analysis is not None
            and self.analysis.selected_pipe is not None
            and self.analysis.selected_pipe.pipe.id != pipe_id
        ):
            self._analysis_generation += 1
            self._analyse_sync(report_errors=False)
        self._refresh_properties()

    def _scenario_selected(self, name: str) -> None:
        self._scenario_name = name
        if self._page_key == "scenarios":
            self._refresh_properties()

    def _delete_element(self, kind: str, element_id: str) -> None:
        if self.project is None:
            return
        if self.settings.confirm_delete:
            if kind == "node":
                node = self.project.find_node(element_id)
                title = "Delete node"
                message = f"Delete '{node.name if node else element_id}' and all connected pipes?"
            else:
                pipe = self.project.find_pipe(element_id)
                title = "Delete pipe"
                message = f"Delete '{pipe.name if pipe else element_id}'?"
            answer = QMessageBox.question(
                self,
                title,
                message,
                QMessageBox.StandardButton.Delete | QMessageBox.StandardButton.Cancel,
                QMessageBox.StandardButton.Cancel,
            )
            if answer != QMessageBox.StandardButton.Delete:
                return
        self._record_undo()
        try:
            if kind == "node":
                removed = self.project.remove_node(element_id)
                self._status(f"Deleted node and {removed} connected pipe(s).")
                self._selection_kind = ""
                self._selection_id = ""
            elif kind == "pipe":
                self.project.remove_pipe(element_id)
                self._selection_kind = ""
                self._selection_id = ""
                self._status("Deleted pipe.")
            else:
                return
        except ProjectError as error:
            self._status(str(error))
            return
        self._project_changed()

    def _settings_changed(self, settings: AppSettings) -> None:
        self.settings = settings
        self.settings_page.set_settings(settings)
        self.reports.set_default_directory(settings.default_reports_directory)
        self.scenarios.set_confirm_delete(settings.confirm_delete)
        self._apply_scope_setting()
        self._log("Application settings updated.")

    def _apply_scope_setting(self) -> None:
        visible = self.settings.show_scope_notes
        if hasattr(self, "dashboard"):
            self.dashboard.set_scope_visible(visible)
            self.hydrology.set_scope_visible(visible)
            self.hydraulics.set_scope_visible(visible)
            self.scenarios.set_scope_visible(visible)
            self.reports.set_scope_visible(visible)

    def _status(self, message: str) -> None:
        self.statusBar().showMessage(message, 8000)

    def _log(self, message: str) -> None:
        stamp = datetime.now().strftime("%H:%M:%S")
        self.log_view.appendPlainText(f"[{stamp}] {message}")

    def _fill_flags(self, analysis: ProjectAnalysis) -> None:
        self.flags_list.clear()
        flags = list(analysis.warnings)
        for warning in flags:
            item = QListWidgetItem(warning.message)
            color = (
                COLORS["danger"]
                if warning.level == "critical"
                else COLORS["warning"]
                if warning.level == "warning"
                else COLORS["text_muted"]
            )
            item.setForeground(QColor(color))
            item.setToolTip(warning.message)
            self.flags_list.addItem(item)
        if not flags:
            item = QListWidgetItem("No screening flags.")
            item.setForeground(QColor(COLORS["success"]))
            self.flags_list.addItem(item)
        self.bottom_tabs.setTabText(0, f"Screening Flags ({len(flags)})")

    def _set_busy(self, busy: bool) -> None:
        self.dashboard.set_busy(busy)
        self.run_button.setEnabled(not busy and self.project is not None)
        self.run_action.setEnabled(not busy and self.project is not None)

    def run_analysis(self) -> None:
        if self.project is None:
            return
        if self._worker is not None and self._worker.isRunning():
            return
        self._analysis_generation += 1
        generation = self._analysis_generation
        self._set_busy(True)
        self._status("Running project screening analysis...")
        self._log("Analysis started.")
        selected_id = self._selection_id if self._selection_kind == "pipe" else None
        worker = AnalysisWorker(self.project, selected_id, generation, self)
        self._worker = worker
        worker.finished_ok.connect(self._analysis_finished)
        worker.failed.connect(self._analysis_failed)
        worker.finished.connect(self._analysis_thread_finished)
        worker.start()

    def _analysis_finished(self, analysis: ProjectAnalysis, generation: int) -> None:
        if generation != self._analysis_generation:
            return
        self.analysis = analysis
        self._set_analysis(analysis)
        self._status(
            f"Analysis complete: {len(analysis.pipes)} pipes screened, "
            f"{analysis.runoff.peak_runoff_m3_s:,.4f} m³/s peak runoff."
        )
        self._log(
            f"Analysis complete. Peak runoff {analysis.runoff.peak_runoff_m3_s:.4f} m3/s; "
            f"{len(analysis.pipes)} pipe(s) screened."
        )

    def _analysis_failed(self, message: str, generation: int) -> None:
        if generation != self._analysis_generation:
            return
        self._status("Analysis failed.")
        self._log(f"Analysis failed: {message}")
        QMessageBox.critical(self, "Analysis failed", message)

    def _analysis_thread_finished(self) -> None:
        self._set_busy(False)

    def new_project(self) -> None:
        if not self._maybe_save_changes():
            return
        dialog = NewProjectDialog(
            default_engineer=self.project.metadata.engineer if self.project else ""
        )
        if dialog.exec() != NewProjectDialog.DialogCode.Accepted:
            return
        values = dialog.values()
        catchment = Catchment(
            area_ha=self.settings.default_area_ha,
            rainfall_intensity_mm_h=self.settings.default_rainfall_intensity_mm_h,
            runoff_coefficient=self.settings.default_runoff_coefficient,
        )
        project = create_starter_project(
            values["name"],
            engineer=values["engineer"],
            location=values["location"],
            description=values["description"],
            catchment=catchment,
        )
        project.metadata.project_number = values["project_number"]
        project.metadata.client = values["client"]
        self._selection_kind = ""
        self._selection_id = ""
        self.current_path = None
        self._set_project(project, path=None, dirty=True, reset_undo=True)
        self.navigate("dashboard")
        self._log(f"Created project '{project.metadata.name}'.")
        self._status("New project created.")

    def load_example(self) -> None:
        if not self._maybe_save_changes():
            return
        project = create_example_project()
        self._selection_kind = ""
        self._selection_id = ""
        self.current_path = None
        self._set_project(project, path=None, dirty=True, reset_undo=True)
        self.navigate("dashboard")
        self._log("Loaded the bundled demonstration project.")
        self._status("Example project loaded. Save it to keep your edits.")

    def open_project(self) -> None:
        if not self._maybe_save_changes():
            return
        default_dir = self.settings.default_project_directory
        ensure_directory(Path(default_dir).expanduser())
        filename, _ = QFileDialog.getOpenFileName(
            self,
            "Open FloodGuard Studio Project",
            default_dir,
            PROJECT_FILE_FILTER + ";;All files (*)",
        )
        if not filename:
            return
        try:
            project = EngineeringProject.load(filename)
        except (ProjectError, OSError) as error:
            QMessageBox.critical(self, "Project could not be opened", str(error))
            self._status("Project open failed.")
            return
        path = Path(filename)
        self.settings.default_project_directory = str(path.parent)
        self.settings.remember_recent(path)
        try:
            self.settings.save()
        except OSError:
            pass
        self._selection_kind = ""
        self._selection_id = ""
        self._set_project(project, path=path, dirty=False, reset_undo=True)
        self.navigate("dashboard")
        self._log(f"Opened project '{project.metadata.name}' from {path}.")
        self._status(f"Opened {path.name}.")

    def save_project(self) -> bool:
        if self.project is None:
            return False
        if self.current_path is None:
            return self.save_project_as()
        try:
            self.project.save(self.current_path)
        except (ProjectError, OSError) as error:
            QMessageBox.critical(self, "Project could not be saved", str(error))
            self._status("Project save failed.")
            return False
        self.dirty = False
        self.settings.remember_recent(self.current_path)
        try:
            self.settings.save()
        except OSError:
            pass
        self._update_project_labels()
        self._refresh_properties()
        self._log(f"Saved project to {self.current_path}.")
        self._status(f"Saved {self.current_path.name}.")
        return True

    def save_project_as(self) -> bool:
        if self.project is None:
            return False
        directory = self.settings.default_project_directory
        ensure_directory(Path(directory).expanduser())
        suggested = Path(directory) / self._filename_stem()
        filename, _ = QFileDialog.getSaveFileName(
            self,
            "Save FloodGuard Studio Project",
            str(suggested),
            PROJECT_FILE_FILTER,
        )
        if not filename:
            return False
        destination = Path(filename)
        if destination.suffix.lower() != PROJECT_EXTENSION:
            destination = destination.with_suffix(PROJECT_EXTENSION)
        try:
            saved = self.project.save(destination)
        except (ProjectError, OSError) as error:
            QMessageBox.critical(self, "Project could not be saved", str(error))
            self._status("Project save failed.")
            return False
        self.current_path = saved
        self.settings.default_project_directory = str(saved.parent)
        self.settings.remember_recent(saved)
        try:
            self.settings.save()
        except OSError:
            pass
        self.dirty = False
        self._update_project_labels()
        self._log(f"Saved project as {saved}.")
        self._status(f"Saved {saved.name}.")
        return True

    def _filename_stem(self) -> str:
        if self.project is None:
            return "FloodGuard_Project"
        name = "".join(
            character if character.isalnum() or character in "-_" else "_"
            for character in self.project.metadata.name
        ).strip("_")
        return (name[:70] or "FloodGuard_Project") + PROJECT_EXTENSION

    def export_report(self) -> None:
        if self.project is None:
            return
        if self.analysis is None:
            QMessageBox.warning(
                self,
                "No analysis available",
                "Run the analysis before exporting a report.",
            )
            return
        self.navigate("reports")
        self.reports.export_pdf()

    def _maybe_save_changes(self) -> bool:
        if not self.dirty or self.project is None:
            return True
        box = QMessageBox(self)
        box.setWindowTitle("Unsaved changes")
        box.setIcon(QMessageBox.Icon.Warning)
        box.setText("Save changes to the current project before continuing?")
        box.setInformativeText(
            "Unsaved engineering inputs and network edits will be lost if you discard them."
        )
        box.setStandardButtons(
            QMessageBox.StandardButton.Save
            | QMessageBox.StandardButton.Discard
            | QMessageBox.StandardButton.Cancel
        )
        box.setDefaultButton(QMessageBox.StandardButton.Save)
        answer = box.exec()
        if answer == QMessageBox.StandardButton.Save:
            return self.save_project()
        return answer == QMessageBox.StandardButton.Discard

    def closeEvent(self, event: QCloseEvent) -> None:
        if not self._maybe_save_changes():
            event.ignore()
            return
        if self._worker is not None and self._worker.isRunning():
            self._worker.wait(2500)
        try:
            self.settings.save()
        except OSError:
            pass
        window_settings = QSettings("FloodGuard", "FloodGuard Studio")
        window_settings.setValue("window/geometry", self.saveGeometry())
        window_settings.setValue("window/state", self.saveState())
        event.accept()

    def set_window_icon(self, icon: QIcon) -> None:
        self.setWindowIcon(icon)
