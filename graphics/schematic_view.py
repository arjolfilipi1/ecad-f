#graphics/schematic_view
from PyQt5.QtWidgets import QGraphicsView, QGraphicsScene,QLabel,QDialog,QAction,QActionGroup,QTreeWidgetItem
from PyQt5.QtWidgets import QDockWidget
from PyQt5.QtGui import QPen, QBrush, QPainter
from .pin_item import PinItem
# from .wire_item import WireItem
from PyQt5.QtCore import Qt, QPointF, QLineF
from .connector_item import ConnectorItem
from enum import Enum

class Tool(Enum):
    SELECT = 0
    ADD_CONNECTOR = 1
    ADD_WIRE = 2


class SchematicView(QGraphicsView):
    GRID = 50
    def __init__(self,scene,parent):
        super().__init__(scene)
        self.parent = parent
        self.setRenderHint(QPainter.Antialiasing)
        self.setDragMode(QGraphicsView.RubberBandDrag)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorUnderMouse)
        self._scene = scene
        self.tool_label = QLabel("SELECT", self)
        self.tool_label.setStyleSheet("""
            QLabel {
                background-color: rgba(0, 0, 0, 150);
                color: white;
                padding: 5px;
                border-radius: 5px;
                font-weight: bold;
            }
        """)
        self.tool_label.resize(150, 20)
        self.current_tool = Tool.SELECT
        self._current_zoom = 1.0
        self.active_pin = None
        # Initialize the Overlay Label
        self.setup_ui_overlay()
        self.create_actions()
        self.bundle_select_mode = False
        self.panning = False
        self.last_pan_point = None
    def keyPressEvent(self, event):
        """Handle key press events"""
        if event.key() == Qt.Key_Delete or event.key() == Qt.Key_Backspace:
            # Delete selected bundles
            selected = self.scene().selectedItems()
            bundles = [item for item in selected if hasattr(item, 'bundle_id')]
            
            if bundles and hasattr(self.parent, 'delete_selected_bundles'):
                self.parent.delete_selected_bundles()
                event.accept()
                return
        
        super().keyPressEvent(event)

    def resizeEvent(self, event):
        # Reposition the label when the window is resized
        super().resizeEvent(event)
        self.update_label_position()

    def wheelEvent(self, event):
        zoom_in_factor = 1.25
        zoom_out_factor = 1 / zoom_in_factor

        if event.angleDelta().y() > 0:
            zoom_factor = zoom_in_factor
        else:
            zoom_factor = zoom_out_factor

        # Calculate new zoom level
        self._current_zoom *= zoom_factor

        # Apply scaling and update label
        self.scale(zoom_factor, zoom_factor)
        self.scale_label.setText(f"Zoom: {int(self._current_zoom * 100)}%")
        self.scale_label.adjustSize()
        self.update_label_position()
    def setup_ui_overlay(self):
        # Create label and style it
        self.scale_label = QLabel("Zoom: 100%", self)
        self.scale_label.setStyleSheet("""
            QLabel {
                background-color: rgba(0, 0, 0, 150);
                color: white;
                padding: 5px;
                border-radius: 5px;
                font-weight: bold;
            }
        """)
        self.update_label_position()
    def update_label_position(self):
        # Keep the label at the bottom-left corner
        margin = 30
        self.scale_label.move(margin, self.height() - self.scale_label.height() - margin)
    def drawBackground(self, painter, rect):
        painter.setPen(QPen(Qt.lightGray, 0))

        left = rect.left() - (rect.left() % self.GRID)
        top = rect.top() - (rect.top() % self.GRID)

        x = left
        while x < rect.right():
            painter.drawLine(QLineF(x, rect.top(), x, rect.bottom()))
            x += self.GRID

        y = top
        while y < rect.bottom():
            painter.drawLine(QLineF(rect.left(), y, rect.right(), y))
            y += self.GRID

        # origin cross
        painter.setPen(QPen(Qt.red, 1))
        painter.drawLine(QLineF(-20, 0, 20, 0))
        painter.drawLine(QLineF(0, -20, 0, 20))
    def set_tool(self, tool):
        self.current_tool = tool
        self.tool_label.setText(str(tool.name))

    def mouseReleaseEvent(self, event):
        """Handle mouse release for panning"""
        if event.button() == Qt.MiddleButton:
            # Stop panning
            self.panning = False
            self.setCursor(Qt.ArrowCursor)
            event.accept()
            return
        
        # Handle wire creation on release
        if event.button() == Qt.LeftButton and self.active_pin:
            pos = self.mapToScene(event.pos())
            item = self.scene().itemAt(pos, self.transform())
            if isinstance(item, PinItem) and self.active_pin != item:
                # Create wire between pins
                wire = WireItem("W_NEW", self.active_pin, item)
                self.scene().addItem(wire)
                # self.netlist.connect(self.active_pin, item)  # Uncomment if netlist exists
            self.active_pin = None
        
        super().mouseReleaseEvent(event)

    def create_actions(self):
        self.act_select = QAction("Select", self, checkable=True)
        self.act_add_connector = QAction("Add Connector", self, checkable=True)
        self.act_add_wire = QAction("Add Wire", self, checkable=True)

        self.act_select.triggered.connect(
            lambda: self.set_tool(Tool.SELECT)
        )
        self.act_add_connector.triggered.connect(
            lambda: self.set_tool(Tool.ADD_CONNECTOR)
        )
        self.act_add_wire.triggered.connect(
            lambda: self.set_tool(Tool.ADD_WIRE)
        )

        self.tool_group = QActionGroup(self)
        for a in (self.act_select, self.act_add_connector, self.act_add_wire):
            self.tool_group.addAction(a)

        self.act_select.setChecked(True)
    def mousePressEvent(self, event):
        """Handle mouse press for panning and other tools"""
        if event.button() == Qt.MiddleButton:
            # Start panning
            self.panning = True
            self.last_pan_point = event.pos()
            self.setCursor(Qt.ClosedHandCursor)
            event.accept()
            return
        
        # Handle left button for tools
        pos = self.mapToScene(event.pos())
        
        if event.button() == Qt.LeftButton:
            if self.current_tool == Tool.ADD_CONNECTOR:
                # Add connector
                c = ConnectorItem(pos.x(), pos.y(), pins=[1, 2])
                c.set_topology_manager(self.parent.topology_manager)
                c.set_main_window(self.parent)
                c.create_topology_node()
                
                # Add to tree
                item = QTreeWidgetItem([c.cid])
                item.setData(0, Qt.UserRole, c)
                self.parent.connectors_tree.addTopLevelItem(item)
                c.tree_item = item
                
                # Add with undo
                self.parent.add_connector_with_undo(c, pos)
                self.scene().addItem(c)
                event.accept()
                return
            
            elif self.current_tool == Tool.ADD_WIRE:
                # Check if clicking on a pin
                item = self.scene().itemAt(pos, self.transform())
                if isinstance(item, PinItem):
                    self.active_pin = item
                    print("pin selected")
        
        # Pass other events to parent
        super().mousePressEvent(event)
    def mouseMoveEvent(self, event):
        """Handle mouse move for panning"""
        if self.panning:
            # Pan the view
            delta = event.pos() - self.last_pan_point
            self.last_pan_point = event.pos()
            
            # Scroll by the delta
            self.horizontalScrollBar().setValue(
                self.horizontalScrollBar().value() - delta.x()
            )
            self.verticalScrollBar().setValue(
                self.verticalScrollBar().value() - delta.y()
            )
            event.accept()
            return
        
        # Pass other move events to parent
        super().mouseMoveEvent(event)

    def set_grid_visible(self, visible: bool):
        """Set grid visibility"""
        self._show_grid = visible
        self.update()
    
    def set_grid_size(self, size: int):
        """Set grid spacing"""
        self.GRID = size
        self.update()
    
    def drawBackground(self, painter, rect):
        """Draw background with grid"""
        if not hasattr(self, '_show_grid') or self._show_grid:
            # Your existing grid drawing code
            painter.setPen(QPen(Qt.lightGray, 0))
            
            left = rect.left() - (rect.left() % self.GRID)
            top = rect.top() - (rect.top() % self.GRID)
            
            x = left
            while x < rect.right():
                painter.drawLine(QLineF(x, rect.top(), x, rect.bottom()))
                x += self.GRID
            
            y = top
            while y < rect.bottom():
                painter.drawLine(QLineF(rect.left(), y, rect.right(), y))
                y += self.GRID
        
        # Always draw origin cross
        painter.setPen(QPen(Qt.red, 1))
        painter.drawLine(QLineF(-20, 0, 20, 0))
        painter.drawLine(QLineF(0, -20, 0, 20))

from PyQt5.QtWidgets import QWidget, QFormLayout, QLineEdit

