#main.py
from model.topology_manager import TopologyManager
from graphics.topology_item import (
    JunctionGraphicsItem, BranchPointGraphicsItem
)
from PyQt5 import sip
from graphics.segment_item import SegmentGraphicsItem
from PyQt5.QtWidgets import (
    QApplication, QMainWindow,QGraphicsScene,QToolBar,QAction,QDialog,QVBoxLayout,QLabel,
    QDockWidget,QTreeWidget,QTabWidget,QTreeWidgetItem,QFileDialog,QGraphicsItem,QInputDialog,
    QShortcut
    
)
from PyQt5.QtGui import QCursor,QPainter,QKeySequence
from graphics.schematic_view import SchematicView
from graphics.connector_item import ConnectorItem
from graphics.wire_item import SegmentedWireItem,WireItem
# from graphics.wire_item import WireItem
from model.netlist import Netlist
import sys
from PyQt5.QtCore import Qt,QFile, QTextStream
from model.models import (
    WiringHarness,NodeType,ConnectorType,SealType,Gender)
from graphics.visualization_manager import VisualizationManager,VisualizationMode
from pathlib import Path
from commands.base_command import BaseCommand
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        from commands.undo_manager import UndoManager
        self.undo_manager = UndoManager(self)
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
        self.topology_manager = TopologyManager()
        from utils.update_dispatcher import UpdateDispatcher
        self.update_dispatcher = UpdateDispatcher()
        self.update_dispatcher.connector_moved.connect(self.on_connector_moved)
        self.update_dispatcher.connector_rotated.connect(self.on_connector_moved)
        
        self.viz_manager = VisualizationManager(self)
        self._create_main_toolbar()      # Basic editing tools

        self._create_import_toolbar()     # Import/export tools
        self._create_view_toolbar()       # Visualization tools
        
        # Arrange toolbars in rows (default behavior)
        self.addToolBarBreak()  # This forces next toolbar to new row
        self._create_edit_toolbar()       # Edit operations
        
        # Initialize settings manager
        from utils.settings_manager import SettingsManager
        self.settings_manager = SettingsManager()
        self._create_file_menu()
        self._create_tools_menu()
        self._create_test_menu()
        # Add project handler
        from database.project_db import ProjectFileHandler
        self.project_handler = ProjectFileHandler()
        
        # Create file menu
        
        self.undo_manager.undo_stack.canRedoChanged.connect(self.set_undo_redo)
        self.undo_manager.undo_stack.canUndoChanged.connect(self.set_undo_redo)
        # Update edit menu/toolbar
        self._create_undo_redo_actions()
        # Delete key
        delete_shortcut = QShortcut(QKeySequence.Delete, self)
        delete_shortcut.activated.connect(self.delete_selected_with_undo)
        
        # Ctrl+A for select all
        select_all_shortcut = QShortcut(QKeySequence.SelectAll, self)
        select_all_shortcut.activated.connect(self.select_all)
        
        # Ctrl+Z for undo (already handled by action)
        # Ctrl+Y for redo (already handled by action)
        
        # Space to toggle selection mode
        # space_shortcut = QShortcut(Qt.Key_Space, self)
        # space_shortcut.activated.connect(self.toggle_selection_mode)

        self._create_bundle_toolbar()
    
        # Store original mouse events for restoration
        self.view.original_mousePressEvent = self.view.mousePressEvent
        self.view.original_mouseMoveEvent = self.view.mouseMoveEvent
        self.view.original_mouseReleaseEvent = self.view.mouseReleaseEvent
        
        # Bundles list
        self.bundles = []

        
        # Install event filter for mouse events
        self.view.viewport().installEventFilter(self)
        
        
        # Apply theme
        self.setStyleSheet(self.settings_manager.get_theme_stylesheet())



        # Demo objects
        
        # self.create_harness_example()
        self.refresh_connector_labels()
        self.view._scene.selectionChanged.connect(self.on_scene_selection)
        self._create_topology_toolbar()   # Topology/routing tools
        self.statusBar().showMessage(
            "Loading complete...", 0
        )
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
    def set_undo_redo(self):
        if self.undo_manager.undo_stack.canRedo():
            self.redo_act.setEnabled(True)
        else:
            self.redo_act.setEnabled(False)
        if self.undo_manager.undo_stack.canUndo():
            self.undo_act.setEnabled(True)
        else:
            self.undo_act.setEnabled(False)
    def _create_edit_toolbar(self):
        """Edit operations toolbar (row 3)"""
        self.addToolBarBreak()
        
        toolbar = QToolBar("Edit Tools")
        toolbar.setObjectName("EditToolBar")
        toolbar.setMovable(True)
        
        # Undo/Redo
        self.undo_act = QAction("↩ Undo", self)
        self.undo_act.triggered.connect(self.undo_manager.undo)
        toolbar.addAction(self.undo_act)
        
        self.redo_act = QAction("↪ Redo", self)
        self.redo_act.triggered.connect(self.undo_manager.redo)
        toolbar.addAction(self.redo_act)
        self.redo_act.setEnabled(False)
        self.redo_act.setEnabled(False)
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
        # Block signals to prevent triggering selection events
        self.connectors_tree.blockSignals(True)
        self.wires_tree.blockSignals(True)
        
        # Clear trees (this properly deletes all items)
        self.connectors_tree.clear()
        self.wires_tree.clear()
        
        # Show connectors
        for conn in self.conns:
            # Check if connector still in scene and not deleted
            if conn and conn.scene() == self.scene:
                try:
                    item = QTreeWidgetItem([conn.cid])
                    item.setData(0, Qt.UserRole, conn)
                    self.connectors_tree.addTopLevelItem(item)
                    conn.tree_item = item
                except RuntimeError:
                    # Connector was deleted, skip
                    pass
        
        # Show wires
        wire_items = []
        
        # Add routed wires if they exist
        if hasattr(self, 'routed_wire_items'):
            wire_items.extend(self.routed_wire_items)
        
        # Add imported wires if they exist
        if hasattr(self, 'imported_wire_items'):
            wire_items.extend(self.imported_wire_items)
        
        for wire_graphics in wire_items:
            try:
                if wire_graphics and wire_graphics.scene() == self.scene:
                    # Get display name
                    if hasattr(wire_graphics, 'wire') and wire_graphics.wire:
                        display_name = wire_graphics.wire.id
                    elif hasattr(wire_graphics, 'wid'):
                        display_name = wire_graphics.wid
                    else:
                        display_name = "Wire"
                    
                    item = QTreeWidgetItem([display_name])
                    item.setData(0, Qt.UserRole, wire_graphics)
                    self.wires_tree.addTopLevelItem(item)
                    wire_graphics.tree_item = item
            except RuntimeError:
                # Wire was deleted, skip
                pass
        
        # Unblock signals
        self.connectors_tree.blockSignals(False)
        self.wires_tree.blockSignals(False)



    
    def on_scene_selection(self):
        """Handle scene selection - select corresponding tree item"""
        items = self.view.scene().selectedItems()
        if not items:
            return

        obj = items[0]
        
        # Check if object has a tree_item
        if hasattr(obj, "tree_item") and obj.tree_item:
            try:
                # Try to access tree_item - will raise RuntimeError if deleted
                tree = obj.tree_item.treeWidget()
                
                # Check if tree still exists and contains this item
                if tree and not sip.isdeleted(tree):
                    # Verify item is still in tree
                    if tree.indexOfTopLevelItem(obj.tree_item) >= 0:
                        tree.setCurrentItem(obj.tree_item)
                        
                        # If it's a connector, show its pins
                        if isinstance(obj, ConnectorItem):
                            print(f"\nSelected {obj.cid}:")
                            for pin in obj.pins:
                                pos = pin.scene_position()
                                print(f"  {pin.pid} at {pos}")
                    else:
                        # Item not in tree, clear reference
                        obj.tree_item = None
                else:
                    # Tree is destroyed, clear reference
                    obj.tree_item = None
                    
            except RuntimeError:
                # Tree item was deleted, clear reference
                obj.tree_item = None


            

    def _create_test_menu(self):
        import_action = QAction("test", self)
        import_action.triggered.connect(self.delete_wires)
        self.toolbar.addAction(import_action)
        
    def delete_wires(self):
        print("undo",self.topology_manager.branches)

    
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
    def add_branch_point(self):
        """Add a branch point at mouse position"""
        pos = self.view.mapToScene(self.view.mapFromGlobal(QCursor.pos()))
        
        # Create data model
        bp_node = self.topology_manager.create_branch_point((pos.x(), pos.y()))
        
        # Create graphics and add to scene
        from graphics.topology_item import BranchPointGraphicsItem
        bp_graphics = BranchPointGraphicsItem(bp_node)
        self.scene.addItem(bp_graphics)
        
        # Optional: Add to selection
        bp_graphics.setSelected(True)
        
        self.statusBar().showMessage(f"Branch point added at ({pos.x():.0f}, {pos.y():.0f})", 2000)
    def add_junction(self):
        """Add a junction at mouse position"""
        pos = self.view.mapToScene(self.view.mapFromGlobal(QCursor.pos()))
        
        junction_node = self.topology_manager.create_junction((pos.x(), pos.y()))
        
        from graphics.topology_item import JunctionGraphicsItem
        junction_graphics = JunctionGraphicsItem(junction_node)
        self.scene.addItem(junction_graphics)
        
        self.statusBar().showMessage(f"Junction added at ({pos.x():.0f}, {pos.y():.0f})", 2000)

    def add_fastener_node(self):
        """Add a fastener node at cursor position"""
        pos = self.view.mapToScene(self.view.mapFromGlobal(QCursor.pos()))
        
        # Ask for fastener type
        from PyQt5.QtWidgets import QInputDialog
        types = ["cable_tie", "clip", "clamp", "adhesive_clip", "other"]
        fastener_type, ok = QInputDialog.getItem(
            self, "Fastener Type", "Select fastener type:", types, 0, False
        )
        
        if ok:
            part_number, ok2 = QInputDialog.getText(
                self, "Part Number", "Enter part number (optional):"
            )
            
            fastener_node = self.topology_manager.create_fastener_node(
                (pos.x(), pos.y()),
                fastener_type=fastener_type,
                part_number=part_number if part_number else None
            )
            
            from graphics.topology_item import FastenerGraphicsItem
            fastener_graphics = FastenerGraphicsItem(fastener_node)
            self.scene.addItem(fastener_graphics)
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



    def add_fastener_node(self):
        """Add a fastener node at cursor position"""
        pos = self.view.mapToScene(self.view.mapFromGlobal(QCursor.pos()))
        
        # Ask for fastener type
        from PyQt5.QtWidgets import QInputDialog
        types = ["cable_tie", "clip", "clamp", "adhesive_clip", "other"]
        fastener_type, ok = QInputDialog.getItem(
            self, "Fastener Type", "Select fastener type:", types, 0, False
        )
        
        if ok:
            part_number, ok2 = QInputDialog.getText(
                self, "Part Number", "Enter part number (optional):"
            )
            
            fastener_node = self.topology_manager.create_fastener_node(
                (pos.x(), pos.y()),
                fastener_type=fastener_type,
                part_number=part_number if part_number else None
            )
            
            from graphics.topology_item import FastenerGraphicsItem
            fastener_graphics = FastenerGraphicsItem(fastener_node)
            self.scene.addItem(fastener_graphics)
    def _create_topology_toolbar(self):
        """Topology and routing tools (row 1, after main tools)"""
        toolbar = QToolBar("Topology Tools")
        toolbar.setObjectName("TopologyToolBar")
        toolbar.setMovable(True)
        

        
        toolbar.addSeparator()
        
        # Add fastener node
        add_fastener_action = QAction("📌 Add Fastener", self)
        add_fastener_action.triggered.connect(self.add_fastener_node)
        toolbar.addAction(add_fastener_action)
        
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
        """Handle tree item click - select corresponding scene item"""
        try:
            obj = item.data(0, Qt.UserRole)
            if obj:
                # Check if object still exists in scene
                if obj.scene() == self.scene:
                    self.view.scene().clearSelection()
                    obj.setSelected(True)
                    self.view.centerOn(obj)
                else:
                    # Object no longer in scene, remove from tree
                    tree = item.treeWidget()
                    if tree and not sip.isdeleted(tree):
                        index = tree.indexOfTopLevelItem(item)
                        if index >= 0:
                            tree.takeTopLevelItem(index)
        except RuntimeError:
            # Item was deleted, ignore
            pass



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
        self.toolbar = QToolBar("Main Tools")
        self.toolbar.setObjectName("MainToolBar")
        self.toolbar.setMovable(True)  # Allow user to move/rearrange
        
        # Add existing tools from your original toolbar
        self.toolbar.addActions(self.view.tool_group.actions())
        
        add_connector = QAction("➕ Connector", self)
        add_connector.triggered.connect(self.show_custom_dialog)
        self.toolbar.addAction(add_connector)
        
        rotate = QAction("🔄 Rotate", self)
        rotate.triggered.connect(self.rotate)
        self.toolbar.addAction(rotate)
        
        toggle_info = QAction("ℹ️ Toggle Info", self)
        toggle_info.triggered.connect(self.toggle_connector_info)
        self.toolbar.addAction(toggle_info)
        # Add settings button at the end
        self.toolbar.addSeparator()
        
        settings_btn = QAction("⚙️ Settings", self)
        settings_btn.triggered.connect(self.show_settings)
        self.toolbar.addAction(settings_btn)

        self.addToolBar(self.toolbar)
        return self.toolbar

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
    def _create_file_menu(self):
        """Create File menu with save/load operations"""
        menubar = self.menuBar()
        file_menu = menubar.addMenu("&File")
        
        # New project
        new_action = QAction("&New Project", self)
        new_action.setShortcut("Ctrl+N")
        new_action.triggered.connect(self.new_project)
        file_menu.addAction(new_action)
        
        # Open project
        open_action = QAction("&Open Project...", self)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self.open_project)
        file_menu.addAction(open_action)
        
        # Save project
        save_action = QAction("&Save", self)
        save_action.setShortcut("Ctrl+S")
        save_action.triggered.connect(self.save_project)
        file_menu.addAction(save_action)
        
        # Save As
        save_as_action = QAction("Save &As...", self)
        save_as_action.setShortcut("Ctrl+Shift+S")
        save_as_action.triggered.connect(self.save_project_as)
        file_menu.addAction(save_as_action)
        
        file_menu.addSeparator()
        
        # Recent files
        self.recent_menu = file_menu.addMenu("Recent Projects")
        self._update_recent_menu()
        
        file_menu.addSeparator()
        
        # Export submenu
        export_menu = file_menu.addMenu("Export")
        
        export_excel = QAction("Export to Excel...", self)
        export_excel.triggered.connect(self.export_to_excel)
        export_menu.addAction(export_excel)
        
        export_hdt = QAction("Harness Drawing Table...", self)
        export_hdt.triggered.connect(self.export_hdt)
        export_menu.addAction(export_hdt)
        
        file_menu.addSeparator()
        
        # Exit
        exit_action = QAction("E&xit", self)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

    def new_project(self):
        """Create a new project"""
        # Check if current project has unsaved changes
        if self.project_handler.modified:
            reply = QMessageBox.question(
                self,
                "Unsaved Changes",
                "Current project has unsaved changes. Create new anyway?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.No:
                return
        
        name, ok = QInputDialog.getText(self, "New Project", "Project Name:")
        if ok and name:
            # Clear current scene properly
            self.clear_scene()
            
            # Create new project
            self.project_handler.new_project(name)
            self.setWindowTitle(f"ECAD - {name}")
            
            self.statusBar().showMessage(f"Created new project: {name}", 3000)


    def open_project(self,*args):
        """Open an existing project"""
        filepath, _ = QFileDialog.getOpenFileName(
            self,
            "Open Project",
            str(Path.home()),
            "ECAD Projects (*.ecad);;All Files (*)"
        )
        
        if filepath:
            # Clear current scene
            self.scene.clear()
            self.conns = []
            self.wires = []
            
            # Load project
            project = self.project_handler.open_project(filepath)
            
            if project:
                self._load_project_to_scene(project)
                self.setWindowTitle(f"ECAD - {project.name} ({Path(filepath).name})")
                
                # Add to recent files
                settings = self.settings_manager
                settings.add_recent_file(filepath)
                self._update_recent_menu()
                
                self.statusBar().showMessage(f"Loaded: {filepath}", 3000)
            else:
                QMessageBox.critical(self, "Error", "Failed to load project")

    def save_project(self):
        """Save current project"""
        if self.project_handler.current_path:
            success = self.project_handler.save_project()
            if success:
                self.statusBar().showMessage(f"Saved: {self.project_handler.current_path}", 3000)
            else:
                QMessageBox.critical(self, "Error", "Failed to save project")
        else:
            self.save_project_as()

    def save_project_as(self):
        """Save project with new name"""
        filepath, _ = QFileDialog.getSaveFileName(
            self,
            "Save Project As",
            str(Path.home() / "untitled.ecad"),
            "ECAD Projects (*.ecad);;All Files (*)"
        )
        
        if filepath:
            # Ensure .ecad extension
            if not filepath.endswith('.ecad'):
                filepath += '.ecad'
            
            # Gather current project data from scene
            project = self._create_project_from_scene()
            self.project_handler.current_project = project
            
            success = self.project_handler.save_project(filepath)
            if success:
                self.setWindowTitle(f"ECAD - {project.name} ({Path(filepath).name})")
                
                # Add to recent files
                settings = self.settings_manager
                settings.add_recent_file(filepath)
                self._update_recent_menu()
                
                self.statusBar().showMessage(f"Saved: {filepath}", 3000)
            else:
                QMessageBox.critical(self, "Error", "Failed to save project")

    def _create_project_from_scene(self) -> WiringHarness:
        """Create project data from current scene"""
        from model.models import WiringHarness, Connector, Wire, Node, Pin
        from model.models import Gender, SealType, ConnectorType, WireType, NodeType
        from model.models import CombinedWireColor
        
        harness = self.project_handler.current_project or WiringHarness(name="Project")
        
        # Clear existing data
        harness.connectors.clear()
        harness.wires.clear()
        harness.nodes.clear()
        harness.branches.clear()
        
        # Add connectors
        for conn_item in self.conns:
            # Create connector
            connector = Connector(
                id=conn_item.cid,
                name=conn_item.cid,
                type=ConnectorType.OTHER,
                gender=Gender.FEMALE,
                seal=SealType.UNSEALED,
                part_number=getattr(conn_item, 'part_number', None),
                manufacturer=getattr(conn_item, 'manufacturer', None),
                position=(conn_item.pos().x(), conn_item.pos().y())
            )
            
            # Add pins
            for pin_item in conn_item.pins:
                wire_id = None
                if pin_item.wires:
                    # Get the first wire's ID
                    wire = pin_item.wires[0]
                    if hasattr(wire, 'wid'):
                        wire_id = wire.wid
                    elif hasattr(wire, 'wire') and hasattr(wire.wire, 'id'):
                        wire_id = wire.wire.id
                
                pin = Pin(
                    number=pin_item.original_id or pin_item.pid,
                    gender=Gender.FEMALE,
                    seal=SealType.UNSEALED,
                    wire_id=wire_id
                )
                connector.pins[pin.number] = pin
            
            harness.connectors[connector.id] = connector
            
            # Create node for connector
            node = Node(
                id=f"NODE_{connector.id}",
                harness_id=harness.id,
                name=connector.id,
                type=NodeType.CONNECTOR,
                connector_id=connector.id,
                position=connector.position
            )
            harness.nodes[node.id] = node
        
        # Add wires from imported_wire_items
        for wire_item in getattr(self, 'imported_wire_items', []):
            if hasattr(wire_item, 'wire_data'):
                wd = wire_item.wire_data
                
                wire = Wire(
                    id=wire_item.wid,
                    harness_id=harness.id,
                    type=WireType.FLRY_B_0_5,
                    color=CombinedWireColor(wd.color),
                    from_node_id=f"NODE_{wd.from_device}",
                    to_node_id=f"NODE_{wd.to_device}",
                    from_pin=wd.from_pin,
                    to_pin=wd.to_pin,
                    signal_name=wd.signal_name,
                    part_number=wd.part_number,
                    cross_section=wd.cross_section
                )
                harness.wires[wire.id] = wire
        
        return harness


    def _load_project_to_scene(self, project: WiringHarness):
        """Load project data into scene"""
        # Clear existing
        self.scene.clear()
        self.conns = []
        self.wires = []
        self.imported_wire_items = []
        
        # Create connectors
        for conn_id, connector in project.connectors.items():
            # Get pin IDs from connector
            pin_ids = list(connector.pins.keys())
            pin_ids.sort()
            
            # Create connector item
            conn_item = ConnectorItem(
                connector.position[0],
                connector.position[1],
                pins=pin_ids
            )
            conn_item.cid = conn_id
            conn_item.part_number = connector.part_number
            conn_item.manufacturer = connector.manufacturer
            
            # Setup topology
            conn_item.set_topology_manager(self.topology_manager)
            conn_item.set_main_window(self)
            conn_item.create_topology_node()
            
            self.scene.addItem(conn_item)
            self.conns.append(conn_item)
        
        # Create wires (as direct wires first)
        from graphics.wire_item import WireItem
        from model.netlist import Netlist
        
        netlist = Netlist()
        self.topology_manager.set_netlist(netlist)
        
        for wire_id, wire in project.wires.items():
            # Find connectors
            from_conn = None
            to_conn = None
            
            for conn in self.conns:
                if conn.cid in wire.from_node_id:
                    from_conn = conn
                if conn.cid in wire.to_node_id:
                    to_conn = conn
            
            if not from_conn or not to_conn:
                continue
            
            # Find pins
            from_pin = from_conn.get_pin_by_id(wire.from_pin) if wire.from_pin else None
            to_pin = to_conn.get_pin_by_id(wire.to_pin) if wire.to_pin else None
            
            if not from_pin or not to_pin:
                continue
            
            # Create net
            net = netlist.connect(from_pin, to_pin)
            
            # Create wire
            wire_item = WireItem(
                wire.id,
                from_pin,
                to_pin,
                wire.color.code if hasattr(wire, 'color') else 'SW',
                net
            )
            wire_item.wire_data = wire
            wire_item.net = net
            
            self.scene.addItem(wire_item)
            self.imported_wire_items.append(wire_item)
            
            from_pin.wires.append(wire_item)
            to_pin.wires.append(wire_item)
        
        # Refresh views
        self.refresh_tree_views()
        self.refresh_connector_labels()


    def _update_recent_menu(self):
        """Update recent files menu"""
        self.recent_menu.clear()
        
        recent_files = self.settings_manager.get_recent_files()
        
        if not recent_files:
            action = self.recent_menu.addAction("(No recent files)")
            action.setEnabled(False)
            return
        
        for filepath in recent_files:
            action = self.recent_menu.addAction(Path(filepath).name)
            action.setData(filepath)
            action.triggered.connect(lambda checked, f=filepath: self.open_recent(f))

    def open_recent(self, filepath):
        """Open a recent file"""
        if Path(filepath).exists():
            self.open_project(filepath)
        else:
            QMessageBox.warning(self, "File Not Found", f"File not found:\n{filepath}")

    def export_to_excel(self):
        """Export current project to Excel"""
        if not self.project_handler.current_project:
            QMessageBox.warning(self, "No Project", "No project to export")
            return
        
        filepath, _ = QFileDialog.getSaveFileName(
            self,
            "Export to Excel",
            str(Path.home() / f"{self.project_handler.current_project.name}.xlsx"),
            "Excel Files (*.xlsx);;All Files (*)"
        )
        
        if filepath:
            success = self.project_handler.export_to_excel(filepath)
            if success:
                self.statusBar().showMessage(f"Exported to: {filepath}", 3000)
            else:
                QMessageBox.critical(self, "Error", "Export failed")

    def export_hdt(self):
        """Export Harness Drawing Table"""
        # This will be implemented later
        QMessageBox.information(self, "Info", "HDT export coming soon!")

    def closeEvent(self, event):
        """Handle window close event"""
        if self.project_handler.modified:
            reply = QMessageBox.question(
                self,
                "Unsaved Changes",
                "Save changes before closing?",
                QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel
            )
            
            if reply == QMessageBox.Yes:
                self.save_project()
                event.accept()
            elif reply == QMessageBox.No:
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()
            
    def _create_undo_redo_actions(self):
        """Create undo/redo actions and add to toolbars"""
        
        # Undo action
        self.undo_action = QAction("↩ Undo", self)
        self.undo_action.setShortcut("Ctrl+Z")
        self.undo_action.setEnabled(False)
        self.undo_action.triggered.connect(self.undo_manager.undo)
        
        # Redo action
        self.redo_action = QAction("↪ Redo", self)
        self.redo_action.setShortcut("Ctrl+Y")
        self.redo_action.setEnabled(False)
        self.redo_action.triggered.connect(self.undo_manager.redo)
        
        # Add to main toolbar
        if hasattr(self, 'toolbar'):
            self.toolbar.addSeparator()
            self.toolbar.addAction(self.undo_action)
            self.toolbar.addAction(self.redo_action)
        
        # Add to edit menu
        menubar = self.menuBar()
        edit_menu = None
        for action in menubar.actions():
            if action.text() == "&Edit":
                edit_menu = action.menu()
                break
        
        if not edit_menu:
            edit_menu = menubar.addMenu("&Edit")
        
        edit_menu.addAction(self.undo_action)
        edit_menu.addAction(self.redo_action)
        edit_menu.addSeparator()
    
    def _wrap_with_undo(self, command: BaseCommand):
        """Helper to push commands to undo manager"""
        self.undo_manager.push(command)

    def on_connector_moved(self, connector):
        """Handle connector movement with undo"""
        # This method is called from the dispatcher
        # We need to store the old position in the connector when movement starts
        
        # Check if we have an old position stored
        if hasattr(connector, '_old_pos'):
            old_pos = connector._old_pos
            new_pos = connector.pos()
            
            # Only create command if position actually changed
            if old_pos != new_pos:
                from commands.connector_commands import MoveConnectorCommand
                cmd = MoveConnectorCommand(connector, old_pos, new_pos)
                self.undo_manager.push(cmd)
                
                # Clear the stored old position
                delattr(connector, '_old_pos')
        
        # Always update topology
        if connector.topology_node:
            connector.topology_node.position = (connector.pos().x(), connector.pos().y())


    def add_connector_with_undo(self, connector_item, pos):
        """Add connector with undo support"""
        from commands.connector_commands import AddConnectorCommand
        cmd = AddConnectorCommand(scene = self.scene, connector_item = connector_item, pos = pos,main_window = self)
        self.undo_manager.push(cmd)

    def delete_selected_with_undo(self):
        """Delete selected items with undo support"""
        selected = self.scene.selectedItems()
        if not selected:
            return
        
        self.undo_manager.begin_macro("Delete Selected")
        
        for item in selected:
            if hasattr(item, 'cid'):  # Connector
                from commands.connector_commands import DeleteConnectorCommand
                cmd = DeleteConnectorCommand(self,self.scene, item)
                self.undo_manager.push(cmd)
            elif hasattr(item, 'wid'):  # Wire
                from commands.wire_commands import DeleteWireCommand
                cmd = DeleteWireCommand(self.scene, item,self)
                self.undo_manager.push(cmd)
        
        self.undo_manager.end_macro()

    def add_wire_with_undo(self, from_pin, to_pin, color="SW"):
        """Add wire with undo support"""
        from graphics.wire_item import WireItem
        from model.netlist import Netlist
        from commands.wire_commands import AddWireCommand
        
        netlist = Netlist()
        net = netlist.connect(from_pin, to_pin)
        wire = WireItem(f"W{len(self.wires)+1}", from_pin, to_pin, color, net)
        
        cmd = AddWireCommand(scene = self.scene, wire_item = wire, from_pin = from_pin, to_pin = to_pin,main_window = self)
        self.undo_manager.push(cmd)
        
        return wire

    def on_property_changed(self, property_name, value):
        """Handle property changes with undo"""
        selected = self.scene.selectedItems()
        if not selected:
            return
        
        item = selected[0]
        
        # Store old value
        old_value = getattr(item, property_name, None)
        if old_value == value:
            return
        
        # Create appropriate command
        if hasattr(item, 'cid'):  # Connector
            from commands.connector_commands import UpdateConnectorPropertiesCommand
            cmd = UpdateConnectorPropertiesCommand(
                item,
                {property_name: old_value},
                {property_name: value}
            )
        elif hasattr(item, 'wid'):  # Wire
            from commands.wire_commands import UpdateWirePropertiesCommand
            cmd = UpdateWirePropertiesCommand(
                item,
                {property_name: old_value},
                {property_name: value}
            )
        else:
            return
        
        self.undo_manager.push(cmd)

    def show_undo_history(self):
        """Show undo history dock widget"""
        if not hasattr(self, 'undo_dock'):
            self.undo_dock = self.undo_manager.create_undo_view()
            self.addDockWidget(Qt.RightDockWidgetArea, self.undo_dock)
        self.undo_dock.show()
    def clear_scene(self):
        """Clear the scene and all associated data"""
        # Clear tree widgets
        self.connectors_tree.clear()
        self.wires_tree.clear()
        
        # Clear lists
        for conn in self.conns:
            conn.cleanup()
        self.conns.clear()
        
        if hasattr(self, 'imported_wire_items'):
            for wire in self.imported_wire_items:
                wire.cleanup()
            self.imported_wire_items.clear()
        
        if hasattr(self, 'routed_wire_items'):
            for wire in self.routed_wire_items:
                wire.cleanup()
            self.routed_wire_items.clear()
        
        self.wires.clear()
        
        # Clear scene
        self.scene.clear()

    def create_branch_from_selection(self):
        """Create a new branch from selected nodes"""
        selected = self.scene.selectedItems()
        if len(selected) < 2:
            QMessageBox.warning(self, "Selection Error", 
                               "Select at least 2 nodes (connectors, branch points, fasteners)")
            return
        
        # Filter to only node types
        nodes = []
        for item in selected:
            if (isinstance(item, ConnectorItem) or 
                isinstance(item, BranchPointGraphicsItem) or
                isinstance(item, FastenerGraphicsItem) or
                isinstance(item, JunctionGraphicsItem)):
                nodes.append(item)
        
        if len(nodes) < 2:
            QMessageBox.warning(self, "Selection Error", 
                               "Select at least 2 valid nodes")
            return
        
        # Open branch creation dialog
        from dialogs.create_branch_dialog import CreateBranchDialog
        dialog = CreateBranchDialog(self, nodes, self)
        
        if dialog.exec_():
            data = dialog.get_branch_data()
            self._create_branch_from_nodes(data['name'], data['protection'], data['nodes'])

    def _create_branch_from_nodes(self, name, protection, nodes):
        """Create a branch from the given nodes"""
        from model.models import HarnessBranch
        import math
        
        # Collect path points and node IDs
        path_points = []
        node_ids = []
        
        for i, node_item in enumerate(nodes):
            # Get node position
            if hasattr(node_item, 'pos'):
                pos = node_item.pos()
                path_points.append((pos.x(), pos.y()))
            
            # Get node ID
            if hasattr(node_item, 'cid'):  # Connector
                node_ids.append(node_item.cid)
            elif hasattr(node_item, 'branch_node'):
                node_ids.append(node_item.branch_node.id)
            elif hasattr(node_item, 'fastener_node'):
                node_ids.append(node_item.fastener_node.id)
            elif hasattr(node_item, 'junction_node'):
                node_ids.append(node_item.junction_node.id)
        
        # Create intermediate points for smooth curves
        if len(path_points) > 2:
            # Add Bezier control points for smooth curves
            smoothed_points = []
            for i in range(len(path_points) - 1):
                p1 = path_points[i]
                p2 = path_points[i + 1]
                
                smoothed_points.append(p1)
                
                # Add midpoint with slight offset for curve
                if i < len(path_points) - 2:
                    mid_x = (p1[0] + p2[0]) / 2
                    mid_y = (p1[1] + p2[1]) / 2
                    smoothed_points.append((mid_x, mid_y))
            
            smoothed_points.append(path_points[-1])
            path_points = smoothed_points
        
        # Create the branch
        branch = HarnessBranch(
            id=f"BRANCH_{uuid.uuid4().hex[:8]}",
            harness_id=self.project_handler.current_project.id if self.project_handler.current_project else "temp",
            name=name,
            protection_id=protection if protection != "None" else None,
            path_points=path_points,
            node_ids=node_ids,
            wire_ids=[]
        )
        
        # Store in topology manager
        self.topology_manager.branches[branch.id] = branch
        
        # Create visual segments between consecutive nodes
        from graphics.segment_item import SegmentGraphicsItem
        
        for i in range(len(nodes) - 1):
            start_item = nodes[i]
            end_item = nodes[i + 1]
            
            # Get topology nodes
            start_node = self._get_topology_node(start_item)
            end_node = self._get_topology_node(end_item)
            
            if start_node and end_node:
                # Create segment
                segment = self.topology_manager.create_segment(start_node, end_node)
                segment_graphics = SegmentGraphicsItem(segment, self.topology_manager)
                self.scene.addItem(segment_graphics)
        
        # Update branch list
        if hasattr(self, 'branch_dock'):
            self.branch_dock.update_list()
        
        self.statusBar().showMessage(f"Branch created: {name}", 3000)

    def _get_topology_node(self, item):
        """Get topology node from graphics item"""
        if hasattr(item, 'topology_node'):
            return item.topology_node
        elif hasattr(item, 'branch_node'):
            return item.branch_node
        elif hasattr(item, 'fastener_node'):
            return item.fastener_node
        elif hasattr(item, 'junction_node'):
            return item.junction_node
        return None
    def _create_bundle_toolbar(self):
        """Create bundle drawing toolbar"""
        from graphics.bundle_toolbar import BundleToolbar
        self.bundle_toolbar = BundleToolbar(self)
        self.addToolBar(Qt.TopToolBarArea, self.bundle_toolbar)

    def assign_wires_to_bundles(self):
        """Auto-assign wires to drawn bundles"""
        if not hasattr(self, 'bundles') or not self.bundles:
            QMessageBox.warning(self, "No Bundles", "Draw some bundles first")
            return
        
        # This would implement wire-to-bundle assignment
        # For now, just show message
        self.statusBar().showMessage("Wire assignment coming soon", 3000)

app = QApplication(sys.argv)
window = MainWindow()
window.resize(1000, 800)
window.show()
sys.exit(app.exec_())