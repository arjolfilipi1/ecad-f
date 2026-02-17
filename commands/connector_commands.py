from PyQt5.QtCore import QPointF
from .base_command import BaseCommand, CompoundCommand

class AddConnectorCommand(BaseCommand):
    """Add a new connector to the scene"""
    
    def __init__(self, scene, connector_item, pos: QPointF, description="Add Connector"):
        super().__init__(description)
        self.scene = scene
        self.connector = connector_item
        self.pos = pos
        self.connector_id = connector_item.cid
        self.pin_count = len(connector_item.pins)
    
    def redo(self):
        if self.first_redo:
            self.first_redo = False
            return
        
        self.connector.setPos(self.pos)
        self.scene.addItem(self.connector)
        
        # Add to main window lists
        if hasattr(self.scene.parent(), 'conns'):
            self.scene.parent().conns.append(self.connector)
        
        # Update tree
        self.scene.parent().refresh_tree_views()
    
    def undo(self):
        self.scene.removeItem(self.connector)
        
        # Remove from main window lists
        if hasattr(self.scene.parent(), 'conns') and self.connector in self.scene.parent().conns:
            self.scene.parent().conns.remove(self.connector)
        
        # Update tree
        self.scene.parent().refresh_tree_views()
    
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
    
    def __init__(self,main_window, scene, connector_item):
        super().__init__("Delete Connector")
        self.scene = scene
        self.main_window = main_window
        self.connector = connector_item
        self.connector_id = connector_item.cid
        self.original_pos = connector_item.pos()
        self.wire_commands = []
        
        # Find all connected wires and create delete commands for them
        for pin in connector_item.pins:
            for wire in list(pin.wires):  # Copy list to avoid modification during iteration
                from commands.wire_commands import DeleteWireCommand
                self.add_command(DeleteWireCommand(scene, wire,self.main_window))
        
        # Store connector data for recreation
        self.pin_ids = connector_item.pin_ids
        self.properties = {
            'part_number': getattr(connector_item, 'part_number', None),
            'manufacturer': getattr(connector_item, 'manufacturer', None),
            'name': connector_item.cid
        }
    
    def redo(self):
        # Remove connector from scene
        self.scene.removeItem(self.connector)
        
        # Remove from main window lists
        if hasattr(self.scene.parent(), 'conns') and self.connector in self.scene.parent().conns:
            self.scene.parent().conns.remove(self.connector)
        
        # Execute wire deletions
        super().redo()
        
        self.main_window.refresh_tree_views()
    
    def undo(self):
        # Recreate connector
        from graphics.connector_item import ConnectorItem
        new_connector = ConnectorItem(
            self.original_pos.x(),
            self.original_pos.y(),
            pins=self.pin_ids
        )
        new_connector.cid = self.connector_id
        
        # Restore properties
        for key, value in self.properties.items():
            if value is not None:
                setattr(new_connector, key, value)
        
        # Setup topology
        new_connector.set_topology_manager(self.scene.parent().topology_manager)
        new_connector.set_main_window(self.scene.parent())
        new_connector.create_topology_node()
        
        self.scene.addItem(new_connector)
        self.scene.parent().conns.append(new_connector)
        self.connector = new_connector
        
        # Undo wire deletions (recreate wires)
        super().undo()
        
        self.scene.parent().refresh_tree_views()


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
            for wire in pin.wires:
                wire.update_path()
    
    def undo(self):
        self.connector.setPos(self.old_pos)
        # Update connected wires
        for pin in self.connector.pins:
            for wire in pin.wires:
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
            for wire in pin.wires:
                wire.update_path()
    
    def undo(self):
        self.connector.setRotation(self.old_angle)
        # Update connected wires
        for pin in self.connector.pins:
            for wire in pin.wires:
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
