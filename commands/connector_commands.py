from PyQt5.QtCore import QPointF,Qt
from PyQt5.QtWidgets import QTreeWidgetItem
from .base_command import BaseCommand, CompoundCommand

class AddConnectorCommand(BaseCommand):
    """Add a new connector to the scene"""
    
    def __init__(self, scene, connector_item, pos: QPointF, description="Add Connector", main_window=None):
        super().__init__(description)
        self.scene = scene
        self.connector = connector_item
        self.pos = pos
        self.main_window = main_window
        self.connector_id = connector_item.model.id
        self.pin_count = len(connector_item.pins)
        self.model = self.connector.model
        self._initialized = False
        self._tree_item = None
    
    def _initialize(self):
        """First time execution"""
        self._execute()
    
    def _redo(self):
        """Subsequent redos"""
        self._execute()
    
    def _execute(self):
        print("add conn")
        """Common execution logic"""
        # Skip if already in scene
        if self.connector.scene() == self.scene:
            return
            
        self.model.graphics_item = self.connector
        self.connector.setPos(self.pos)
        self.scene.addItem(self.connector)
        self.main_window.wiringharness.add_connector(self.model)
        
        # Setup info table if not already done
        if not hasattr(self.connector, 'info_table') or not self.connector.info_table:
            self.connector.setup_info_table()
        
        # Create tree item if needed
        if not self.connector.tree_item:
            item = QTreeWidgetItem([self.connector.model.id])
            item.setData(0, Qt.UserRole, self.connector)
            if hasattr(self.main_window, 'objects_dock'):
                self.main_window.objects_dock.connectors_tree.addTopLevelItem(item)
            self.connector.tree_item = item
            self._tree_item = item
        self.connector.info_table.refresh()
        self.main_window.refresh_tree_views()
    
    def undo(self):
        print("unadd conn")
        """Undo the command"""
        # Clean up info table
        if hasattr(self.connector, 'info_table') and self.connector.info_table:
            try:
                if self.connector.info_table.scene():
                    self.scene.removeItem(self.connector.info_table)
                self.connector.info_table.deleteLater()
            except RuntimeError:
                pass
            self.connector.info_table = None
        
        # Remove from scene
        if self.connector.scene() == self.scene:
            self.scene.removeItem(self.connector)
        else:
            print("connector was already removed")
            
        # Remove from harness
        if self.model.id in self.main_window.wiringharness.connectors:
            self.main_window.wiringharness.remove_connector(self.model)
        
        # Remove tree item
        if self.connector.tree_item:
            try:
                tree = self.connector.tree_item.treeWidget()
                if tree and not sip.isdeleted(tree):
                    index = tree.indexOfTopLevelItem(self.connector.tree_item)
                    if index >= 0:
                        tree.takeTopLevelItem(index)
            except RuntimeError:
                pass
            self.connector.tree_item = None
        
        self.main_window.refresh_tree_views()
    
    def redo(self):
        """Override to use the new pattern"""
        if not self._initialized:
            self._initialized = True
            self._initialize()
        else:
            self._redo()


class DeleteConnectorCommand(CompoundCommand):
    """Delete a connector and all connected wires"""
    
    def __init__(self, main_window, scene, connector_item):
        super().__init__("Delete Connector")
        self.main_window = main_window
        self.scene = scene
        self.connector = connector_item
        self._initialized = False
        
        # Store connector data for recreation
        self.connector_id = connector_item.model.id
        self.model = connector_item.model
        self.position = connector_item.pos()
        self.rotation = connector_item.model.rotation
        
        # Store pin data and wire connections
        self.pins_data = []
        self.connected_wires = []  # Store wires that were connected to this connector
        
        # Store wire connections but DON'T delete them
        for pin in connector_item.pins:
            pin_wires = list(pin.wire_items)
            wire_ids = []
            
            for wire in pin_wires:
                # Store wire reference
                if wire not in self.connected_wires:
                    self.connected_wires.append(wire)
                
                # Store which pin this wire was connected to
                wire_ids.append({
                    'wire': wire,
                    'wire_id': wire.wid,
                    'pin_id': pin.model.pid
                })
            
            self.pins_data.append({
                'pin_id': pin.model.pid,
                'wire_ids': wire_ids
            })
    

    
    def _initialize(self):
        """First time execution"""
        self._execute()
    
    def _redo(self):
        """Subsequent redos"""
        self._execute()
    
    def _execute(self):
        print("delete conn")
        """Execute the deletion - remove connector but keep wires"""
        
        # First, disconnect all wires from this connector's pins
        for pin in self.connector.pins:
            # Clear wire references from pin model
            if pin.model.wire_ids:
                if isinstance(pin.model.wire_ids, list):
                    pin.model.wire_ids.clear()
                else:
                    pin.model.wire_ids = None
            
            # Remove wire references from pin graphics
            wire_items = list(pin.wire_items)  # Make a copy
            for wire in wire_items:
                if wire in pin.wire_items:
                    pin.wire_items.remove(wire)

        
        # Call cleanup on connector
        self.connector.cleanup()
        
        # Remove connector from scene
        if self.connector.scene() == self.scene:
            self.scene.removeItem(self.connector)
        else:
            print("connector was already removed")
        # Remove from harness
        if self.model.id in self.main_window.wiringharness.connectors:
            del self.main_window.wiringharness.connectors[self.model.id]
        
        # Update wire paths (they're now disconnected at one end)
        for wire in self.connected_wires:
            try:
                wire.update_path()
                wire.update()
            except RuntimeError:
                pass
        
        self.main_window.refresh_tree_views()

        self.main_window.refresh_tree_views()
    
    def undo(self):
        print("undelete conn")
        """Undo the deletion"""
        # First, recreate the connector
        from graphics.connector_item import ConnectorItem
        
        new_connector = ConnectorItem(self.model)
        new_connector.setRotation(self.rotation)
        new_connector.setPos(self.position)
        
        # Setup topology
        new_connector.set_topology_manager(self.main_window.topology_manager)
        new_connector.set_main_window(self.main_window)
        new_connector.create_topology_node()
        new_connector.setup_info_table()
        
        # Add to scene
        self.scene.addItem(new_connector)
        self.connector = new_connector
        self.main_window.conns.append(new_connector)
        self.main_window.wiringharness.add_connector(self.model)
        
        # Create tree item
        item = QTreeWidgetItem([self.model.id])
        item.setData(0, Qt.UserRole, new_connector)
        if hasattr(self.main_window, 'objects_dock'):
            self.main_window.objects_dock.connectors_tree.addTopLevelItem(item)
        new_connector.tree_item = item
        # Reconnect wires to their original pins
        for pin_data in self.pins_data:
            # Find the pin in the new connector
            pin = new_connector.get_pin_by_id(pin_data['pin_id'])
            if not pin:
                continue
            
            # Reconnect each wire that was connected to this pin
            for wire_info in pin_data['wire_ids']:
                wire = wire_info['wire']
                
                # Check which end of the wire was connected to this connector
                if wire.start_pin and wire.start_pin.parent == self.connector:
                    # This connector was the start - reconnect start pin
                    wire.start_pin = pin
                    pin.add_wire(wire)
                    if wire.model:
                        wire.model.from_pin = pin.model.pid
                        wire.model.from_node_id = self.model.id
                
                elif wire.end_pin and wire.end_pin.parent == self.connector:
                    # This connector was the end - reconnect end pin
                    wire.end_pin = pin
                    pin.add_wire(wire)
                    if wire.model:
                        wire.model.to_pin = pin.model.pid
                        wire.model.to_node_id = self.model.id
                
                # Update pin model wire reference
                if not pin.model.wire_ids:
                    pin.model.wire_ids = []
                if isinstance(pin.model.wire_ids, list):
                    if wire.wid not in pin.model.wire_ids:
                        pin.model.wire_ids.append(wire.wid)

        self.connector = new_connector
        # Update all affected wires
        for wire in self.connected_wires:
            try:
                wire.update_path()
                wire.update()
            except RuntimeError:
                pass

        # Now undo wire deletions (recreate wires)
        super().undo()
        
        self.main_window.refresh_tree_views()
    
    def redo(self):
        """Override to use the new pattern"""
        if not self._initialized:
            self._initialized = True
            self._execute()
        else:
            super().redo()  # This will call the CompoundCommand's redo which executes all child commands


class MoveConnectorCommand(BaseCommand):
    """Move a connector to a new position"""
    
    def __init__(self, connector, old_pos: QPointF, new_pos: QPointF):
        super().__init__("Move Connector")
        self.connector = connector
        self.old_pos = old_pos
        self.new_pos = new_pos
        self._initialized = False
    
    def _initialize(self):
        """First time execution - shouldn't happen for move commands"""
        self._redo()
    
    def _redo(self):
        """Execute the move"""
        self.connector.setPos(self.new_pos)
        self._update_connected_wires()
        self.connector.model.position = [self.new_pos.x(), self.new_pos.y()]
    
    def undo(self):
        """Undo the move"""
        self.connector.setPos(self.old_pos)
        self._update_connected_wires()
        self.connector.model.position = [self.old_pos.x(), self.old_pos.y()]
    
    def _update_connected_wires(self):
        """Update all wires connected to this connector"""
        for pin in self.connector.pins:
            for wire in pin.wire_items:
                try:
                    wire.update_path()
                except RuntimeError:
                    pass  # Wire might be deleted
    
    def redo(self):
        """Override to use the new pattern"""
        if not self._initialized:
            self._initialized = True
            self._initialize()
        else:
            self._redo()
    
    def mergeWith(self, other) -> bool:
        """Merge consecutive move commands"""
        if not isinstance(other, MoveConnectorCommand):
            return False
        if other.connector != self.connector:
            return False
        
        # Merge by taking the final position
        self.new_pos = other.new_pos
        return True


class RotateConnectorCommand(BaseCommand):
    """Rotate a connector"""
    
    def __init__(self, connector, old_angle: float, new_angle: float):
        super().__init__("Rotate Connector")
        self.connector = connector
        self.old_angle = old_angle
        self.new_angle = new_angle
        self._initialized = False
    
    def _initialize(self):
        """First time execution"""
        self._redo()
    
    def _redo(self):
        """Execute the rotation"""
        self.connector.setRotation(self.new_angle)
        self.connector.model.rotation = self.new_angle
        self._update_connected_wires()
    
    def undo(self):
        """Undo the rotation"""
        self.connector.setRotation(self.old_angle)
        self.connector.model.rotation = self.old_angle
        self._update_connected_wires()
    
    def _update_connected_wires(self):
        """Update all wires connected to this connector"""
        for pin in self.connector.pins:
            for wire in pin.wire_items:
                try:
                    wire.update_path()
                except RuntimeError:
                    pass
    
    def redo(self):
        """Override to use the new pattern"""
        if not self._initialized:
            self._initialized = True
            self._initialize()
        else:
            self._redo()


class UpdateConnectorPropertiesCommand(BaseCommand):
    """Update connector properties (part number, name, etc.)"""
    
    def __init__(self, connector, old_props: dict, new_props: dict):
        super().__init__("Edit Connector Properties")
        self.connector = connector
        self.old_props = old_props
        self.new_props = new_props
        self._initialized = False
    
    def _initialize(self):
        """First time execution"""
        self._redo()
    
    def _redo(self):
        """Apply new properties"""
        for key, value in self.new_props.items():
            if hasattr(self.connector, key):
                setattr(self.connector, key, value)
            elif hasattr(self.connector.model, key):
                setattr(self.connector.model, key, value)
        
        # Update display
        if hasattr(self.connector, 'info_table'):
            self.connector.info_table.update_table()
        if hasattr(self.connector, '_label'):
            self.connector._label.setText(self.connector.model.id)
    
    def undo(self):
        """Revert to old properties"""
        for key, value in self.old_props.items():
            if hasattr(self.connector, key):
                setattr(self.connector, key, value)
            elif hasattr(self.connector.model, key):
                setattr(self.connector.model, key, value)
        
        # Update display
        if hasattr(self.connector, 'info_table'):
            self.connector.info_table.update_table()
        if hasattr(self.connector, '_label'):
            self.connector._label.setText(self.connector.model.id)
    
    def redo(self):
        """Override to use the new pattern"""
        if not self._initialized:
            self._initialized = True
            self._initialize()
        else:
            self._redo()

