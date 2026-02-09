

from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QGraphicsView, QGraphicsScene,
    QGraphicsLineItem, QGraphicsEllipseItem, QToolBar, QAction,
    QWidget,QDockWidget,QFormLayout,QLineEdit
    
)
from PyQt5.QtCore import QRectF
from PyQt5.QtGui import QPen, QBrush, QPainter
import sys
from PyQt5.QtCore import Qt
class ConnectorItem(QGraphicsEllipseItem):
    def __init__(self, cid, x, y, radius=10):
        super().__init__(-radius, -radius, radius*2, radius*2)
        self.cid = cid
        self.wires = []

        self.setBrush(QBrush())
        self.setFlag(self.ItemIsMovable)
        self.setFlag(self.ItemIsSelectable)
        self.setFlag(self.ItemSendsGeometryChanges)

        self.setPos(x, y)

    def add_wire(self, wire):
        self.wires.append(wire)

    def itemChange(self, change, value):
        if change == self.ItemPositionChange:
            for wire in self.wires:
                wire.update_position()
        return super().itemChange(change, value)
from PyQt5.QtWidgets import QGraphicsLineItem
from PyQt5.QtGui import QPen
from PyQt5.QtCore import QLineF

class WireItem(QGraphicsLineItem):
    def __init__(self, wid, start_connector, end_connector):
        super().__init__()
        self.wid = wid
        self.start = start_connector
        self.end = end_connector

        self.setPen(QPen())
        self.setFlag(self.ItemIsSelectable)

        self.start.add_wire(self)
        self.end.add_wire(self)

        self.update_position()

    def update_position(self):
        line = QLineF(
            self.start.scenePos(),
            self.end.scenePos()
        )
        self.setLine(line)
        
        
class SchematicView(QGraphicsView):
    def __init__(self):
        self._scene = QGraphicsScene()
        super().__init__(scene)
        self.setRenderHints(self.renderHints() | QPainter.Antialiasing)

    @property
    def scene(self):
        return self.graphicsScene()
        
class PropertiesWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.layout = QFormLayout(self)
        self.current_item = None

        self.id_edit = QLineEdit()
        self.layout.addRow("ID", self.id_edit)

        self.id_edit.textChanged.connect(self.update_item)

    def set_item(self, item):
        self.current_item = item
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
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.view = SchematicView()
        self.setCentralWidget(self.view)

        self.props = PropertiesDock()
        self.addDockWidget(Qt.RightDockWidgetArea, self.props)

        self.view.scene.selectionChanged.connect(self.on_selection)

        # Demo objects
        c1 = ConnectorItem("C1", 50, 50)
        c2 = ConnectorItem("C2", 300, 150)

        self.view.scene.addItem(c1)
        self.view.scene.addItem(c2)

        w1 = WireItem("W1", c1, c2)
        self.view.scene.addItem(w1)

    def on_selection(self):
        items = self.view.scene.selectedItems()
        if items:
            self.props.widget.set_item(items[0])
        else:
            self.props.widget.set_item(None)

app = QApplication(sys.argv)
window = MainWindow()
window.resize(800, 600)
window.show()
sys.exit(app.exec_())