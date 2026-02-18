from .base_command import BaseCommand, CompoundCommand
from PyQt5.QtWidgets import QTreeWidgetItem
from PyQt5.QtCore import Qt
class AddWireCommand(BaseCommand):
    """Add a new wire between two pins"""
    
    def __init__(self, scene, wire_item, from_pin, to_pin, description="Add Wire",main_window = None):
        super().__init__(description)
        self.scene = scene
        self.main_window = main_window
        self.wire = wire_item
        self.wire_id = wire_item.wid
        self.from_pin = from_pin
        self.to_pin = to_pin
        self.color = wire_item.color_data.code if hasattr(wire_item, 'color_data') else 'SW'
        self.net = wire_item.net
    
    def redo(self):
        if self.first_redo:
            self.first_redo = False
            return
        
        self.scene.addItem(self.wire)
        self.from_pin.wires.append(self.wire)
        self.to_pin.wires.append(self.wire)
        
        # Add to main window lists
        if hasattr(self.main_window, 'wires'):
            self.main_window.wires.append(self.wire)
        if hasattr(self.main_window, 'imported_wire_items'):
            self.main_window.imported_wire_items.append(self.wire)
        
        self.main_window.refresh_tree_views()
    
    def undo(self):
        self.scene.removeItem(self.wire)
        if self.wire in self.from_pin.wires:
            self.from_pin.wires.remove(self.wire)
        if self.wire in self.to_pin.wires:
            self.to_pin.wires.remove(self.wire)
        
        # Remove from main window lists
        if hasattr(self.main_window, 'wires') and self.wire in self.main_window.wires:
            self.main_window.wires.remove(self.wire)
        if hasattr(self.main_window, 'imported_wire_items') and self.wire in self.scene.parent().imported_wire_items:
            self.main_window.imported_wire_items.remove(self.wire)
        
        self.main_window.refresh_tree_views()


class DeleteWireCommand(BaseCommand):
    """Delete a wire"""
    
    def __init__(self, scene, wire_item,main_window):
        super().__init__("Delete Wire")
        self.scene = scene
        self.main_window = main_window
        self.wire = wire_item
        self.wire_id = wire_item.wid
        self.from_pin = wire_item.start_pin
        self.to_pin = wire_item.end_pin
        self.color = wire_item.color_data.code if hasattr(wire_item, 'color_data') else 'SW'
        self.net = wire_item.net
        self.wire_data = getattr(wire_item, 'wire_data', None)
        self.tree_item_text = None
        if wire_item.tree_item:
            self.tree_item_text = wire_item.tree_item.text(0)

    
    def redo(self):
        # Call cleanup
        self.wire.cleanup()

        # Remove from scene
        self.scene.removeItem(self.wire)
        
        # Remove from pins
        if self.wire in self.from_pin.wires:
            self.from_pin.wires.remove(self.wire)
        if self.wire in self.to_pin.wires:
            self.to_pin.wires.remove(self.wire)
        
        # Remove from main window lists
        if hasattr(self.main_window, 'wires') and self.wire in self.main_window.wires:
            self.main_window.wires.remove(self.wire)
        if hasattr(self.main_window, 'imported_wire_items') and self.wire in self.main_window.imported_wire_items:
            self.main_window.imported_wire_items.remove(self.wire)
        
        self.main_window.refresh_tree_views()

    
    def undo(self):
        from graphics.wire_item import WireItem
        new_wire = WireItem(
            self.wire_id,
            self.from_pin,
            self.to_pin,
            self.color,
            self.net
        )
        new_wire.wire_data = self.wire_data
        new_wire.net = self.net
        
        self.scene.addItem(new_wire)
        self.from_pin.wires.append(new_wire)
        self.to_pin.wires.append(new_wire)
        
        # Create NEW tree item (don't try to reuse old one)
        item = QTreeWidgetItem([self.tree_item_text or new_wire.wid])
        item.setData(0, Qt.UserRole, new_wire)
        self.main_window.wires_tree.addTopLevelItem(item)
        new_wire.tree_item = item
        
        self.wire = new_wire
        
        # Add to main window lists
        self.main_window.wires.append(new_wire)
        self.main_window.imported_wire_items.append(new_wire)
        
        # Refresh tree to ensure consistency
        self.main_window.refresh_tree_views()




class UpdateWirePropertiesCommand(BaseCommand):
    """Update wire properties (color, signal, etc.)"""
    
    def __init__(self, wire, old_props: dict, new_props: dict):
        super().__init__("Edit Wire Properties")
        self.wire = wire
        self.old_props = old_props
        self.new_props = new_props
    
    def redo(self):
        for key, value in self.new_props.items():
            setattr(self.wire, key, value)
        if hasattr(self.wire, 'update_path'):
            self.wire.update_path()
    
    def undo(self):
        for key, value in self.old_props.items():
            setattr(self.wire, key, value)
        if hasattr(self.wire, 'update_path'):
            self.wire.update_path()


class RouteWiresCommand(CompoundCommand):
    """Convert direct wires to routed topology"""
    
    def __init__(self, main_window, wire_items, branch_points, segments):
        super().__init__("Create Branches")
        self.main_window = main_window
        self.wire_items = wire_items
        self.branch_points = branch_points
        self.segments = segments
        self.original_wire_visibility = []
        
        # Store original wire visibility
        for wire in wire_items:
            self.original_wire_visibility.append(wire.isVisible())
    
    def redo(self):
        # Hide original wires
        for wire in self.wire_items:
            wire.setVisible(False)
        
        # Add branch points and segments to scene
        for bp in self.branch_points:
            self.main_window.scene.addItem(bp)
        for seg in self.segments:
            self.main_window.scene.addItem(seg)
        
        # Add routed wires
        if hasattr(self.main_window, 'routed_wire_items'):
            for wire in self.main_window.routed_wire_items:
                self.main_window.scene.addItem(wire)
        
        # Update visualization
        if hasattr(self.main_window, 'viz_manager'):
            self.main_window.viz_manager.on_auto_route_complete()
        
        self.main_window.refresh_tree_views()
    
    def undo(self):
        # Show original wires
        for wire, visible in zip(self.wire_items, self.original_wire_visibility):
            wire.setVisible(visible)
        
        # Remove branch points and segments
        for bp in self.branch_points:
            if bp.scene():
                self.main_window.scene.removeItem(bp)
        for seg in self.segments:
            if seg.scene():
                self.main_window.scene.removeItem(seg)
        
        # Remove routed wires
        if hasattr(self.main_window, 'routed_wire_items'):
            for wire in self.main_window.routed_wire_items:
                if wire.scene():
                    self.main_window.scene.removeItem(wire)
        
        # Update visualization
        if hasattr(self.main_window, 'viz_manager'):
            self.main_window.viz_manager.on_clear_topology()
        
        self.main_window.refresh_tree_views()
