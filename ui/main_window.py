"""
Main window for ECAD application
Combines all UI components and manages the main application state
"""
from pathlib import Path
from PyQt5.QtWidgets import (
    QMainWindow, QGraphicsScene, QDockWidget, QTabWidget,
    QTreeWidget, QTreeWidgetItem, QHeaderView, QShortcut,
    QMessageBox, QInputDialog, QFileDialog
)
from PyQt5.QtCore import Qt, QPointF
from PyQt5.QtGui import QKeySequence, QIcon, QPainter
from graphics.schematic_view import SchematicView
from graphics.connector_item import ConnectorItem
from graphics.wire_item import WireItem
from model.netlist import Netlist
from model.models import WiringHarness
from model.topology_manager import TopologyManager
from graphics.visualization_manager import VisualizationManager
from commands.undo_manager import UndoManager
from utils.settings_manager import SettingsManager
from utils.update_dispatcher import UpdateDispatcher
from database.project_db import ProjectFileHandler
from ui.objects_dock import ObjectsDock
from ui.wires_tab import WiresTab
from controllers.project_controller import ProjectController
from controllers.selection_controller import SelectionController
from menus.file_menu import FileMenu
from menus.edit_menu import EditMenu
from menus.tools_menu import ToolsMenu
from menus.test_menu import TestMenu
from toolbars.main_toolbar import MainToolbar
from toolbars.edit_toolbar import EditToolbar
from toolbars.import_toolbar import ImportToolbar
from toolbars.view_toolbar import ViewToolbar
from toolbars.topology_toolbar import TopologyToolbar
from graphics.bundle_toolbar import BundleToolbar


class MainWindow(QMainWindow):
    """Main application window"""
    
    def __init__(self):
        super().__init__()
        self.setWindowIcon(QIcon('icon.ico'))
        self.undo_manager = UndoManager(self)
        # Initialize managers
        self.settings_manager = SettingsManager()
        # Setup UI
        self.setup_scene()
        
        self.setup_connections()
        self.setup_shortcuts()
        self.wiringharness = WiringHarness()
        
        self.topology_manager = TopologyManager(self)
        self.viz_manager = VisualizationManager(self)
        self.update_dispatcher = UpdateDispatcher()
        self.project_handler = ProjectFileHandler(self)
        # Connect signals
        self.update_dispatcher.connector_moved.connect(self.on_connector_moved)
        self.update_dispatcher.connector_rotated.connect(self.on_connector_moved)
        
        # Data containers
        # self.conns = []
        # self.wires = []
        self.bundles = []
        # self.imported_wire_items = []
        # self.routed_wire_items = []
        self.moving_connector = None
        
        self.graphics_repository = {
            'connectors': {},  # id -> connector_item
            'wires': {},       # id -> wire_item
            'bundles': {},     # id -> bundle_item
            'branch_points': {}, # id -> branch_point_item
            'junctions': {},   # id -> junction_item
        }
        
        # Track items that are "alive" but not in scene
        self.orphaned_items = {
            'connectors': {},
            'wires': {},
            'bundles': {},
            'branch_points': {},
            'junctions': {},
        }
        
        # Apply theme
        self.setStyleSheet(self.settings_manager.get_theme_stylesheet())
        
        # Final setup
        self.refresh_connector_labels()
        self.statusBar().showMessage("Loading complete...", 0)
        self.setup_ui()
     # Add helper properties for backward compatibility during transition
    
    @property
    def conns(self):
        """Get all connector graphics items from the harness"""
        return [conn.graphics_item for conn in self.wiringharness.connectors.values() 
                if conn.graphics_item is not None]
    
    @property
    def imported_wire_items(self):
        """Get all imported wire graphics items from the harness"""
        return [wire.graphics_item for wire in self.wiringharness.wires.values() 
                if wire.graphics_item is not None and 
                hasattr(wire.graphics_item, 'is_connected') and 
                wire.graphics_item.is_connected]
    
    @property
    def routed_wire_items(self):
        """Get all routed wire graphics items"""
        # This might need to be stored separately or in the topology manager
        if hasattr(self, '_routed_wire_items'):
            return self._routed_wire_items
        return []
    
    @routed_wire_items.setter
    def routed_wire_items(self, value):
        self._routed_wire_items = value
    
    @property
    def wires(self):
        """Get all wire models (for backward compatibility)"""
        return list(self.wiringharness.wires.values())
    def export_to_excel(self):
        """ tbd """
        pass
    def export_hdt(self):
        """ tbd """
        pass
    def setup_scene(self):
        """Setup graphics scene and view"""
        self.scene = QGraphicsScene(-2000, -2000, 4000, 4000)
        self.view = SchematicView(self.scene, self)
        self.setCentralWidget(self.view)
        self.view._scene.selectionChanged.connect(self.on_selection)
    
    def setup_ui(self):
        """Setup all UI components"""
        # Create docks
        self.objects_dock = ObjectsDock(self)
        self.addDockWidget(Qt.LeftDockWidgetArea, self.objects_dock)
        
        # Create property editor
        self.show_props()
        
        # Create bundles dock
        self._create_bundles_dock()
        
        # Create toolbars (in specific order for layout)
        self._create_main_toolbar()
        self._create_import_toolbar()
        self._create_view_toolbar()
        self.addToolBarBreak()
        self._create_edit_toolbar()
        self._create_topology_toolbar()
        self._create_bundle_toolbar()
        
        # Create menus
        self._create_file_menu()
        # self._create_edit_menu()
        self._create_tools_menu()
        self._create_test_menu()
    
    def setup_connections(self):
        """Setup signal connections"""
        self.undo_manager.undo_stack.canRedoChanged.connect(self.set_undo_redo)
        self.undo_manager.undo_stack.canUndoChanged.connect(self.set_undo_redo)
        self.view._scene.selectionChanged.connect(self.on_scene_selection)
    
    def setup_shortcuts(self):
        """Setup keyboard shortcuts"""
        delete_shortcut = QShortcut(QKeySequence.Delete, self)
        delete_shortcut.activated.connect(self.delete_selected_with_undo)
        
        select_all_shortcut = QShortcut(QKeySequence.SelectAll, self)
        select_all_shortcut.activated.connect(self.select_all)
        
        # Store original mouse events for restoration
        self.view.original_mousePressEvent = self.view.mousePressEvent
        self.view.original_mouseMoveEvent = self.view.mouseMoveEvent
        self.view.original_mouseReleaseEvent = self.view.mouseReleaseEvent
        
        # Install event filter
        self.view.viewport().installEventFilter(self)
    
    # ============ UI Creation Methods ============
    def refresh_prop(self):
        if self.property_editor is not None:
            self.property_editor.refresh()
    def show_props(self):
        """Create and show property editor dock"""
        from graphics.property_editor import PropertyEditor
        
        self.props = QDockWidget("Properties", self)
        self.props.setFeatures(QDockWidget.DockWidgetMovable | QDockWidget.DockWidgetFloatable)
        
        self.property_editor = PropertyEditor(self)
        self.props.setWidget(self.property_editor)
        
        # Make sure the dock widget is scrollable
        self.props.setMinimumWidth(300)
        
        self.addDockWidget(Qt.RightDockWidgetArea, self.props)
        
        # Connect selection changes to property editor
        self.view._scene.selectionChanged.connect(self.on_selection_changed)

    
    def _create_main_toolbar(self):
        """Main editing toolbar"""
        toolbar = MainToolbar(self)
        self.addToolBar(toolbar)
        return toolbar
    
    def _create_import_toolbar(self):
        """Import and routing toolbar"""
        self.addToolBarBreak()
        toolbar = ImportToolbar(self)
        self.addToolBar(toolbar)
        return toolbar
    
    def _create_view_toolbar(self):
        """View and visualization toolbar"""
        toolbar = ViewToolbar(self)
        self.addToolBar(toolbar)
        return toolbar
    
    def _create_edit_toolbar(self):
        """Edit operations toolbar"""
        self.addToolBarBreak()
        toolbar = EditToolbar(self)
        self.addToolBar(toolbar)
        return toolbar
    
    def _create_topology_toolbar(self):
        """Topology tools toolbar"""
        toolbar = TopologyToolbar(self)
        self.addToolBar(toolbar)
        return toolbar
    
    def _create_bundle_toolbar(self):
        """Bundle drawing toolbar"""
        self.bundle_toolbar = BundleToolbar(self)
        self.addToolBar(Qt.TopToolBarArea, self.bundle_toolbar)
    
    def _create_file_menu(self):
        """Create file menu"""
        FileMenu(self)
    def _create_edit_menu(self):
        """Create file menu"""
        EditMenu(self)
    def _create_tools_menu(self):
        """Create tools menu"""
        ToolsMenu(self)
    
    def _create_test_menu(self):
        """Create test menu (for debugging)"""
        TestMenu(self)
    
    def _create_bundles_dock(self):
        """Create dock widget for bundles tree"""
        self.bundles_dock = QDockWidget("Bundles", self)
        self.bundles_dock.setAllowedAreas(Qt.LeftDockWidgetArea | Qt.RightDockWidgetArea)
        
        self.bundles_tree = QTreeWidget()
        self.bundles_tree.setHeaderLabels(["Bundle", "Length", "Wires"])
        self.bundles_tree.header().setSectionResizeMode(0, QHeaderView.Stretch)
        self.bundles_tree.header().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.bundles_tree.header().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.bundles_tree.itemClicked.connect(self.on_bundle_tree_clicked)
        self.bundles_tree.itemSelectionChanged.connect(self.on_bundle_selection_changed)
        
        self.bundles_dock.setWidget(self.bundles_tree)
        self.addDockWidget(Qt.LeftDockWidgetArea, self.bundles_dock)
    
    # ============ Event Handlers ============
    
    def mousePressEvent(self, event):
        """Handle mouse press for move mode"""
        if self.moving_connector:
            pos = self.view.mapToScene(event.pos())
            
            from commands.connector_commands import MoveConnectorCommand
            cmd = MoveConnectorCommand(
                self.moving_connector,
                self.moving_connector.pos(),
                pos
            )
            self.undo_manager.push(cmd)
            
            self.moving_connector = None
            self.statusBar().showMessage("", 0)
            event.accept()
            return
        
        super().mousePressEvent(event)
    
    def on_selection(self):
        """Handle scene selection - update property editor"""
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
    
    def on_selection_changed(self):
        """Update property editor when selection changes"""
        items = self.view._scene.selectedItems()
        if items:
            self.property_editor.set_item(items[0])
        else:
            self.property_editor.set_item(None)
    
    def on_scene_selection(self):
        """Handle scene selection - select corresponding tree item"""
        items = self.view.scene().selectedItems()
        if not items:
            return
        
        SelectionController.handle_scene_selection(self, items[0])
    
    def on_tree_clicked(self, item):
        """Handle tree item click - select corresponding scene item"""
        from PyQt5 import sip
        
        try:
            obj = item.data(0, Qt.UserRole)
            if obj:
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
            pass
    
    def on_bundle_tree_clicked(self, item):
        """Handle bundle tree item click"""
        bundle = item.data(0, Qt.UserRole)
        if bundle and bundle.scene() == self.scene:
            for selected in self.scene.selectedItems():
                selected.setSelected(False)
            bundle.setSelected(True)
            self.view.centerOn(bundle)
    
    def on_bundle_selection_changed(self):
        """Handle bundle tree selection change"""
        selected = self.bundles_tree.selectedItems()
        if selected and hasattr(self, 'bundle_property_editor'):
            bundle = selected[0].data(0, Qt.UserRole)
            self.bundle_property_editor.set_bundle(bundle)
    
    def on_connector_moved(self, connector):
        """Handle connector movement with undo"""
        if hasattr(connector, '_old_pos'):
            old_pos = connector._old_pos
            new_pos = connector.pos()
            
            if old_pos != new_pos:
                from commands.connector_commands import MoveConnectorCommand
                cmd = MoveConnectorCommand(connector, old_pos, new_pos)
                self.undo_manager.push(cmd)
                delattr(connector, '_old_pos')
        
        if connector.topology_node:
            connector.topology_node.position = (connector.pos().x(), connector.pos().y())
    
    # ============ Selection Methods ============
    
    def select_all(self):
        """Select all items in scene"""
        for item in self.scene.items():
            if item.flags() & item.ItemIsSelectable:
                item.setSelected(True)
    
    def clear_selection(self):
        """Clear all selections"""
        for item in self.scene.items():
            item.setSelected(False)
    
    def select_all_bundles(self):
        """Select all bundle items in scene"""
        for item in self.scene.items():
            if hasattr(item, 'bundle_id'):
                item.setSelected(True)
    
    # ============ Update Methods ============
    
    def set_undo_redo(self):
        """Update undo/redo action states"""
        self.undo_act.setEnabled(self.undo_manager.undo_stack.canUndo())
        self.redo_act.setEnabled(self.undo_manager.undo_stack.canRedo())
    
    def refresh_connector_labels(self):
        """Refresh all connector info labels"""
        for conn in self.wiringharness.connectors.values():
            if conn.graphics_item:
                if hasattr(conn.graphics_item, 'info'):
                    conn.graphics_item.info.update_text()
                if hasattr(conn.graphics_item, 'info_table'):
                    conn.graphics_item.info_table.update_table()
                    
    def refresh_tree_views(self):
        """Refresh tree widget contents"""
        if hasattr(self.objects_dock, 'connectors_tree'):
            # Get all connectors from harness
            connectors = [conn.graphics_item for conn in self.wiringharness.connectors.values() 
                         if conn.graphics_item is not None]

            wires = [wire.graphics_item for wire in self.wiringharness.wires.values() 
                    if wire.graphics_item is not None]
            self.objects_dock.refresh_trees(connectors, wires)
    
    def refresh_bundle_tree(self):
        """Refresh the bundles tree with wire counts"""
        if not hasattr(self, 'bundles_tree'):
            return
        
        self.bundles_tree.blockSignals(True)
        self.bundles_tree.clear()
        
        for bundle in self.bundles:
            if bundle and bundle.scene() == self.scene:
                display_name = getattr(bundle, 'name', bundle.bundle_id)
                
                if bundle.specified_length:
                    length_text = f"{bundle.specified_length:.0f} mm"
                else:
                    length_text = f"{bundle.length:.0f} units"
                
                wires_text = str(bundle.wire_count)
                
                item = QTreeWidgetItem([display_name, length_text, wires_text])
                item.setData(0, Qt.UserRole, bundle)
                
                # Color based on wire count
                if bundle.wire_count > 0:
                    if bundle.wire_count < 5:
                        item.setForeground(0, Qt.darkGreen)
                    elif bundle.wire_count < 15:
                        item.setForeground(0, Qt.darkBlue)
                    else:
                        item.setForeground(0, Qt.darkRed)
                else:
                    item.setForeground(0, Qt.gray)
                
                self.bundles_tree.addTopLevelItem(item)
                bundle.tree_item = item
        
        self.bundles_tree.blockSignals(False)
    
    def get_all_wires(self):
        """Get all wire items (both imported and routed)"""
        """Get all wire graphics items from harness"""
        return [wire.graphics_item for wire in self.wiringharness.wires.values() if wire.graphics_item is not None]

    
    # ============ Action Methods ============
    
    def toggle_connector_info(self):
        """Toggle connector info display (table format)"""
        for item in self.scene.items():
            if isinstance(item, ConnectorItem):
                if hasattr(item, 'info_table'):
                    visible = item.info_table.isVisible()
                    item.info_table.setVisible(not visible)
                elif hasattr(item, 'info'):
                    visible = item.info.isVisible()
                    item.info.setVisible(not visible)
    
    def toggle_compact_mode(self):
        """Toggle between compact and full table view"""
        for item in self.scene.selectedItems():
            if isinstance(item, ConnectorItem) and hasattr(item, 'toggle_info_display'):
                item.toggle_info_display()
    
    def rotate_selected(self):
        """Rotate selected connectors"""
        items = self.view.scene().selectedItems()
        for item in items:
            if getattr(item, "rotate_90", None):
                item.rotate_90()
    
    def add_branch_point(self):
        """Add a branch point at mouse position"""
        from graphics.topology_item import BranchPointGraphicsItem
        from model.models import BranchPoint
        from commands.topology_commands import AddBranchPointCommand
        
        pos = self.view.mapToScene(self.view.mapFromGlobal(QCursor.pos()))
        pos_tuple = (pos.x(), pos.y())
        
        # Create branch point model
        bp_id = self.wiringharness.next_bpid()
        bp_model = BranchPoint(
            id=bp_id,
            name=bp_id,
            position=pos_tuple,
            branch_type="split"
        )
        
        # Add to harness
        self.wiringharness.add_branch_point(bp_model)
        
        # Create topology node for backward compatibility
        from model.topology import BranchPointNode
        bp_node = BranchPointNode(pos_tuple, "split")
        bp_node.id = bp_id
        self.topology_manager.nodes[bp_id] = bp_node
        
        # Create graphics item from model
        bp_graphics = BranchPointGraphicsItem(bp_model, self)
        bp_graphics.branch_node = bp_node  # For backward compatibility
        
        # Add with undo
        cmd = AddBranchPointCommand(
            self.scene,
            bp_graphics,
            pos_tuple,
            main_window=self
        )
        self.undo_manager.push(cmd)
        
        bp_graphics.setSelected(True)

    def add_junction(self):
        """Add a junction at mouse position"""
        from graphics.topology_item import JunctionGraphicsItem
        
        pos = self.view.mapToScene(self.view.mapFromGlobal(QCursor.pos()))
        junction_node = self.topology_manager.create_junction((pos.x(), pos.y()))
        junction_graphics = JunctionGraphicsItem(junction_node)
        self.scene.addItem(junction_graphics)
        self.statusBar().showMessage(f"Junction added at ({pos.x():.0f}, {pos.y():.0f})", 2000)
    
    def add_fastener_node(self):
        """Add a fastener node at cursor position"""
        from PyQt5.QtWidgets import QInputDialog
        from graphics.topology_item import FastenerGraphicsItem
        
        pos = self.view.mapToScene(self.view.mapFromGlobal(QCursor.pos()))
        
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
            
            fastener_graphics = FastenerGraphicsItem(fastener_node)
            self.scene.addItem(fastener_graphics)
    
    def create_smart_wire(self):
        """Create a wire that goes through selected nodes"""
        from graphics.wire_item import SegmentedWireItem
        
        selected = self.scene.selectedItems()
        if len(selected) < 2:
            return
        
        connectors = [item for item in selected if isinstance(item, ConnectorItem)]
        nodes = [item for item in selected 
                if isinstance(item, (JunctionGraphicsItem, BranchPointGraphicsItem))]
        
        if len(connectors) != 2:
            QMessageBox.warning(self, "Error", "Select exactly 2 connectors")
            return
        
        from_pin = connectors[0].pins[0]
        to_pin = connectors[1].pins[0]
        
        via_nodes = []
        for node_item in nodes:
            if isinstance(node_item, JunctionGraphicsItem):
                via_nodes.append(node_item.junction_node)
            elif isinstance(node_item, BranchPointGraphicsItem):
                via_nodes.append(node_item.branch_node)
        
        wire = self.topology_manager.route_wire(from_pin, to_pin, via_nodes)
        if not wire:
            self.statusBar().showMessage("Wire could not be created", 3000)
            return
        
        wire_graphics = SegmentedWireItem(wire)
        self.scene.addItem(wire_graphics)
        self.imported_wire_items.append(wire_graphics)
    
    # ============ Undo/Redo Methods ============
    
    def add_connector_with_undo(self, connector_item, pos):
        """Add connector with undo support"""
        from commands.connector_commands import AddConnectorCommand
        cmd = AddConnectorCommand(self.scene, connector_item, pos, main_window=self)
        self.undo_manager.push(cmd)
    
    def delete_selected_with_undo(self):
        """Delete selected items with undo support"""
        selected = self.scene.selectedItems()
        if not selected:
            return
        
        self.undo_manager.begin_macro("Delete Selected")
        
        for item in selected:
            if hasattr(item, 'node_type') and item.node_type == "Connector":  # Connector
                from commands.connector_commands import DeleteConnectorCommand
                cmd = DeleteConnectorCommand(self, self.scene, item)
                self.undo_manager.push(cmd)
            elif hasattr(item, 'wid'):  # Wire
                from commands.wire_commands import DeleteWireCommand
                cmd = DeleteWireCommand(self.scene, item, self)
                self.undo_manager.push(cmd)
            elif hasattr(item, 'bundle_id'):  # Bundle
                from commands.bundle_commands import DeleteBundleCommand
                cmd = DeleteBundleCommand(self.scene, item, self)
                self.undo_manager.push(cmd)
        
        self.undo_manager.end_macro()
    
    def delete_selected_bundles(self):
        """Delete selected bundles with undo"""
        selected = self.scene.selectedItems()
        bundles = [item for item in selected if hasattr(item, 'bundle_id')]
        
        if not bundles:
            return
        
        self.undo_manager.begin_macro(f"Delete {len(bundles)} Bundle(s)")
        
        for bundle in bundles:
            from commands.bundle_commands import DeleteBundleCommand
            cmd = DeleteBundleCommand(self.scene, bundle, self)
            self.undo_manager.push(cmd)
        
        self.undo_manager.end_macro()
    
    # ============ Import/Export Methods ============
    
    def import_from_excel(self):
        """Import Excel file with wires only"""
        from utils.excel_import import import_from_excel_to_scene
        
        filepath, _ = QFileDialog.getOpenFileName(
            self, "Import Wire List", "", "Excel Files (*.xlsx *.xls);;CSV Files (*.csv)"
        )
        
        if filepath:
            success = import_from_excel_to_scene(
                filepath,  self, auto_route=False
            )
            
            if success:
                self.statusBar().showMessage(f"Imported {filepath}", 5000)
                from utils.auto_route import HarnessAutoRouter
                self.auto_router = HarnessAutoRouter(self.topology_manager, self)
            else:
                self.statusBar().showMessage("Import failed", 5000)
    
    def auto_route_wires(self):
        """Convert direct wires to branched topology"""
        if not hasattr(self, 'auto_router'):
            from utils.auto_route import HarnessAutoRouter
            self.auto_router = HarnessAutoRouter(self.topology_manager, self)
        
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
            
            if success:
                self.statusBar().showMessage("Topology created successfully", 3000)
                if hasattr(self, 'viz_manager'):
                    self.viz_manager.set_mode(VisualizationMode.BUNDLES_ONLY)
            else:
                self.statusBar().showMessage("Auto-routing failed", 3000)
    
    def clear_topology(self):
        """Remove all branch points and segments, keep connectors and wires"""
        if hasattr(self, 'auto_router'):
            self.auto_router.clear_topology()
            self.statusBar().showMessage("Topology cleared", 3000)
    
    def launch_connector_manager(self):
        """Launch the standalone connector database manager"""
        import subprocess
        from pathlib import Path
        
        manager_path = Path(__file__).parent / "connector_manager.py"
        
        if not manager_path.exists():
            QMessageBox.critical(
                self,
                "File Not Found",
                f"Connector manager not found at:\n{manager_path}"
            )
            return
        
        db_path = self.settings_manager.get('database_path', 'connectors.db')
        
        try:
            subprocess.Popen([sys.executable, str(manager_path), db_path])
            self.statusBar().showMessage("Connector Database Manager launched", 3000)
        except Exception as e:
            QMessageBox.critical(self, "Launch Failed", f"Failed to launch connector manager:\n{str(e)}")
    
    def log_to_console(self):
        # from dialogs.debug import AttributeViewerDialog
        # dialog = AttributeViewerDialog(self.wiringharness)
        # dialog.exec_()

        print(self.wiringharness.to_dict())
        
    def show_settings(self):
        """Show settings dialog"""
        from dialogs.settings_dialog import SettingsDialog
        
        dialog = SettingsDialog(self.settings_manager, self)
        dialog.settings_changed.connect(self.on_settings_changed)
        
        if dialog.exec_():
            pass
    
    def on_settings_changed(self):
        """Handle settings changes"""
        self.setStyleSheet(self.settings_manager.get_theme_stylesheet())
        self.view.set_grid_visible(self.settings_manager.get('show_grid', True))
        self.view.set_grid_size(self.settings_manager.get('grid_size', 50))
        
        for conn in self.conns:
            if hasattr(conn, 'info'):
                conn.info.setVisible(self.settings_manager.get('show_connector_labels', True))
        
        self.view.setRenderHint(QPainter.Antialiasing, 
                               self.settings_manager.get('antialiasing', True))
        
        self.statusBar().showMessage("Settings updated", 3000)
    
    # ============ Project Methods ============
    
    def new_project(self):
        """Create a new project"""
        if self.project_handler.modified:
            reply = QMessageBox.question(
                self,
                "Unsaved Changes",
                "Current project has unsaved changes. Create new anyway?",
                QMessageBox.Yes | QMessageBox.No
            )
            if reply == QMessageBox.No:
                return
        
        from dialogs.project_properties_dialog import ProjectPropertiesDialog
        
        # Create new project
        name, ok = QInputDialog.getText(self, "New Project", "Project Name:")
        if ok and name:
            self.clear_scene()
            self.project_handler.new_project(name)
            
            # Show properties dialog to set additional info
            dialog = ProjectPropertiesDialog(self.project_handler.current_project, self)
            dialog.exec_()  # User can set more properties
            
            self.setWindowTitle(f"ECAD - {self.project_handler.current_project.name}")
            self.statusBar().showMessage(f"Created new project: {self.project_handler.current_project.name}", 3000)

    
    
    def save_project(self):
        """Save current project"""
        from controllers.project_controller import ProjectController
        ProjectController.save_project(self)


    def save_project_as(self):
        """Save project with new name"""
        from controllers.project_controller import ProjectController
        ProjectController.save_project_as(self)

    def _update_recent_menu(self):
        """Update recent files menu (called from FileMenu)"""
        # This is handled by FileMenu, but we keep this method for compatibility
        pass

    def open_project(self, filepath=None):
        """Open an existing project"""
        from controllers.project_controller import ProjectController
        ProjectController.open_project(self, filepath)
    
    def open_recent(self, filepath):
        """Open a recent file"""
        from controllers.project_controller import ProjectController
        ProjectController.open_recent(self, filepath)

    def show_project_properties(self):
        """Show the project properties dialog"""

        
        from dialogs.project_properties_dialog import ProjectPropertiesDialog
        
        dialog = ProjectPropertiesDialog(self.project_handler.current_project, self)
        
        # Store original name for undo
        old_name = self.project_handler.current_project.name
        old_part_number = self.project_handler.current_project.part_number
        old_revision = self.project_handler.current_project.revision
        old_description = getattr(self.project_handler.current_project, 'description', '')
        
        if dialog.exec_():
            # Update window title if name changed
            if self.project_handler.current_project.name != old_name:
                self.setWindowTitle(f"ECAD - {self.project_handler.current_project.name}")
            
            # Mark as modified
            self.project_handler.modified = True
            
            # Update any displays that show project name
            self.statusBar().showMessage(
                f"Project properties updated: {self.project_handler.current_project.name}", 
                3000
            )
            
            # Refresh relevant views
            self.refresh_tree_views()

    def _update_models_before_save(self):
        """Update all model data from graphics items before saving"""
        # Update connector positions
        for conn in self.conns:
            if conn.model.id in self.wiringharness.connectors:
                model = self.wiringharness.connectors[conn.model.id]
                pos = conn.pos()
                model.position = (pos.x(), pos.y())
                model.rotation = conn.rotation()
        
        # Update bundle data
        for bundle in self.bundles:
            if bundle.model.id in self.wiringharness.bundles:
                model = self.wiringharness.bundles[bundle.model.id]
                model.start_point = (bundle.start_point.x(), bundle.start_point.y())
                model.end_point = (bundle.end_point.x(), bundle.end_point.y())
                model.specified_length = bundle.specified_length
                model.wire_count = bundle.wire_count
                model.wire_ids = bundle.wire_ids.copy()
        
        # Update branch points
        for item in self.scene.items():
            if hasattr(item, 'model') and hasattr(item.model, 'position'):
                if item.model.id in self.wiringharness.branch_points:
                    pos = item.pos()
                    item.model.position = (pos.x(), pos.y())

    def _recreate_scene_from_models(self):
        """Recreate the entire scene from the wiring harness models"""
        from graphics.connector_item import ConnectorItem
        from graphics.wire_item import WireItem, SegmentedWireItem
        from graphics.bundle_item import BundleItem
        from graphics.topology_item import BranchPointGraphicsItem, JunctionGraphicsItem
        from model.topology import TopologyNode, BranchPointNode, JunctionNode, WireSegment
        from model.models import TopologySegment
        
        # Clear existing scene
        self.scene.clear()

        
        # Clear topology manager but keep reference
        self.topology_manager.nodes.clear()
        self.topology_manager.segments.clear()
        
        # STEP 1: Recreate connector nodes
        for conn_model in self.wiringharness.connectors.values():
            conn_item = ConnectorItem(conn_model)
            conn_item.set_topology_manager(self.topology_manager)
            conn_item.set_main_window(self)
            
            # Create topology node
            node = TopologyNode(conn_model.id, conn_model.position)
            node.node_type = "connector"
            node.connector_ref = conn_item
            self.topology_manager.nodes[node.id] = node
            conn_item.topology_node = node
            
            conn_item.setPos(conn_model.position[0], conn_model.position[1])
            conn_item.setRotation(conn_model.rotation)
            
            self.scene.addItem(conn_item)
            self.conns.append(conn_item)
            
            # Create tree item
            item = QTreeWidgetItem([conn_model.id])
            item.setData(0, Qt.UserRole, conn_item)
            self.objects_dock.connectors_tree.addTopLevelItem(item)
            conn_item.tree_item = item
            
            self.register_graphics_item(conn_item, 'connectors')
        
        # STEP 2: Recreate branch point nodes
        for bp_model in self.wiringharness.branch_points.values():
            # Create topology node
            bp_node = BranchPointNode(bp_model.position, bp_model.branch_type)
            bp_node.id = bp_model.id
            self.topology_manager.nodes[bp_node.id] = bp_node
            
            # Create graphics
            bp_graphics = BranchPointGraphicsItem(bp_model, self)
            bp_graphics.branch_node = bp_node
            bp_graphics.setPos(bp_model.position[0], bp_model.position[1])
            
            self.scene.addItem(bp_graphics)
            self.register_graphics_item(bp_graphics, 'branch_points')
        
        # STEP 3: Recreate segments from saved data
        for seg_model in self.wiringharness.segments.values():
            start_node = self.topology_manager.nodes.get(seg_model.start_node_id)
            end_node = self.topology_manager.nodes.get(seg_model.end_node_id)
            
            if start_node and end_node:
                # Create topology segment
                segment = WireSegment(
                    segment_id=seg_model.id,
                    start_node=start_node,
                    end_node=end_node,
                    wires=[]
                )
                self.topology_manager.segments[segment.id] = segment
                
                # Create graphics
                from graphics.segment_item import SegmentGraphicsItem
                segment_graphics = SegmentGraphicsItem(segment, self.topology_manager)
                self.scene.addItem(segment_graphics)
        
        # STEP 4: Recreate bundles
        for bundle_model in self.wiringharness.bundles.values():
            bundle_item = BundleItem(bundle_model, self)
            
            # Find start and end nodes
            if bundle_model.start_node_id:
                node = self.topology_manager.nodes.get(bundle_model.start_node_id)
                if node:
                    bundle_item.start_node = node
                    # Find graphics for this node
                    for item in self.scene.items():
                        if hasattr(item, 'model') and item.model.id == node.id:
                            bundle_item.start_item = item
                            break
            
            if bundle_model.end_node_id:
                node = self.topology_manager.nodes.get(bundle_model.end_node_id)
                if node:
                    bundle_item.end_node = node
                    for item in self.scene.items():
                        if hasattr(item, 'model') and item.model.id == node.id:
                            bundle_item.end_item = item
                            break
            
            # Restore wire assignments
            bundle_item.wire_ids = bundle_model.wire_ids.copy()
            bundle_item.wire_count = bundle_model.wire_count
            
            bundle_item.update_path()
            self.scene.addItem(bundle_item)
            self.bundles.append(bundle_item)
            self.register_graphics_item(bundle_item, 'bundles')
            
            # Link bundle to its segment
            for seg_id, seg_model in self.wiringharness.segments.items():
                if seg_model.bundle_id == bundle_model.id:
                    segment = self.topology_manager.segments.get(seg_id)
                    if segment:
                        bundle_item.segment = segment
                        bundle_item.segment_graphics = None  # Will be set later
        
        # STEP 5: Recreate wires
        netlist = Netlist()
        self.topology_manager.set_netlist(netlist)
        
        for wire_model in self.wiringharness.wires.values():
            # Find connector graphics
            from_conn = None
            to_conn = None
            
            for conn in self.conns:
                if conn.model.id == wire_model.from_node_id:
                    from_conn = conn
                if conn.model.id == wire_model.to_node_id:
                    to_conn = conn
            
            if not from_conn or not to_conn:
                continue
            
            # Find pin graphics
            from_pin = from_conn.get_pin_by_id(f"{wire_model.from_node_id}_{wire_model.from_pin}")
            to_pin = to_conn.get_pin_by_id(f"{wire_model.to_node_id}_{wire_model.to_pin}")
            
            if not from_pin or not to_pin:
                continue
            
            # Create direct wire item
            wire_item = WireItem(wire_model)
            wire_item.set_main_window(self)
            wire_item.connect_to_pins(from_pin, to_pin)
            
            net = netlist.connect(from_pin, to_pin)
            wire_item.net = net
            
            self.scene.addItem(wire_item)
            self.imported_wire_items.append(wire_item)
            
            # Create tree item
            item = QTreeWidgetItem([wire_model.id])
            item.setData(0, Qt.UserRole, wire_item)
            self.objects_dock.wires_tab.wires_tree.addTopLevelItem(item)
            wire_item.tree_item = item
            
            self.register_graphics_item(wire_item, 'wires')
            
            # Add wire to segments based on saved segment wire_ids
            path_segments = []
            for seg_id, seg_model in self.wiringharness.segments.items():
                if wire_model.id in seg_model.wire_ids:
                    segment = self.topology_manager.segments.get(seg_id)
                    if segment:
                        path_segments.append(segment)
                        if wire_model not in segment.wires:
                            segment.wires.append(wire_model)
            
            # If wire has route, create SegmentedWireItem
            if wire_model.route and path_segments:
                routed_wire = SegmentedWireItem(
                    wire_model=wire_model,
                    path_segments=path_segments,
                    main_window=self
                )
                routed_wire.connect_to_pins(from_pin, to_pin)
                routed_wire.original_wire = wire_item
                
                self.scene.addItem(routed_wire)
                
                if not hasattr(self, 'routed_wire_items'):
                    self.routed_wire_items = []
                self.routed_wire_items.append(routed_wire)
                
                self.register_graphics_item(routed_wire, 'routed_wires')
                wire_model.add_routed_graphics(routed_wire)
                
                # Hide direct wire by default
                wire_item.setVisible(False)
        
        # Refresh trees
        self.refresh_tree_views()
        self.refresh_bundle_tree()

        
        

    def _find_segment_between_nodes(self, node1, node2):
        """Find existing segment between two nodes"""
        for segment in self.topology_manager.segments.values():
            print(segments,"s")
            if (segment.start_node == node1 and segment.end_node == node2) or \
               (segment.start_node == node2 and segment.end_node == node1):
                return segment
        return None

    
    def publish_project(self):
        """Publish current project to central database"""
        ProjectController.publish_project(self)
    
    def open_from_database(self):
        """Open a project from central database"""
        ProjectController.open_from_database(self)
    
    def reconstruct_bundles_from_data(self):
        """Reconstruct bundles from loaded database data"""
        ProjectController.reconstruct_bundles_from_data(self)
    
    def clear_scene(self):
        """Clear the scene and all associated data"""
        self.objects_dock.connectors_tree.clear()
        self.objects_dock.wires_tab.wires_tree.clear()
        if hasattr(self, 'bundles_tree'):
            self.bundles_tree.clear()
        
        # Clean up all graphics items
        for conn in self.wiringharness.connectors.values():
            if conn.graphics_item:
                conn.graphics_item.cleanup()
        
        for wire in self.wiringharness.wires.values():
            if wire.graphics_item:
                wire.graphics_item.cleanup()
        
        # Clear the harness
        self.wiringharness.connectors.clear()
        self.wiringharness.wires.clear()
        
        # Clear routed wires if any
        if hasattr(self, '_routed_wire_items'):
            for wire in self._routed_wire_items:
                if wire.scene():
                    self.scene.removeItem(wire)
            self._routed_wire_items.clear()
        
        # Clear topology
        self.topology_manager.nodes.clear()
        self.topology_manager.segments.clear()
        self.topology_manager.wires.clear()
        
        # Clear bundles
        if hasattr(self, 'bundles'):
            for bundle in self.bundles:
                bundle.cleanup()
            self.bundles.clear()
        
        self.scene.clear()
    
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
    
    def register_graphics_item(self, item, item_type=None):
        """Register a graphics item in the repository"""
        if item_type is None:
            # Auto-detect type
            if hasattr(item, 'model') and hasattr(item.model, 'id'):
                item_id = item.model.id
                if hasattr(item, 'pins'):  # ConnectorItem
                    item_type = 'connectors'
                elif hasattr(item, 'wid'):  # WireItem
                    item_type = 'wires'
            elif hasattr(item, 'bundle_id'):
                item_id = item.bundle_id
                item_type = 'bundles'
            elif hasattr(item, 'branch_node'):
                item_id = item.branch_node.id
                item_type = 'branch_points'
            elif hasattr(item, 'junction_node'):
                item_id = item.junction_node.id
                item_type = 'junctions'
            else:
                return None
        else:
            # Get ID based on type
            if item_type == 'connectors':
                item_id = item.model.id
            elif item_type == 'wires':
                item_id = item.wid
            elif item_type == 'bundles':
                item_id = item.bundle_id
            elif item_type == 'branch_points':
                item_id = item.branch_node.id
            elif item_type == 'junctions':
                item_id = item.junction_node.id
            else:
                return None
        
        # Store in repository
        self.graphics_repository[item_type][item_id] = item
        
        # Remove from orphaned if it was there
        if item_id in self.orphaned_items[item_type]:
            del self.orphaned_items[item_type][item_id]
        
        return item_id
    
    def unregister_graphics_item(self, item, item_type=None):
        """Move item from repository to orphaned (when removed from scene but not deleted)"""
        if item_type is None:
            # Auto-detect type
            if hasattr(item, 'model') and hasattr(item.model, 'id'):
                item_id = item.model.id
                if hasattr(item, 'pins'):  # ConnectorItem
                    item_type = 'connectors'
                elif hasattr(item, 'wid'):  # WireItem
                    item_type = 'wires'
            elif hasattr(item, 'bundle_id'):
                item_id = item.bundle_id
                item_type = 'bundles'
            elif hasattr(item, 'branch_node'):
                item_id = item.branch_node.id
                item_type = 'branch_points'
            elif hasattr(item, 'junction_node'):
                item_id = item.junction_node.id
                item_type = 'junctions'
            else:
                return False
        else:
            if item_type == 'connectors':
                item_id = item.model.id
            elif item_type == 'wires':
                item_id = item.wid
            elif item_type == 'bundles':
                item_id = item.bundle_id
            elif item_type == 'branch_points':
                item_id = item.branch_node.id
            elif item_type == 'junctions':
                item_id = item.junction_node.id
            else:
                return False
        
        # Move from repository to orphaned
        if item_id in self.graphics_repository[item_type]:
            self.orphaned_items[item_type][item_id] = self.graphics_repository[item_type][item_id]
            del self.graphics_repository[item_type][item_id]
            return True
        
        return False
    
    def delete_graphics_item(self, item, item_type=None):
        """Completely remove item from both repository and orphaned"""
        if item_type is None:
            # Auto-detect type
            if hasattr(item, 'model') and hasattr(item.model, 'id'):
                item_id = item.model.id
                if hasattr(item, 'pins'):  # ConnectorItem
                    item_type = 'connectors'
                elif hasattr(item, 'wid'):  # WireItem
                    item_type = 'wires'
            elif hasattr(item, 'bundle_id'):
                item_id = item.bundle_id
                item_type = 'bundles'
            elif hasattr(item, 'branch_node'):
                item_id = item.branch_node.id
                item_type = 'branch_points'
            elif hasattr(item, 'junction_node'):
                item_id = item.junction_node.id
                item_type = 'junctions'
            else:
                return False
        else:
            if item_type == 'connectors':
                item_id = item.model.id
            elif item_type == 'wires':
                item_id = item.wid
            elif item_type == 'bundles':
                item_id = item.bundle_id
            elif item_type == 'branch_points':
                item_id = item.branch_node.id
            elif item_type == 'junctions':
                item_id = item.junction_node.id
            else:
                return False
        
        # Remove from both dictionaries
        if item_id in self.graphics_repository[item_type]:
            del self.graphics_repository[item_type][item_id]
        if item_id in self.orphaned_items[item_type]:
            del self.orphaned_items[item_type][item_id]
        
        return True
    
    def get_graphics_item(self, item_id, item_type):
        """Get a graphics item by ID, checking both repository and orphaned"""
        if item_id in self.graphics_repository[item_type]:
            return self.graphics_repository[item_type][item_id]
        if item_id in self.orphaned_items[item_type]:
            return self.orphaned_items[item_type][item_id]
        return None
    
    def restore_orphaned_item(self, item_id, item_type):
        """Move an item from orphaned back to repository (when re-added to scene)"""
        if item_id in self.orphaned_items[item_type]:
            item = self.orphaned_items[item_type][item_id]
            self.graphics_repository[item_type][item_id] = item
            del self.orphaned_items[item_type][item_id]
            return item
        return None