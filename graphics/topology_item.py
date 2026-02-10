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

class SegmentGraphicsItem(QGraphicsPathItem):
    """Visual representation of a wire segment (can contain multiple wires)"""
    def __init__(self, segment: WireSegment,tm = None):
        super().__init__()
        self.segment = segment
        self.topology_manager = tm
        self.setFlag(self.ItemIsSelectable)
        self.update_path()
        self.update_appearance()
        
    def update_path(self):
        """Update the visual path based on segment nodes"""
        if not self.segment.start_node or not self.segment.end_node:
            return
            
        path = QPainterPath()
        p1 = QPointF(*self.segment.start_node.position)
        p2 = QPointF(*self.segment.end_node.position)
        
        # Create a curved path for better visualization
        mid_x = (p1.x() + p2.x()) / 2
        path.moveTo(p1)
        path.cubicTo(
            QPointF(mid_x, p1.y()),
            QPointF(mid_x, p2.y()),
            p2
        )
        
        self.setPath(path)
        
    def update_appearance(self):
        """Update visual style based on segment contents"""
        if not self.segment.wires:
            # Default appearance for empty segment
            pen = QPen(QColor(100, 100, 100), 1, Qt.DashLine)
            self.setPen(pen)
            return
            
        # Show bundle with multiple wires
        if len(self.segment.wires) == 1:
            # Single wire
            wire = self.segment.wires[0]
            pen = QPen(QColor(*wire.color_data.rgb), 2)
            self.setPen(pen)
        else:
            # Bundle of wires - thicker line with pattern
            pen = QPen(QColor(50, 50, 50), 3)
            pen.setDashPattern([3, 2])
            self.setPen(pen)