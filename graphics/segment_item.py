from PyQt5.QtWidgets import QGraphicsPathItem, QStyle
from PyQt5.QtCore import  QPointF,Qt
from PyQt5.QtGui import QPainterPath,QPen, QColor
class SegmentGraphicsItem(QGraphicsPathItem):
    def __init__(self, segment, topology_manager=None):
        super().__init__()
        self.segment = segment
        self.topology_manager = topology_manager
        self.setFlag(self.ItemIsSelectable)
        
        # Store reference back to segment
        segment.graphics_item = self
        
        self.update_path()
        self.update_appearance()
    
    def update_path(self):
        """Update segment path based on node positions"""
        if not self.segment.start_node or not self.segment.end_node:
            return
            
        p1 = QPointF(*self.segment.start_node.position)
        p2 = QPointF(*self.segment.end_node.position)
        
        path = QPainterPath(p1)
        
        # Calculate direction for smart routing
        dx = p2.x() - p1.x()
        dy = p2.y() - p1.y()
        
        if abs(dx) > 50 or abs(dy) > 50:  # Long segments get curved
            # Create orthogonal path with single bend
            if abs(dx) > abs(dy):
                # Horizontal dominant: go horizontal then vertical
                mid_x = p1.x() + dx * 0.5
                path.lineTo(mid_x, p1.y())
                path.lineTo(mid_x, p2.y())
                path.lineTo(p2)
            else:
                # Vertical dominant: go vertical then horizontal
                mid_y = p1.y() + dy * 0.5
                path.lineTo(p1.x(), mid_y)
                path.lineTo(p2.x(), mid_y)
                path.lineTo(p2)
        else:
            # Short segment - direct line
            path.lineTo(p2)
        
        self.setPath(path)
        self.update_appearance()
    
    def update_appearance(self):
        """Update visual style based on segment contents and visualization mode"""
        wire_count = len(self.segment.wires)
        
        if wire_count == 0:
            # Empty segment - dashed gray
            pen = QPen(QColor(150, 150, 150), 1)
            pen.setStyle(Qt.DashLine)
            self.setPen(pen)
            self.setZValue(0)
            return
        
        # Calculate bundle diameter (visual thickness)
        total_cross_section = sum(w.cross_section for w in self.segment.wires)
        bundle_diameter = 2 * (total_cross_section ** 0.5) + 2  # mm
        
        # Scale for visualization
        thickness = min(max(int(bundle_diameter), 2), 8)
        
        if wire_count == 1:
            # Single wire - use wire color
            wire = self.segment.wires[0]
            pen = QPen(QColor(*wire.color_data.rgb), thickness)
            self.setPen(pen)
            self.setZValue(1)
        else:
            # Bundle - use dark color with thickness based on wire count
            color = QColor(80, 80, 80)  # Dark gray
            if wire_count > 10:
                color = QColor(50, 50, 50)  # Darker for large bundles
            
            pen = QPen(color, thickness)
            
            # Add pattern for very large bundles
            if wire_count > 20:
                pen.setStyle(Qt.DashLine)
            
            self.setPen(pen)
            self.setZValue(1)
        
        # Add tooltip with bundle info
        wire_names = ", ".join([w.id for w in self.segment.wires[:5]])
        if len(self.segment.wires) > 5:
            wire_names += f"... and {len(self.segment.wires) - 5} more"
        self.setToolTip(f"Bundle: {len(self.segment.wires)} wires\n{wire_names}")
