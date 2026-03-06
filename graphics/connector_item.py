#graphics/connector_item
from PyQt5.QtWidgets import QGraphicsRectItem, QGraphicsSimpleTextItem, QGraphicsItem, QGraphicsTextItem, QGraphicsDropShadowEffect
from PyQt5.QtCore import QRectF, QPointF, Qt, QPropertyAnimation, QEasingCurve
from PyQt5.QtGui import QBrush, QFont, QPen, QColor, QPainter, QPainterPath
from .pin_item import PinItem
from itertools import count
from typing import Union, List,Optional
from PyQt5 import sip
from model.models import Connector,ConnectorType,Gender,SealType,Pin

class ConnectorItem(QGraphicsRectItem):
    
    
    def __init__(self,model:Connector):
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
        self.pins:[PinItem] = []
        self.model = model
        self._label = QGraphicsSimpleTextItem(self.model.id, self)
        self.tree_item = None     
        self.main_window = None
        self.topology_manager = None
        self.topology_node = None
        self.node_type = "Connector"
        # Visual properties
        self.normal_brush = QBrush(Qt.lightGray)
        self.normal_pen = QPen(Qt.black, 1)
        self.hover_pen = QPen(QColor(255, 200, 0), 1)  # Yellow glow
        self.selected_pen = QPen(QColor(0, 120, 255), 2)  # Blue glow
        
        self.setBrush(self.normal_brush)
        self.setPen(self.normal_pen)

        self.setTransformOriginPoint(0, 0)
        self.setPos(self.model.position[0], self.model.position[1])
        
        self._label.setFlag(QGraphicsItem.ItemIgnoresTransformations)
        self.update_label_pos()
        # Selection state
        self._is_hovered = False

        # Create pins based on input
        
        self._create_pins_from_model()
        from graphics.connector_info_table import ConnectorInfoTable
        self.info_table = ConnectorInfoTable(self)
        self.compact_mode = False

        self.shadow = QGraphicsDropShadowEffect()
        self.setup_info_table()
        # 2. Configure properties
        self.shadow.setBlurRadius(10)             # Softness of the shadow (default is 1)
        self.shadow.setXOffset(5)                 # Horizontal displacement
        self.shadow.setYOffset(5)                 # Vertical displacement
        self.shadow.setColor(QColor(250, 250, 250, 160)) # Shadow color with transparency
        self.setGraphicsEffect(self.shadow)
        self.shadow.setEnabled(True)
    def update_info_display(self):
        """Refresh the info table"""
        if hasattr(self, 'info_table'):
            self.info_table.update_table()
    def toggle_info_display(self):
        """Toggle between compact and full table view"""
        from graphics.connector_info_table import ConnectorInfoTable, CompactConnectorInfoTable
        
        # Store current position
        pos = self.info_table.pos()
        
        # Remove current table
        self.info_table.deleteLater()
        
        # Create new table
        if self.compact_mode:
            self.info_table = ConnectorInfoTable(self)
        else:
            self.info_table = CompactConnectorInfoTable(self)
        
        self.compact_mode = not self.compact_mode
        self.info_table.setPos(pos)
        self.info_table.update_table()
    def get_node(self):
        return self.topology_node
    def __str__(self):
        return self.model.id
    def _update_connected_bundles(self):
        """Update all bundles connected to this connector"""
        if not self.topology_node:
            # print("no topology node")
            return
        
        # Find all bundles connected to this node
        if hasattr(self.main_window, 'bundles'):
            for bundle in self.main_window.bundles:
                if bundle.start_node == self.topology_node or bundle.end_node == self.topology_node:
                    bundle.update_position_from_nodes()

    
    
    def _create_pins_from_model(self):
        """Create pin graphics items from the model"""
        self.pins.clear()
        
        # Position pins vertically on left side
        pin_count = len(self.model.pins)
        spacing = 20 / (pin_count + 1)
        
        for i, (pin_number, pin_model) in enumerate(self.model.pins.items()):
            offset = QPointF(-20, -10 + spacing * (i + 1))
            pin = PinItem(pin_model, offset, self)
            self.pins.append(pin)

    
    def get_pin_by_id(self, pin_id: str) -> Optional[PinItem]:
        """Find pin by its original identifier (e.g., 'A1', '3')"""
        for pin in self.pins:
            if hasattr(pin, 'model') and pin.model.pid == pin_id:
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
                self.model.id, 
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
            self.update()
            
        if change == QGraphicsItem.GraphicsItemChange.ItemSceneHasChanged:
            if self.scene() is None:
                self.cleanup()
            
        elif change == self.ItemPositionChange:
            self.old_pos = self.pos()
            
        elif change == self.ItemPositionHasChanged:
            # Notify main window
            if self.main_window and hasattr(self.main_window, 'update_dispatcher'):
                self.main_window.update_dispatcher.notify_connector_moved(self)
            # if hasattr(self, 'info_table') and self.info_table is not None:
                # self.info_table.update_table()
            # Update topology node position
            if self.topology_node:
                self.topology_node.position = (self.pos().x(), self.pos().y())
            self.model.position = [self.pos().x(),self.pos().y()]
            # Update pins
            for pin in self.pins:
                pin.invalidate_cache()
                for wire in list(pin.wire_items):
                    if hasattr(wire, 'update_path'):
                        wire.update_path()
            
            # Update segments
            self._update_connected_segments()
            
            # NEW: Update connected bundles
            self._update_connected_bundles()
            
            # Update label
            self.update_label_pos()
            

            if hasattr(self, 'info_table') and self.info_table is not None:
                self.info_table.update_table()
        elif change == self.ItemRotationHasChanged:
            # Handle rotation
            self._update_pin_positions_after_rotation()
            for pin in self.pins:
                for wire in list(pin.wire_items):
                    if hasattr(wire, 'update_path'):
                        wire.update_path()
            self._update_connected_segments()
            # NEW: Update connected bundles (rotation affects pin positions)
            self._update_connected_bundles()
        
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
        self.model.rotation = (self.model.rotation + 90) % 360
        self.setRotation(self.model.rotation)
        
        # Force update of pin positions
        self._update_pin_positions_after_rotation()
        
        # Update wires
        for pin in self.pins:
            for wire in list(pin.wire_items):
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
    def contextMenuEvent(self, event):
        """Handle right-click context menu"""
        from graphics.context_menus import ConnectorContextMenu
        
        # Select this item
        self.setSelected(True)
        
        # Create and show menu
        menu = ConnectorContextMenu(self, self.main_window)
        menu.exec_(event.screenPos())
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
    def cleanup(self):
        """Remove tree item references before deletion"""
        if self.tree_item:
            # Remove from tree widget
            try:
                tree = self.tree_item.treeWidget()
                if tree and not sip.isdeleted(tree):
                    index = tree.indexOfTopLevelItem(self.tree_item)
                    if index >= 0:
                        tree.takeTopLevelItem(index)
            except:
                pass
            self.tree_item = None
        
        # Clear pin references
        for pin in self.pins:
            pin.cleanup()
        
        # Clear wire references
        for wire in list(self.model.pins.values()):
            # This would need proper wire tracking
            pass

        # CRITICAL: Clean up info table
        if hasattr(self, 'info_table') and self.info_table:
            try:
                # Remove from scene if it's a graphics item
                if self.info_table.scene():
                    self.scene().removeItem(self.info_table)
                self.info_table.deleteLater()
            except:
                pass
            self.info_table = None
        
    def setup_info_table(self):
        if self.info_table is None:
            """Create or recreate the info table"""
            from graphics.connector_info_table import ConnectorInfoTable
            self.info_table = ConnectorInfoTable(self)
            # Position it correctly
            self.info_table.setPos(25, -15)

