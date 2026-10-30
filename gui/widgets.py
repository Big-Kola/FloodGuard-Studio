"""Reusable Qt widgets and layout helpers."""

from __future__ import annotations

import math

from PySide6.QtCore import QRectF, Qt
from PySide6.QtGui import QColor, QFont, QPainter, QPen
from PySide6.QtWidgets import (
    QFrame,
    QHBoxLayout,
    QLabel,
    QLayout,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from gui.theme import COLORS, STATUS_COLORS


def alpha_color(color: str, alpha: str) -> str:
    """Return a Qt CSS colour with a leading alpha channel (#AARRGGBB)."""
    return f"#{alpha}{color.lstrip('#')}"


def clear_layout(layout: QLayout) -> None:
    while layout.count():
        item = layout.takeAt(0)
        widget = item.widget()
        child_layout = item.layout()
        if widget is not None:
            widget.hide()
            widget.setParent(None)
            widget.deleteLater()
        elif child_layout is not None:
            clear_layout(child_layout)


def label(text: str, object_name: str = "", *, wrap: bool = False) -> QLabel:
    widget = QLabel(text)
    if object_name:
        widget.setObjectName(object_name)
    widget.setWordWrap(wrap)
    return widget


class Card(QFrame):
    def __init__(self, title: str = "", parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setObjectName("Card")
        self.layout = QVBoxLayout(self)
        self.layout.setContentsMargins(16, 14, 16, 14)
        self.layout.setSpacing(10)
        if title:
            self.layout.addWidget(label(title.upper(), "CardTitle"))

    def add(self, widget_or_layout) -> None:
        if isinstance(widget_or_layout, QLayout):
            self.layout.addLayout(widget_or_layout)
        else:
            self.layout.addWidget(widget_or_layout)

    def add_stretch(self) -> None:
        self.layout.addStretch(1)


class MetricCard(QFrame):
    def __init__(
        self,
        caption: str,
        value: str = "-",
        unit: str = "",
        accent: str | None = None,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("Card")
        self.setMinimumWidth(145)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(15, 12, 15, 12)
        layout.setSpacing(3)
        top = QHBoxLayout()
        top.setSpacing(6)
        self.caption = label(caption.upper(), "CardTitle")
        top.addWidget(self.caption)
        top.addStretch(1)
        self.marker = QLabel(" ")
        self.marker.setFixedSize(7, 7)
        self.marker.setStyleSheet(
            f"background: {accent or COLORS['accent']}; border-radius: 3px;"
        )
        top.addWidget(self.marker)
        layout.addLayout(top)
        row = QHBoxLayout()
        row.setSpacing(5)
        self.value = label(value, "KpiValue")
        self.unit = label(unit, "KpiUnit")
        row.addWidget(self.value)
        row.addWidget(self.unit, 0, Qt.AlignmentFlag.AlignBottom)
        row.addStretch(1)
        layout.addLayout(row)
        self.footnote = label("", "Faint")
        layout.addWidget(self.footnote)

    def set_value(
        self,
        value: str,
        unit: str | None = None,
        footnote: str | None = None,
        accent: str | None = None,
    ) -> None:
        self.value.setText(value)
        if unit is not None:
            self.unit.setText(unit)
        if footnote is not None:
            self.footnote.setText(footnote)
        if accent is not None:
            self.marker.setStyleSheet(f"background: {accent}; border-radius: 3px;")


class StatusPill(QLabel):
    def __init__(self, text: str = "", parent: QWidget | None = None) -> None:
        super().__init__(text, parent)
        self.setObjectName("StatusPill")
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.set_classification(text)

    def set_classification(self, classification: str) -> None:
        color = STATUS_COLORS.get(classification, COLORS["info"])
        self.setText(classification)
        self.setStyleSheet(
            f"background: {alpha_color(color, '22')}; color: {color};"
            f"border: 1px solid {alpha_color(color, '66')};"
            "border-radius: 10px; padding: 4px 10px; font-size: 9px; font-weight: 700;"
        )


class GaugeWidget(QWidget):
    """Compact utilisation gauge rendered with Qt painting."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._utilisation = 0.0
        self._classification = "Within calculated capacity"
        self.setMinimumSize(190, 180)
        self.setFixedHeight(180)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def set_utilisation(self, value: float, classification: str) -> None:
        self._utilisation = max(0.0, float(value))
        self._classification = classification
        self.update()

    def paintEvent(self, event) -> None:
        del event
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        width = self.width()
        height = self.height()
        side = min(width - 28, height * 0.84)
        if side < 80:
            return
        arc_rect = QRectF(
            (width - side) / 2,
            height * 0.08,
            side,
            side,
        )
        pen = QPen(QColor(COLORS["border"]), 10)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        painter.drawArc(arc_rect, 225 * 16, -270 * 16)

        maximum = max(100.0, math.ceil(self._utilisation / 20.0) * 20.0)
        fraction = min(self._utilisation / maximum, 1.0)
        color = STATUS_COLORS.get(self._classification, COLORS["accent"])
        pen = QPen(QColor(color), 10)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        painter.drawArc(arc_rect, 225 * 16, int(-270 * 16 * fraction))

        font = QFont(self.font())
        font.setPointSize(20)
        font.setWeight(QFont.Weight.Bold)
        painter.setFont(font)
        painter.setPen(QColor(COLORS["text"]))
        value_box = QRectF(0, arc_rect.center().y() - 26, width, 34)
        painter.drawText(
            value_box,
            Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignVCenter,
            f"{self._utilisation:.1f}%",
        )

        font.setPointSize(8)
        font.setWeight(QFont.Weight.Medium)
        painter.setFont(font)
        painter.setPen(QColor(COLORS["text_muted"]))
        painter.drawText(
            QRectF(0, arc_rect.center().y() + 10, width, 20),
            Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop,
            "capacity utilisation",
        )

        painter.setPen(QColor(color))
        painter.drawText(
            QRectF(0, height - 23, width, 18),
            Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop,
            self._classification,
        )


class Banner(QFrame):
    def __init__(
        self,
        text: str = "",
        *,
        warning: bool = False,
        parent: QWidget | None = None,
    ) -> None:
        super().__init__(parent)
        self.setObjectName("WarningBanner" if warning else "ScopeBanner")
        layout = QHBoxLayout(self)
        layout.setContentsMargins(11, 8, 11, 8)
        self.label = label(text, "Muted", wrap=True)
        layout.addWidget(self.label)

    def setText(self, text: str) -> None:
        self.label.setText(text)


def hline() -> QFrame:
    line = QFrame()
    line.setFixedHeight(1)
    line.setStyleSheet(f"background: {COLORS['border_soft']};")
    return line


def mono(text: str) -> QLabel:
    widget = label(text, "Formula")
    widget.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
    return widget


def field_caption(text: str) -> QLabel:
    return label(text, "Faint")
