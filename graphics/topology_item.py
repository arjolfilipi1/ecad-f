#graphics/topology_item
from PyQt5.QtWidgets import (
    QGraphicsEllipseItem, QGraphicsPathItem, 
    QGraphicsItem, QGraphicsTextItem
)
from PyQt5.QtGui import QPainterPath, QPen, QBrush, QColor, QPainter
from PyQt5.QtCore import Qt, QPointF
from model.topology import JunctionNode, BranchPointNode, WireSegment

class JunctionGraphicsItem(QGraphicsEllipseItem):
    """Visual representation of a junction"""
    def __init__(self, junction_node: JunctionNode):
        super().__init__(-5, -5, 10, 10)
        self.junction_node = junction_node
        self.setPos(*junction_node.position)
        self.setFlag(self.ItemIsSelectable, True)
        self.setFlag(self.ItemIsFocusable, True)
        self.setAcceptHoverEvents(True)
        
        self.normal_brush = QBrush(QColor(100, 100, 100))
        self.normal_pen = QPen(Qt.black, 1)
        self.hover_pen = QPen(QColor(255, 255, 0), 2)
        self.selected_pen = QPen(QColor(0, 120, 255), 2)
        
        self.setBrush(self.normal_brush)
        self.setPen(self.normal_pen)
        self.setZValue(4)
        
        self._is_hovered = False
    
    def paint(self, painter, option, widget=None):
        painter.save()
        painter.setRenderHint(QPainter.Antialiasing)
        
        if self.isSelected():
            painter.setPen(self.selected_pen)
            painter.setBrush(self.brush())
        elif self._is_hovered:
            painter.setPen(self.hover_pen)
            painter.setBrush(self.brush())
        else:
            painter.setPen(self.normal_pen)
            painter.setBrush(self.brush())
        
        painter.drawEllipse(self.rect())
        painter.restore()
    
    def hoverEnterEvent(self, event):
        self._is_hovered = True
        self.update()
        super().hoverEnterEvent(event)
    
    def hoverLeaveEvent(self, event):
        self._is_hovered = False
        self.update()
        super().hoverLeaveEvent(event)

        
    def itemChange(self, change, value):
        if change == self.ItemPositionHasChanged:
            # Update node position
            self.junction_node.position = (self.pos().x(), self.pos().y())
            # Update connected segments
            for segment in self.junction_node.connected_segments:
                if hasattr(segment, 'graphics_item'):
                    segment.graphics_item.update_path()
        return super().itemChange(change, value)

class BranchPointGraphicsItem(QGraphicsEllipseItem):
    """Visual representation of a branch point"""
    def __init__(self, branch_node: BranchPointNode):
        super().__init__(-7, -7, 14, 14)
        self.branch_node = branch_node
        self.setPos(*branch_node.position)
        
        # Enable selection and hover
        self.setFlag(self.ItemIsSelectable, True)
        self.setFlag(self.ItemIsFocusable, True)
        self.setAcceptHoverEvents(True)
        
        # Visual properties
        if branch_node.branch_type == "splice":
            self.normal_brush = QBrush(QColor(200, 150, 50))
        else:
            self.normal_brush = QBrush(QColor(150, 200, 100))
        
        self.normal_pen = QPen(Qt.black, 1)
        self.hover_pen = QPen(QColor(255, 255, 0), 2)
        self.selected_pen = QPen(QColor(0, 120, 255), 2)
        
        self.setBrush(self.normal_brush)
        self.setPen(self.normal_pen)
        self.setZValue(3)
        
        self._is_hovered = False

    def paint(self, painter, option, widget=None):
        """Custom paint with glow effects"""
        painter.save()
        painter.setRenderHint(QPainter.Antialiasing)
        
        if self.isSelected():
            painter.setPen(self.selected_pen)
            painter.setBrush(self.brush())
        elif self._is_hovered:
            painter.setPen(self.hover_pen)
            painter.setBrush(self.brush())
        else:
            painter.setPen(self.normal_pen)
            painter.setBrush(self.brush())
        
        painter.drawEllipse(self.rect())
        painter.restore()
    
    def hoverEnterEvent(self, event):
        self._is_hovered = True
        self.update()
        super().hoverEnterEvent(event)
    
    def hoverLeaveEvent(self, event):
        self._is_hovered = False
        self.update()
        super().hoverLeaveEvent(event)

    def itemChange(self, change, value):
        if change == self.ItemPositionHasChanged:
            self.branch_node.position = (self.pos().x(), self.pos().y())
            for segment in self.branch_node.connected_segments:
                if hasattr(segment, 'graphics_item'):
                    segment.graphics_item.update_path()
        return super().itemChange(change, value)
