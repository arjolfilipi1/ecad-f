from PyQt5.QtWidgets import QGraphicsPathItem, QStyle
from PyQt5.QtGui import QPainterPath, QPen, QColor
from PyQt5.QtCore import Qt,QPointF
from model.wire import Wire
from model.topology import WireSegment
from PyQt5.QtWidgets import QGraphicsPathItem, QStyle
from PyQt5.QtGui import QPainterPath, QPen, QColor
from PyQt5.QtCore import Qt, QPointF

class WireItem(QGraphicsPathItem):
    def __init__(self, wid, start_pin, end_pin, color_txt="SW", net=None):
        super().__init__()
        self.wid = wid
        self.start_pin = start_pin
        self.end_pin = end_pin
        self.tree_item = None
        self.color_data = CombinedWireColor(color_txt)
        self.color = QColor(self.color_data.rgb[0], 
                          self.color_data.rgb[1], 
                          self.color_data.rgb[2])
        self.setPen(QPen(self.color, 2))
        self.setFlag(self.ItemIsSelectable)
        
        # Track connection state
        self.is_connected = True
        
        # Connect to pins
        start_pin.wires.append(self)
        end_pin.wires.append(self)
        
        # ADD: Reference to parent window for topology updates
        self.main_window = None
        
        self.update_path()
        self.net = net
    
    def set_main_window(self, window):
        """Set reference to main window for topology access"""
        self.main_window = window
    
    def update_path(self):
        """Update wire path based on current pin positions"""
        if not self.is_connected:
            return
            
        # Get current scene positions (force update if needed)
        p1 = self.start_pin.update_scene_position()
        p2 = self.end_pin.update_scene_position()
        
        # Check if pins are still valid
        if not p1 or not p2:
            self.is_connected = False
            return
        
        # Create path with nice curves
        path = QPainterPath(p1)
        
        # Calculate control points for Bezier curve
        dx = abs(p2.x() - p1.x())
        dy = abs(p2.y() - p1.y())
        
        if dx > dy:
            # More horizontal - use horizontal-vertical-horizontal routing
            mid_x1 = p1.x() + dx * 0.4
            mid_x2 = p2.x() - dx * 0.4
            
            path.cubicTo(
                QPointF(mid_x1, p1.y()),
                QPointF(mid_x2, p2.y()),
                p2
            )
        else:
            # More vertical - use vertical-horizontal-vertical routing
            mid_y1 = p1.y() + dy * 0.4
            mid_y2 = p2.y() - dy * 0.4
            
            path.cubicTo(
                QPointF(p1.x(), mid_y1),
                QPointF(p2.x(), mid_y2),
                p2
            )
        
        self.setPath(path)
        
        # Update topology if this is part of a segmented wire
        self._update_topology_path()
    
    def _update_topology_path(self):
        """Update the underlying topology if this wire uses segments"""
        if not self.main_window or not hasattr(self, 'topology_wire'):
            return
            
        # Get the topology wire from main window
        topology_manager = self.main_window.topology_manager
        if not topology_manager:
            return
            
        # Find if this visual wire corresponds to a topology wire
        if hasattr(self, 'topology_wire_id'):
            topology_wire = topology_manager.wires.get(self.topology_wire_id)
            if topology_wire:
                # Update wire graphics
                if hasattr(topology_wire, 'graphics_item'):
                    topology_wire.graphics_item.update_path()
class SegmentedWireItem(QGraphicsPathItem):
    """Visual representation of a wire that can go through multiple segments"""
    def __init__(self, wire: Wire):
        super().__init__()
        self.wire = wire
        self.setFlag(self.ItemIsSelectable)
        self.update_path()
        self.main_window = None
    def set_main_window(self, window):
        """Set reference to main window for topology access"""
        self.main_window = window
    def update_path(self):
        """Draw the complete path of the wire through segments"""
        if not self.wire.segments:
            return
            
        path = QPainterPath()
        
        # Start from the from_pin
        if self.wire.from_pin:
            start_pos = self.wire.from_pin.scene_position()
            path.moveTo(start_pos)
            
            # Connect to first segment
            if self.wire.segments:
                first_node = self.wire.segments[0].start_node
                if first_node:
                    path.lineTo(QPointF(*first_node.position))
        
        # Add each segment
        for segment in self.wire.segments:
            if segment.start_node and segment.end_node:
                p1 = QPointF(*segment.start_node.position)
                p2 = QPointF(*segment.end_node.position)
                
                # Add curved segment
                mid_x = (p1.x() + p2.x()) / 2
                path.cubicTo(
                    QPointF(mid_x, p1.y()),
                    QPointF(mid_x, p2.y()),
                    p2
                )
        
        # Connect to to_pin
        if self.wire.to_pin:
            end_pos = self.wire.to_pin.scene_position()
            path.lineTo(end_pos)
            
        self.setPath(path)
        
        # Set color from wire
        pen = QPen(QColor(*self.wire.color_data.rgb), 2)
        self.setPen(pen)
        
    def paint(self, painter, option, widget):
        pen = self.pen()
        if option.state & QStyle.State_Selected:
            pen.setWidth(4)
            pen.setColor(Qt.cyan)
        else:
            pen.setWidth(2)
            pen.setColor(QColor(*self.wire.color_data.rgb))
            
        painter.setPen(pen)
        painter.drawPath(self.path())

class SegmentGraphicsItem(QGraphicsPathItem):
    def __init__(self, segment, topology_manager):
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
        
        # Use Bezier curve for smooth segments
        dx = abs(p2.x() - p1.x())
        dy = abs(p2.y() - p1.y())
        
        if dx > 100 or dy > 100: # Long segments get curved
            mid_x = (p1.x() + p2.x()) / 2
            path.cubicTo(
                QPointF(mid_x, p1.y()),
                QPointF(mid_x, p2.y()),
                p2
            )
        else:
            path.lineTo(p2)
        
        self.setPath(path)
        
        # Update appearance based on new path
        self.update_appearance()
    
    def update_appearance(self):
        """Update visual style"""
        if not self.segment.wires:
            # Empty segment - dashed gray
            pen = QPen(QColor(150, 150, 150), 1)
            pen.setStyle(Qt.DashLine)
            self.setPen(pen)
            return
            
        # Segment with wires
        wire_count = len(self.segment.wires)
        
        if wire_count == 1:
            # Single wire - use wire color
            wire = self.segment.wires[0]
            pen = QPen(QColor(*wire.color_data.rgb), 2)
        elif wire_count <= 3:
            # Small bundle - medium thickness
            pen = QPen(QColor(70, 70, 70), 3)
        elif wire_count <= 10:
            # Medium bundle - thicker
            pen = QPen(QColor(50, 50, 50), 4)
            pen.setStyle(Qt.DashLine)
        else:
            # Large bundle - very thick
            pen = QPen(QColor(30, 30, 30), 6)
            pen.setStyle(Qt.DotLine)
        
        self.setPen(pen)