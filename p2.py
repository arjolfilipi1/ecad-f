

from PyQt5.QtWidgets import (
    QApplication, QMainWindow,QGraphicsScene,QToolBar,QAction,QDialog,QVBoxLayout,QLabel,
    QDockWidget,QTreeWidget,QTabWidget,QTreeWidgetItem
    
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
        self.view = SchematicView(self.scene,self)
        self.setCentralWidget(self.view)
        self.objects_dock = QDockWidget("Objects", self)
        self.objects_tabs = QTabWidget()
        self.objects_tabs.setTabsClosable(False)
        #connector tree
        self.connectors_tree = QTreeWidget()
        self.connectors_tree.setHeaderLabels(["Connector"])
        self.connectors_tree.itemClicked.connect(self.on_tree_clicked)
        #connector tree
        self.wires_tree = QTreeWidget()
        self.wires_tree.setHeaderLabels(["Wire"])
        self.wires_tree.itemClicked.connect(self.on_tree_clicked)
        self.objects_tabs.addTab(self.connectors_tree, "Connectors")
        self.objects_tabs.addTab(self.wires_tree, "Wires")

        self.objects_dock.setWidget(self.objects_tabs)
        self.addDockWidget(Qt.LeftDockWidgetArea, self.objects_dock)
        
        self.show_props()
        self.view._scene.selectionChanged.connect(self.on_selection)
        self._create_toolbar()
        netlist = Netlist()
        self.conns =[]
        self.wires = []
        net = Netlist()
        # Demo objects
        c1 = ConnectorItem( 50, 50)
        item = QTreeWidgetItem([c1.cid])
        item.setData(0, Qt.UserRole, c1)

        self.connectors_tree.addTopLevelItem(item)
        c1.tree_item = item
        c2 = ConnectorItem( 300, 150)
        item = QTreeWidgetItem([c2.cid])
        item.setData(0, Qt.UserRole, c2)

        self.connectors_tree.addTopLevelItem(item)
        c2.tree_item = item
        c3 = ConnectorItem( 200, 100)
        item = QTreeWidgetItem([c3.cid])
        item.setData(0, Qt.UserRole, c3)
        self.connectors_tree.addTopLevelItem(item)
        c3.tree_item = item
        self.view._scene.addItem(c1)
        self.view._scene.addItem(c2)
        self.view._scene.addItem(c3)
        net =netlist.connect(c1.pins[0], c2.pins[0])
        w1 = WireItem( net ,self.view._scene)
        item = QTreeWidgetItem([w1.wid])
        item.setData(0, Qt.UserRole, w1)
        self.wires_tree.addTopLevelItem(item)
        w1.tree_item = item
        net =netlist.connect(c1.pins[1], c3.pins[1])
        w2 = WireItem("W2", c1.pins[1], c3.pins[1],"GE",net)
        item = QTreeWidgetItem([w2.wid])
        item.setData(0, Qt.UserRole, w2)
        self.wires_tree.addTopLevelItem(item)
        w2.tree_item = item
        net =netlist.connect(c3.pins[0], c2.pins[1])
        w3 = WireItem("W3", c3.pins[0], c2.pins[1],"GN",net)
        item = QTreeWidgetItem([w3.wid])
        item.setData(0, Qt.UserRole, w3)
        self.wires_tree.addTopLevelItem(item)
        w3.tree_item = item
        self.wires.append(w1)
        self.wires.append(w2)
        self.wires.append(w3)
        self.conns.append(c1)
        self.conns.append(c2)
        self.conns.append(c3)
        self.view._scene.addItem(w1)
        self.view._scene.addItem(w2)
        self.view._scene.addItem(w3)
        self.refresh_connector_labels()
        self.view._scene.selectionChanged.connect(self.on_scene_selection)
    def on_scene_selection(self):
        items = self.view.scene().selectedItems()
        if not items:
            return

        obj = items[0]
        if hasattr(obj, "tree_item") and obj.tree_item:
            tree = obj.tree_item.treeWidget()
            tree.setCurrentItem(obj.tree_item)

    def on_tree_clicked(self, item):
        obj = item.data(0, Qt.UserRole)
        if obj:
            self.view.scene().clearSelection()
            obj.setSelected(True)
            self.view.centerOn(obj)

    def show_props(self):
        self.props = PropertiesDock()
        self.addDockWidget(Qt.RightDockWidgetArea, self.props)
    def on_selection(self):
        items = self.view._scene.selectedItems()
        if items:
            self.props.widget.set_item(items[0])
        else:
            self.props.widget.set_item(None)
    def toggle_connector_info(self):
        for item in self.scene.items():
            if isinstance(item, ConnectorItem):
                visible = item.info.isVisible()
                item.info.setVisible(not visible)

    def refresh_connector_labels(self):
        for item in self.conns:
            if isinstance(item, ConnectorItem):
                item.info.update_text()
    def split_segment(segment, split_pos):
        p1 = segment.line().p1()
        p2 = segment.line().p2()

        # Remove old segment
        scene.removeItem(segment)

        # Create junction
        junction = JunctionItem(split_pos)
        scene.addItem(junction)

        # Create two new segments
        s1 = WireSegmentItem(p1, split_pos, segment.net)
        s2 = WireSegmentItem(split_pos, p2, segment.net)

        scene.addItem(s1)
        scene.addItem(s2)

    def _create_toolbar(self):
        tb = QToolBar("Tools")

        tb.addActions(self.view.tool_group.actions())
        self.addToolBar(tb)
        add_connetor = QAction("Add connetor", self)
        add_connetor.triggered.connect(self.show_custom_dialog)
        tb.addAction(add_connetor)
        rotate = QAction("rotate", self)
        rotate.triggered.connect(self.rotate)
        tb.addAction(rotate)
        toggle_connector_info = QAction("Toggle connector info", self)
        toggle_connector_info.triggered.connect(self.toggle_connector_info)
        tb.addAction(toggle_connector_info)
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
    def rotate(self):
        items = self.view.scene().selectedItems()
        for item in items:
            if getattr(item, "rotate_90", None):
                item.rotate_90()
        

app = QApplication(sys.argv)
window = MainWindow()
window.resize(800, 600)
window.show()
sys.exit(app.exec_())