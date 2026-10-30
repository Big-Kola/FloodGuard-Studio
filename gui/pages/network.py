"""Interactive drainage network page."""

from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QKeySequence, QShortcut
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from floodguard.analysis import ProjectAnalysis
from floodguard.project import EngineeringProject
from gui.network_view import NetworkScene, NetworkView
from gui.theme import COLORS
from gui.widgets import Banner, label


class NetworkPage(QWidget):
    before_change = Signal()
    project_changed = Signal()
    element_selected = Signal(str, str)
    delete_requested = Signal(str, str)
    status_message = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.project: EngineeringProject | None = None
        self.analysis: ProjectAnalysis | None = None
        self._selected_kind = ""
        self._selected_id = ""
        self._connect_start = ""
        self._needs_fit = True
        self._build()

    def _build(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(24, 20, 24, 20)
        layout.setSpacing(12)

        header = QHBoxLayout()
        titles = QVBoxLayout()
        titles.setSpacing(3)
        titles.addWidget(label("Drainage Network", "PageTitle"))
        self.subtitle = label(
            "Schematic network editor",
            "PageSubtitle",
        )
        titles.addWidget(self.subtitle)
        header.addLayout(titles)
        header.addStretch(1)

        self.add_junction_button = QPushButton("Add Junction")
        self.add_junction_button.clicked.connect(self.add_junction)
        self.add_outfall_button = QPushButton("Add Outfall")
        self.add_outfall_button.clicked.connect(self.add_outfall)
        self.connect_button = QPushButton("Connect Pipe")
        self.connect_button.setCheckable(True)
        self.connect_button.toggled.connect(self._toggle_connect)
        self.fit_button = QPushButton("Fit View")
        self.fit_button.clicked.connect(self._fit_view)
        self.delete_button = QPushButton("Delete")
        self.delete_button.setObjectName("DangerButton")
        self.delete_button.clicked.connect(self._delete_selected)
        for button in (
            self.add_junction_button,
            self.add_outfall_button,
            self.connect_button,
            self.fit_button,
            self.delete_button,
        ):
            header.addWidget(button)
        layout.addLayout(header)

        self.hint = Banner(
            "Select an asset to edit it in the properties panel. Scroll to zoom; "
            "middle-drag to pan; drag nodes to revise schematic positions."
        )
        layout.addWidget(self.hint)

        self.scene = NetworkScene(self)
        self.view = NetworkView(self.scene, self)
        self.scene.prepare_change.connect(self.before_change)
        self.scene.node_moved.connect(self._node_moved)
        self.scene.element_selected.connect(self._scene_selected)
        self.scene.node_clicked.connect(self._node_clicked)
        self.scene.connect_cancelled.connect(self._cancel_connect)
        self.view.zoom_changed.connect(lambda _: self._update_summary())
        layout.addWidget(self.view, 1)

        footer = QHBoxLayout()
        self.summary = label("No network loaded", "Muted")
        footer.addWidget(self.summary)
        footer.addStretch(1)
        for text, color in (
            ("Within calculated capacity", COLORS["success"]),
            ("Approaching", COLORS["warning"]),
            ("Exceeds capacity", COLORS["danger"]),
        ):
            chip = QLabel("  " + text)
            chip.setStyleSheet(
                f"color: {COLORS['text_muted']}; font-size: 9px; "
                f"border-left: 3px solid {color}; padding-left: 6px;"
            )
            footer.addWidget(chip)
        layout.addLayout(footer)

        self._delete_shortcut = QShortcut(
            QKeySequence(QKeySequence.StandardKey.Delete), self
        )
        self._delete_shortcut.setContext(Qt.ShortcutContext.WidgetWithChildrenShortcut)
        self._delete_shortcut.activated.connect(self._delete_selected)

    def set_project(
        self,
        project: EngineeringProject,
        selected_kind: str = "",
        selected_id: str = "",
    ) -> None:
        self.project = project
        self.scene.bind_project(project)
        self.scene.set_analysis(self.analysis)
        self._connect_start = ""
        self.connect_button.blockSignals(True)
        self.connect_button.setChecked(False)
        self.connect_button.blockSignals(False)
        self.scene.set_connect_mode(False)
        self.view.setCursor(Qt.CursorShape.ArrowCursor)
        if selected_kind and selected_id:
            self._selected_kind = selected_kind
            self._selected_id = selected_id
            self.scene.select_element(selected_kind, selected_id)
        else:
            self._selected_kind = ""
            self._selected_id = ""
        self._update_summary()

    def set_analysis(self, analysis: ProjectAnalysis | None) -> None:
        self.analysis = analysis
        if self.project is not None:
            self.scene.set_analysis(analysis)

    def set_selected_element(self, kind: str, element_id: str) -> None:
        self._selected_kind = kind
        self._selected_id = element_id
        self.scene.select_element(kind, element_id)

    def _update_summary(self) -> None:
        if self.project is None:
            self.summary.setText("No network loaded")
            return
        self.summary.setText(
            f"{len(self.project.nodes)} nodes  |  {len(self.project.pipes)} pipes  |  "
            f"zoom {self.view.transform().m11() * 100:.0f}%"
        )
        self.subtitle.setText(
            "Schematic network editor"
            + (f"  |  {self.project.metadata.name}" if self.project else "")
        )

    @property
    def needs_fit(self) -> bool:
        return self._needs_fit

    def request_fit(self) -> None:
        self._needs_fit = True
        if self.isVisible():
            self.fit_view()

    def fit_view(self) -> None:
        self.view.fit_network()
        self._needs_fit = False
        self._update_summary()

    def _fit_view(self) -> None:
        self.fit_view()

    def _next_offset(self) -> tuple[float, float]:
        count = len(self.project.nodes) if self.project else 0
        offset = ((count * 37) % 140) - 70
        return offset, offset * 0.55

    def add_junction(self) -> None:
        self._add_node("junction")

    def add_outfall(self) -> None:
        self._add_node("outfall")

    def _add_node(self, kind: str) -> None:
        if self.project is None:
            return
        center = self.view.mapToScene(self.view.viewport().rect().center())
        offset_x, offset_y = self._next_offset()
        self.before_change.emit()
        node = self.project.add_node(kind, center.x() + offset_x, center.y() + offset_y)
        self._selected_kind = "node"
        self._selected_id = node.id
        self.element_selected.emit("node", node.id)
        self.project_changed.emit()
        self.status_message.emit(f"Added {node.display_kind.lower()} {node.name}.")
        self.scene.select_element("node", node.id)

    def _toggle_connect(self, enabled: bool) -> None:
        if self.project is None or len(self.project.nodes) < 2:
            if enabled:
                self.connect_button.setChecked(False)
                self.status_message.emit(
                    "Add at least two nodes before connecting a pipe."
                )
            return
        self.scene.set_connect_mode(enabled)
        if enabled:
            self._connect_start = ""
            self.view.setCursor(Qt.CursorShape.CrossCursor)
            self.hint.setText(
                "Connect mode: click the upstream node, then the downstream node. "
                "Click empty canvas or press Escape to cancel."
            )
        else:
            self._clear_connect_highlight()
            self._connect_start = ""
            self.view.setCursor(Qt.CursorShape.ArrowCursor)
            self.hint.setText(
                "Select an asset to edit it in the properties panel. Scroll to zoom; "
                "middle-drag to pan; drag nodes to revise schematic positions."
            )

    def _node_clicked(self, node_id: str) -> None:
        if self.project is None:
            return
        if not self._connect_start:
            self._connect_start = node_id
            self._clear_connect_highlight()
            item = self.scene.node_items.get(node_id)
            if item is not None:
                item.set_connect_highlight(True)
            node = self.project.find_node(node_id)
            self.hint.setText(
                f"Connect pipe: start = {node.name if node else node_id}. "
                "Now click the downstream node."
            )
            return
        if node_id == self._connect_start:
            self.status_message.emit("A pipe requires two different nodes.")
            return
        self.before_change.emit()
        try:
            pipe = self.project.add_pipe(self._connect_start, node_id)
        except Exception as error:  # noqa: BLE001 - user-facing model error
            self.status_message.emit(str(error))
            return
        self._selected_kind = "pipe"
        self._selected_id = pipe.id
        self.connect_button.setChecked(False)
        self.element_selected.emit("pipe", pipe.id)
        self.project_changed.emit()
        self.status_message.emit(f"Added {pipe.name}.")
        self.scene.select_element("pipe", pipe.id)

    def _cancel_connect(self) -> None:
        if self.connect_button.isChecked():
            self.connect_button.setChecked(False)
            self.status_message.emit("Pipe connection cancelled.")

    def _clear_connect_highlight(self) -> None:
        for item in self.scene.node_items.values():
            item.set_connect_highlight(False)

    def _scene_selected(self, kind: str, element_id: str) -> None:
        self._selected_kind = kind
        self._selected_id = element_id
        self.element_selected.emit(kind, element_id)

    def _node_moved(self) -> None:
        self.project_changed.emit()
        self.status_message.emit("Node position updated.")

    def _delete_selected(self) -> None:
        if self._selected_kind and self._selected_id:
            self.delete_requested.emit(self._selected_kind, self._selected_id)
        else:
            self.status_message.emit("Select a node or pipe to delete.")

    def keyPressEvent(self, event) -> None:
        if event.key() == Qt.Key.Key_Escape and self.connect_button.isChecked():
            self.connect_button.setChecked(False)
            return
        super().keyPressEvent(event)
