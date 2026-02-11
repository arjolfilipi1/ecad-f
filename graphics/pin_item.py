from PyQt5.QtWidgets import QGraphicsEllipseItem, QGraphicsItem
from PyQt5.QtCore import QPointF,Qt
from PyQt5.QtGui import QBrush, QTransform

class PinItem(QGraphicsEllipseItem):
    def __init__(self, pid, offset: QPointF, parent,pos =""):
        super().__init__(-3, -3, 6, 6, parent)
        self.pid = pid
        self.pos = pos
        self.offset = offset  # Position RELATIVE to parent connector
        self.wires = []
        self.cached_scene_pos = None
        self.topology_connection = None
        self.parent = parent
        
        # CRITICAL: Set local position relative to parent
        self.setPos(offset)  # This is LOCAL position within parent coordinate system
        
        self.setFlag(QGraphicsItem.ItemIgnoresTransformations, False)
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        self.setBrush(QBrush(Qt.black))
        
        # Store initial position
        self.update_scene_position()
    
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
