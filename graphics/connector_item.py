#graphics/connector_item
from PyQt5.QtWidgets import QGraphicsRectItem, QGraphicsSimpleTextItem, QGraphicsItem, QGraphicsTextItem, QGraphicsDropShadowEffect
from PyQt5.QtCore import QRectF, QPointF, Qt, QPropertyAnimation, QEasingCurve
from PyQt5.QtGui import QBrush, QFont, QPen, QColor, QPainter, QPainterPath
from .pin_item import PinItem
from itertools import count
from typing import Union, List,Optional

class ConnectorItem(QGraphicsRectItem):
    _ids = count(0)
    
    def __init__(self, x: float, y: float, pins: Union[int, List[str]] = 2,orcid:str = ""):
        """
        Args:
            x, y: position
            pins: either integer pin count or list of pin identifiers (strings)
        """
        super().__init__(QRectF(-20, -10, 40, 20))
        # Remove the default selection rectangle
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.ItemIsMovable, True)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges, True)
        self.setFlag(QGraphicsItem.ItemIsFocusable, True)  # For hover events
        
        # Enable hover events
        self.setAcceptHoverEvents(True)

        self.cid = ("C"+str(next(self._ids))) if not orcid else orcid

        self._label = QGraphicsSimpleTextItem(self.cid, self)
        self.pins = []
        self.pin_ids = []  # Store original pin identifiers
        self.tree_item = None
        self.rotation_angle = 0
        self.wires = []
        self.main_window = None
        self.topology_manager = None
        self.topology_node = None
        
        # Visual properties
        self.normal_brush = QBrush(Qt.lightGray)
        self.normal_pen = QPen(Qt.black, 1)
        self.hover_pen = QPen(QColor(255, 200, 0), 1)  # Yellow glow
        self.selected_pen = QPen(QColor(0, 120, 255), 2)  # Blue glow
        
        self.setBrush(self.normal_brush)
        self.setPen(self.normal_pen)

        self.setTransformOriginPoint(0, 0)
        self.setPos(x, y)
        
        self._label.setFlag(QGraphicsItem.ItemIgnoresTransformations)
        self.update_label_pos()
        # Selection state
        self._is_hovered = False

        # Create pins based on input
        self._create_pins(pins)
        
        self.info = ConnectorInfoItem(self)
        self.shadow = QGraphicsDropShadowEffect()

        # 2. Configure properties
        self.shadow.setBlurRadius(10)             # Softness of the shadow (default is 1)
        self.shadow.setXOffset(5)                 # Horizontal displacement
        self.shadow.setYOffset(5)                 # Vertical displacement
        self.shadow.setColor(QColor(250, 250, 250, 160)) # Shadow color with transparency
        self.setGraphicsEffect(self.shadow)
        self.shadow.setEnabled(True)
    def _create_pins(self, pins_spec: Union[int, List[str]]):
        """Create pin items from specification"""
        self.pins.clear()
        self.pin_ids.clear()
        
        if isinstance(pins_spec, int):
            # Legacy mode: generate sequential pin numbers
            pin_count = pins_spec
            self.pin_ids = [str(i+1) for i in range(pin_count)]
        else:
            # List of pin identifiers (strings)
            self.pin_ids = pins_spec.copy()
            pin_count = len(self.pin_ids)
        
        # Position pins vertically on left side
        spacing = 20 / (pin_count + 1)
        for i, pin_id in enumerate(self.pin_ids):
            pin = PinItem(
                f"{self.cid}_{pin_id}",  # e.g., "C0_A1"
                QPointF(-20, -10 + spacing * (i + 1)),
                self
            )
            # Store the original pin identifier for lookup
            pin.original_id = pin_id
            self.pins.append(pin)
    
    def get_pin_by_id(self, pin_id: str) -> Optional[PinItem]:
        """Find pin by its original identifier (e.g., 'A1', '3')"""
        for pin in self.pins:
            if hasattr(pin, 'original_id') and pin.original_id == pin_id:
                return pin
        return None

    
    def set_topology_manager(self, topology_manager):
        """Complete topology setup for this connector"""
        self.topology_manager = topology_manager
        self.topology_node = topology_manager.create_connector_node(self)

    def set_main_window(self, window):
        """Set reference to main window for topology access"""
        self.main_window = window
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
        if change == self.ItemSelectedChange:
            # Selection state is changing
            self.update()
            

        if change == self.ItemPositionChange:
            # Store old position for topology updates
            self.old_pos = self.pos()
            
        elif change == self.ItemPositionHasChanged:
                # Notify main window
            if self.main_window and hasattr(self.main_window, 'update_dispatcher'):
                self.main_window.update_dispatcher.notify_connector_moved(self)
            
            # Update topology node position
            if self.topology_node:
                self.topology_node.position = (self.pos().x(), self.pos().y())
            
            # Update pins
            for pin in self.pins:
                pin.invalidate_cache()
                for wire in list(pin.wires):
                    if hasattr(wire, 'update_path'):
                        wire.update_path()
            
            # Update segments
            self._update_connected_segments()
            
            # Update label
            self.update_label_pos()
            
            if hasattr(self, 'info'):
                self.info.update_text()
        
        elif change == self.ItemRotationHasChanged:
            # Handle rotation
            self._update_pin_positions_after_rotation()
            for pin in self.pins:
                for wire in list(pin.wires):
                    if hasattr(wire, 'update_path'):
                        wire.update_path()
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
                if pin.topology_connection:
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
    def paint(self, painter, option, widget=None):
        """Custom paint to remove selection rectangle and add glow effects"""
        # Save the painter state
        painter.save()
        
        # Set pen based on state
        if self.isSelected():
            painter.setPen(self.selected_pen)
            # Add subtle glow effect
            painter.setBrush(self.brush())
        elif self._is_hovered:
            painter.setPen(self.hover_pen)
            self.shadow.setEnabled(True)
            painter.setBrush(self.brush())
        else:
            self.shadow.setEnabled(True)
            painter.setPen(self.normal_pen)
            painter.setBrush(self.brush())
        
        # Draw the connector rectangle
        painter.drawRect(self.rect())
        
        # Restore painter
        painter.restore()
        
        # Draw children (pins, label, info) - they paint themselves
    
    def hoverEnterEvent(self, event):
        """Handle mouse enter for yellow glow"""
        self._is_hovered = True
        self.update()
        super().hoverEnterEvent(event)
    
    def hoverLeaveEvent(self, event):
        """Handle mouse leave - remove yellow glow"""
        self._is_hovered = False
        self.update()
        super().hoverLeaveEvent(event)


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
        self.connector._label.setText(self.connector.cid)
        for pin in self.connector.pins:
            
            wids = [w.wid for w in pin.wires]
            net_name = ",".join(wids) if pin.wires else "—"
            lines.append(f"{pin.pid}: {net_name}")

        self.setPlainText("\n".join(lines))
