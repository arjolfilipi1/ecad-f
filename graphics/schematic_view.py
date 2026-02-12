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
        self.setDragMode(QGraphicsView.ScrollHandDrag)
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
    def mousePressEvent(self, event):
        item = self.itemAt(event.pos())
        if isinstance(item, PinItem):
            self.active_pin = item
            print("pin selected")
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        item = self.itemAt(event.pos())
        if isinstance(item, PinItem) and self.active_pin:
            wire = WireItem("W_NEW", self.active_pin, item)
            self.scene().addItem(wire)
            self.netlist.connect(self.active_pin, item)
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
        pos = self.mapToScene(event.pos())

        if self.current_tool == Tool.ADD_CONNECTOR:
            c = ConnectorItem( pos.x(), pos.y(), pin_count=2)
            item = QTreeWidgetItem([c.cid])
            item.setData(0, Qt.UserRole, c)

            self.parent.connectors_tree.addTopLevelItem(item)
            c.tree_item = item

            self.scene().addItem(c)

        elif self.current_tool == Tool.ADD_WIRE:
            item = self.scene().itemAt(pos, self.transform())
            if isinstance(item, PinItem):
                self.handle_wire_drawing(item)

        else:
            super().mousePressEvent(event)
    
from PyQt5.QtWidgets import QWidget, QFormLayout, QLineEdit

class PropertiesWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.layout = QFormLayout(self)
        self.current_item = None
        self.type_label = QLabel("")
        self.id_edit = QLineEdit()
        self.layout.addRow("Type", self.type_label)
        self.layout.addRow("ID", self.id_edit)

        self.id_edit.textChanged.connect(self.update_item)

    def set_item(self, item):
        self.current_item = item
        self.type_label.setText(str(type(item)))
        if hasattr(item, "cid"):
            self.id_edit.setText(item.cid)
        elif hasattr(item, "wid"):
            self.id_edit.setText(item.wid)

    def update_item(self, text):
        if self.current_item:
            if hasattr(self.current_item, "cid"):
                self.current_item.cid = text
            elif hasattr(self.current_item, "wid"):
                self.current_item.wid = text





class PropertiesDock(QDockWidget):
    def __init__(self):
        super().__init__("Properties")
        self.widget = PropertiesWidget()
        self.setWidget(self.widget)
        
