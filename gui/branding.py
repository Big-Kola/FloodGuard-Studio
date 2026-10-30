"""Application icon rendering kept independent of external image assets."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import (
    QColor,
    QFont,
    QIcon,
    QLinearGradient,
    QPainter,
    QPainterPath,
    QPen,
    QPixmap,
)


def render_icon(size: int = 256) -> QPixmap:
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)

    margin = size * 0.055
    rect = QRectF(margin, margin, size - margin * 2, size - margin * 2)
    gradient = QLinearGradient(rect.topLeft(), rect.bottomRight())
    gradient.setColorAt(0.0, QColor("#123B50"))
    gradient.setColorAt(1.0, QColor("#08141F"))
    painter.setBrush(gradient)
    painter.setPen(QPen(QColor("#2BC4D9"), size * 0.012))
    painter.drawRoundedRect(rect, size * 0.20, size * 0.20)

    wave = QPainterPath(QPointF(size * 0.13, size * 0.63))
    wave.cubicTo(
        size * 0.30,
        size * 0.49,
        size * 0.42,
        size * 0.77,
        size * 0.55,
        size * 0.62,
    )
    wave.cubicTo(
        size * 0.68,
        size * 0.47,
        size * 0.78,
        size * 0.65,
        size * 0.88,
        size * 0.56,
    )
    painter.setBrush(Qt.BrushStyle.NoBrush)
    painter.setPen(
        QPen(
            QColor("#2BC4D9"),
            size * 0.055,
            Qt.PenStyle.SolidLine,
            Qt.PenCapStyle.RoundCap,
        )
    )
    painter.drawPath(wave)
    second = QPainterPath(QPointF(size * 0.20, size * 0.76))
    second.cubicTo(
        size * 0.34,
        size * 0.67,
        size * 0.46,
        size * 0.86,
        size * 0.62,
        size * 0.73,
    )
    second.cubicTo(
        size * 0.73,
        size * 0.64,
        size * 0.80,
        size * 0.74,
        size * 0.86,
        size * 0.70,
    )
    painter.setPen(
        QPen(
            QColor("#36C98F"),
            size * 0.026,
            Qt.PenStyle.SolidLine,
            Qt.PenCapStyle.RoundCap,
        )
    )
    painter.drawPath(second)

    font = QFont("DejaVu Sans")
    font.setPixelSize(int(size * 0.25))
    font.setWeight(QFont.Weight.Black)
    painter.setFont(font)
    painter.setPen(QColor("#E9F1F8"))
    painter.drawText(
        QRectF(0, size * 0.13, size, size * 0.40),
        Qt.AlignmentFlag.AlignCenter,
        "FG",
    )
    painter.end()
    return pixmap


def app_icon() -> QIcon:
    icon = QIcon()
    for size in (16, 24, 32, 48, 64, 128, 256):
        icon.addPixmap(render_icon(size))
    return icon


def write_icon_assets(directory: Path) -> None:
    directory.mkdir(parents=True, exist_ok=True)
    pixmap = render_icon(256)
    pixmap.save(str(directory / "floodguard_studio.png"), "PNG")
