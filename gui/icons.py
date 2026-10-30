"""Small vector-style icons drawn with Qt for the navigation rail."""

from __future__ import annotations

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QIcon, QPainter, QPainterPath, QPen, QPixmap


def _pixmap(key: str, color: str, size: int = 32) -> QPixmap:
    pixmap = QPixmap(size, size)
    pixmap.fill(Qt.GlobalColor.transparent)
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    pen = QPen(QColor(color), 2.0)
    pen.setCapStyle(Qt.PenCapStyle.RoundCap)
    pen.setJoinStyle(Qt.PenJoinStyle.RoundJoin)
    painter.setPen(pen)
    painter.setBrush(Qt.BrushStyle.NoBrush)

    if key == "dashboard":
        for x in (6, 17):
            for y in (6, 17):
                painter.drawRoundedRect(QRectF(x, y, 9, 9), 2, 2)
    elif key == "network":
        painter.drawEllipse(QPointF(8, 23), 3.4, 3.4)
        painter.drawEllipse(QPointF(24, 10), 3.4, 3.4)
        painter.drawEllipse(QPointF(24, 23), 3.4, 3.4)
        painter.drawLine(QPointF(11, 22), QPointF(21, 12))
        painter.drawLine(QPointF(11, 24), QPointF(21, 24))
    elif key == "hydrology":
        for offset in (0, 7, 14):
            path = QPainterPath(QPointF(5, 9 + offset))
            path.cubicTo(11, 4 + offset, 14, 13 + offset, 20, 9 + offset)
            path.cubicTo(24, 6 + offset, 26, 10 + offset, 28, 9 + offset)
            painter.drawPath(path)
    elif key == "hydraulics":
        painter.drawEllipse(QPointF(9, 16), 5.5, 8.0)
        painter.drawEllipse(QPointF(9, 16), 2.3, 4.0)
        painter.drawLine(QPointF(15, 12), QPointF(26, 12))
        painter.drawLine(QPointF(15, 20), QPointF(26, 20))
        painter.drawLine(QPointF(21, 16), QPointF(27, 16))
    elif key == "scenarios":
        painter.drawLine(QPointF(5, 26), QPointF(27, 26))
        painter.drawRoundedRect(QRectF(7, 17, 4, 7), 1, 1)
        painter.drawRoundedRect(QRectF(14, 11, 4, 13), 1, 1)
        painter.drawRoundedRect(QRectF(21, 7, 4, 17), 1, 1)
    elif key == "reports":
        path = QPainterPath(QPointF(8, 5))
        path.lineTo(20, 5)
        path.lineTo(25, 10)
        path.lineTo(25, 27)
        path.lineTo(8, 27)
        path.closeSubpath()
        painter.drawPath(path)
        painter.drawLine(QPointF(20, 5), QPointF(20, 10))
        painter.drawLine(QPointF(20, 10), QPointF(25, 10))
        painter.drawLine(QPointF(11, 15), QPointF(22, 15))
        painter.drawLine(QPointF(11, 19), QPointF(22, 19))
        painter.drawLine(QPointF(11, 23), QPointF(18, 23))
    elif key == "settings":
        for y in (9, 16, 23):
            painter.drawLine(QPointF(5, y), QPointF(27, y))
            knob_x = (13, 21, 10)[(y - 9) // 7]
            painter.setBrush(QColor(color))
            painter.drawEllipse(QPointF(knob_x, y), 2.3, 2.3)
            painter.setBrush(Qt.BrushStyle.NoBrush)
    elif key == "new":
        path = QPainterPath(QPointF(8, 5))
        path.lineTo(20, 5)
        path.lineTo(25, 10)
        path.lineTo(25, 27)
        path.lineTo(8, 27)
        path.closeSubpath()
        painter.drawPath(path)
        painter.drawLine(QPointF(20, 5), QPointF(20, 10))
        painter.drawLine(QPointF(20, 10), QPointF(25, 10))
        painter.drawLine(QPointF(14, 18), QPointF(20, 18))
        painter.drawLine(QPointF(17, 15), QPointF(17, 21))
    elif key == "open":
        path = QPainterPath(QPointF(5, 11))
        path.lineTo(5, 25)
        path.lineTo(27, 25)
        path.lineTo(27, 12)
        path.lineTo(15, 12)
        path.lineTo(12, 8)
        path.lineTo(5, 8)
        path.closeSubpath()
        painter.drawPath(path)
        painter.drawLine(QPointF(5, 15), QPointF(27, 15))
    elif key == "save":
        painter.drawRoundedRect(QRectF(7, 5, 18, 22), 2, 2)
        painter.drawRect(QRectF(11, 5, 10, 7))
        painter.drawRoundedRect(QRectF(10, 17, 12, 10), 1, 1)
    elif key == "run":
        painter.setBrush(QColor(color))
        path = QPainterPath(QPointF(11, 7))
        path.lineTo(25, 16)
        path.lineTo(11, 25)
        path.closeSubpath()
        painter.drawPath(path)
        painter.setBrush(Qt.BrushStyle.NoBrush)
    elif key == "export":
        painter.drawRoundedRect(QRectF(7, 5, 18, 14), 2, 2)
        painter.drawLine(QPointF(16, 12), QPointF(16, 27))
        painter.drawLine(QPointF(16, 27), QPointF(11, 22))
        painter.drawLine(QPointF(16, 27), QPointF(21, 22))
    elif key == "undo":
        path = QPainterPath(QPointF(8, 18))
        path.cubicTo(9, 10, 18, 7, 25, 13)
        painter.drawPath(path)
        painter.drawLine(QPointF(8, 18), QPointF(7, 11))
        painter.drawLine(QPointF(8, 18), QPointF(15, 17))
    elif key == "redo":
        path = QPainterPath(QPointF(24, 18))
        path.cubicTo(23, 10, 14, 7, 7, 13)
        painter.drawPath(path)
        painter.drawLine(QPointF(24, 18), QPointF(25, 11))
        painter.drawLine(QPointF(24, 18), QPointF(17, 17))
    painter.end()
    return pixmap


def nav_icon(key: str) -> QIcon:
    icon = QIcon()
    icon.addPixmap(_pixmap(key, "#91A6BB"), QIcon.Mode.Normal, QIcon.State.Off)
    icon.addPixmap(_pixmap(key, "#2BC4D9"), QIcon.Mode.Selected, QIcon.State.Off)
    icon.addPixmap(_pixmap(key, "#2BC4D9"), QIcon.Mode.Active, QIcon.State.Off)
    return icon


def action_icon(key: str, color: str) -> QIcon:
    return QIcon(_pixmap(key, color))
