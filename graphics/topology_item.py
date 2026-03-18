#graphics/topology_item
from PyQt5.QtWidgets import (
    QGraphicsEllipseItem, QGraphicsPathItem, 
    QGraphicsItem, QGraphicsTextItem
)
from PyQt5.QtGui import QPainterPath, QPen, QBrush, QColor, QPainter
from PyQt5.QtCore import Qt, QPointF
from model.topology import JunctionNode, BranchPointNode, WireSegment

class JunctionGraphicsItem(QGraphicsEllipseItem):
    """Visual representation of a junction"""
    def __init__(self, junction_node: JunctionNode):
        super().__init__(-5, -5, 10, 10)
        self.junction_node = junction_node
        self.setPos(*junction_node.position)
        self.setFlag(self.ItemIsSelectable, True)
        self.setFlag(self.ItemIsFocusable, True)
        self.setAcceptHoverEvents(True)
        self.node_type = "Junction"
        self.normal_brush = QBrush(QColor(100, 100, 100))
        self.normal_pen = QPen(Qt.black, 1)
        self.hover_pen = QPen(QColor(255, 255, 0), 2)
        self.selected_pen = QPen(QColor(0, 120, 255), 2)
        
        self.setBrush(self.normal_brush)
        self.setPen(self.normal_pen)
        self.setZValue(4)
        
        self._is_hovered = False
        self._updating = False
    
    def _update_connected_bundles(self):
        """Update all bundles connected to this junction"""
        if self._updating:
            return
        
        self._updating = True
        try:
            if hasattr(self.main_window, 'bundles'):
                for bundle in self.main_window.bundles:
                    if bundle.start_node == self.junction_node or bundle.end_node == self.junction_node:
                        bundle.update_position_from_nodes()
        finally:
            self._updating = False

    def get_node(self):
        return self.junction_node
    def paint(self, painter, option, widget=None):
        painter.save()
        painter.setRenderHint(QPainter.Antialiasing)
        
        if self.isSelected():
            painter.setPen(self.selected_pen)
            painter.setBrush(self.brush())
        elif self._is_hovered:
            painter.setPen(self.hover_pen)
            painter.setBrush(self.brush())
        else:
            painter.setPen(self.normal_pen)
            painter.setBrush(self.brush())
        
        painter.drawEllipse(self.rect())
        painter.restore()
    
    def hoverEnterEvent(self, event):
        self._is_hovered = True
        self.update()
        super().hoverEnterEvent(event)
    
    def hoverLeaveEvent(self, event):
        self._is_hovered = False
        self.update()
        super().hoverLeaveEvent(event)

        
    def itemChange(self, change, value):
        if change == self.ItemPositionHasChanged:
            # Update node position
            self.junction_node.position = (self.pos().x(), self.pos().y())
            
            # Update connected segments
            for segment in self.junction_node.connected_segments:
                if hasattr(segment, 'graphics_item'):
                    segment.graphics_item.update_path()
            
            # NEW: Update connected bundles
            self._update_connected_bundles()
            
        return super().itemChange(change, value)

    def cleanup(self):
        """Clean up junction references"""
        pass

class BranchPointGraphicsItem(QGraphicsEllipseItem):
    """Visual representation of a branch point"""
    
    def __init__(self, model, main_window=None):
        """
        Create a branch point graphics item from a BranchPoint model.
        
        Args:
            model: The BranchPoint model object
            main_window: Reference to main window
        """
        super().__init__(-7, -7, 14, 14)
        self.model = model
        self.model.graphics_item = self  # Set reverse reference
        self.main_window = main_window
        self.node_type = "Branch point"
        self.branch_node = None  # For backward compatibility
        self.tree_item = None
        self._old_pos = None  # For undo tracking
        
        # Set position from model
        self.setPos(model.position[0], model.position[1])
        
        # Enable selection, movement, and hover
        self.setFlag(self.ItemIsSelectable, True)
        self.setFlag(self.ItemIsMovable, True)  # Make it draggable
        self.setFlag(self.ItemIsFocusable, True)
        self.setFlag(self.ItemSendsGeometryChanges, True)  # Track position changes
        self.setAcceptHoverEvents(True)
        
        # Visual properties based on branch type
        if model.branch_type == "splice":
            self.normal_brush = QBrush(QColor(200, 150, 50))
        else:
            self.normal_brush = QBrush(QColor(150, 200, 100))
        
        self.normal_pen = QPen(Qt.black, 1)
        self.hover_pen = QPen(QColor(255, 255, 0), 2)
        self.selected_pen = QPen(QColor(0, 120, 255), 2)
        
        self.setBrush(self.normal_brush)
        self.setPen(self.normal_pen)
        self.setZValue(3)
        
        self._is_hovered = False
        self._updating = False
    
    def get_node(self):
        """Get the topology node (for backward compatibility)"""
        return self
    @property
    def position(self):
        return [self.pos().x(),self.pos().y()]
    @property
    def id(self) -> str:
        """Get wire ID from model"""
        return self.model.id

    def get_branch_point(self):
        """Get the branch point model"""
        return self.model

    
    def set_main_window(self, window):
        """Set reference to main window and register"""
        self.main_window = window
        if window:
            window.register_graphics_item(self, 'branch_points')
    
    def _update_connected_bundles(self):
        """Update all bundles connected to this branch point"""
        if self._updating:
            return
        
        self._updating = True
        try:
            if hasattr(self.main_window, 'bundles'):
                for bundle in self.main_window.bundles:
                    if (bundle.start_node and bundle.start_node.id == self.model.id) or \
                       (bundle.end_node and bundle.end_node.id == self.model.id):
                        bundle.update_position_from_nodes()
        finally:
            self._updating = False
    
    def _update_connected_segments(self):
        """Update all segments connected to this branch point"""
        if not self.branch_node or not hasattr(self.main_window, 'topology_manager'):
            return
        
        # Find all segments connected to this node
        for segment in self.main_window.topology_manager.segments.values():
            if segment.start_node == self.branch_node or segment.end_node == self.branch_node:
                # Update segment graphics if it exists
                if hasattr(segment, 'graphics_item') and segment.graphics_item:
                    segment.graphics_item.update_path()
                
                # Update any wires in this segment
                for wire in segment.wires:
                    if hasattr(wire, 'graphics_item') and wire.graphics_item:
                        wire.graphics_item.update_path()
    
    def itemChange(self, change, value):
        if change == self.ItemPositionChange and self.scene():
            # Store old position for undo
            self._old_pos = self.pos()
            
        elif change == self.ItemPositionHasChanged:
            # Update model position
            self.model.position = (self.pos().x(), self.pos().y())
            
            # Update topology node if it exists
            if self.branch_node:
                self.branch_node.position = self.model.position
            
            # Update connected segments
            self._update_connected_segments()
            
            # Update connected bundles
            self._update_connected_bundles()
            
        return super().itemChange(change, value)
    
    def mouseReleaseEvent(self, event):
        """Handle mouse release - create undo command if moved"""
        if event.button() == Qt.LeftButton and self._old_pos is not None:
            new_pos = self.pos()
            if self._old_pos != new_pos:
                self._create_move_undo_command(self._old_pos, new_pos)
        
        self._old_pos = None
        super().mouseReleaseEvent(event)
    
    def _create_move_undo_command(self, old_pos, new_pos):
        """Create undo command for move operation"""
        if not self.main_window:
            return
        
        from commands.topology_commands import MoveBranchPointCommand
        cmd = MoveBranchPointCommand(self, old_pos, new_pos, self.main_window)
        self.main_window.undo_manager.push(cmd)
    
    def contextMenuEvent(self, event):
        """Handle right-click context menu"""
        from graphics.context_menus import BranchPointContextMenu
        self.setSelected(True)
        menu = BranchPointContextMenu(self, self.main_window)
        menu.exec_(event.screenPos())

    def paint(self, painter, option, widget=None):
        """Custom paint with glow effects"""
        painter.save()
        painter.setRenderHint(QPainter.Antialiasing)
        
        if self.isSelected():
            painter.setPen(self.selected_pen)
            painter.setBrush(self.brush())
        elif self._is_hovered:
            painter.setPen(self.hover_pen)
            painter.setBrush(self.brush())
        else:
            painter.setPen(self.normal_pen)
            painter.setBrush(self.brush())
        
        painter.drawEllipse(self.rect())
        painter.restore()
    
    def hoverEnterEvent(self, event):
        self._is_hovered = True
        self.update()
        super().hoverEnterEvent(event)
    
    def hoverLeaveEvent(self, event):
        self._is_hovered = False
        self.update()
        super().hoverLeaveEvent(event)

    def cleanup(self):
        """Clean up branch point references"""
        # Unregister from main window
        if self.main_window:
            self.main_window.unregister_graphics_item(self, 'branch_points')
        
        # Clear graphics item reference from model
        if self.model:
            self.model.graphics_item = None
        
        if self.tree_item:
            try:
                tree = self.tree_item.treeWidget()
                if tree and not sip.isdeleted(tree):
                    index = tree.indexOfTopLevelItem(self.tree_item)
                    if index >= 0:
                        tree.takeTopLevelItem(index)
            except:
                pass
            self.tree_item = None


        
class FastenerGraphicsItem(QGraphicsEllipseItem):
    """Visual representation of a fastener point"""
    def __init__(self, fastener_node):
        super().__init__(-6, -6, 12, 12)
        self.fastener_node = fastener_node
        self.setPos(*fastener_node.position)
        
        # Enable selection and hover
        self.setFlag(self.ItemIsSelectable, True)
        self.setFlag(self.ItemIsFocusable, True)
        self.setAcceptHoverEvents(True)
        self.node_type = "Fastner"
        # Visual properties based on fastener type
        if fastener_node.fastener_type == "cable_tie":
            self.normal_brush = QBrush(QColor(0, 150, 255))  # Blue for cable ties
        elif fastener_node.fastener_type == "clip":
            self.normal_brush = QBrush(QColor(255, 150, 0))  # Orange for clips
        else:
            self.normal_brush = QBrush(QColor(150, 150, 150))  # Gray for others
        
        self.normal_pen = QPen(Qt.black, 1)
        self.hover_pen = QPen(QColor(255, 255, 0), 2)
        self.selected_pen = QPen(QColor(0, 120, 255), 2)
        
        self.setBrush(self.normal_brush)
        self.setPen(self.normal_pen)
        self.setZValue(3)
        
        self._is_hovered = False
    def get_node(self):
        return self.fastener_node
    def paint(self, painter, option, widget=None):
        painter.save()
        painter.setRenderHint(QPainter.Antialiasing)
        
        # Draw diamond shape for fasteners
        if self.isSelected():
            painter.setPen(self.selected_pen)
        elif self._is_hovered:
            painter.setPen(self.hover_pen)
        else:
            painter.setPen(self.normal_pen)
        
        painter.setBrush(self.brush())
        
        # Draw a diamond
        rect = self.rect()
        points = [
            QPointF(rect.center().x(), rect.top()),
            QPointF(rect.right(), rect.center().y()),
            QPointF(rect.center().x(), rect.bottom()),
            QPointF(rect.left(), rect.center().y()),
            QPointF(rect.center().x(), rect.top())
        ]
        
        for i in range(len(points) - 1):
            painter.drawLine(points[i], points[i+1])
        
        painter.restore()
    
    def hoverEnterEvent(self, event):
        self._is_hovered = True
        self.update()
        super().hoverEnterEvent(event)
    
    def hoverLeaveEvent(self, event):
        self._is_hovered = False
        self.update()
        super().hoverLeaveEvent(event)