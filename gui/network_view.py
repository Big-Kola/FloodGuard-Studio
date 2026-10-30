"""Interactive drainage network scene and view."""

from __future__ import annotations

import math

from PySide6.QtCore import QLineF, QPointF, QRectF, Qt, Signal
from PySide6.QtGui import (
    QColor,
    QFont,
    QFontMetrics,
    QPainter,
    QPainterPath,
    QPainterPathStroker,
    QPen,
)
from PySide6.QtWidgets import (
    QGraphicsItem,
    QGraphicsObject,
    QGraphicsPathItem,
    QGraphicsScene,
    QGraphicsView,
)

from floodguard.analysis import ProjectAnalysis
from floodguard.project import EngineeringProject, Node
from gui.theme import COLORS, STATUS_COLORS

NODE_RADIUS = 16.0


class NodeItem(QGraphicsObject):
    def __init__(self, node: Node) -> None:
        super().__init__()
        self.node = node
        self._hovered = False
        self._drag_change_sent = False
        self._connect_highlight = False
        self.setFlags(
            QGraphicsItem.GraphicsItemFlag.ItemIsMovable
            | QGraphicsItem.GraphicsItemFlag.ItemIsSelectable
            | QGraphicsItem.GraphicsItemFlag.ItemSendsGeometryChanges
        )
        self.setAcceptHoverEvents(True)
        self.setZValue(3)
        self.setPos(node.x, node.y)
        self.setToolTip(
            f"<b>{node.name}</b><br>{node.display_kind} | {node.id}<br>"
            f"Invert: {node.invert_elevation_m:.3f} m"
        )

    def boundingRect(self) -> QRectF:
        return QRectF(
            -NODE_RADIUS - 8,
            -NODE_RADIUS - 8,
            NODE_RADIUS * 2 + 16,
            NODE_RADIUS * 2 + 34,
        )

    def shape(self) -> QPainterPath:
        path = QPainterPath()
        path.addEllipse(QPointF(0, 0), NODE_RADIUS + 3, NODE_RADIUS + 3)
        return path

    def _body_color(self) -> QColor:
        if self.node.kind == "outfall":
            return QColor("#123E36")
        return QColor("#12374A")

    def _border_color(self) -> QColor:
        if self._connect_highlight:
            return QColor(COLORS["warning"])
        if self.node.kind == "outfall":
            return QColor(COLORS["success"])
        return QColor(COLORS["accent"])

    def paint(self, painter: QPainter, option, widget=None) -> None:
        del option, widget
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        selected = self.isSelected()
        border = self._border_color()
        if self._hovered:
            border = border.lighter(120)

        if selected or self._connect_highlight:
            painter.setPen(
                QPen(QColor(border.red(), border.green(), border.blue(), 70), 7)
            )
            painter.setBrush(Qt.BrushStyle.NoBrush)
            if self.node.kind == "outfall":
                painter.drawRoundedRect(
                    QRectF(
                        -NODE_RADIUS - 5,
                        -NODE_RADIUS - 5,
                        NODE_RADIUS * 2 + 10,
                        NODE_RADIUS * 2 + 10,
                    ),
                    8,
                    8,
                )
            else:
                painter.drawEllipse(QPointF(0, 0), NODE_RADIUS + 5, NODE_RADIUS + 5)

        painter.setPen(QPen(border, 2.0))
        painter.setBrush(self._body_color())
        if self.node.kind == "outfall":
            painter.drawRoundedRect(
                QRectF(-NODE_RADIUS, -NODE_RADIUS, NODE_RADIUS * 2, NODE_RADIUS * 2),
                5,
                5,
            )
            painter.setPen(QPen(border, 1.0))
            painter.drawLine(QPointF(-7, 0), QPointF(7, 0))
            painter.drawLine(QPointF(0, -7), QPointF(0, 7))
        else:
            painter.drawEllipse(QPointF(0, 0), NODE_RADIUS, NODE_RADIUS)
            painter.setPen(QPen(border, 1.2))
            painter.drawEllipse(QPointF(0, 0), 5.5, 5.5)

        font = QFont()
        font.setPointSize(7)
        font.setWeight(QFont.Weight.DemiBold)
        painter.setFont(font)
        painter.setPen(QColor(COLORS["text"]))
        painter.drawText(
            QRectF(-22, -8, 44, 16),
            Qt.AlignmentFlag.AlignCenter,
            self.node.id.replace("J-", "J").replace("O-", "O"),
        )

        font.setPointSize(8)
        font.setWeight(QFont.Weight.Medium)
        painter.setFont(font)
        painter.setPen(QColor(COLORS["text_muted"]))
        painter.drawText(
            QRectF(-80, NODE_RADIUS + 4, 160, 16),
            Qt.AlignmentFlag.AlignHCenter | Qt.AlignmentFlag.AlignTop,
            self.node.name,
        )

    def set_connect_highlight(self, enabled: bool) -> None:
        self._connect_highlight = enabled
        self.update()

    def hoverEnterEvent(self, event) -> None:
        self._hovered = True
        self.update()
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event) -> None:
        self._hovered = False
        self.update()
        super().hoverLeaveEvent(event)

    def itemChange(self, change, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemPositionChange:
            scene = self.scene()
            if (
                isinstance(scene, NetworkScene)
                and not self._drag_change_sent
                and not scene.connect_mode
            ):
                scene.prepare_change.emit()
                self._drag_change_sent = True
        elif change == QGraphicsItem.GraphicsItemChange.ItemPositionHasChanged:
            self.node.x = self.pos().x()
            self.node.y = self.pos().y()
            scene = self.scene()
            if isinstance(scene, NetworkScene):
                scene.update_connections(self.node.id)
        elif change == QGraphicsItem.GraphicsItemChange.ItemSelectedHasChanged:
            self.update()
        return super().itemChange(change, value)

    def mousePressEvent(self, event) -> None:
        scene = self.scene()
        if (
            isinstance(scene, NetworkScene)
            and scene.connect_mode
            and event.button() == Qt.MouseButton.LeftButton
        ):
            scene.node_clicked.emit(self.node.id)
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        super().mouseReleaseEvent(event)
        if self._drag_change_sent:
            scene = self.scene()
            if isinstance(scene, NetworkScene):
                scene.node_moved.emit()
            self._drag_change_sent = False


class PipeItem(QGraphicsPathItem):
    def __init__(self, pipe_id: str, name: str) -> None:
        super().__init__()
        self.pipe_id = pipe_id
        self.pipe_name = name
        self._start = QPointF()
        self._end = QPointF()
        self._classification: str | None = None
        self._hovered = False
        self.setFlags(QGraphicsItem.GraphicsItemFlag.ItemIsSelectable)
        self.setAcceptHoverEvents(True)
        self.setZValue(1)

    def update_geometry(self, start: QPointF, end: QPointF) -> None:
        self.prepareGeometryChange()
        self._start = QPointF(start)
        self._end = QPointF(end)
        line = QLineF(start, end)
        if line.length() > NODE_RADIUS * 2:
            offset = NODE_RADIUS + 3
            unit = line.unitVector()
            visible_start = start + unit.pointAt(offset) - start
            visible_end = end - unit.pointAt(offset) + start
            path = QPainterPath(visible_start)
            path.lineTo(visible_end)
            self.setPath(path)
        else:
            path = QPainterPath(start)
            path.lineTo(end)
            self.setPath(path)

    def set_classification(self, classification: str | None) -> None:
        self._classification = classification
        if classification:
            color = STATUS_COLORS.get(classification, COLORS["info"])
            self.setToolTip(f"{self.pipe_name}: {classification}")
            self.setPen(QPen(QColor(color), 3.5))
        else:
            self.setPen(QPen(QColor(COLORS["border"]), 3.0))
            self.setToolTip(self.pipe_name)
        self.update()

    def boundingRect(self) -> QRectF:
        return super().boundingRect().adjusted(-20, -28, 20, 28)

    def shape(self) -> QPainterPath:
        path = super().shape()
        stroker = QPainterPathStroker()
        stroker.setWidth(12)
        return stroker.createStroke(path)

    def paint(self, painter: QPainter, option, widget=None) -> None:
        del option, widget
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        selected = self.isSelected()
        if selected:
            color = QColor(COLORS["accent"])
            width = 6.0
        elif self._hovered:
            color = QColor(
                STATUS_COLORS.get(self._classification, COLORS["text_muted"])
            ).lighter(120)
            width = 4.5
        else:
            color = QColor(STATUS_COLORS.get(self._classification, COLORS["border"]))
            width = 3.0
        pen = QPen(color, width)
        pen.setCapStyle(Qt.PenCapStyle.RoundCap)
        painter.setPen(pen)
        painter.drawPath(self.path())

        if not self.path().isEmpty():
            end = self.path().pointAtPercent(1.0)
            angle = math.atan2(
                self.path().pointAtPercent(1.0).y()
                - self.path().pointAtPercent(0.94).y(),
                self.path().pointAtPercent(1.0).x()
                - self.path().pointAtPercent(0.94).x(),
            )
            arrow_size = 8.0
            left = end - QPointF(
                math.cos(angle - math.pi / 6) * arrow_size,
                math.sin(angle - math.pi / 6) * arrow_size,
            )
            right = end - QPointF(
                math.cos(angle + math.pi / 6) * arrow_size,
                math.sin(angle + math.pi / 6) * arrow_size,
            )
            arrow = QPainterPath(end)
            arrow.lineTo(left)
            arrow.moveTo(end)
            arrow.lineTo(right)
            painter.setPen(QPen(color, 1.8))
            painter.drawPath(arrow)

        if not self.path().isEmpty():
            midpoint = self.path().pointAtPercent(0.5)
            label_text = self.pipe_id
            font = QFont()
            font.setPointSize(7)
            font.setWeight(QFont.Weight.DemiBold)
            painter.setFont(font)
            metrics = QFontMetrics(font)
            text_width = metrics.horizontalAdvance(label_text) + 10
            box = QRectF(
                midpoint.x() - text_width / 2,
                midpoint.y() - 19,
                text_width,
                14,
            )
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(COLORS["bg"]))
            painter.drawRoundedRect(box, 4, 4)
            painter.setPen(QColor(COLORS["text_muted"]))
            painter.drawText(box, Qt.AlignmentFlag.AlignCenter, label_text)

    def hoverEnterEvent(self, event) -> None:
        self._hovered = True
        self.update()
        super().hoverEnterEvent(event)

    def hoverLeaveEvent(self, event) -> None:
        self._hovered = False
        self.update()
        super().hoverLeaveEvent(event)

    def itemChange(self, change, value):
        if change == QGraphicsItem.GraphicsItemChange.ItemSelectedHasChanged:
            self.update()
        return super().itemChange(change, value)


class NetworkScene(QGraphicsScene):
    prepare_change = Signal()
    node_moved = Signal()
    element_selected = Signal(str, str)
    node_clicked = Signal(str)
    connect_cancelled = Signal()

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self.setSceneRect(-600, -360, 1200, 720)
        self.node_items: dict[str, NodeItem] = {}
        self.pipe_items: dict[str, PipeItem] = {}
        self.connect_mode = False
        self._building = False
        self.selectionChanged.connect(self._emit_selection)

    def drawBackground(self, painter: QPainter, rect: QRectF) -> None:
        painter.fillRect(rect, QColor("#09121D"))
        minor = 25
        major = 100
        left = math.floor(rect.left() / minor) * minor
        top = math.floor(rect.top() / minor) * minor

        painter.setPen(QPen(QColor("#101F2E"), 0.6))
        x = left
        while x < rect.right():
            painter.drawLine(QLineF(x, rect.top(), x, rect.bottom()))
            x += minor
        y = top
        while y < rect.bottom():
            painter.drawLine(QLineF(rect.left(), y, rect.right(), y))
            y += minor

        painter.setPen(QPen(QColor("#172B3D"), 0.8))
        x = math.floor(rect.left() / major) * major
        while x < rect.right():
            painter.drawLine(QLineF(x, rect.top(), x, rect.bottom()))
            x += major
        y = math.floor(rect.top() / major) * major
        while y < rect.bottom():
            painter.drawLine(QLineF(rect.left(), y, rect.right(), y))
            y += major

    def build(self, project: EngineeringProject) -> None:
        self._building = True
        self.clear()
        self.node_items = {}
        self.pipe_items = {}
        for node in project.nodes:
            item = NodeItem(node)
            self.addItem(item)
            self.node_items[node.id] = item
        for pipe in project.pipes:
            item = PipeItem(pipe.id, pipe.name)
            self.addItem(item)
            self.pipe_items[pipe.id] = item
        self.update_connections()
        self._building = False

    def update_connections(self, node_id: str | None = None) -> None:
        del node_id
        for pipe_item in self.pipe_items.values():
            start_item = self._pipe_endpoint(pipe_item.pipe_id, "from")
            end_item = self._pipe_endpoint(pipe_item.pipe_id, "to")
            if start_item is not None and end_item is not None:
                pipe_item.update_geometry(start_item.pos(), end_item.pos())

    def bind_project(self, project: EngineeringProject) -> None:
        self.project = project
        self.build(project)

    def _pipe_endpoint(self, pipe_id: str, side: str) -> NodeItem | None:
        project = getattr(self, "project", None)
        if project is None:
            return None
        pipe = project.find_pipe(pipe_id)
        if pipe is None:
            return None
        node_id = pipe.from_node_id if side == "from" else pipe.to_node_id
        return self.node_items.get(node_id)

    def set_analysis(self, analysis: ProjectAnalysis | None) -> None:
        for pipe_id, item in self.pipe_items.items():
            result = analysis.pipe_result(pipe_id) if analysis else None
            item.set_classification(
                result.assessment.classification if result else None
            )

    def select_element(self, kind: str, element_id: str) -> None:
        self.blockSignals(True)
        self.clearSelection()
        item = None
        if kind == "node":
            item = self.node_items.get(element_id)
        elif kind == "pipe":
            item = self.pipe_items.get(element_id)
        if item is not None:
            item.setSelected(True)
        self.blockSignals(False)

    def _emit_selection(self) -> None:
        if self._building:
            return
        items = self.selectedItems()
        for item in items:
            if isinstance(item, NodeItem):
                self.element_selected.emit("node", item.node.id)
                return
        for item in items:
            if isinstance(item, PipeItem):
                self.element_selected.emit("pipe", item.pipe_id)
                return
        self.element_selected.emit("", "")

    def set_connect_mode(self, enabled: bool) -> None:
        self.connect_mode = enabled

    def mousePressEvent(self, event) -> None:
        if (
            self.connect_mode
            and event.button() == Qt.MouseButton.LeftButton
            and not self.items(event.scenePos())
        ):
            self.connect_cancelled.emit()
            event.accept()
            return
        super().mousePressEvent(event)


class NetworkView(QGraphicsView):
    zoom_changed = Signal(float)

    def __init__(self, scene: NetworkScene, parent=None) -> None:
        super().__init__(scene, parent)
        self.setRenderHints(
            QPainter.RenderHint.Antialiasing
            | QPainter.RenderHint.TextAntialiasing
            | QPainter.RenderHint.SmoothPixmapTransform
        )
        self.setDragMode(QGraphicsView.DragMode.RubberBandDrag)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.AnchorViewCenter)
        self.setViewportUpdateMode(
            QGraphicsView.ViewportUpdateMode.BoundingRectViewportUpdate
        )
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self._panning = False
        self._pan_start = QPointF()
        self.setMinimumHeight(330)

    def wheelEvent(self, event) -> None:
        factor = 1.15 if event.angleDelta().y() > 0 else 1 / 1.15
        current = self.transform().m11()
        target = current * factor
        if 0.25 <= target <= 3.5:
            self.scale(factor, factor)
            self.zoom_changed.emit(target)
        event.accept()

    def mousePressEvent(self, event) -> None:
        if event.button() == Qt.MouseButton.MiddleButton:
            self._panning = True
            self._pan_start = event.position()
            self.setCursor(Qt.CursorShape.ClosedHandCursor)
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event) -> None:
        if self._panning:
            delta = event.position() - self._pan_start
            self._pan_start = event.position()
            self.horizontalScrollBar().setValue(
                self.horizontalScrollBar().value() - int(delta.x())
            )
            self.verticalScrollBar().setValue(
                self.verticalScrollBar().value() - int(delta.y())
            )
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event) -> None:
        if self._panning and event.button() == Qt.MouseButton.MiddleButton:
            self._panning = False
            self.setCursor(Qt.CursorShape.ArrowCursor)
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def fit_network(self) -> None:
        rect = self.scene().itemsBoundingRect()
        if rect.isEmpty():
            return
        margin = max(60.0, rect.width() * 0.08)
        self.fitInView(
            rect.adjusted(-margin, -margin, margin, margin),
            Qt.AspectRatioMode.KeepAspectRatio,
        )
        if self.transform().m11() > 2.0:
            self.resetTransform()
            self.centerOn(rect.center())
