from PyQt5.QtWidgets import (
    QGraphicsEllipseItem, QGraphicsPathItem, 
    QGraphicsItem, QGraphicsTextItem
)
from PyQt5.QtGui import QPainterPath, QPen, QBrush, QColor
from PyQt5.QtCore import Qt, QPointF
from model.topology import JunctionNode, BranchPointNode, WireSegment

class JunctionGraphicsItem(QGraphicsEllipseItem):
    """Visual representation of a junction"""
    def __init__(self, junction_node: JunctionNode):
        super().__init__(-5, -5, 10, 10)
        self.junction_node = junction_node
        self.setPos(*junction_node.position)
        self.setBrush(QBrush(QColor(100, 100, 100)))
        self.setFlag(self.ItemIsMovable)
        self.setFlag(self.ItemIsSelectable)
        self.setFlag(self.ItemSendsGeometryChanges)
        
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
        
        # Color based on type
        if branch_node.branch_type == "splice":
            self.setBrush(QBrush(QColor(200, 150, 50)))  # Gold for splice
        else:
            self.setBrush(QBrush(QColor(150, 200, 100)))  # Green for branch
        
        self.setFlag(self.ItemIsMovable)
        self.setFlag(self.ItemIsSelectable)
        self.setFlag(self.ItemSendsGeometryChanges)
        
    def itemChange(self, change, value):
        if change == self.ItemPositionHasChanged:
            self.branch_node.position = (self.pos().x(), self.pos().y())
            for segment in self.branch_node.connected_segments:
                if hasattr(segment, 'graphics_item'):
                    segment.graphics_item.update_path()
        return super().itemChange(change, value)
