"""PyQtGraph charts used by the desktop dashboard and analysis pages."""

from __future__ import annotations

from collections.abc import Sequence

import pyqtgraph as pg
from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont
from PySide6.QtWidgets import QVBoxLayout, QWidget

from gui.theme import COLORS, STATUS_COLORS


def _style_axis(axis: pg.AxisItem) -> None:
    axis.setPen(pg.mkPen(COLORS["border"]))
    axis.setTextPen(pg.mkPen(COLORS["text_muted"]))
    font = QFont()
    font.setPointSize(8)
    axis.setStyle(tickFont=font, tickLength=4)


class UtilisationChart(QWidget):
    """Categorical screening chart with 80% and 100% reference lines."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        self.plot = pg.PlotWidget(background=None)
        self.plot.setMinimumHeight(220)
        self.plot.setMenuEnabled(False)
        self.plot.setMouseEnabled(x=False, y=False)
        self.plot.hideButtons()
        self.plot.showGrid(x=False, y=True, alpha=0.14)
        self.plot.setLabel("left", "Capacity utilisation", units="%")
        self.plot.getAxis("left").setWidth(46)
        self.plot.getAxis("bottom").setHeight(34)
        _style_axis(self.plot.getAxis("left"))
        _style_axis(self.plot.getAxis("bottom"))
        self.plot.getAxis("left").setLabel(
            "Utilisation (%)", color=COLORS["text_muted"], size="8pt"
        )
        self.plot.getPlotItem().layout.setContentsMargins(2, 4, 8, 2)
        layout.addWidget(self.plot)
        self._has_data = False

    def set_data(
        self,
        labels: Sequence[str],
        values: Sequence[float],
        classifications: Sequence[str],
        *,
        empty_message: str = "No pipe results available",
    ) -> None:
        self.plot.clear()
        font = QFont()
        font.setPointSize(8)
        bottom = self.plot.getAxis("bottom")
        bottom.setStyle(tickFont=font)

        if not values:
            text = pg.TextItem(
                empty_message,
                color=COLORS["text_muted"],
                anchor=(0.5, 0.5),
            )
            self.plot.addItem(text)
            text.setPos(0, 50)
            self.plot.setXRange(-1, 1, padding=0)
            self.plot.setYRange(0, 120, padding=0)
            bottom.setTicks([[]])
            self._has_data = False
            return

        x_values = list(range(len(values)))
        brushes = [
            pg.mkBrush(QColor(STATUS_COLORS.get(item, COLORS["accent"])))
            for item in classifications
        ]
        self.plot.addItem(
            pg.BarGraphItem(
                x=x_values,
                height=list(values),
                width=0.56,
                brushes=brushes,
                pen=pg.mkPen(None),
            )
        )

        line_80 = pg.InfiniteLine(
            pos=80,
            angle=0,
            pen=pg.mkPen(
                COLORS["warning"],
                width=1,
                style=Qt.PenStyle.DashLine,
            ),
            label="80%",
            labelOpts={
                "color": COLORS["warning"],
                "position": 0.97,
                "anchors": [(1, 1), (1, 1)],
            },
        )
        line_100 = pg.InfiniteLine(
            pos=100,
            angle=0,
            pen=pg.mkPen(
                COLORS["danger"],
                width=1,
                style=Qt.PenStyle.DashLine,
            ),
            label="100%",
            labelOpts={
                "color": COLORS["danger"],
                "position": 0.97,
                "anchors": [(1, 1), (1, 1)],
            },
        )
        self.plot.addItem(line_80)
        self.plot.addItem(line_100)

        short_labels = []
        for index, text in enumerate(labels):
            clean = text if len(text) <= 16 else text[:15] + "..."
            short_labels.append((index, clean))
        bottom.setTicks([short_labels])
        self.plot.setXRange(-0.65, len(values) - 0.35, padding=0)
        top = max(120.0, max(values) * 1.16)
        self.plot.setYRange(0, top, padding=0)
        self._has_data = True
