from PyQt5.QtWidgets import QToolBar, QAction, QSpinBox, QLabel, QCheckBox, QPushButton
from PyQt5.QtCore import Qt, QSize
from PyQt5.QtGui import QIcon, QColor

class BundleToolbar(QToolBar):
    """Toolbar for bundle drawing tools"""
    
    def __init__(self, main_window):
        super().__init__("Bundle Tools")
        self.main_window = main_window
        self.bundle_tool = None
        self.setIconSize(QSize(24, 24))
        self.setMovable(True)
        
        self.setup_ui()
    def route_wires_through_bundles(self):
        """Route wires through drawn bundles"""
        from utils.bundle_router import BundleRouter
        
        router = BundleRouter(self.main_window)
        router.route_wires_through_bundles()

    def setup_ui(self):
        """Setup toolbar UI"""
        
        # Draw bundle tool
        self.draw_action = QAction("✏️ Draw Bundle", self)
        self.draw_action.setCheckable(True)
        self.draw_action.setToolTip("Draw bundle segments (Start on existing item, end anywhere)")
        self.draw_action.triggered.connect(self.toggle_draw_tool)
        self.addAction(self.draw_action)
        
        self.addSeparator()
         # ROUTE WIRES BUTTON - ADD THIS
        self.route_bundles_action = QAction("🔄 Route Wires", self)
        self.route_bundles_action.setToolTip("Route all imported wires through drawn bundles")
        self.route_bundles_action.triggered.connect(self.route_wires_through_bundles)
        self.addAction(self.route_bundles_action)
        
        self.addSeparator()

        # Snap options
        self.addWidget(QLabel("Snap:"))
        
        self.snap_grid = QCheckBox("Grid")
        self.snap_grid.setChecked(True)
        self.snap_grid.stateChanged.connect(self.update_snap_settings)
        self.addWidget(self.snap_grid)
        
        self.snap_connector = QCheckBox("Connector")
        self.snap_connector.setChecked(True)
        self.snap_connector.stateChanged.connect(self.update_snap_settings)
        self.addWidget(self.snap_connector)
        
        self.snap_branch = QCheckBox("Branch")
        self.snap_branch.setChecked(True)
        self.snap_branch.stateChanged.connect(self.update_snap_settings)
        self.addWidget(self.snap_branch)
        
        self.snap_fastener = QCheckBox("Fastener")
        self.snap_fastener.setChecked(True)
        self.snap_fastener.stateChanged.connect(self.update_snap_settings)
        self.addWidget(self.snap_fastener)
        
        self.addSeparator()
        
        # Snap tolerance
        self.addWidget(QLabel("Tolerance:"))
        self.snap_tolerance = QSpinBox()
        self.snap_tolerance.setRange(5, 50)
        self.snap_tolerance.setValue(15)
        self.snap_tolerance.setSuffix(" px")
        self.snap_tolerance.valueChanged.connect(self.update_snap_tolerance)
        self.addWidget(self.snap_tolerance)
        
        self.addSeparator()
        
        # Auto-create nodes at end (always enabled)
        self.auto_nodes_label = QLabel("✓ Auto-create nodes at ends")
        self.auto_nodes_label.setStyleSheet("color: green;")
        self.addWidget(self.auto_nodes_label)
        
        self.addSeparator()
        
        # Bundle properties
        self.select_bundle = QAction("🔍 Select Bundle", self)
        self.select_bundle.triggered.connect(self.select_bundle_mode)
        self.addAction(self.select_bundle)
        
        self.edit_length = QAction("📏 Edit Length", self)
        self.edit_length.triggered.connect(self.edit_selected_length)
        self.addAction(self.edit_length)
        
        self.addSeparator()
        
        # Clear all bundles
        self.clear_bundles = QAction("🗑️ Clear Bundles", self)
        self.clear_bundles.triggered.connect(self.clear_all_bundles)
        self.addAction(self.clear_bundles)
    
    def toggle_draw_tool(self, checked):
        """Toggle bundle drawing tool"""
        if checked:
            from tools.bundle_draw_tool import BundleDrawTool
            self.bundle_tool = BundleDrawTool(self.main_window.view, self.main_window)
            
            # Apply current settings
            self.update_snap_settings()
            self.update_snap_tolerance(self.snap_tolerance.value())
            
            # Auto-create nodes is always True
            self.bundle_tool.auto_create_nodes = True
            
            # Activate tool
            self.bundle_tool.activate()
            
            self.main_window.statusBar().showMessage(
                "Bundle mode: Click on a connector/branch to start, click anywhere to end, ESC to cancel", 0
            )
        else:
            if self.bundle_tool:
                self.bundle_tool.deactivate()
                self.bundle_tool = None
                self.main_window.statusBar().showMessage("", 0)



    
    def bundle_tool_mouse_press(self, event):
        """Forward mouse press to bundle tool"""
        if self.bundle_tool:
            self.bundle_tool.mouse_press(event)
    
    def bundle_tool_mouse_move(self, event):
        """Forward mouse move to bundle tool"""
        if self.bundle_tool:
            self.bundle_tool.mouse_move(event)
    
    def bundle_tool_mouse_release(self, event):
        """Forward mouse release to bundle tool"""
        # Not used currently
        pass
    
    def update_snap_settings(self):
        """Update snap settings in bundle tool"""
        if not self.bundle_tool:
            return
        
        from tools.bundle_draw_tool import BundleDrawTool
        
        # Update snap modes
        modes = []
        if self.snap_grid.isChecked():
            modes.append(BundleDrawTool.SNAP_GRID)
        if self.snap_connector.isChecked():
            modes.append(BundleDrawTool.SNAP_CONNECTOR)
        if self.snap_branch.isChecked():
            modes.append(BundleDrawTool.SNAP_BRANCH)
        
        self.bundle_tool.snap_modes = modes
    
    def update_snap_tolerance(self, value):
        """Update snap tolerance"""
        if self.bundle_tool:
            self.bundle_tool.snap_tolerance = value
    
    def toggle_length_mode(self, checked):
        """Toggle length input mode"""
        if self.bundle_tool:
            self.bundle_tool.length_input_mode = checked
    
    def toggle_auto_nodes(self, checked):
        """Toggle auto node creation"""
        if self.bundle_tool:
            self.bundle_tool.auto_create_nodes = checked
    
    def select_bundle_mode(self):
        """Enter bundle selection mode"""
        self.main_window.statusBar().showMessage("Click on a bundle to select it", 3000)
        # This would set a selection tool
    
    def edit_selected_length(self):
        """Edit length of selected bundle"""
        selected = self.main_window.scene.selectedItems()
        bundles = [item for item in selected if hasattr(item, 'specified_length')]
        
        if not bundles:
            self.main_window.statusBar().showMessage("No bundle selected", 2000)
            return
        
        from PyQt5.QtWidgets import QInputDialog
        bundle = bundles[0]
        
        current = bundle.specified_length or bundle.length
        length, ok = QInputDialog.getDouble(
            self.main_window,
            "Edit Bundle Length",
            f"Enter length for bundle (current: {current:.0f} mm):",
            current, 0, 10000, 1
        )
        
        if ok:
            bundle.set_specified_length(length)
            self.main_window.statusBar().showMessage(f"Bundle length set to {length} mm", 2000)
    
    def clear_all_bundles(self):
        """Clear all bundles from scene"""
        from PyQt5.QtWidgets import QMessageBox
        
        reply = QMessageBox.question(
            self.main_window,
            "Clear Bundles",
            "Remove all bundle segments?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            if hasattr(self.main_window, 'bundles'):
                for bundle in self.main_window.bundles:
                    if bundle.scene():
                        self.main_window.scene.removeItem(bundle)
                self.main_window.bundles.clear()
            
            self.main_window.statusBar().showMessage("All bundles cleared", 2000)
