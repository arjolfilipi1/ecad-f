

from PyQt5.QtWidgets import (
    QApplication, QMainWindow,QGraphicsScene,QToolBar,QAction,QDialog,QVBoxLayout,QLabel
    
)
from graphics.schematic_view import SchematicView,PropertiesDock
from graphics.connector_item import ConnectorItem
from graphics.wire_item import WireItem
from model.netlist import Netlist
import sys
from PyQt5.QtCore import Qt,QFile, QTextStream




class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.undo_stack = []
        self.redo_stack = []
        self.scene = QGraphicsScene(-2000, -2000, 4000, 4000)
        self.view = SchematicView(self.scene)
        self.setCentralWidget(self.view)

        self.props = PropertiesDock()
        self.addDockWidget(Qt.RightDockWidgetArea, self.props)

        self.view._scene.selectionChanged.connect(self.on_selection)
        self._create_toolbar()
        netlist = Netlist()
        self.conns =[]
        self.wires = []
        net = Netlist()
        # Demo objects
        c1 = ConnectorItem("C1", 50, 50)
        c2 = ConnectorItem("C2", 300, 150)
        
        self.view._scene.addItem(c1)
        self.view._scene.addItem(c2)
        net =netlist.connect(c1.pins[0], c2.pins[0])
        w1 = WireItem("W1", c1.pins[0], c2.pins[0],"SW")
        net =netlist.connect(c1.pins[1], c2.pins[1])
        w2 = WireItem("W2", c1.pins[1], c2.pins[1],"GE")
        self.wires.append(w1)
        self.wires.append(w2)
        self.conns.append(c1)
        self.conns.append(c2)
        self.view._scene.addItem(w1)
        self.view._scene.addItem(w2)
        self.refresh_connector_labels()
    def on_selection(self):
        items = self.view._scene.selectedItems()
        if items:
            self.props.widget.set_item(items[0])
        else:
            self.props.widget.set_item(None)
    def refresh_connector_labels(self):
        for item in self.conns:
            if isinstance(item, ConnectorItem):
                item.info.update_text()
    
    def _create_toolbar(self):
        tb = QToolBar("Tools")
        self.addToolBar(tb)
        add_connetor = QAction("Add connetor", self)
        add_connetor.triggered.connect(self.show_custom_dialog)
        tb.addAction(add_connetor)
        add_wire = QAction("Add Wire", self)
        add_wire.triggered.connect(self.add_wire)
        tb.addAction(add_wire)
    def show_custom_dialog(self):
        # 3. Create and execute the Dialog
        dialog = QDialog(self)
        dialog.setWindowTitle("Settings Dialog")
        
        # Add some content to the dialog
        layout = QVBoxLayout()
        layout.addWidget(QLabel("Configure your view settings here."))
        dialog.setLayout(layout)
        
        # .exec_() runs the dialog modally (it must be closed before returning to main window)
        dialog.exec_()
    def add_wire(self):
        print("add wire")

app = QApplication(sys.argv)
window = MainWindow()
window.resize(800, 600)
window.show()
sys.exit(app.exec_())