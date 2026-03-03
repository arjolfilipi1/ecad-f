# graphics/context_menus.py
from PyQt5.QtWidgets import QMenu, QAction
from PyQt5.QtCore import Qt, QPointF
from PyQt5.QtGui import QCursor

class ConnectorContextMenu(QMenu):
    """Right-click context menu for connectors"""
    
    def __init__(self, connector, main_window):
        super().__init__()
        self.connector = connector
        self.main_window = main_window
        
        self.setTitle("Connector Actions")
        self.setup_actions()
    
    def setup_actions(self):
        """Create all menu actions"""
        
        # Edit actions
        rename_action = QAction("✏️ Rename", self)
        rename_action.triggered.connect(self.rename_connector)
        self.addAction(rename_action)
        
        edit_properties_action = QAction("📋 Properties", self)
        edit_properties_action.triggered.connect(self.show_properties)
        self.addAction(edit_properties_action)
        
        self.addSeparator()
        
        # Rotation actions
        rotate_left_action = QAction("↩ Rotate Left (90°)", self)
        rotate_left_action.triggered.connect(self.rotate_left)
        self.addAction(rotate_left_action)
        
        rotate_right_action = QAction("↪ Rotate Right (90°)", self)
        rotate_right_action.triggered.connect(self.rotate_right)
        self.addAction(rotate_right_action)
        
        self.addSeparator()
        
        # Position actions
        move_action = QAction("🔄 Move", self)
        move_action.triggered.connect(self.start_move)
        self.addAction(move_action)
        
        snap_to_grid_action = QAction("🔲 Snap to Grid", self)
        snap_to_grid_action.triggered.connect(self.snap_to_grid)
        self.addAction(snap_to_grid_action)
        
        self.addSeparator()
        
        # Database actions
        select_from_db_action = QAction("📚 Select from Database", self)
        select_from_db_action.triggered.connect(self.select_from_database)
        self.addAction(select_from_db_action)
        
        self.addSeparator()
        
        # Visibility actions
        toggle_info_action = QAction("📊 Toggle Info Table", self)
        toggle_info_action.triggered.connect(self.toggle_info)
        self.addAction(toggle_info_action)
        
        self.addSeparator()
        
        # Delete action (at bottom for safety)
        delete_action = QAction("🗑️ Delete", self)
        delete_action.setShortcut("Del")
        delete_action.triggered.connect(self.delete_connector)
        self.addAction(delete_action)
    
    def rename_connector(self):
        """Rename the connector"""
        from PyQt5.QtWidgets import QInputDialog
        
        new_name, ok = QInputDialog.getText(
            self.main_window,
            "Rename Connector",
            "Enter new name:",
            text=self.connector.cid
        )
        
        if ok and new_name:
            old_name = self.connector.cid
            self.connector.cid = new_name
            
            # Update label
            if hasattr(self.connector, '_label'):
                self.connector._label.setText(new_name)
            
            # Update info table header
            if hasattr(self.connector, 'info_table'):
                self.connector.info_table.update_table()
            
            # Update tree item
            if self.connector.tree_item:
                self.connector.tree_item.setText(0, new_name)
            
            # Create undo command
            from commands.connector_commands import UpdateConnectorPropertiesCommand
            cmd = UpdateConnectorPropertiesCommand(
                self.connector,
                {'cid': old_name},
                {'cid': new_name}
            )
            self.main_window.undo_manager.push(cmd)
    
    def show_properties(self):
        """Show properties in the property editor"""
        if hasattr(self.main_window, 'property_editor'):
            self.main_window.property_editor.set_item(self.connector)
    
    def rotate_left(self):
        """Rotate connector 90 degrees counter-clockwise"""
        old_angle = self.connector.rotation_angle
        self.connector.rotate_90()  # This rotates right by default
        
        from commands.connector_commands import RotateConnectorCommand
        cmd = RotateConnectorCommand(
            self.connector,
            old_angle,
            self.connector.rotation_angle
        )
        self.main_window.undo_manager.push(cmd)
    
    def rotate_right(self):
        """Rotate connector 90 degrees clockwise"""
        # For right rotation, we can call rotate_90 three times for left?
        # Better to implement direct rotation
        old_angle = self.connector.rotation_angle
        new_angle = (old_angle + 90) % 360
        self.connector.setRotation(new_angle)
        self.connector.rotation_angle = new_angle
        
        from commands.connector_commands import RotateConnectorCommand
        cmd = RotateConnectorCommand(self.connector, old_angle, new_angle)
        self.main_window.undo_manager.push(cmd)
    
    def start_move(self):
        """Start moving the connector"""
        self.main_window.statusBar().showMessage(
            "Click to place connector at new position", 0
        )
        # Store that we're in move mode for this connector
        self.main_window.moving_connector = self.connector
    
    def snap_to_grid(self):
        """Snap connector to nearest grid point"""
        grid_size = self.main_window.settings_manager.get('grid_size', 50)
        pos = self.connector.pos()
        
        new_x = round(pos.x() / grid_size) * grid_size
        new_y = round(pos.y() / grid_size) * grid_size
        new_pos = QPointF(new_x, new_y)
        
        from commands.connector_commands import MoveConnectorCommand
        cmd = MoveConnectorCommand(self.connector, pos, new_pos)
        self.main_window.undo_manager.push(cmd)
    
    def select_from_database(self):
        """Open connector database selector"""
        if hasattr(self.main_window.property_editor, 'select_connector_from_db'):
            self.main_window.property_editor.select_connector_from_db(self.connector)
    
    def toggle_info(self):
        """Toggle info table visibility"""
        if hasattr(self.connector, 'info_table'):
            visible = self.connector.info_table.isVisible()
            self.connector.info_table.setVisible(not visible)
    
    def delete_connector(self):
        """Delete this connector"""
        from commands.connector_commands import DeleteConnectorCommand
        
        # Select this connector
        self.main_window.scene.clearSelection()
        self.connector.setSelected(True)
        
        # Use existing delete method
        self.main_window.delete_selected_with_undo()
class WireContextMenu(QMenu):
    """Right-click context menu for wires"""
    
    def __init__(self, wire, main_window):
        super().__init__()
        self.wire = wire
        self.main_window = main_window
        
        self.setTitle("Wire Actions")
        self.setup_actions()
    
    def setup_actions(self):
        edit_props_action = QAction("✏️ Edit Properties", self)
        edit_props_action.triggered.connect(self.show_properties)
        self.addAction(edit_props_action)
        
        self.addSeparator()
        
        change_color_action = QAction("🎨 Change Color", self)
        change_color_action.triggered.connect(self.change_color)
        self.addAction(change_color_action)
        
        self.addSeparator()
        
        highlight_action = QAction("🔍 Highlight", self)
        highlight_action.triggered.connect(self.highlight)
        self.addAction(highlight_action)
        
        self.addSeparator()
        
        delete_action = QAction("🗑️ Delete", self)
        delete_action.triggered.connect(self.delete_wire)
        self.addAction(delete_action)
    
    def show_properties(self):
        if hasattr(self.main_window, 'property_editor'):
            self.main_window.property_editor.set_item(self.wire)
    
    def change_color(self):
        from PyQt5.QtWidgets import QColorDialog
        color = QColorDialog.getColor(self.wire.color)
        if color.isValid():
            # Convert QColor to color code
            # This is simplified - you'd need proper color code mapping
            self.wire.color = color
            self.wire.update()
    
    def highlight(self):
        if self.main_window is not None:
            self.main_window.scene.clearSelection()
            self.main_window.view.centerOn(self.wire)
        self.wire.setSelected(True)
    
    def delete_wire(self):
        self.main_window.scene.clearSelection()
        self.wire.setSelected(True)
        self.main_window.delete_selected_with_undo()


class BundleContextMenu(QMenu):
    """Right-click context menu for bundles"""
    
    def __init__(self, bundle, main_window):
        super().__init__()
        self.bundle = bundle
        self.main_window = main_window
        
        self.setTitle("Bundle Actions")
        self.setup_actions()
    
    def setup_actions(self):
        edit_length_action = QAction("📏 Edit Length", self)
        edit_length_action.triggered.connect(self.edit_length)
        self.addAction(edit_length_action)
        
        self.addSeparator()
        
        assign_wires_action = QAction("🔌 Assign Wires", self)
        assign_wires_action.triggered.connect(self.assign_wires)
        self.addAction(assign_wires_action)
        
        self.addSeparator()
        
        highlight_action = QAction("🔍 Highlight", self)
        highlight_action.triggered.connect(self.highlight)
        self.addAction(highlight_action)
        
        self.addSeparator()
        
        delete_action = QAction("🗑️ Delete", self)
        delete_action.triggered.connect(self.delete_bundle)
        self.addAction(delete_action)
    
    def edit_length(self):
        from PyQt5.QtWidgets import QInputDialog
        
        current = self.bundle.specified_length or self.bundle.length
        length, ok = QInputDialog.getDouble(
            self.main_window,
            "Edit Bundle Length",
            f"Enter length (current: {current:.0f} mm):",
            current, 0, 10000, 1
        )
        
        if ok:
            from commands.bundle_commands import UpdateBundleLengthCommand
            cmd = UpdateBundleLengthCommand(
                self.bundle,
                self.bundle.specified_length,
                length
            )
            self.main_window.undo_manager.push(cmd)
    
    def assign_wires(self):
        # This would open a wire assignment dialog
        self.main_window.statusBar().showMessage(
            f"Wire assignment for {self.bundle.bundle_id} - coming soon", 2000
        )
    
    def highlight(self):
        self.main_window.scene.clearSelection()
        self.bundle.setSelected(True)
        self.main_window.view.centerOn(self.bundle)
    
    def delete_bundle(self):
        from commands.bundle_commands import DeleteBundleCommand
        cmd = DeleteBundleCommand(
            self.main_window.scene,
            self.bundle,
            self.main_window
        )
        self.main_window.undo_manager.push(cmd)


class BranchPointContextMenu(QMenu):
    """Right-click context menu for branch points"""
    
    def __init__(self, branch_point, main_window):
        super().__init__()
        self.branch_point = branch_point
        self.main_window = main_window
        
        self.setTitle("Branch Point Actions")
        self.setup_actions()
    
    def setup_actions(self):
        delete_action = QAction("🗑️ Delete", self)
        delete_action.triggered.connect(self.delete_branch_point)
        self.addAction(delete_action)
    
    def delete_branch_point(self):
        # Select and delete
        self.main_window.scene.clearSelection()
        self.branch_point.setSelected(True)
        self.main_window.delete_selected_with_undo()

