from PyQt5.QtWidgets import QGraphicsPathItem, QGraphicsTextItem, QGraphicsItem
from PyQt5.QtGui import QPainterPath, QPen, QColor, QFont, QPainter
from PyQt5.QtCore import Qt, QPointF, QLineF
import math
from typing import List
from model.models import Bundle

class BundleItem(QGraphicsPathItem):
    """Interactive bundle segment that can be drawn manually"""
    
    # Visual states
    NORMAL = 0
    HIGHLIGHTED = 1
    SELECTED = 2
    CONNECTED = 3
    
    def __init__(self, model: Bundle, main_window=None):
        """
        Create a bundle graphics item from a Bundle model.
        
        Args:
            model: The Bundle model object containing all bundle data
            main_window: Reference to main window
        """
        super().__init__()
        self.model = model
        self.model.graphics_item = self  # Set reverse reference
        self.main_window = main_window
        self.node_type = "Bundle"
        
        # For backward compatibility during transition
        self.bundle_id = model.id
        self.start_point = QPointF(model.start_point[0], model.start_point[1])
        self.end_point = QPointF(model.end_point[0], model.end_point[1])
        self.specified_length = model.specified_length
        self.wire_count = model.wire_count
        self.wire_ids = model.wire_ids.copy() if model.wire_ids else []
        
        # Node references
        self.start_node = None
        self.end_node = None
        self.start_item = None
        self.end_item = None
        
        # Visual properties
        self.setFlag(QGraphicsItem.ItemIsSelectable, True)
        self.setFlag(QGraphicsItem.ItemIsMovable, False)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges, True)
        self.setAcceptHoverEvents(True)
        
        self.pen_normal = QPen(QColor(0, 150, 215), 2, Qt.DashLine)
        self.pen_highlight = QPen(QColor(255, 215, 0), 4)
        self.pen_selected = QPen(QColor(255, 0, 0), 4)
        self.pen_connected = QPen(QColor(0, 200, 0), 3)
        
        self.setPen(self.pen_normal)
        self.setZValue(5)
        
        # Length label - ALWAYS VISIBLE
        self.length_label = BundleLengthLabel(self)
        self.length_label.setPos((self.start_point + self.end_point) / 2)
        self.length_label.setVisible(True)
        
        # Add workspace units indicator
        self.workspace_label = QGraphicsTextItem("(workspace units)", self)
        self.workspace_label.setFlag(QGraphicsItem.ItemIgnoresTransformations)
        self.workspace_label.setDefaultTextColor(QColor(150, 150, 150))
        self.workspace_label.setFont(QFont("Arial", 6))
        self.workspace_label.setVisible(True)
        
        # State
        self.state = self.NORMAL
        self._is_hovered = False
        self.tree_item = None
        self._updating = False
        
        # Update path and label
        self.update_path()
        self.update_label_text()
    
    def contextMenuEvent(self, event):
        """Handle right-click context menu"""
        from graphics.context_menus import BundleContextMenu
        self.setSelected(True)
        menu = BundleContextMenu(self, self.main_window)
        menu.exec_(event.screenPos())
    
    def set_start_node(self, node, graphics_item=None):
        """Set the start node and optionally its graphics item"""
        self.start_node = node
        if graphics_item:
            self.start_item = graphics_item
        # Update model
        if node:
            self.model.start_node_id = node.id
    
    def set_end_node(self, node, graphics_item=None):
        """Set the end node and optionally its graphics item"""
        self.end_node = node
        if graphics_item:
            self.end_item = graphics_item
        # Update model
        if node:
            self.model.end_node_id = node.id
    
    def update_position_from_nodes(self):
        """Update bundle position based on connected nodes"""
        if self._updating:
            return
        
        self._updating = True
        
        try:
            changed = False
            
            # Update start point from node
            if self.start_node:
                new_start = QPointF(self.start_node.position[0], self.start_node.position[1])
                if self.start_point != new_start:
                    self.start_point = new_start
                    self.model.start_point = (new_start.x(), new_start.y())
                    changed = True
            
            # Update end point from node
            if self.end_node:
                new_end = QPointF(self.end_node.position[0], self.end_node.position[1])
                if self.end_point != new_end:
                    self.end_point = new_end
                    self.model.end_point = (new_end.x(), new_end.y())
                    changed = True
            
            # Update path if anything changed
            if changed:
                self.update_path()
                
                # Update any wires in this bundle
                for wire_id in self.wire_ids:
                    # Find wire graphics and update
                    if self.main_window:
                        wire = self.main_window.get_graphics_item(wire_id, 'wires')
                        if wire and hasattr(wire, 'update_path'):
                            wire.update_path()
        finally:
            self._updating = False

    def update_path(self):
        """Update the bundle path"""
        path = QPainterPath()
        path.moveTo(self.start_point)
        
        if self.end_point:
            # Draw line with slight curve for visibility
            dx = self.end_point.x() - self.start_point.x()
            dy = self.end_point.y() - self.start_point.y()
            distance = math.sqrt(dx*dx + dy*dy)
            self.model.length = distance
            
            if abs(dx) > 50 or abs(dy) > 50:
                # Add slight curve for long bundles
                ctrl_x = (self.start_point.x() + self.end_point.x()) / 2
                ctrl_y = (self.start_point.y() + self.end_point.y()) / 2
                path.quadTo(ctrl_x + dy*0.05, ctrl_y - dx*0.05, 
                           self.end_point.x(), self.end_point.y())
            else:
                path.lineTo(self.end_point)
        
        self.setPath(path)
        
        # Update label position and text
        mid_point = (self.start_point + self.end_point) / 2
        self.length_label.setPos(mid_point)
        self.workspace_label.setPos(mid_point.x(), mid_point.y() + 15)
        
        # Update label rotation
        angle = math.degrees(math.atan2(
            self.end_point.y() - self.start_point.y(), 
            self.end_point.x() - self.start_point.x()
        ))
        angle = angle if -90 <= angle <= 90 else angle + 180
        self.length_label.setRotation(angle)
        
        self.update_label_text()
    
    def update_label_text(self):
        """Update the length label text"""
        if self.specified_length is not None:
            self.length_label.setPlainText(f"{self.specified_length:.0f} mm*")
            self.model.specified_length = self.specified_length
        else:
            self.length_label.setPlainText(f"{self.model.length:.0f} units")
    
    def set_specified_length(self, length: float):
        """Set user-specified length override"""
        self.specified_length = length
        self.model.specified_length = length
        self.update_label_text()
    
    def assign_wire(self, wire_id: str):
        """Assign a wire to this bundle"""
        if wire_id not in self.wire_ids:
            self.wire_ids.append(wire_id)
            self.wire_count = len(self.wire_ids)
            self.model.wire_ids = self.wire_ids.copy()
            self.model.wire_count = self.wire_count
            self.update_appearance()
            
            # Update tree item if exists
            if self.tree_item:
                if self.wire_count > 0:
                    self.tree_item.setForeground(0, Qt.darkGreen)
                else:
                    self.tree_item.setForeground(0, Qt.black)
    
    def assign_wires(self, wire_ids: List[str]):
        """Assign multiple wires to this bundle at once"""
        for wire_id in wire_ids:
            if wire_id not in self.wire_ids:
                self.wire_ids.append(wire_id)
        
        self.wire_count = len(self.wire_ids)
        self.model.wire_ids = self.wire_ids.copy()
        self.model.wire_count = self.wire_count
        self.update_appearance()
        
        # Update tree item
        if self.tree_item:
            if self.wire_count > 0:
                self.tree_item.setForeground(0, Qt.darkGreen)
            else:
                self.tree_item.setForeground(0, Qt.black)
    
    def remove_wire(self, wire_id: str):
        """Remove a wire from this bundle"""
        if wire_id in self.wire_ids:
            self.wire_ids.remove(wire_id)
            self.wire_count = len(self.wire_ids)
            self.model.wire_ids = self.wire_ids.copy()
            self.model.wire_count = self.wire_count
            self.update_appearance()
            
            # Update tree item
            if self.tree_item:
                if self.wire_count > 0:
                    self.tree_item.setForeground(0, Qt.darkGreen)
                else:
                    self.tree_item.setForeground(0, Qt.black)
    
    def get_wire_ids(self) -> List[str]:
        """Get list of wire IDs in this bundle"""
        return self.wire_ids.copy()

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
        
        # Update length label to show wire count
        if hasattr(self, 'length_label'):
            if self.specified_length is not None:
                self.length_label.setPlainText(f"{self.specified_length:.0f} mm* ({self.wire_count})")
            else:
                self.length_label.setPlainText(f"{self.model.length:.0f} units ({self.wire_count})")
    
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
    
    def set_main_window(self, window):
        """Set reference to main window and register"""
        self.main_window = window
        if window:
            window.register_graphics_item(self, 'bundles')
    
    def cleanup(self):
        """Clean up references"""
        # Unregister from main window
        if self.main_window:
            self.main_window.unregister_graphics_item(self, 'bundles')
        
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
        
        # Clear graphics item reference from model
        if self.model:
            self.model.graphics_item = None


class BundleLengthLabel(QGraphicsTextItem):
    """Floating label showing bundle length - always visible"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setFlag(QGraphicsItem.ItemIgnoresTransformations)
        self.setDefaultTextColor(Qt.white)
        self.setFont(QFont("Arial", 8, QFont.Bold))
    
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
