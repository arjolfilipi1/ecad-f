#graphics/pin_item
from PyQt5.QtWidgets import QGraphicsEllipseItem, QGraphicsItem
from PyQt5.QtCore import QPointF,Qt
from PyQt5.QtGui import QBrush, QTransform, QPen, QColor

class PinItem(QGraphicsEllipseItem):
    def __init__(self, pid, offset: QPointF, parent,pos =""):
        super().__init__(-3, -3, 6, 6, parent)
        self.pid = pid  # e.g., "C0_A1"
        self.original_id = None  # will be set by connector

        self.pos = pos
        self.offset = offset  # Position RELATIVE to parent connector
        self.wires = []
        self.cached_scene_pos = None
        self.topology_connection = None
        self.parent = parent
        
        # CRITICAL: Set local position relative to parent
        self.setPos(offset)  # This is LOCAL position within parent coordinate system
        # Remove default selection
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.ItemIsFocusable, True)
        self.setAcceptHoverEvents(True)
        
        # Visual properties
        self.normal_brush = QBrush(Qt.black)
        self.normal_pen = QPen(Qt.black, 1)
        self.hover_pen = QPen(QColor(255, 230, 0), 3)
        self.selected_pen = QPen(QColor(0, 120, 255), 2)
        self.connected_brush = QBrush(Qt.darkGreen)
        
        self._is_hovered = False

        self.setFlag(QGraphicsItem.ItemIgnoresTransformations, False)

        self.setBrush(self.normal_brush)
        self.setPen(self.normal_pen)
        self.setPos(offset)
        self.update_scene_position()

        
        # Store initial position
        self.update_scene_position()
    def paint(self, painter, option, widget=None):
        """Custom paint for pin with glow effects"""
        painter.save()
        
        # Determine if pin has connected wires
        has_wires = len(self.wires) > 0
        
        # Set visual style based on state
        if self.isSelected():
            painter.setPen(self.selected_pen)
            painter.setBrush(QBrush(Qt.white))
        elif self._is_hovered:
            painter.setPen(self.hover_pen)
            painter.setBrush(self.brush())
        else:
            painter.setPen(self.normal_pen)
            painter.setBrush(self.brush())
        
        # Draw the pin
        painter.drawEllipse(self.rect())
        
        painter.restore()
    
    def hoverEnterEvent(self, event):
        """Yellow glow on hover"""
        self._is_hovered = True
        self.update()
        super().hoverEnterEvent(event)
    
    def hoverLeaveEvent(self, event):
        """Remove yellow glow"""
        self._is_hovered = False
        self.update()
        super().hoverLeaveEvent(event)
    def mousePressEvent(self, event):
        """Select pin when clicked"""
        self.setSelected(True)
        super().mousePressEvent(event)

    def scene_position(self):
        """Get absolute scene position of this pin"""
        # Calculate from parent's transformation
        if self.cached_scene_pos is None:
            # Get parent's transform and apply to local offset
            parent_transform = self.parent.sceneTransform()
            # Map the local offset (relative to connector) to scene coordinates
            self.cached_scene_pos = parent_transform.map(self.offset)
        return self.cached_scene_pos
    
    def invalidate_cache(self):
        """Clear cached position - call when parent moves/rotates"""
        self.cached_scene_pos = None
        if self.topology_connection:
            pos = self.scene_position()
            self.topology_connection.position = (pos.x(), pos.y())
    
    def update_scene_position(self):
        """Force recalculation of scene position"""
        self.cached_scene_pos = None
        return self.scene_position()
    
    def get_local_offset(self):
        """Get the offset relative to connector center"""
        return self.offset
