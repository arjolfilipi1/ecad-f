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
    def __init__(self,  model, main_window=None):
        super().__init__(-7, -7, 14, 14)
        self.model = model
        self.model.graphics_item = self  # Set reverse reference
        self.main_window = main_window
        self.node_type = "Branch point"
        self.branch_node = None  # For backward compatibility
        
        # Set position from model
        self.setPos(model.position[0], model.position[1])
        
        # Enable selection and hover
        self.setFlag(self.ItemIsSelectable, True)
        self.setFlag(self.ItemIsFocusable, True)
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
        self.tree_item = None

    def get_node(self):
        return self.branch_node
        
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
    
    def itemChange(self, change, value):
        if change == self.ItemPositionHasChanged:
            # Update model position
            self.model.position = (self.pos().x(), self.pos().y())
            
            # Update connected segments (to be implemented)
            
            # Update connected bundles
            self._update_connected_bundles()
            
        return super().itemChange(change, value)
    
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