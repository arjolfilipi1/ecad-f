"""
Main window for ECAD application
Combines all UI components and manages the main application state
"""

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

# Import UI components
from ui.objects_dock import ObjectsDock
from ui.wires_tab import WiresTab

# Import controllers
from controllers.project_controller import ProjectController
from controllers.selection_controller import SelectionController

# Import menus
from menus.file_menu import FileMenu
from menus.edit_menu import EditMenu
from menus.tools_menu import ToolsMenu
from menus.test_menu import TestMenu

# Import toolbars
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
        self.setup_ui()
        self.setup_connections()
        self.setup_shortcuts()
        self.wiringharness = WiringHarness()
        
        self.topology_manager = TopologyManager(self)
        self.update_dispatcher = UpdateDispatcher()
        self.viz_manager = VisualizationManager(self)
        self.project_handler = ProjectFileHandler()
        
        # Connect signals
        self.update_dispatcher.connector_moved.connect(self.on_connector_moved)
        self.update_dispatcher.connector_rotated.connect(self.on_connector_moved)
        
        # Data containers
        self.conns = []
        self.wires = []
        self.bundles = []
        self.imported_wire_items = []
        self.routed_wire_items = []
        self.moving_connector = None
        
        
        
        # Apply theme
        self.setStyleSheet(self.settings_manager.get_theme_stylesheet())
        
        # Final setup
        self.refresh_connector_labels()
        self.statusBar().showMessage("Loading complete...", 0)
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
    
    def show_props(self):
        """Create and show property editor dock"""
        from graphics.property_editor import PropertyEditor
        
        self.props = QDockWidget("Properties")
        self.property_editor = PropertyEditor(self)
        self.props.setWidget(self.property_editor)
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
        for item in self.conns:
            if isinstance(item, ConnectorItem):
                item.info.update_text()
                item.info_table.update_table()
    
    def refresh_tree_views(self):
        """Refresh tree widget contents"""
        if hasattr(self.objects_dock, 'connectors_tree'):
            self.objects_dock.refresh_trees(self.conns, self.get_all_wires())
    
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
        wire_items = []
        if hasattr(self, 'routed_wire_items'):
            wire_items.extend(self.routed_wire_items)
        if hasattr(self, 'imported_wire_items'):
            wire_items.extend(self.imported_wire_items)
        return wire_items
    
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
        
        pos = self.view.mapToScene(self.view.mapFromGlobal(QCursor.pos()))
        bp_node = self.topology_manager.create_branch_point((pos.x(), pos.y()))
        bp_graphics = BranchPointGraphicsItem(bp_node)
        self.scene.addItem(bp_graphics)
        bp_graphics.setSelected(True)
        self.statusBar().showMessage(f"Branch point added at ({pos.x():.0f}, {pos.y():.0f})", 2000)
    
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
        from utils.excel_import import import_from_excel_to_topology
        
        filepath, _ = QFileDialog.getOpenFileName(
            self, "Import Wire List", "", "Excel Files (*.xlsx *.xls);;CSV Files (*.csv)"
        )
        
        if filepath:
            success = import_from_excel_to_topology(
                filepath, self.topology_manager, self, auto_route=False
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
        print(self.conns)
        print(self.wiringharness.connectors)
        
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
        
        name, ok = QInputDialog.getText(self, "New Project", "Project Name:")
        if ok and name:
            self.clear_scene()
            self.project_handler.new_project(name)
            self.setWindowTitle(f"ECAD - {name}")
            self.statusBar().showMessage(f"Created new project: {name}", 3000)
    
    def open_project(self, filepath=None):
        """Open an existing project"""
        filepath = filepath or self.settings_manager.get('database_path', '.')
        ProjectController.open_project(self, filepath)
    
    def save_project(self):
        """Save current project"""
        ProjectController.save_project(self)
    
    def save_project_as(self):
        """Save project with new name"""
        ProjectController.save_project_as(self)
    
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
        
        if hasattr(self, 'bundles'):
            for bundle in self.bundles:
                bundle.cleanup()
            self.bundles.clear()
        
        self.wires.clear()
        
        self.topology_manager.nodes.clear()
        self.topology_manager.segments.clear()
        self.topology_manager.wires.clear()
        
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
