#main.py
from model.topology_manager import TopologyManager
from graphics.topology_item import (
    JunctionGraphicsItem, BranchPointGraphicsItem
)
from graphics.segment_item import SegmentGraphicsItem
from PyQt5.QtWidgets import (
    QApplication, QMainWindow,QGraphicsScene,QToolBar,QAction,QDialog,QVBoxLayout,QLabel,
    QDockWidget,QTreeWidget,QTabWidget,QTreeWidgetItem,QFileDialog,QGraphicsItem
    
)
from PyQt5.QtGui import QCursor,QPainter
from graphics.schematic_view import SchematicView
from graphics.connector_item import ConnectorItem
from graphics.wire_item import SegmentedWireItem,WireItem
# from graphics.wire_item import WireItem
from model.netlist import Netlist
import sys
from PyQt5.QtCore import Qt,QFile, QTextStream

from graphics.visualization_manager import VisualizationManager,VisualizationMode


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
        netlist = Netlist()
        self.conns =[]
        self.wires = []
        net = Netlist()
        self.topology_manager = TopologyManager()
        from utils.update_dispatcher import UpdateDispatcher
        self.update_dispatcher = UpdateDispatcher()
        self.update_dispatcher.connector_moved.connect(self.on_connector_moved)
        self.update_dispatcher.connector_rotated.connect(self.on_connector_moved)
        
        self.viz_manager = VisualizationManager(self)
        self._create_main_toolbar()      # Basic editing tools
        self._create_topology_toolbar()   # Topology/routing tools
        self._create_import_toolbar()     # Import/export tools
        self._create_view_toolbar()       # Visualization tools
        
        # Arrange toolbars in rows (default behavior)
        self.addToolBarBreak()  # This forces next toolbar to new row
        self._create_edit_toolbar()       # Edit operations

        # Initialize settings manager
        from utils.settings_manager import SettingsManager
        self.settings_manager = SettingsManager()
        self._create_tools_menu()
        # Apply theme
        self.setStyleSheet(self.settings_manager.get_theme_stylesheet())


        # Demo objects
        
        # self.create_harness_example()
        self.refresh_connector_labels()
        self.view._scene.selectionChanged.connect(self.on_scene_selection)
    def undo(self):
        """Undo last operation"""
        if hasattr(self, 'undo_stack') and self.undo_stack:
            command = self.undo_stack.pop()
            command.undo()
            self.redo_stack.append(command)
    
    def redo(self):
        """Redo last undone operation"""
        if hasattr(self, 'redo_stack') and self.redo_stack:
            command = self.redo_stack.pop()
            command.redo()
            self.undo_stack.append(command)
    
    def select_all(self):
        """Select all items in scene"""
        for item in self.scene.items():
            if item.flags() & QGraphicsItem.ItemIsSelectable:
                item.setSelected(True)
    
    def clear_selection(self):
        """Clear all selections"""
        for item in self.scene.items():
            item.setSelected(False)

    def _create_view_toolbar(self):
        """View and visualization tools (row 2, after import)"""
        toolbar = QToolBar("View Tools")
        toolbar.setObjectName("ViewToolBar")
        toolbar.setMovable(True)
        
        # Use the visualization manager's toolbar creation
        if hasattr(self, 'viz_manager'):
            # Add visualization toggles
            viz_actions = self.viz_manager.create_toolbar_actions()
            for action in viz_actions:
                toolbar.addAction(action)
        
        self.addToolBar(toolbar)
        return toolbar
    
    def _create_edit_toolbar(self):
        """Edit operations toolbar (row 3)"""
        self.addToolBarBreak()
        
        toolbar = QToolBar("Edit Tools")
        toolbar.setObjectName("EditToolBar")
        toolbar.setMovable(True)
        
        # Undo/Redo
        undo_act = QAction("↩ Undo", self)
        undo_act.triggered.connect(self.undo)
        toolbar.addAction(undo_act)
        
        redo_act = QAction("↪ Redo", self)
        redo_act.triggered.connect(self.redo)
        toolbar.addAction(redo_act)
        
        toolbar.addSeparator()
        
        # Selection tools
        select_all = QAction("🔲 Select All", self)
        select_all.triggered.connect(self.select_all)
        toolbar.addAction(select_all)
        
        clear_sel = QAction("❌ Clear Selection", self)
        clear_sel.triggered.connect(self.clear_selection)
        toolbar.addAction(clear_sel)
        
        self.addToolBar(toolbar)
        return toolbar

    def _create_import_toolbar(self):
        """Import and routing tools (row 2)"""
        # Add toolbar break to start new row
        self.addToolBarBreak()
        
        toolbar = QToolBar("Import & Routing")
        toolbar.setObjectName("ImportToolBar")
        toolbar.setMovable(True)
        
        # Import button
        import_btn = QAction("📥 Import Excel", self)
        import_btn.triggered.connect(self.import_from_excel)
        toolbar.addAction(import_btn)
        
        # Auto-route button
        route_btn = QAction("🔄 Create Branches", self)
        route_btn.triggered.connect(self.auto_route_wires)
        toolbar.addAction(route_btn)
        
        # Clear topology button
        clear_btn = QAction("🗑️ Clear Topology", self)
        clear_btn.triggered.connect(self.clear_topology)
        toolbar.addAction(clear_btn)

        self.addToolBar(toolbar)
        return toolbar


    def create_harness_example(self):
        """Create a T-configuration harness with proper topology"""
    
        # Set netlist in topology manager
        from model.netlist import Netlist
        self.netlist = Netlist()
        self.topology_manager.set_netlist(self.netlist)
        
        # 1. CREATE CONNECTORS
        c1 = ConnectorItem(100, 200, pin_count=3)  # Left
        c2 = ConnectorItem(500, 100, pin_count=3)  # Top right
        c3 = ConnectorItem(500, 300, pin_count=3)  # Bottom right
        
        # Setup topology for connectors
        c1.set_topology_manager(self.topology_manager)
        c2.set_topology_manager(self.topology_manager)
        c3.set_topology_manager(self.topology_manager)
        c1.set_main_window(self)
        c2.set_main_window(self)
        c3.set_main_window(self)
        
        # Create topology nodes
        c1.create_topology_node()
        c2.create_topology_node()
        c3.create_topology_node()
        
        # Add to scene
        self.scene.addItem(c1)
        self.scene.addItem(c2)
        self.scene.addItem(c3)
        
        # 2. CREATE BRANCH POINT (T-junction)
        bp_pos = (300, 200)  # Between connectors
        bp_node = self.topology_manager.create_branch_point(bp_pos, "split")
        bp_graphics = BranchPointGraphicsItem(bp_node)
        self.scene.addItem(bp_graphics)
        
        # 3. CREATE SEGMENTS (The "roads")
        # Main trunk: C1 to Branch Point
        seg1 = self.topology_manager.create_segment(c1.topology_node, bp_node)
        seg1_graphics = SegmentGraphicsItem(seg1, self.topology_manager)
        self.scene.addItem(seg1_graphics)
        
        # Branch to C2
        seg2 = self.topology_manager.create_segment(bp_node, c2.topology_node)
        seg2_graphics = SegmentGraphicsItem(seg2, self.topology_manager)
        self.scene.addItem(seg2_graphics)
        
        # Branch to C3
        seg3 = self.topology_manager.create_segment(bp_node, c3.topology_node)
        seg3_graphics = SegmentGraphicsItem(seg3, self.topology_manager)
        self.scene.addItem(seg3_graphics)
        
        # Store segments for later use
        self.segments = [seg1, seg2, seg3]
        
        # 4. CREATE WIRES (The "vehicles")
        # Wire 1: C1 Pin1 to C2 Pin1 (through branch point)
        wire1 = self.topology_manager.route_wire(c1.pins[0], c2.pins[0], [bp_node])
        
        # Wire 2: C1 Pin2 to C3 Pin2 (through branch point)
        wire2 = self.topology_manager.route_wire(c1.pins[1], c3.pins[1], [bp_node])
        
        # Wire 3: C1 Pin3 to C2 Pin3 (through branch point)
        wire3 = self.topology_manager.route_wire(c1.pins[2], c2.pins[2], [bp_node])
        
        # Wire 4: C1 Pin3 to C3 Pin3 (same pin, through branch point)
        wire4 = self.topology_manager.route_wire(c1.pins[2], c3.pins[2], [bp_node])
        
        # Create graphics for wires
        self.wire_graphics = []
        
        if wire1:
            from graphics.wire_item import SegmentedWireItem
            w1g = SegmentedWireItem(wire1)
            w1g.set_main_window(self)
            self.scene.addItem(w1g)
            wire1.graphics_item = w1g
            c1.pins[0].wires.append(w1g)
            c2.pins[0].wires.append(w1g)
            self.wire_graphics.append(w1g)
        
        if wire2:
            from graphics.wire_item import SegmentedWireItem
            w2g = SegmentedWireItem(wire2)
            w2g.set_main_window(self)
            self.scene.addItem(w2g)
            wire2.graphics_item = w2g
            c1.pins[1].wires.append(w2g)
            c3.pins[1].wires.append(w2g)
            self.wire_graphics.append(w2g)
        
        if wire3:
            from graphics.wire_item import SegmentedWireItem
            w3g = SegmentedWireItem(wire3)
            w3g.set_main_window(self)
            self.scene.addItem(w3g)
            wire3.graphics_item = w3g
            c1.pins[2].wires.append(w3g)
            c2.pins[2].wires.append(w3g)
            self.wire_graphics.append(w3g)
        
        if wire4:
            from graphics.wire_item import SegmentedWireItem
            w4g = SegmentedWireItem(wire4)
            w4g.set_main_window(self)
            self.scene.addItem(w4g)
            wire4.graphics_item = w4g
            c1.pins[2].wires.append(w4g)  # Same pin, second wire
            c3.pins[2].wires.append(w4g)
            self.wire_graphics.append(w4g)
        
        # Store references
        self.conns = [c1, c2, c3]
        self.wires = []
        if wire1: self.wires.append(wire1)
        if wire2: self.wires.append(wire2)
        if wire3: self.wires.append(wire3)
        if wire4: self.wires.append(wire4)
        
        # Add to tree views
        self.refresh_tree_views()
        

    def refresh_tree_views(self):
        """Refresh tree widget contents - ONLY SHOW CONNECTORS AND ROUTED WIRES"""
        self.connectors_tree.clear()
        self.wires_tree.clear()
        
        # Show connectors
        for conn in self.conns:
            item = QTreeWidgetItem([conn.cid])
            item.setData(0, Qt.UserRole, conn)
            self.connectors_tree.addTopLevelItem(item)
            conn.tree_item = item
        
        # Show ONLY ROUTED WIRES (SegmentedWireItem), NOT direct WireItem
        if hasattr(self, 'routed_wire_items'):
            for wire_graphics in self.routed_wire_items:
                if hasattr(wire_graphics, 'wire') and wire_graphics.wire:
                    item = QTreeWidgetItem([wire_graphics.wire.id])
                    item.setData(0, Qt.UserRole, wire_graphics)
                    self.wires_tree.addTopLevelItem(item)
                    wire_graphics.tree_item = item

    
    def on_scene_selection(self):
        """Handle scene selection - select corresponding tree item"""
        items = self.view.scene().selectedItems()
        if not items:
            return

        obj = items[0]
        if hasattr(obj, "tree_item") and obj.tree_item:
            tree = obj.tree_item.treeWidget()
            tree.setCurrentItem(obj.tree_item)
            
            # If it's a connector, show its pins
            if isinstance(obj, ConnectorItem):
                print(f"\nSelected {obj.cid}:")
                for pin in obj.pins:
                    pos = pin.scene_position()
                    print(f"  {pin.pid} at {pos}")
    def _create_test_menu(self):
        import_action = QAction("test", self)
        import_action.triggered.connect(self.delete_wires)
        self.toolbar.addAction(import_action)
    def delete_wires(self):
        print("test")
        for w in self.imported_wire_items:
            print(str(type(w)),w.wid)

    def import_from_excel(self):
        """Import Excel file with wires only (no topology)"""
        from PyQt5.QtWidgets import QFileDialog
        from utils.excel_import import import_from_excel_to_topology
        
        filepath, _ = QFileDialog.getOpenFileName(
            self, 
            "Import Wire List", 
            "", 
            "Excel Files (*.xlsx *.xls);;CSV Files (*.csv)"
        )
        
        if filepath:
            success = import_from_excel_to_topology(
                filepath,
                self.topology_manager,
                self,
                auto_route=False  # IMPORTANT: wires only!
            )
            
            if success:
                self.statusBar().showMessage(f"Imported {filepath}", 5000)
                # Initialize auto-router after import
                from utils.auto_route import HarnessAutoRouter
                self.auto_router = HarnessAutoRouter(self.topology_manager, self)
            else:
                self.statusBar().showMessage("Import failed", 5000)
    
    def auto_route_wires(self):
        """Convert direct wires to branched topology"""
        if not hasattr(self, 'auto_router'):
            from utils.auto_route import HarnessAutoRouter
            self.auto_router = HarnessAutoRouter(self.topology_manager, self)
        
        # Confirm with user
        from PyQt5.QtWidgets import QMessageBox
        reply = QMessageBox.question(
            self,
            "Create Branches",
            "This will replace direct wires with branched topology.\n"
            "Existing branch points and segments will be cleared.\n\n"
            "Continue?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            
            self.auto_router.clear_topology()
            success = self.auto_router.route_from_imported_data()
            from graphics.visualization_manager import VisualizationManager,VisualizationMode
            if success:
                self.statusBar().showMessage("Topology created successfully", 3000)
                # Switch to bundle view
                if hasattr(self, 'viz_manager'):
                    self.viz_manager.set_mode(VisualizationMode.BUNDLES_ONLY)
            else:
                self.statusBar().showMessage("Auto-routing failed", 3000)
    def clear_topology(self):
        """Remove all branch points and segments, keep connectors and wires"""
        if hasattr(self, 'auto_router'):
            self.auto_router.clear_topology()
            self.statusBar().showMessage("Topology cleared", 3000)

    def add_branch_point_manual(self):
        """Add branch point at cursor position"""
        if not hasattr(self, 'manual_router'):
            from utils.auto_route import ManualRouter
            self.manual_router = ManualRouter(self.topology_manager, self)
        
        self.manual_router.create_branch_point_at_cursor()

    def add_segment_manual(self):
        """Create segment between two selected nodes"""
        if not hasattr(self, 'manual_router'):
            from utils.auto_route import ManualRouter
            self.manual_router = ManualRouter(self.topology_manager, self)
        
        self.manual_router.create_segment_between_selected()

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
        """Topology and routing tools (row 1, after main tools)"""
        toolbar = QToolBar("Topology Tools")
        toolbar.setObjectName("TopologyToolBar")
        toolbar.setMovable(True)
        
        # Add branch point tool
        add_branch = QAction("⬤ Branch Point", self)
        add_branch.triggered.connect(self.add_branch_point)
        toolbar.addAction(add_branch)
        
        # Add junction tool
        add_junction = QAction("◉ Junction", self)
        add_junction.triggered.connect(self.add_junction)
        toolbar.addAction(add_junction)
        
        # Add split segment tool
        split_segment = QAction("✂️ Split", self)
        split_segment.triggered.connect(self.split_segment)
        toolbar.addAction(split_segment)
        
        # Add smart wire tool
        smart_wire = QAction("⚡ Smart Wire", self)
        smart_wire.triggered.connect(self.create_smart_wire)
        toolbar.addAction(smart_wire)
        
        self.addToolBar(toolbar)
        return toolbar

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
        wire = self.topology_manager.route_wire(from_pin, to_pin, via_nodes)
        if not wire:
            self.statusBar().showMessage("Wire could not be created", 3000)
            return    
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


    def on_tree_clicked(self, item):
        obj = item.data(0, Qt.UserRole)
        if obj:
            self.view.scene().clearSelection()
            obj.setSelected(True)
            self.view.centerOn(obj)

    def show_props(self):
        """Create and show property editor dock"""
        from graphics.property_editor import PropertyEditor
        
        self.props = QDockWidget("Properties")
        self.property_editor = PropertyEditor(self)
        self.props.setWidget(self.property_editor)
        self.addDockWidget(Qt.RightDockWidgetArea, self.props)
        
        # Connect selection changes to property editor
        self.view._scene.selectionChanged.connect(self.on_selection_changed)

    def on_selection_changed(self):
        """Update property editor when selection changes"""
        items = self.view._scene.selectedItems()
        if items:
            self.property_editor.set_item(items[0])
        else:
            self.property_editor.set_item(None)

    def on_selection(self):
        """Your existing on_selection method - keep for other functionality"""
        items = self.view._scene.selectedItems()
        if len(items) > 0 and hasattr(items[0], "net"):
            for cp in items[0].net.connection_points:
                cp.setBrush(Qt.red)
        
        # Update property editor
        if hasattr(self, 'property_editor'):
            if items:
                self.property_editor.set_item(items[0])
            else:
                self.property_editor.set_item(None)

        
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

    def _create_main_toolbar(self):
        """Main editing toolbar (row 1)"""
        toolbar = QToolBar("Main Tools")
        toolbar.setObjectName("MainToolBar")
        toolbar.setMovable(True)  # Allow user to move/rearrange
        
        # Add existing tools from your original toolbar
        toolbar.addActions(self.view.tool_group.actions())
        
        add_connector = QAction("➕ Connector", self)
        add_connector.triggered.connect(self.show_custom_dialog)
        toolbar.addAction(add_connector)
        
        rotate = QAction("🔄 Rotate", self)
        rotate.triggered.connect(self.rotate)
        toolbar.addAction(rotate)
        
        toggle_info = QAction("ℹ️ Toggle Info", self)
        toggle_info.triggered.connect(self.toggle_connector_info)
        toolbar.addAction(toggle_info)
        # Add settings button at the end
        toolbar.addSeparator()
        
        settings_btn = QAction("⚙️ Settings", self)
        settings_btn.triggered.connect(self.show_settings)
        toolbar.addAction(settings_btn)

        self.addToolBar(toolbar)
        return toolbar

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
        
    def show_settings(self):
        """Show settings dialog"""
        from dialogs.settings_dialog import SettingsDialog
        
        dialog = SettingsDialog(self.settings_manager, self)
        dialog.settings_changed.connect(self.on_settings_changed)
        
        if dialog.exec_():
            # Settings already applied in dialog.accept()
            pass

    def on_settings_changed(self):
        """Handle settings changes"""
        # Apply theme
        self.setStyleSheet(self.settings_manager.get_theme_stylesheet())
        
        # Update grid visibility
        self.view.set_grid_visible(self.settings_manager.get('show_grid', True))
        self.view.set_grid_size(self.settings_manager.get('grid_size', 50))
        
        # Update connector labels
        for conn in self.conns:
            if hasattr(conn, 'info'):
                conn.info.setVisible(self.settings_manager.get('show_connector_labels', True))
        
        # Update antialiasing
        self.view.setRenderHint(QPainter.Antialiasing, 
                               self.settings_manager.get('antialiasing', True))
        
        # Update status bar
        self.statusBar().showMessage("Settings updated", 3000)
    def _create_tools_menu(self):
        """Add Connector Database Manager to tools menu"""
        menubar = self.menuBar()
        
        # Create Tools menu if it doesn't exist
        tools_menu = None
        for action in menubar.actions():
            if action.text() == "&Tools":
                tools_menu = action.menu()
                break
        
        if not tools_menu:
            tools_menu = menubar.addMenu("&Tools")
        
        # Add connector database action
        db_action = QAction("Connector Database Manager", self)
        db_action.triggered.connect(self.launch_connector_manager)
        tools_menu.addAction(db_action)
        
        # Add separator and settings
        tools_menu.addSeparator()
        settings_action = QAction("Settings...", self)
        settings_action.triggered.connect(self.show_settings)
        tools_menu.addAction(settings_action)

    def launch_connector_manager(self):
        """Launch the standalone connector database manager"""
        import subprocess
        import sys
        from pathlib import Path
        
        # Get path to connector_manager.py
        manager_path = Path(__file__).parent / "connector_manager.py"
        
        if not manager_path.exists():
            QMessageBox.critical(
                self,
                "File Not Found",
                f"Connector manager not found at:\n{manager_path}"
            )
            return
        
        # Get database path from settings
        db_path = self.settings_manager.get('database_path', 'connectors.db')
        
        # Launch as separate process
        try:
            subprocess.Popen([sys.executable, str(manager_path), db_path])
            self.statusBar().showMessage("Connector Database Manager launched", 3000)
        except Exception as e:
            QMessageBox.critical(
                self,
                "Launch Failed",
                f"Failed to launch connector manager:\n{str(e)}"
            )

app = QApplication(sys.argv)
window = MainWindow()
window.resize(800, 600)
window.show()
sys.exit(app.exec_())