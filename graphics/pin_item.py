from PyQt5.QtWidgets import QGraphicsEllipseItem, QGraphicsItem
from PyQt5.QtCore import QPointF
from PyQt5.QtGui import QBrush, QTransform
from model.topology import ConnectionPoint
class PinItem(QGraphicsEllipseItem):
    def __init__(self, pid, offset: QPointF, parent):
        super().__init__(-3, -3, 6, 6, parent)
        self.pid = pid
        self.offset = offset
        self.wires = []
        self.cached_scene_pos = None # Cache scene position
        self.topology_connection = None # Link to topology connection point
        self.parent = parent
        self.setPos(offset)
        self.setFlag(QGraphicsItem.ItemIgnoresTransformations, False)
        self.setFlag(QGraphicsItem.ItemIsSelectable)
        self.setBrush(QBrush())
    def create_topology_connection(self,tm):
        if not tm:
            return None
        if not hasattr(self.parent,"topology_node":
            return None
        self.topology_connection = ConnectionPoint(point_id = f"{self.parent.cid}_{self.pid}",node = self.parent.topology_node,pin = self)
        tm.connection_points[self.topology_connection.id] = self.topology_connection
        return self.topology_connection
    def scene_position(self):
        """Get scene position with caching"""
        if self.cached_scene_pos is None:
            # Calculate scene position
            self.cached_scene_pos = self.scenePos()
        return self.cached_scene_pos
    
    def invalidate_cache(self):
        """Invalidate cached position"""
        self.cached_scene_pos = None
    
    def update_scene_position(self):
        """Force update of scene position"""
        self.cached_scene_pos = self.scenePos()
        return self.cached_scene_pos