from PyQt5.QtCore import QPointF,Qt
from PyQt5.QtWidgets import QTreeWidgetItem
from .base_command import BaseCommand, CompoundCommand

class AddConnectorCommand(BaseCommand):
    """Add a new connector to the scene"""
    
    def __init__(self, scene, connector_item, pos: QPointF, description="Add Connector",main_window= None):
        super().__init__(description)
        self.scene = scene
        self.connector = connector_item
        self.pos = pos
        self.main_window = main_window
        main_window.conns.append(connector_item)
        main_window.wiringharness.add_connector(connector_item.model)
        self.connector_id = connector_item.model.id
        self.pin_count = len(connector_item.pins)
        self.model = self.connector.model
    def redo(self):
        if self.first_redo:
            self.first_redo = False
            return
        
        self.connector.setPos(self.pos)
        self.scene.addItem(self.connector)
        

        self.main_window.wiringharness.add_connector(self.model)
        # Setup info table if not already done
        if not hasattr(self.connector, 'info_table') or not self.connector.info_table:
            self.connector.setup_info_table()

        # Update tree
        self.main_window.refresh_tree_views()
    
    def undo(self):
        # Clean up info table first
        if hasattr(self.connector, 'info_table') and self.connector.info_table:
            if self.connector.info_table.scene():
                self.scene.removeItem(self.connector.info_table)
            self.connector.info_table.deleteLater()
            self.connector.info_table = None

        self.scene.removeItem(self.connector)
        
        # Remove from main window lists
        if hasattr(self.main_window, 'conns') and self.connector in self.main_window.conns:
            self.main_window.conns.remove(self.connector)
        
        # Update tree
        self.main_window.refresh_tree_views()
    
    def to_dict(self) -> dict:
        data = super().to_dict()
        data.update({
            'connector_id': self.connector_id,
            'pos_x': self.pos.x(),
            'pos_y': self.pos.y(),
            'pin_count': self.pin_count
        })
        return data


class DeleteConnectorCommand(CompoundCommand):
    """Delete a connector and all connected wires"""
    
    def __init__(self, main_window, scene, connector_item):
        super().__init__("Delete Connector")
        self.scene = scene
        self.main_window = main_window
        self.connector = connector_item
        self.wire_commands = []
        
        # Store connector data for recreation
        self.connector_id = connector_item.model.id
        self.pins_data = []  # Store pin wire connections
        self.wire_data_list = []  # Store wire data for recreation
        
        # Store which wires were connected to which pins
        for pin in connector_item.pins:
            # Store the wire items and their data before they're deleted
            pin_wires = list(pin.wire_items)
            wire_ids = []
            
            for wire in pin_wires:
                # Store wire data
                wire_data = {
                    'wid': wire.wid,
                    'color': wire.color_data.code if hasattr(wire, 'color_data') else 'SW',
                    'net': wire.net,
                    'from_pin': wire.start_pin,
                    'to_pin': wire.end_pin,
                    'tree_item_text': wire.tree_item.text(0) if wire.tree_item else None
                }
                self.wire_data_list.append(wire_data)
                wire_ids.append(wire.wid)
                
                # Create delete command for the wire
                from commands.wire_commands import DeleteWireCommand
                self.add_command(DeleteWireCommand(scene, wire, main_window))
            
            self.pins_data.append({
                'pin_id': pin.original_id or pin.pid,
                'wire_ids': wire_ids
            })
        
        # Store connector properties
        self.properties = {
            'part_number': getattr(connector_item, 'part_number', None),
            'manufacturer': getattr(connector_item, 'manufacturer', None),
            'pos': connector_item.pos(),
            'rotation': connector_item.model.rotation
        }
    
    def redo(self):
        # Call cleanup on connector before removing
        self.connector.cleanup()
        
        # Remove connector from scene
        self.scene.removeItem(self.connector)
        
        # Remove from main window lists
        if hasattr(self.main_window, 'conns') and self.connector in self.main_window.conns:
            self.main_window.conns.remove(self.connector)
            
        # Execute wire deletions
        super().redo()
        self.main_window.refresh_tree_views()
    
    def undo(self):
        # First, execute parent undo (which will undo wire deletions)
        super().undo()
        
        # Now recreate the connector
        from graphics.connector_item import ConnectorItem
        
        new_connector = ConnectorItem(self.connector.model)
        new_connector.setRotation(self.properties['rotation'])
        
        # Restore properties
        for key, value in self.properties.items():
            if value is not None and key not in ['pos', 'rotation']:
                setattr(new_connector, key, value)
        
        # Setup topology
        new_connector.set_topology_manager(self.main_window.topology_manager)
        new_connector.set_main_window(self.main_window)
        new_connector.create_topology_node()
        new_connector.setup_info_table()
        
        # Set position
        new_connector.setPos(self.properties['pos'])
        
        # Add to scene
        self.scene.addItem(new_connector)
        self.main_window.conns.append(new_connector)
        self.main_window.wiringharness.add_connector(new_connector.model)
        
        # Recreate tree item
        from PyQt5.QtWidgets import QTreeWidgetItem
        item = QTreeWidgetItem([new_connector.model.id])
        item.setData(0, Qt.UserRole, new_connector)
        self.main_window.objects_dock.connectors_tree.addTopLevelItem(item)
        new_connector.tree_item = item
        
        # Now recreate the wires
        from graphics.wire_item import WireItem
        from model.netlist import Netlist
        
        # Create a netlist if needed
        netlist = Netlist()
        self.main_window.topology_manager.set_netlist(netlist)
        
        for wire_data in self.wire_data_list:
            # Find the pins in the new connector
            from_pin = None
            to_pin = None
            
            # If the wire was connected to this connector at either end
            if wire_data['from_pin'].parent == self.connector:
                # Find the corresponding pin in the new connector
                pin_id = wire_data['from_pin'].original_id
                from_pin = new_connector.get_pin_by_id(pin_id)
                to_pin = wire_data['to_pin']  # This should still exist
            elif wire_data['to_pin'].parent == self.connector:
                # Find the corresponding pin in the new connector
                pin_id = wire_data['to_pin'].original_id
                to_pin = new_connector.get_pin_by_id(pin_id)
                from_pin = wire_data['from_pin']  # This should still exist
            else:
                continue  # Wire not connected to this connector? Shouldn't happen
            
            if not from_pin or not to_pin:
                continue
            
            # Create net
            net = netlist.connect(from_pin, to_pin)
            
            # Recreate the wire
            new_wire = WireItem(
                wire_data['wid'],
                from_pin,
                to_pin,
                wire_data['color'],
                net
            )
            new_wire.net = net
            
            # Add to scene
            self.scene.addItem(new_wire)
            
            # Add to main window lists
            if not hasattr(self.main_window, 'imported_wire_items'):
                self.main_window.imported_wire_items = []
            self.main_window.imported_wire_items.append(new_wire)
            
            # Create tree item
            wire_item = QTreeWidgetItem([wire_data['wid']])
            wire_item.setData(0, Qt.UserRole, new_wire)
            self.main_window.objects_dock.wires_tab.wires_tree.addTopLevelItem(wire_item)
            new_wire.tree_item = wire_item
        
        self.connector = new_connector
        self.main_window.refresh_tree_views()



class MoveConnectorCommand(BaseCommand):
    """Move a connector to a new position"""
    
    def __init__(self, connector, old_pos: QPointF, new_pos: QPointF):
        super().__init__("Move Connector")
        self.connector = connector
        self.old_pos = old_pos
        self.new_pos = new_pos
        self.moved_pins = []  # Store pin positions for debugging
    
    def redo(self):
        self.connector.setPos(self.new_pos)
        # Update connected wires
        for pin in self.connector.pins:
            for wire in pin.wire_items:
                wire.update_path()
    
    def undo(self):
        self.connector.setPos(self.old_pos)
        # Update connected wires
        for pin in self.connector.pins:
            for wire in pin.wire_items:
                wire.update_path()
    
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
    
    def redo(self):
        self.connector.setRotation(self.new_angle)
        # Update connected wires
        for pin in self.connector.pins:
            for wire in pin.wire_items:
                wire.update_path()
    
    def undo(self):
        self.connector.setRotation(self.old_angle)
        # Update connected wires
        for pin in self.connector.pins:
            for wire in pin.wire_items:
                wire.update_path()


class UpdateConnectorPropertiesCommand(BaseCommand):
    """Update connector properties (part number, name, etc.)"""
    
    def __init__(self, connector, old_props: dict, new_props: dict):
        super().__init__("Edit Connector Properties")
        self.connector = connector
        self.old_props = old_props
        self.new_props = new_props
    
    def redo(self):
        for key, value in self.new_props.items():
            setattr(self.connector, key, value)
        if hasattr(self.connector, 'info'):
            self.connector.info.update_text()
    
    def undo(self):
        for key, value in self.old_props.items():
            setattr(self.connector, key, value)
        if hasattr(self.connector, 'info'):
            self.connector.info.update_text()
