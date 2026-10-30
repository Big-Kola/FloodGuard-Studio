"""Background analysis worker."""

from __future__ import annotations

from PySide6.QtCore import QThread, Signal

from floodguard.analysis import analyse_project
from floodguard.project import EngineeringProject


class AnalysisWorker(QThread):
    finished_ok = Signal(object, int)
    failed = Signal(str, int)

    def __init__(
        self,
        project: EngineeringProject,
        selected_pipe_id: str | None,
        generation: int,
        parent=None,
    ) -> None:
        super().__init__(parent)
        self._project = project.clone()
        self._selected_pipe_id = selected_pipe_id
        self._generation = generation

    def run(self) -> None:
        try:
            result = analyse_project(
                self._project,
                selected_pipe_id=self._selected_pipe_id,
            )
        except Exception as error:  # noqa: BLE001 - surfaced in the UI
            self.failed.emit(str(error), self._generation)
            return
        self.finished_ok.emit(result, self._generation)
