from model.topology_manager import TopologyManager
from graphics.topology_item import (
    JunctionGraphicsItem, BranchPointGraphicsItem, 
    SegmentGraphicsItem
)

from PyQt5.QtWidgets import (
    QApplication, QMainWindow,QGraphicsScene,QToolBar,QAction,QDialog,QVBoxLayout,QLabel,
    QDockWidget,QTreeWidget,QTabWidget,QTreeWidgetItem
    
)
from graphics.schematic_view import SchematicView,PropertiesDock
from graphics.connector_item import ConnectorItem
from graphics.wire_item import SegmentedWireItem
# from graphics.wire_item import WireItem
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
        self.topology_manager = TopologyManager()
        self._create_topology_toolbar()
        # Demo objects
        '''
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
        '''
        
        self.create_harness_example()
        self.refresh_connector_labels()
        self.view._scene.selectionChanged.connect(self.on_scene_selection)
    def create_harness_example(self):
        """Setup demo with topology integration"""
        # Create connectors with topology manager reference
        c1 = ConnectorItem(50, 50, pin_count=2)
        c1.set_topology_manager(self.topology_manager)
        c1.create_topology_node()
        
        c2 = ConnectorItem(300, 150, pin_count=2)
        c2.set_topology_manager(self.topology_manager)
        c2.create_topology_node()
        
        c3 = ConnectorItem(200, 100, pin_count=2)
        c3.set_topology_manager(self.topology_manager)
        c3.create_topology_node()
        
        # Add to scene
        self.scene.addItem(c1)
        self.scene.addItem(c2)
        self.scene.addItem(c3)
        
        # Create a branch point
        from model.topology import BranchPointNode
        bp = BranchPointNode((175, 75), "split")
        self.topology_manager.nodes[bp.id] = bp
        
        # Create segments between nodes
        from model.topology import WireSegment

        
        # C1 -> Branch Point
        seg1 = WireSegment(
            start_node=c1.topology_node,
            end_node=bp,
            wires=[]
        )
        self.topology_manager.segments[seg1.id] = seg1
        seg1_graphics = SegmentGraphicsItem(seg1, self.topology_manager)
        self.scene.addItem(seg1_graphics)
        
        # Branch Point -> C2
        seg2 = WireSegment(
            start_node=bp,
            end_node=c2.topology_node,
            wires=[]
        )
        self.topology_manager.segments[seg2.id] = seg2
        seg2_graphics = SegmentGraphicsItem(seg2, self.topology_manager)
        self.scene.addItem(seg2_graphics)
        
        # Branch Point -> C3
        seg3 = WireSegment(
            start_node=bp,
            end_node=c3.topology_node,
            wires=[]
        )
        self.topology_manager.segments[seg3.id] = seg3
        seg3_graphics = SegmentGraphicsItem(seg3, self.topology_manager)
        self.scene.addItem(seg3_graphics)
        
        # Create wires through topology
        from model.wire import Wire
        
        # Wire 1: C1.P1 -> C2.P1 through branch point
        wire1 = Wire("W1", c1.pins[0], c2.pins[0], "RT")
        wire1.add_segment(seg1)
        wire1.add_segment(seg2)
        seg1.wires.append(wire1)
        seg2.wires.append(wire1)
        
        wire1_graphics = SegmentedWireItem(wire1)
        wire1.graphics_item = wire1_graphics
        self.scene.addItem(wire1_graphics)
        
        # Wire 2: C1.P2 -> C3.P1 through branch point
        wire2 = Wire("W2", c1.pins[1], c3.pins[1], "BL")
        wire2.add_segment(seg1)
        wire2.add_segment(seg3)
        seg1.wires.append(wire2)
        seg3.wires.append(wire2)
        
        wire2_graphics = SegmentedWireItem(wire2)
        wire2.graphics_item = wire2_graphics
        self.scene.addItem(wire2_graphics)
        
        # Store references
        self.connectors = [c1, c2, c3]
        self.wires = [wire1, wire2]
        self.segments = [seg1, seg2, seg3]
        
        # Connect pins
        c1.pins[0].wires.append(wire1_graphics)
        c2.pins[0].wires.append(wire1_graphics)
        c1.pins[1].wires.append(wire2_graphics)
        c3.pins[1].wires.append(wire2_graphics)
        
        # Set main window reference on wire graphics
        wire1_graphics.set_main_window(self)
        wire2_graphics.set_main_window(self)
    def on_connector_moved(self, connector):
        """Handle connector movement updates"""
        if connector.topology_node:
            # Update node position
            connector.topology_node.position = (
                connector.pos().x(), 
                connector.pos().y()
            )
            
            # Update all segments connected to this node
            for segment in self.topology_manager.segments.values():
                if (segment.start_node == connector.topology_node or 
                    segment.end_node == connector.topology_node):
                    if hasattr(segment, 'graphics_item'):
                        segment.graphics_item.update_path()
            
            # Update all wires in connected segments
            for wire in self.wires:
                if hasattr(wire, 'graphics_item'):
                    wire.graphics_item.update_path()
    def _create_topology_toolbar(self):
        """Add topology-specific tools"""
        tb = self.findChild(QToolBar, "Tools")
        if not tb:
            return
            
        # Add branch point tool
        add_branch_btn = QAction("Add Branch Point", self)
        add_branch_btn.triggered.connect(self.add_branch_point)
        tb.addAction(add_branch_btn)
        
        # Add junction tool
        add_junction_btn = QAction("Add Junction", self)
        add_junction_btn.triggered.connect(self.add_junction)
        tb.addAction(add_junction_btn)
        
        # Add split segment tool
        split_segment_btn = QAction("Split Segment", self)
        split_segment_btn.triggered.connect(self.split_segment)
        tb.addAction(split_segment_btn)
        
        # Add wire through nodes tool
        smart_wire_btn = QAction("Smart Wire", self)
        smart_wire_btn.triggered.connect(self.create_smart_wire)
        tb.addAction(smart_wire_btn)
    def add_branch_point(self):
        """Add a branch point at mouse position"""
        pos = self.view.mapToScene(self.view.mapFromGlobal(QCursor.pos()))
        bp_node = self.topology_manager.create_branch_point((pos.x(), pos.y()))
        bp_graphics = BranchPointGraphicsItem(bp_node)
        self.scene.addItem(bp_graphics)
        
    def add_junction(self):
        """Add a junction at mouse position"""
        pos = self.view.mapToScene(self.view.mapFromGlobal(QCursor.pos()))
        junction_node = self.topology_manager.create_junction((pos.x(), pos.y()))
        junction_graphics = JunctionGraphicsItem(junction_node)
        self.scene.addItem(junction_graphics)
        
    def split_segment(self):
        """Split selected segment at mouse position"""
        selected = self.scene.selectedItems()
        if len(selected) != 1:
            return
            
        item = selected[0]
        if isinstance(item, SegmentGraphicsItem):
            pos = self.view.mapToScene(self.view.mapFromGlobal(QCursor.pos()))
            new_segments = self.topology_manager.split_segment(
                item.segment, 
                (pos.x(), pos.y())
            )
            
            # Update graphics
            self.scene.removeItem(item)
            for seg in new_segments:
                seg_graphics = SegmentGraphicsItem(seg)
                self.scene.addItem(seg_graphics)
                
    def create_smart_wire(self):
        """Create a wire that goes through selected nodes"""
        selected = self.scene.selectedItems()
        if len(selected) < 2:
            return
            
        # Sort: connector -> nodes -> connector
        connectors = [item for item in selected if isinstance(item, ConnectorItem)]
        nodes = [item for item in selected if isinstance(item, (JunctionGraphicsItem, BranchPointGraphicsItem))]
        
        if len(connectors) != 2:
            QMessageBox.warning(self, "Error", "Select exactly 2 connectors")
            return
            
        # Get pins (for now, use first pin of each)
        from_pin = connectors[0].pins[0]
        to_pin = connectors[1].pins[0]
        
        # Get node objects
        via_nodes = []
        for node_item in nodes:
            if isinstance(node_item, JunctionGraphicsItem):
                via_nodes.append(node_item.junction_node)
            elif isinstance(node_item, BranchPointGraphicsItem):
                via_nodes.append(node_item.branch_node)
        
        # Create wire through topology
        wire = self.topology_manager.create_wire_path(from_pin, to_pin, via_nodes)
        
        # Create graphics
        wire_graphics = SegmentedWireItem(wire)
        self.scene.addItem(wire_graphics)
        
        # Add to wires tree
        item = QTreeWidgetItem([wire.id])
        item.setData(0, Qt.UserRole, wire_graphics)
        self.wires_tree.addTopLevelItem(item)
        wire_graphics.tree_item = item
        
    def refresh_topology_view(self):
        """Refresh all topology graphics"""
        # Clear existing segment graphics
        for item in self.scene.items():
            if isinstance(item, SegmentGraphicsItem):
                self.scene.removeItem(item)
        
        # Recreate segment graphics
        for segment in self.topology_manager.segments.values():
            seg_graphics = SegmentGraphicsItem(segment)
            segment.graphics_item = seg_graphics
            self.scene.addItem(seg_graphics)
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