from PyQt5.QtWidgets import QGraphicsPathItem, QGraphicsTextItem, QGraphicsItem
from PyQt5.QtGui import QPainterPath, QPen, QColor, QFont, QPainter
from PyQt5.QtCore import Qt, QPointF, QLineF
import math

class BundleItem(QGraphicsPathItem):
    """Interactive bundle segment that can be drawn manually"""
    
    # Visual states
    NORMAL = 0
    HIGHLIGHTED = 1
    SELECTED = 2
    CONNECTED = 3
    
    def __init__(self, start_point, end_point: QPointF = None, bundle_id=None):
        super().__init__()
        
        self.bundle_id = bundle_id or f"B{id(self)}"
        self.start_point = start_point
        self.end_point = end_point or start_point
        print("dec",start_point , end_point)
        print(self.start_point , self.end_point)
        self.start_node = None
        self.end_node = None
        self.length = 0.0
        self.specified_length = None  # User-specified length override
        self.wire_count = 0
        self.wire_ids = []  # Wires assigned to this bundle
        
        # Visual properties
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.ItemIsMovable, False)  # Not directly movable
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges, True)
        self.setAcceptHoverEvents(True)
        
        self.pen_normal = QPen(QColor(0, 120, 215), 3)  # Blue
        self.pen_highlight = QPen(QColor(255, 215, 0), 4)  # Gold
        self.pen_selected = QPen(QColor(255, 0, 0), 4)  # Red for selected
        self.pen_connected = QPen(QColor(0, 200, 0), 3)  # Green when wires assigned
        
        self.setPen(self.pen_normal)
        self.setZValue(5)  # Above wires but below connectors
        
        # Length label - ALWAYS VISIBLE now
        self.length_label = BundleLengthLabel(self)
        # print(self.start_point , self.end_point)
        self.length_label.setPos((self.start_point + self.end_point) / 2)
        self.length_label.setVisible(True)  # Always visible
        
        # Add workspace units indicator
        self.workspace_label = QGraphicsTextItem("(workspace units)", self)
        self.workspace_label.setFlag(QGraphicsItem.ItemIgnoresTransformations)
        self.workspace_label.setDefaultTextColor(QColor(150, 150, 150))
        self.workspace_label.setFont(QFont("Arial", 6))
        self.workspace_label.setPos(
            self.length_label.pos().x(),
            self.length_label.pos().y() + 15
        )
        self.workspace_label.setVisible(True)
        
        # State
        self.state = self.NORMAL
        self._is_hovered = False
        
        self.update_path()
    
    def update_path(self):
        """Update the bundle path"""
        path = QPainterPath()
        path.moveTo(self.start_point)
        
        if self.end_point:
            # Draw line with slight curve for visibility
            dx = self.end_point.x() - self.start_point.x()
            dy = self.end_point.y() - self.start_point.y()
            distance = math.sqrt(dx*dx + dy*dy)
            self.length = distance
            
            if abs(dx) > 50 or abs(dy) > 50:
                # Add slight curve for long bundles
                ctrl_x = (self.start_point.x() + self.end_point.x()) / 2
                ctrl_y = (self.start_point.y() + self.end_point.y()) / 2
                path.quadTo(ctrl_x + dy*0.1, ctrl_y - dx*0.1, 
                           self.end_point.x(), self.end_point.y())
            else:
                path.lineTo(self.end_point)
        
        self.setPath(path)
        
        # Update label position and text
        mid_point = (self.start_point + self.end_point) / 2
        self.length_label.setPos(mid_point)
        self.workspace_label.setPos(mid_point.x(), mid_point.y() + 15)
        self.update_label_text()
    
    def update_label_text(self):
        """Update the length label text"""
        if self.specified_length is not None:
            self.length_label.setPlainText(f"{self.specified_length:.0f} mm*")
        else:
            self.length_label.setPlainText(f"{self.length:.0f} units")
    
    def set_end_point(self, point: QPointF):
        """Set end point and update path"""
        self.end_point = point
        self.update_path()
    
    def set_specified_length(self, length: float):
        """Set user-specified length override"""
        self.specified_length = length
        self.update_label_text()
    
    def assign_wire(self, wire_id: str):
        """Assign a wire to this bundle"""
        if wire_id not in self.wire_ids:
            self.wire_ids.append(wire_id)
            self.wire_count = len(self.wire_ids)
            self.update_appearance()
    
    def update_appearance(self):
        """Update visual appearance based on state"""
        if self.state == self.SELECTED:
            self.setPen(self.pen_selected)
        elif self.state == self.HIGHLIGHTED:
            self.setPen(self.pen_highlight)
        elif self.wire_count > 0:
            self.setPen(self.pen_connected)
        else:
            self.setPen(self.pen_normal)
    
    def hoverEnterEvent(self, event):
        self._is_hovered = True
        self.state = self.HIGHLIGHTED
        self.update_appearance()
        super().hoverEnterEvent(event)
    
    def hoverLeaveEvent(self, event):
        self._is_hovered = False
        self.state = self.NORMAL
        self.update_appearance()
        super().hoverLeaveEvent(event)
    
    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.state = self.SELECTED
            self.update_appearance()
        super().mousePressEvent(event)
    
    def mouseReleaseEvent(self, event):
        self.state = self.HIGHLIGHTED if self._is_hovered else self.NORMAL
        self.update_appearance()
        super().mouseReleaseEvent(event)
    
    def paint(self, painter, option, widget=None):
        """Custom paint to show bundle thickness based on wire count"""
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Adjust thickness based on wire count
        pen = self.pen()
        if self.wire_count > 0:
            thickness = min(3 + self.wire_count, 8)
            pen.setWidth(thickness)
        
        painter.setPen(pen)
        painter.drawPath(self.path())
        
        # Draw direction indicator
        if self.end_point and self.start_point != self.end_point:
            self._draw_arrow(painter)
    
    def _draw_arrow(self, painter):
        """Draw direction arrow at midpoint"""
        path = self.path()
        percent = 0.5
        point = path.pointAtPercent(percent)
        angle = path.angleAtPercent(percent)
        
        painter.save()
        painter.translate(point)
        painter.rotate(-angle)
        
        # Draw arrowhead
        arrow_size = 8
        painter.setPen(QPen(Qt.black, 1))
        painter.setBrush(Qt.black)
        
        arrow_path = QPainterPath()
        arrow_path.moveTo(0, -arrow_size/2)
        arrow_path.lineTo(arrow_size, 0)
        arrow_path.lineTo(0, arrow_size/2)
        arrow_path.closeSubpath()
        
        painter.drawPath(arrow_path)
        painter.restore()


class BundleLengthLabel(QGraphicsTextItem):
    """Floating label showing bundle length - always visible"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFlag(QGraphicsItem.ItemIgnoresTransformations)
        self.setDefaultTextColor(Qt.white)
        self.setFont(QFont("Arial", 8, QFont.Bold))
        # Always visible, so no hide/show logic
    
    def paint(self, painter, option, widget=None):
        """Draw with background"""
        painter.save()
        
        # Draw background
        rect = self.boundingRect()
        padding = 2
        bg_rect = rect.adjusted(-padding, -padding, padding, padding)
        
        painter.setBrush(QColor(0, 0, 0, 180))
        painter.setPen(Qt.NoPen)
        painter.drawRoundedRect(bg_rect, 3, 3)
        
        # Draw text
        painter.setPen(Qt.white)
        painter.drawText(rect, Qt.AlignCenter, self.toPlainText())
        
        painter.restore()
