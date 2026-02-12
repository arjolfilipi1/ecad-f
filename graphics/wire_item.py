#graphics/wire_item
from PyQt5.QtWidgets import QGraphicsPathItem, QStyle
from PyQt5.QtGui import QPainterPath, QPen, QColor
from PyQt5.QtCore import Qt,QPointF
from model.wire import Wire
from model.topology import WireSegment
from PyQt5.QtWidgets import QGraphicsPathItem, QStyle
from PyQt5.QtGui import QPainterPath, QPen, QColor
from PyQt5.QtCore import Qt, QPointF
from model.models import CombinedWireColor
class WireItem(QGraphicsPathItem):
    def __init__(self, wid, start_pin, end_pin, color_txt="SW", net=None):
        super().__init__()
        self.wid = wid
        self.start_pin = start_pin  # This is a PinItem!
        self.end_pin = end_pin      # This is a PinItem!
        self.tree_item = None
        self.color_data = CombinedWireColor(color_txt)
        self.color = QColor(*self.color_data.rgb)
        self.setPen(QPen(self.color, 2))
        self.setFlag(self.ItemIsSelectable)
        self.is_connected = True
        
        # Connect to pins
        start_pin.wires.append(self)
        end_pin.wires.append(self)
        
        # Reference for topology
        self.main_window = None
        
        # Initial path
        self.update_path()
        self.net = net
    
    def update_path(self):
        """Update wire path connecting the TWO PIN POSITIONS"""
        if not self.is_connected:
            return
            
        # Get current pin positions (FORCE recalculation)
        p1 = self.start_pin.update_scene_position()
        p2 = self.end_pin.update_scene_position()
        
        if not p1 or not p2:
            print(f"Warning: Wire {self.wid} has invalid pin positions")
            self.is_connected = False
            return
        

        # Create path with proper elbow routing
        path = QPainterPath(p1)
        
        # Calculate direction
        dx = p2.x() - p1.x()
        dy = p2.y() - p1.y()
        
        # Simple Manhattan routing (right-angle)
        if abs(dx) > abs(dy):
            # More horizontal: go horizontal first
            mid_x = p1.x() + dx * 0.5
            path.lineTo(mid_x, p1.y())
            path.lineTo(mid_x, p2.y())
            path.lineTo(p2)
        else:
            # More vertical: go vertical first
            mid_y = p1.y() + dy * 0.5
            path.lineTo(p1.x(), mid_y)
            path.lineTo(p2.x(), mid_y)
            path.lineTo(p2)
        
        self.setPath(path)
        
        # Update visual style
        pen = QPen(self.color, 2)
        self.setPen(pen)
    
    def paint(self, painter, option, widget):
        """Custom paint to show selection"""
        pen = self.pen()
        if option.state & QStyle.State_Selected:
            pen.setWidth(4)
            pen.setColor(Qt.cyan)
        else:
            pen.setWidth(2)
            pen.setColor(self.color)
        
        painter.setPen(pen)
        painter.drawPath(self.path())

                    

class SegmentedWireItem(QGraphicsPathItem):
    """Visual representation of a wire that goes through topology"""
    def __init__(self, wire: Wire):
        super().__init__()
        self.wire = wire
        self.setFlag(self.ItemIsSelectable)
        self.setZValue(2)  # Wires above segments
        self.main_window = None
        self.update_path()
    
    def set_main_window(self, window):
        self.main_window = window
    
    def update_path(self):
        """Draw the complete path of the wire through segments"""
        if not self.wire.segments:
            # Fallback to direct connection
            self._draw_direct_path()
            return
        
        path = QPainterPath()
        
        # Start from the from_pin
        if self.wire.from_pin:
            start_pos = self.wire.from_pin.scene_position()
            path.moveTo(start_pos)
        
        # Add all segment paths
        for i, segment in enumerate(self.wire.segments):
            if segment.start_node and segment.end_node:
                p1 = QPointF(*segment.start_node.position)
                p2 = QPointF(*segment.end_node.position)
                
                # Determine direction
                if i == 0 and self.wire.from_pin:
                    # First segment: connect from pin to first node
                    self._add_connection_path(path, start_pos, p1)
                
                # Add the segment path
                self._add_segment_path(path, p1, p2)
                
                # If last segment, connect to to_pin
                if i == len(self.wire.segments) - 1 and self.wire.to_pin:
                    end_pos = self.wire.to_pin.scene_position()
                    self._add_connection_path(path, p2, end_pos)
        
        self.setPath(path)
        
        # Set color from wire
        pen = QPen(QColor(*self.wire.color_data.rgb), 1.5)
        self.setPen(pen)
    
    def _add_segment_path(self, path, p1, p2):
        """Add a segment path with orthogonal routing"""
        dx = p2.x() - p1.x()
        dy = p2.y() - p1.y()
        
        if abs(dx) > 20 or abs(dy) > 20:
            # Orthogonal routing
            if abs(dx) > abs(dy):
                mid_x = (p1.x() + p2.x()) / 2
                path.lineTo(mid_x, p1.y())
                path.lineTo(mid_x, p2.y())
                path.lineTo(p2)
            else:
                mid_y = (p1.y() + p2.y()) / 2
                path.lineTo(p1.x(), mid_y)
                path.lineTo(p2.x(), mid_y)
                path.lineTo(p2)
        else:
            # Direct line for short distances
            path.lineTo(p2)
    
    def _add_connection_path(self, path, from_point, to_point):
        """Add connection from pin to node"""
        path.lineTo(to_point)
    
    def _draw_direct_path(self):
        """Fallback: draw direct Manhattan path"""
        if not self.wire.from_pin or not self.wire.to_pin:
            return
        
        p1 = self.wire.from_pin.scene_position()
        p2 = self.wire.to_pin.scene_position()
        
        path = QPainterPath(p1)
        
        dx = p2.x() - p1.x()
        dy = p2.y() - p1.y()
        
        if abs(dx) > abs(dy):
            mid_x = p1.x() + dx * 0.5
            path.lineTo(mid_x, p1.y())
            path.lineTo(mid_x, p2.y())
            path.lineTo(p2)
        else:
            mid_y = p1.y() + dy * 0.5
            path.lineTo(p1.x(), mid_y)
            path.lineTo(p2.x(), mid_y)
            path.lineTo(p2)
        
        self.setPath(path)
    
    def paint(self, painter, option, widget):
        pen = self.pen()
        if option.state & QStyle.State_Selected:
            pen.setWidth(3)
            pen.setColor(Qt.cyan)
        painter.setPen(pen)
        painter.drawPath(self.path())

