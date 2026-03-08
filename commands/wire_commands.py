from .base_command import BaseCommand, CompoundCommand
from PyQt5.QtWidgets import QTreeWidgetItem
from PyQt5.QtCore import Qt
from PyQt5 import sip
class AddWireCommand(BaseCommand):
    """Add a new wire between two pins"""
    
    def __init__(self, scene, wire_item, from_pin, to_pin, description="Add Wire", main_window=None):
        super().__init__(description)
        self.scene = scene
        self.main_window = main_window
        self.wire = wire_item
        self.wire_id = wire_item.wid
        self.wire_model = wire_item.model  # Store the wire model
        self.from_pin = from_pin
        self.to_pin = to_pin
        self.color = wire_item.color_data.code if hasattr(wire_item, 'color_data') else 'SW'
        self.net = wire_item.net
    
    def redo(self):
        if self.first_redo:
            self.first_redo = False
            return
        
        self.scene.addItem(self.wire)
        self.from_pin.add_wire(self.wire)
        self.to_pin.add_wire(self.wire)
        
        # Add wire model to wiringharness
        if self.main_window and hasattr(self.main_window, 'wiringharness'):
            self.main_window.wiringharness.add_wire(self.wire_model)
        
        # Add to main window lists
        if hasattr(self.main_window, 'wires'):
            self.main_window.wires.append(self.wire)
        if hasattr(self.main_window, 'imported_wire_items'):
            self.main_window.imported_wire_items.append(self.wire)
        self._refresh_connector_tables()
        self.main_window.refresh_tree_views()
    
    def undo(self):
        self.scene.removeItem(self.wire_model.graphics_item)
        
        # Remove wire model from wiringharness
        if self.main_window and hasattr(self.main_window, 'wiringharness'):
            if self.wire_id in self.main_window.wiringharness.wires:
                del self.main_window.wiringharness.wires[self.wire_id]
        
        # Remove from pins - FIX: Check by wire_id, not the wire object itself
        if self.from_pin.model.wire_id:
            if isinstance(self.from_pin.model.wire_id, list):
                # If it's a list, remove by id
                self.from_pin.model.wire_id = [w for w in self.from_pin.model.wire_id 
                                               if getattr(w, 'wid', None) != self.wire_id]
            else:
                # If it's a single string, clear it
                self.from_pin.model.wire_id = None
        
        if self.to_pin.model.wire_id:
            if isinstance(self.to_pin.model.wire_id, list):
                self.to_pin.model.wire_id = [w for w in self.to_pin.model.wire_id 
                                             if getattr(w, 'wid', None) != self.wire_id]
            else:
                self.to_pin.model.wire_id = None
        
        # Remove from pins' wire_items lists
        if self.wire in self.from_pin.wire_items:
            self.from_pin.wire_items.remove(self.wire)
        if self.wire in self.to_pin.wire_items:
            self.to_pin.wire_items.remove(self.wire)
        
        # Remove from main window lists
        if hasattr(self.main_window, 'wires') and self.wire in self.main_window.wires:
            self.main_window.wires.remove(self.wire)
        if hasattr(self.main_window, 'imported_wire_items') and self.wire in self.main_window.imported_wire_items:
            self.main_window.imported_wire_items.remove(self.wire)
        
        self._refresh_connector_tables()
        self.main_window.refresh_tree_views()
    
    def _refresh_connector_tables(self):
        """Refresh info tables for affected connectors"""
        # Refresh from connector's table
        if hasattr(self.from_pin.parent, 'info_table'):
            self.from_pin.parent.info_table.refresh()
        
        # Refresh to connector's table
        if hasattr(self.to_pin.parent, 'info_table'):
            self.to_pin.parent.info_table.refresh()

class DeleteWireCommand(BaseCommand):
    """Delete a wire"""
    
    def __init__(self, scene, wire_item, main_window):
        super().__init__("Delete Wire")
        self.scene = scene
        self.main_window = main_window
        self.wire = wire_item
        self.wire_id = wire_item.wid
        self.wire_model = wire_item.model  # Store the wire model
        self.from_pin = wire_item.start_pin
        self.to_pin = wire_item.end_pin
        self.color = wire_item.color_data.code if hasattr(wire_item, 'color_data') else 'SW'
        self.net = wire_item.net
        self.wire_data = getattr(wire_item, 'wire_data', None)
        
        # Store tree item text and parent tree
        self.tree_item_text = None
        self.tree_parent = None
        if wire_item.tree_item:
            self.tree_item_text = wire_item.tree_item.text(0)
            self.tree_parent = wire_item.tree_item.treeWidget()
        
        # Store pin IDs to find them later
        self.from_connector_id = wire_item.start_pin.parent.model.id
        self.from_pin_id = wire_item.start_pin.model.pid
        self.to_connector_id = wire_item.end_pin.parent.model.id
        self.to_pin_id = wire_item.end_pin.model.pid
    
    def redo(self):
        # Remove wire model from wiringharness
        if self.main_window and hasattr(self.main_window, 'wiringharness'):
            if self.wire_id in self.main_window.wiringharness.wires:
                del self.main_window.wiringharness.wires[self.wire_id]
        
        # Call cleanup on wire (removes from pins and tree)
        self.wire.cleanup()

        # Remove from scene
        self.scene.removeItem(self.wire)
        

        
        self.main_window.refresh_tree_views()
    
    def undo(self):
        from graphics.wire_item import WireItem
        
        # Find the connectors and pins again (they should still exist)
        from_connector = None
        to_connector = None
        
        # Find connectors by ID
        for conn in self.main_window.conns:
            if conn.model.id == self.from_connector_id:
                from_connector = conn
            if conn.model.id == self.to_connector_id:
                to_connector = conn
        
        if not from_connector or not to_connector:
            print(f"Error: Could not find connectors for wire {self.wire_id}")
            return
        
        # Find pins by ID
        from_pin = from_connector.get_pin_by_id(self.from_pin_id)
        to_pin = to_connector.get_pin_by_id(self.to_pin_id)
        
        if not from_pin or not to_pin:
            print(f"Error: Could not find pins for wire {self.wire_id}")
            return
        
        # Create new wire from the stored model
        new_wire = WireItem(self.wire_model)
        new_wire.connect_to_pins(from_pin, to_pin)
        new_wire.net = self.net
        new_wire.wire_data = self.wire_data
        
        self.scene.addItem(new_wire)
        
        # Add wire model back to wiringharness
        if self.main_window and hasattr(self.main_window, 'wiringharness'):
            self.main_window.wiringharness.add_wire(self.wire_model)
        
        # Create NEW tree item
        from PyQt5.QtWidgets import QTreeWidgetItem
        item = QTreeWidgetItem([self.tree_item_text or new_wire.wid])
        item.setData(0, Qt.UserRole, new_wire)
        
        # Add to wires tree (use the stored parent or default)
        if self.tree_parent and not sip.isdeleted(self.tree_parent):
            self.tree_parent.addTopLevelItem(item)
        elif hasattr(self.main_window, 'objects_dock'):
            wires_tree = self.main_window.objects_dock.wires_tab.wires_tree
            wires_tree.addTopLevelItem(item)
        
        new_wire.tree_item = item
        self.wire = new_wire
        
        # Add to main window lists
        if hasattr(self.main_window, 'wires'):
            self.main_window.wires.append(new_wire)
        if hasattr(self.main_window, 'imported_wire_items'):
            self.main_window.imported_wire_items.append(new_wire)
        
        # Refresh tree to ensure consistency
        self.main_window.refresh_tree_views()
        
        # Update connector info tables
        if hasattr(from_connector, 'info_table'):
            from_connector.info_table.update_table()
        if hasattr(to_connector, 'info_table'):
            to_connector.info_table.update_table()
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
    """Convert direct wires to routed topology - USING BUNDLES"""
    
    def __init__(self, main_window, wire_items, branch_points, bundles):
        super().__init__("Create Branches")
        self.main_window = main_window
        self.wire_items = wire_items
        self.branch_points = branch_points
        self.bundles = bundles  # Now bundles instead of segments
        self.original_wire_visibility = []
        
        # Store original wire visibility
        for wire in wire_items:
            self.original_wire_visibility.append(wire.isVisible())
    
    def redo(self):
        # Hide original wires
        for wire in self.wire_items:
            wire.setVisible(False)
        
        # Add branch points and bundles to scene
        for bp in self.branch_points:
            self.main_window.scene.addItem(bp)
        for bundle in self.bundles:
            self.main_window.scene.addItem(bundle)
        
        # Add routed wires
        if hasattr(self.main_window, 'routed_wire_items'):
            for wire in self.main_window.routed_wire_items:
                self.main_window.scene.addItem(wire)
        
        # Update visualization
        if hasattr(self.main_window, 'viz_manager'):
            self.main_window.viz_manager.on_auto_route_complete()
        
        self.main_window.refresh_tree_views()
        self.main_window.refresh_bundle_tree()
    
    def undo(self):
        # Show original wires
        for wire, visible in zip(self.wire_items, self.original_wire_visibility):
            wire.setVisible(visible)
        
        # Remove branch points and bundles
        for bp in self.branch_points:
            if bp.scene():
                self.main_window.scene.removeItem(bp)
        for bundle in self.bundles:
            if bundle.scene():
                self.main_window.scene.removeItem(bundle)
        
        # Remove routed wires
        if hasattr(self.main_window, 'routed_wire_items'):
            for wire in self.main_window.routed_wire_items:
                if wire.scene():
                    self.main_window.scene.removeItem(wire)
        
        # Update visualization
        if hasattr(self.main_window, 'viz_manager'):
            self.main_window.viz_manager.on_clear_topology()
        
        self.main_window.refresh_tree_views()
        self.main_window.refresh_bundle_tree()

