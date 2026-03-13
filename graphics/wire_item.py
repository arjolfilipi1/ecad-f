#graphics/wire_item
from PyQt5.QtWidgets import QGraphicsPathItem, QStyle, QGraphicsDropShadowEffect
from PyQt5.QtGui import QPainterPath, QPen, QColor, QPainter
from PyQt5.QtCore import Qt,QPointF
from model.models import Wire
from model.topology import WireSegment
from PyQt5.QtWidgets import QGraphicsPathItem, QStyle
from PyQt5.QtGui import QPainterPath, QPen, QColor
from PyQt5.QtCore import Qt, QPointF
from model.models import CombinedWireColor
from PyQt5 import sip
from typing import List

class WireItem(QGraphicsPathItem):
    def __init__(self, model: Wire):
        """
        Create a wire graphics item from a Wire model.
        
        Args:
            model: The Wire model object containing all wire data
        """
        super().__init__()
        self.model = model
        self.node_type = "Wire"
        self.model.graphics_item = self  # Set reverse reference
        self.tree_item = None
        self.main_window = None
        
        # Get pin references from the model
        self.start_pin = None  # Will be set later by the scene
        self.end_pin = None    # Will be set later by the scene
        self.is_connected = False
        
        # Color data
        self.color_data = model.color
        self.color = QColor(*self.color_data.rgb)
        
        # Visual properties
        self.normal_pen = QPen(self.color, 2)
        self.hover_pen = QPen(QColor(255, 255, 0), 3)
        self.selected_pen = QPen(QColor(0, 120, 255), 3)
        
        self.setPen(self.normal_pen)
        self.setZValue(1)
        
        # Enable interactions
        self.setFlag(self.ItemIsSelectable, True)
        self.setFlag(self.ItemIsFocusable, True)
        self.setAcceptHoverEvents(True)
        
        self._is_hovered = False
        
        # Path will be updated when pins are connected
        self.update_path()
    
    @property
    def wid(self) -> str:
        """Get wire ID from model"""
        return self.model.id
    
    def connect_to_pins(self, start_pin, end_pin):
        """
        Connect this wire to actual pin graphics items.
        This should be called after adding to scene.
        
        Args:
            start_pin: The start PinItem
            end_pin: The end PinItem
        """
        self.start_pin = start_pin
        self.end_pin = end_pin
        self.is_connected = True
        
        # Add this wire to the pins' wire lists
        start_pin.add_wire(self) if start_pin else None
        end_pin.add_wire(self)   if   end_pin else None
        
       
        
        # Update the path
        self.update_path()
    
    def contextMenuEvent(self, event):
        """Handle right-click context menu"""
        from graphics.context_menus import WireContextMenu
        self.setSelected(True)
        menu = WireContextMenu(self, self.main_window)
        menu.exec_(event.screenPos())
    
    def update_path(self):
        """Update wire path connecting the two pins"""
        if not self.is_connected or not self.start_pin or not self.end_pin:
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
        
        # Update pen color (in case it changed)
        self.color = QColor(*self.color_data.rgb)
        self.normal_pen.setColor(self.color)
        self.update_appearance()
    
    def update_appearance(self):
        """Update pen based on selection/hover state"""
        if self.isSelected():
            self.setPen(self.selected_pen)
        elif self._is_hovered:
            self.setPen(self.hover_pen)
        else:
            self.setPen(self.normal_pen)
    
    def paint(self, painter, option, widget=None):
        """Custom paint with glow effects and no selection rectangle"""
        painter.save()
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Set pen based on state
        self.update_appearance()
        painter.setPen(self.pen())
        
        painter.drawPath(self.path())
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
    
    def cleanup(self):
        """Clean up wire references before deletion"""
        # Remove from pins' wire_items lists
        if self.start_pin:
            self.start_pin.remove_wire(self)
        if self.end_pin:
            self.end_pin.remove_wire(self)
        # Remove tree item reference (don't try to remove from tree here,
        # as the tree might be in the process of being cleared)
        self.tree_item = None
        
        # Clear graphics item reference from model
        # if hasattr(self, 'model') and self.model:
            # self.model.graphics_item = None
        
    def __del__(self):
        """Ensure cleanup on deletion"""
        try:
            self.cleanup()
        except:
            pass

    def set_main_window(self, window):
            """Set reference to main window"""
            self.main_window = window
            if window:
                window.register_graphics_item(self, 'wires')
                
class SegmentedWireItem(QGraphicsPathItem):
    """Visual representation of a wire routed through bundles"""
    
    def __init__(self, wire_model: Wire, path_segments: List, main_window=None):
        """
        Create a segmented wire graphics item from a Wire model and path segments.
        
        Args:
            wire_model: The Wire model object (from model.models)
            path_segments: List of topology segments that form the path
            main_window: Reference to main window
        """
        super().__init__()
        self.wire_model = wire_model  # Reference to the actual wire model
        self.model = wire_model  # Reference to the actual wire model for properties 
        self.setFlag(self.ItemIsSelectable, True)
        self.main_window = main_window
        self.node_type = "Wire segment"
        self.tree_item = None
        self.original_wire = None  # Reference to original wire graphics if this is a routed version
        self.used_bundles = []  # Bundles this wire passes through
        self.path_segments = path_segments  # Store segments for path calculation
        
        # Add this graphics item to the wire model's routed_graphics list
        if wire_model:
            wire_model.add_routed_graphics(self)
        
        # Connection points (set when connecting to pins)
        self.start_pin = None
        self.end_pin = None
        self.is_connected = False
        
        # Visual properties - use the wire model's color
        self.color_data = wire_model.color
        self.color = QColor(*self.color_data.rgb)
        self.normal_pen = QPen(self.color, 1.5)
        self.hover_pen = QPen(QColor(255, 255, 0), 2.5)
        self.selected_pen = QPen(QColor(0, 120, 255), 2.5)
        
        self.setPen(self.normal_pen)
        self.setZValue(4)
        
        self._is_hovered = False
        
        # Path will be updated when segments are available
        self.update_path()
    
    @property
    def wid(self) -> str:
        """Get wire ID from the wire model"""
        return self.wire_model.id
    
    def connect_to_pins(self, start_pin, end_pin):
        """Connect this wire to actual pin graphics items"""
        self.start_pin = start_pin
        self.end_pin = end_pin
        self.is_connected = True
        
        # Add this wire to the pins' wire lists
        if start_pin and self not in start_pin.wire_items:
            start_pin.wire_items.append(self)
        if end_pin and self not in end_pin.wire_items:
            end_pin.wire_items.append(self)
        
        self.update_path()
    
    def update_path(self):
        """Draw the complete path of the wire through segments"""
        path = QPainterPath()
        
        # Build node path from segments
        node_positions = []
        
        # Start from the start pin if available
        if self.start_pin and self.is_connected:
            start_pos = self.start_pin.scene_position()
            path.moveTo(start_pos)
            node_positions.append(start_pos)
        
        # Add all segment end nodes
        for segment in self.path_segments:
            if segment.end_node:
                end_pos = QPointF(*segment.end_node.position)
                path.lineTo(end_pos)
                node_positions.append(end_pos)
        
        # Connect to end pin if available
        if self.end_pin and self.is_connected:
            end_pos = self.end_pin.scene_position()
            if node_positions and node_positions[-1] != end_pos:
                path.lineTo(end_pos)
        
        self.setPath(path)
        
        # Update color
        self.color = QColor(*self.color_data.rgb)
        self.normal_pen.setColor(self.color)
        self.update_appearance()
    
    def update_appearance(self):
        """Update pen based on selection/hover state"""
        if self.isSelected():
            self.setPen(self.selected_pen)
        elif self._is_hovered:
            self.setPen(self.hover_pen)
        else:
            self.setPen(self.normal_pen)
    
    def paint(self, painter, option, widget=None):
        """Custom paint with glow effects"""
        painter.save()
        painter.setRenderHint(QPainter.Antialiasing)
        
        self.update_appearance()
        painter.setPen(self.pen())
        painter.drawPath(self.path())
        
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
    
    def set_main_window(self, window):
        """Set reference to main window"""
        self.main_window = window
    
    def cleanup(self):
        """Clean up wire references"""
        # Remove from wire model's routed_graphics list
        if self.wire_model:
            self.wire_model.remove_routed_graphics(self)
        
        # Remove from pins' wire_items lists
        if self.start_pin and self in self.start_pin.wire_items:
            self.start_pin.wire_items.remove(self)
        if self.end_pin and self in self.end_pin.wire_items:
            self.end_pin.wire_items.remove(self)
        
        if self.tree_item:
            try:
                tree = self.tree_item.treeWidget()
                if tree and not sip.isdeleted(tree):
                    index = tree.indexOfTopLevelItem(self.tree_item)
                    if index >= 0:
                        tree.takeTopLevelItem(index)
            except RuntimeError:
                pass
            self.tree_item = None

    
    def __del__(self):
        try:
            self.cleanup()
        except:
            pass