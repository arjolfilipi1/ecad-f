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
        self.wire_model = wire_item.model
        self.from_pin = from_pin
        self.to_pin = to_pin
        self.color = wire_item.color_data.code if hasattr(wire_item, 'color_data') else 'SW'
        self.net = wire_item.net
        self._initialized = False
        self._tree_item = None
    
    def _initialize(self):
        """First time execution"""
        self._execute()
    
    def _redo(self):
        """Subsequent redos"""
        self._execute()
    
    def _execute(self):
        print("add wire")
        """Common execution logic"""
        # Skip if already in scene
        if self.wire.scene() == self.scene:
            return
            
        self.wire_model.graphics_item = self.wire
        self.scene.addItem(self.wire)
        
        # Connect to pins
        self.from_pin.add_wire(self.wire)
        self.to_pin.add_wire(self.wire)
        
        # Add wire model to wiringharness
        if self.main_window and hasattr(self.main_window, 'wiringharness'):
            self.main_window.wiringharness.add_wire(self.wire_model)
        

        # Create tree item if needed
        if not self.wire.tree_item:
            item = QTreeWidgetItem([self.wire_id])
            item.setData(0, Qt.UserRole, self.wire)
            if hasattr(self.main_window, 'objects_dock'):
                self.main_window.objects_dock.wires_tab.wires_tree.addTopLevelItem(item)
            self.wire.tree_item = item
            self._tree_item = item
        
        self._refresh_connector_tables()
        self.main_window.refresh_tree_views()
    
    def undo(self):
        print("remove wire")
        """Undo the command"""
        # Remove from scene
        if self.wire.scene() == self.scene:
            self.scene.removeItem(self.wire)
        
        # Remove wire model from wiringharness
        if self.main_window and hasattr(self.main_window, 'wiringharness'):
            if self.wire_id in self.main_window.wiringharness.wires:
                del self.main_window.wiringharness.wires[self.wire_id]
        
        # Remove from pins' wire lists
        if self.wire in self.from_pin.wire_items:
            self.from_pin.wire_items.remove(self.wire)
        if self.wire in self.to_pin.wire_items:
            self.to_pin.wire_items.remove(self.wire)
        
        # Update pin models
        if self.from_pin.model.wire_ids:
            if isinstance(self.from_pin.model.wire_ids, list):
                self.from_pin.model.wire_ids = [w for w in self.from_pin.model.wire_ids 
                                               if w != self.wire_id]
            else:
                self.from_pin.model.wire_ids = []
        
        if self.to_pin.model.wire_ids:
            if isinstance(self.to_pin.model.wire_ids, list):
                self.to_pin.model.wire_ids = [w for w in self.to_pin.model.wire_ids 
                                             if w != self.wire_id]
            else:
                self.to_pin.model.wire_ids = []
        
        
        # Remove tree item
        if self.wire.tree_item:
            try:
                tree = self.wire.tree_item.treeWidget()
                if tree and not sip.isdeleted(tree):
                    index = tree.indexOfTopLevelItem(self.wire.tree_item)
                    if index >= 0:
                        tree.takeTopLevelItem(index)
            except RuntimeError:
                pass
            self.wire.tree_item = None
        
        self._refresh_connector_tables()
        self.main_window.refresh_tree_views()
    
    def _refresh_connector_tables(self):
        """Refresh info tables for affected connectors"""
        if hasattr(self.from_pin.parent, 'info_table') and  self.from_pin.parent.info_table is not None:
            try:
                self.from_pin.parent.info_table.refresh()
            except RuntimeError:
                pass
        
        if hasattr(self.to_pin.parent, 'info_table') and self.to_pin.parent.info_table is not None:
            try:
                self.to_pin.parent.info_table.refresh()
            except RuntimeError:
                pass
    
    def redo(self):
        """Override to use the new pattern"""
        if not self._initialized:
            self._initialized = True
            self._initialize()
        else:
            self._redo()


class DeleteWireCommand(BaseCommand):
    """Delete a wire"""
    
    def __init__(self, scene, wire_item, main_window):
        super().__init__("Delete Wire")
        self.scene = scene
        self.main_window = main_window
        self.wire = wire_item
        self.wire_id = wire_item.wid
        self.wire_model = wire_item.model
        self.from_pin = wire_item.start_pin
        self.to_pin = wire_item.end_pin
        self.color = wire_item.color_data.code if hasattr(wire_item, 'color_data') else 'SW'
        self.net = wire_item.net
        self._initialized = False
        
        # Store connection data for recreation
        self.from_connector_id = wire_item.start_pin.parent.model.id if wire_item.start_pin else None
        self.from_pin_id = wire_item.start_pin.model.pid
        self.to_connector_id = wire_item.end_pin.parent.model.id if wire_item.end_pin else None
        self.to_pin_id = wire_item.end_pin.model.pid
        
        # Store tree item data
        self.tree_item_text = None
        self.tree_parent = None
        if wire_item.tree_item:
            self.tree_item_text = wire_item.tree_item.text(0)
            self.tree_parent = wire_item.tree_item.treeWidget()
    
    def _initialize(self):
        """First time execution"""
        self._execute()
    
    def _redo(self):
        """Subsequent redos"""
        self._execute()
    
    def _execute(self):
        print("delete wire")
        """Execute the deletion"""
        # Remove wire model from wiringharness
        if self.main_window and hasattr(self.main_window, 'wiringharness'):
            if self.wire_id in self.main_window.wiringharness.wires:
                del self.main_window.wiringharness.wires[self.wire_id]
        
        # Call cleanup on wire (removes from pins)
        self.wire.cleanup()
        
        # Remove from scene
        if self.wire.scene() == self.scene:
            self.scene.removeItem(self.wire)
        
        self.main_window.refresh_tree_views()
    
    def undo(self):
        print("undelete wire")
        """Undo the deletion"""
        from graphics.wire_item import WireItem
        
        # Find the connectors and pins if they still exist
        from_connector = None
        to_connector = None
        from_pin = None
        to_pin = None
        
        # Only try to find connectors if we have IDs
        if self.from_connector_id:
            for conn in self.main_window.conns:
                if conn.model.id == self.from_connector_id:
                    from_connector = conn
                    if self.from_pin_id:
                        from_pin = from_connector.get_pin_by_id(self.from_pin_id)
                    break
        
        if self.to_connector_id:
            for conn in self.main_window.conns:
                if conn.model.id == self.to_connector_id:
                    to_connector = conn
                    if self.to_pin_id:
                        to_pin = to_connector.get_pin_by_id(self.to_pin_id)
                    break
        
        # Recreate wire
        if self.wire_model.graphics_item is None:
            new_wire = WireItem(self.wire_model)
            
            # Only connect to pins that exist
            if from_pin:
                new_wire.start_pin = from_pin
            if to_pin:
                new_wire.end_pin = to_pin
            

            new_wire.connect_to_pins(from_pin, to_pin) if to_pin else None

            
            new_wire.net = self.net
            self.wire_model.graphics_item = new_wire
        else:
            new_wire = self.wire_model.graphics_item
        
        # Add to scene
        self.scene.addItem(new_wire)
        
        # Add wire model back to wiringharness
        if self.main_window and hasattr(self.main_window, 'wiringharness'):
            self.main_window.wiringharness.add_wire(self.wire_model)
        
        # Recreate tree item
        item = QTreeWidgetItem([self.tree_item_text or new_wire.wid])
        item.setData(0, Qt.UserRole, new_wire)
        
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
        
        # Update wire path
        new_wire.update_path()
        
        self.main_window.refresh_tree_views()
        
        # Update connector info tables if they exist
        if from_connector and hasattr(from_connector, 'info_table'):
            try:
                from_connector.info_table.update_table()
            except RuntimeError:
                pass
        if to_connector and hasattr(to_connector, 'info_table'):
            try:
                to_connector.info_table.update_table()
            except RuntimeError:
                pass
    
    def redo(self):
        """Override to use the new pattern"""
        if not self._initialized:
            self._initialized = True
            self._execute()
        else:
            self._redo()



class UpdateWirePropertiesCommand(BaseCommand):
    """Update wire properties (color, signal, etc.)"""
    
    def __init__(self, wire, old_props: dict, new_props: dict):
        super().__init__("Edit Wire Properties")
        self.wire = wire
        self.old_props = old_props
        self.new_props = new_props
        self._initialized = False
    
    def _initialize(self):
        """First time execution"""
        self._redo()
    
    def _redo(self):
        """Apply new properties"""
        for key, value in self.new_props.items():
            if hasattr(self.wire, key):
                setattr(self.wire, key, value)
            elif hasattr(self.wire.model, key):
                setattr(self.wire.model, key, value)
        
        if hasattr(self.wire, 'update_path'):
            self.wire.update_path()
        if hasattr(self.wire, 'update'):
            self.wire.update()
    
    def undo(self):
        """Revert to old properties"""
        for key, value in self.old_props.items():
            if hasattr(self.wire, key):
                setattr(self.wire, key, value)
            elif hasattr(self.wire.model, key):
                setattr(self.wire.model, key, value)
        
        if hasattr(self.wire, 'update_path'):
            self.wire.update_path()
        if hasattr(self.wire, 'update'):
            self.wire.update()
    
    def redo(self):
        """Override to use the new pattern"""
        if not self._initialized:
            self._initialized = True
            self._initialize()
        else:
            self._redo()



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

