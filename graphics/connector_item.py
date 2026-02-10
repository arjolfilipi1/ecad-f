from PyQt5.QtWidgets import QGraphicsRectItem,QGraphicsSimpleTextItem,QGraphicsItem,QGraphicsTextItem
from PyQt5.QtCore import QRectF, QPointF
from PyQt5.QtGui import QBrush,QFont
from .pin_item import PinItem
from PyQt5.QtCore import Qt
from itertools import count

class ConnectorItem(QGraphicsRectItem):
    _ids = count(0)
    def __init__(self, x, y, pin_count=2):
        super().__init__(QRectF(-20, -10, 40, 20))
        self.cid = "C"+str(next(self._ids))
        self._label = QGraphicsSimpleTextItem(self.cid, self)
        self.pins = []
        self.tree_item = None
        self.rotation_angle = 0
        self.wires = []
        
        # ADD: Reference to topology manager
        self.topology_manager = None
        self.topology_node = None
        
        self.setBrush(QBrush(Qt.lightGray))
        self.setFlag(self.ItemIsMovable)
        self.setFlag(self.ItemIsSelectable)
        self.setFlag(self.ItemSendsGeometryChanges)
        self.setTransformOriginPoint(0, 0)
        self.setPos(x, y)
        
        
        self._label.setFlag(QGraphicsItem.ItemIgnoresTransformations)
        self.update_label_pos()
        
        # Create pins
        spacing = 20 / (pin_count + 1)
        for i in range(pin_count):
            pin = PinItem(
                f"{self.cid}_P{i+1}",
                QPointF(-20, -10 + spacing * (i + 1)),
                self
            )
            self.pins.append(pin)
        
        self.info = ConnectorInfoItem(self)
    
    def set_topology_manager(self, manager):
        """Set reference to topology manager"""
        self.topology_manager = manager
        
    def create_topology_node(self):
        """Create topology node for this connector"""
        if self.topology_manager:
            from model.topology import TopologyNode
            self.topology_node = TopologyNode(
                f"CONN_{self.cid}", 
                (self.pos().x(), self.pos().y())
            )
            self.topology_manager.nodes[self.topology_node.id] = self.topology_node
            
    def get_pin_scene_positions(self):
        """Get scene positions of all pins"""
        positions = {}
        for pin in self.pins:
            positions[pin.pid] = pin.scene_position()
        return positions
    
    def itemChange(self, change, value):
        if change == self.ItemPositionChange:
            # Store old position for topology updates
            self.old_position = self.pos()
            
        elif change == self.ItemPositionHasChanged:
            # Update topology node position
            if self.topology_node:
                self.topology_node.position = (self.pos().x(), self.pos().y())
            
            # Update visual wires connected to pins
            for pin in self.pins:
                for wire in list(pin.wires):
                    if hasattr(wire, 'update_path'):
                        wire.update_path()
                    # Also update topology segments
                    self._update_connected_segments()
            
            # Update label position
            self.update_label_pos()
            
            # Update connector info display
            if hasattr(self, 'info'):
                self.info.update_text()
        
        elif change == self.ItemRotationHasChanged:
            # Update pin positions after rotation
            self._update_pin_positions_after_rotation()
            
            # Update connected wires
            for pin in self.pins:
                for wire in list(pin.wires):
                    if hasattr(wire, 'update_path'):
                        wire.update_path()
            
            # Update topology
            self._update_connected_segments()
        
        return super().itemChange(change, value)
    
    def _update_pin_positions_after_rotation(self):
        """Recalculate pin positions in scene coordinates after rotation"""
        # Get the transformation matrix
        transform = self.sceneTransform()
        
        # Update each pin's scene position in topology
        for pin in self.pins:
            # Pin position relative to connector
            local_pos = pin.offset
            
            # Apply connector's transformation
            scene_pos = transform.map(local_pos)
            
            # Update pin's cached scene position
            pin.cached_scene_pos = QPointF(scene_pos.x(), scene_pos.y())
            
            # If pin has a topology connection point, update it
            if hasattr(pin, 'topology_connection'):
                pin.topology_connection.position = (scene_pos.x(), scene_pos.y())
    
    def _update_connected_segments(self):
        """Update all segments connected to this connector's topology node"""
        if not self.topology_node or not self.topology_manager:
            return
            
        # Find all segments connected to this node
        for segment_id, segment in list(self.topology_manager.segments.items()):
            if segment.start_node == self.topology_node or segment.end_node == self.topology_node:
                # Update segment graphics if it exists
                if hasattr(segment, 'graphics_item'):
                    segment.graphics_item.update_path()
                    
                # Update any wires in this segment
                for wire in segment.wires:
                    if hasattr(wire, 'graphics_item'):
                        wire.graphics_item.update_path()
    
    def rotate_90(self):
        """Rotate connector by 90 degrees"""
        self.rotation_angle = (self.rotation_angle + 90) % 360
        self.setRotation(self.rotation_angle)
        
        # Force update of pin positions
        self._update_pin_positions_after_rotation()
        
        # Update wires
        for pin in self.pins:
            for wire in list(pin.wires):
                wire.update_path()
    def update_label_pos(self):
        self._label.setPos(
            self.rect().center().x() - self._label.boundingRect().width() / 2,
            -self._label.boundingRect().height() - 10
        )


class ConnectorInfoItem(QGraphicsTextItem):
    def __init__(self, connector):
        super().__init__(connector)
        self.connector = connector

        self.setFont(QFont("Consolas", 8))
        self.setDefaultTextColor(Qt.darkGray)
        self.setFlag(self.ItemIgnoresTransformations)  # stays readable
        self.setZValue(10)

        self.setPos(25, -15)  # offset to the right of connector
        self.update_text()

    def update_text(self):
        lines = [f"{self.connector.cid}"]
        for pin in self.connector.pins:
            nets = {w.wid for w in getattr(pin, "wires", []) if hasattr(w, "net")}
            net_name = ",".join(nets) if nets else "—"
            lines.append(f"{pin.pid}: {net_name}")

        self.setPlainText("\n".join(lines))
