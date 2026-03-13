from PyQt5.QtCore import QPointF, Qt
from PyQt5.QtWidgets import QTreeWidgetItem
from .base_command import BaseCommand, CompoundCommand
class AddBundleCommand(BaseCommand):
    """Add a new bundle to the scene"""
    
    def __init__(self, scene, bundle_item, start_point, end_point, main_window=None):
        super().__init__("Add Bundle")
        self.scene = scene
        self.bundle = bundle_item
        self.bundle_model = bundle_item.model
        self.start_point = start_point
        self.end_point = end_point
        self.main_window = main_window
        self.bundle_id = bundle_item.bundle_id
        self._initialized = False
        self._tree_item = None
    
    def _initialize(self):
        """First time execution"""
        self._execute()
    
    def _redo(self):
        """Subsequent redos"""
        self._execute()
    
    def _execute(self):
        """Common execution logic"""
        # Skip if already in scene
        if self.bundle.scene() == self.scene:
            return
        
        # Ensure model has correct data
        self.bundle_model.start_point = (self.start_point.x(), self.start_point.y())
        self.bundle_model.end_point = (self.end_point.x(), self.end_point.y())
        
        # Add to scene
        self.scene.addItem(self.bundle)
        
        # Add to main window's bundle list
        if hasattr(self.main_window, 'bundles'):
            self.main_window.bundles.append(self.bundle)
        
        # Add to wiring harness
        if hasattr(self.main_window, 'wiringharness'):
            self.main_window.wiringharness.add_bundle(self.bundle_model)
        
        # Register with main window's graphics repository
        if self.main_window:
            self.main_window.register_graphics_item(self.bundle, 'bundles')
        
        # Create tree item if needed
        if not self.bundle.tree_item and hasattr(self.main_window, 'bundles_tree'):
            from PyQt5.QtWidgets import QTreeWidgetItem
            display_name = getattr(self.bundle, 'name', self.bundle_id)
            
            # Create display text with length info
            if self.bundle.specified_length:
                length_text = f"{self.bundle.specified_length:.0f} mm"
            else:
                length_text = f"{self.bundle.model.length:.0f} units"
            
            item = QTreeWidgetItem([display_name, length_text, str(self.bundle.wire_count)])
            item.setData(0, Qt.UserRole, self.bundle)
            self.main_window.bundles_tree.addTopLevelItem(item)
            self.bundle.tree_item = item
            self._tree_item = item
        
        self.main_window.refresh_bundle_tree()
    
    def undo(self):
        """Undo the command"""
        # Remove from scene
        if self.bundle.scene() == self.scene:
            self.scene.removeItem(self.bundle)
        
        # Remove from main window's bundle list
        if hasattr(self.main_window, 'bundles') and self.bundle in self.main_window.bundles:
            self.main_window.bundles.remove(self.bundle)
        
        # Remove from wiring harness
        if hasattr(self.main_window, 'wiringharness'):
            self.main_window.wiringharness.remove_bundle(self.bundle_model)
        
        # Unregister from main window
        if self.main_window:
            self.main_window.unregister_graphics_item(self.bundle, 'bundles')
        
        # Remove tree item
        if self.bundle.tree_item:
            try:
                tree = self.bundle.tree_item.treeWidget()
                if tree and not sip.isdeleted(tree):
                    index = tree.indexOfTopLevelItem(self.bundle.tree_item)
                    if index >= 0:
                        tree.takeTopLevelItem(index)
            except:
                pass
            self.bundle.tree_item = None
        
        self.main_window.refresh_bundle_tree()
    
    def redo(self):
        """Override to use the new pattern"""
        if not self._initialized:
            self._initialized = True
            self._initialize()
        else:
            self._redo()


class DeleteBundleCommand(BaseCommand):
    """Delete a bundle"""
    
    def __init__(self, scene, bundle_item, main_window=None):
        super().__init__("Delete Bundle")
        self.scene = scene
        self.bundle = bundle_item
        self.bundle_model = bundle_item.model
        self.main_window = main_window
        self.bundle_id = bundle_item.bundle_id
        self.start_point = bundle_item.start_point
        self.end_point = bundle_item.end_point
        self.specified_length = bundle_item.specified_length
        self.start_node = bundle_item.start_node
        self.end_node = bundle_item.end_node
        self.start_item = bundle_item.start_item
        self.end_item = bundle_item.end_item
        self.wire_count = bundle_item.wire_count
        self.wire_ids = bundle_item.wire_ids.copy()
        self._initialized = False
        
        # Store tree item text
        self.tree_item_text = None
        if bundle_item.tree_item:
            self.tree_item_text = bundle_item.tree_item.text(0)
    
    def _initialize(self):
        """First time execution"""
        self._execute()
    
    def _redo(self):
        """Subsequent redos"""
        self._execute()
    
    def _execute(self):
        """Execute the deletion"""
        # Remove from main window's bundle list
        if hasattr(self.main_window, 'bundles') and self.bundle in self.main_window.bundles:
            self.main_window.bundles.remove(self.bundle)
        
        # Remove from wiring harness
        if hasattr(self.main_window, 'wiringharness'):
            self.main_window.wiringharness.remove_bundle(self.bundle_model)
        
        # Remove from scene
        if self.bundle.scene() == self.scene:
            self.scene.removeItem(self.bundle)
        
        # Unregister from main window
        if self.main_window:
            self.main_window.unregister_graphics_item(self.bundle, 'bundles')
        
        # Remove tree item
        if self.bundle.tree_item:
            try:
                tree = self.bundle.tree_item.treeWidget()
                if tree and not sip.isdeleted(tree):
                    index = tree.indexOfTopLevelItem(self.bundle.tree_item)
                    if index >= 0:
                        tree.takeTopLevelItem(index)
            except:
                pass
            self.bundle.tree_item = None
        
        self.main_window.refresh_bundle_tree()
    
    def undo(self):
        """Undo the deletion"""
        from graphics.bundle_item import BundleItem
        
        # Recreate bundle from model
        new_bundle = BundleItem(self.bundle_model, self.main_window)
        new_bundle.set_start_node(self.start_node, self.start_item)
        new_bundle.set_end_node(self.end_node, self.end_item)
        new_bundle.set_specified_length(self.specified_length)
        new_bundle.wire_count = self.wire_count
        new_bundle.wire_ids = self.wire_ids.copy()
        
        # Update model
        self.bundle_model.wire_count = self.wire_count
        self.bundle_model.wire_ids = self.wire_ids.copy()
        
        # Add to scene
        self.scene.addItem(new_bundle)
        
        # Add to main window
        if hasattr(self.main_window, 'bundles'):
            self.main_window.bundles.append(new_bundle)
        
        # Add to wiring harness
        if hasattr(self.main_window, 'wiringharness'):
            self.main_window.wiringharness.add_bundle(self.bundle_model)
        
        # Register with main window
        if self.main_window:
            self.main_window.register_graphics_item(new_bundle, 'bundles')
        
        # Recreate tree item
        if self.tree_item_text and hasattr(self.main_window, 'bundles_tree'):
            item = QTreeWidgetItem([self.tree_item_text])
            item.setData(0, Qt.UserRole, new_bundle)
            self.main_window.bundles_tree.addTopLevelItem(item)
            new_bundle.tree_item = item
        
        self.bundle = new_bundle
        self.main_window.refresh_bundle_tree()
    
    def redo(self):
        """Override to use the new pattern"""
        if not self._initialized:
            self._initialized = True
            self._execute()
        else:
            self._redo()


class UpdateBundleLengthCommand(BaseCommand):
    """Update bundle length"""
    
    def __init__(self, bundle, old_length, new_length):
        super().__init__("Update Bundle Length")
        self.bundle = bundle
        self.bundle_model = bundle.model
        self.old_length = old_length
        self.new_length = new_length
        self._initialized = False
    
    def _initialize(self):
        """First time execution"""
        self._execute()
    
    def _redo(self):
        """Subsequent redos"""
        self._execute()
    
    def _execute(self):
        """Apply the length change"""
        self.bundle.set_specified_length(self.new_length)
        self.bundle_model.specified_length = self.new_length
        self._update_tree_text()
    
    def undo(self):
        """Revert the length change"""
        self.bundle.set_specified_length(self.old_length)
        self.bundle_model.specified_length = self.old_length
        self._update_tree_text()
    
    def _update_tree_text(self):
        """Update tree item text"""
        if self.bundle.tree_item:
            display_text = f"{self.bundle.bundle_id}"
            if self.bundle.specified_length:
                display_text += f" ({self.bundle.specified_length:.0f} mm)"
            elif self.bundle.model.length:
                display_text += f" ({self.bundle.model.length:.0f} units)"
            
            self.bundle.tree_item.setText(0, display_text)
            
            # Update length column if it exists
            tree = self.bundle.tree_item.treeWidget()
            if tree and tree.columnCount() > 1:
                if self.bundle.specified_length:
                    length_text = f"{self.bundle.specified_length:.0f} mm"
                else:
                    length_text = f"{self.bundle.model.length:.0f} units"
                self.bundle.tree_item.setText(1, length_text)
    
    def redo(self):
        """Override to use the new pattern"""
        if not self._initialized:
            self._initialized = True
            self._execute()
        else:
            self._redo()


class UpdateBundlePropertiesCommand(BaseCommand):
    """Update bundle properties (name, etc.)"""
    
    def __init__(self, bundle, old_props: dict, new_props: dict):
        super().__init__("Edit Bundle Properties")
        self.bundle = bundle
        self.bundle_model = bundle.model
        self.old_props = old_props
        self.new_props = new_props
        self._initialized = False
    
    def _initialize(self):
        """First time execution"""
        self._execute()
    
    def _redo(self):
        """Subsequent redos"""
        self._execute()
    
    def _execute(self):
        """Apply new properties"""
        for key, value in self.new_props.items():
            if hasattr(self.bundle, key):
                setattr(self.bundle, key, value)
            if hasattr(self.bundle_model, key):
                setattr(self.bundle_model, key, value)
        
        self._update_tree_text()
    
    def undo(self):
        """Revert to old properties"""
        for key, value in self.old_props.items():
            if hasattr(self.bundle, key):
                setattr(self.bundle, key, value)
            if hasattr(self.bundle_model, key):
                setattr(self.bundle_model, key, value)
        
        self._update_tree_text()
    
    def _update_tree_text(self):
        """Update tree item display"""
        if self.bundle.tree_item:
            display_name = getattr(self.bundle, 'name', self.bundle.bundle_id)
            self.bundle.tree_item.setText(0, display_name)
    
    def redo(self):
        """Override to use the new pattern"""
        if not self._initialized:
            self._initialized = True
            self._execute()
        else:
            self._redo()


class MoveBundleEndCommand(BaseCommand):
    """Move bundle end point"""
    
    def __init__(self, bundle, old_end, new_end):
        super().__init__("Move Bundle End")
        self.bundle = bundle
        self.bundle_model = bundle.model
        self.old_end = old_end
        self.new_end = new_end
        self._initialized = False
    
    def _initialize(self):
        """First time execution"""
        self._execute()
    
    def _redo(self):
        """Subsequent redos"""
        self._execute()
    
    def _execute(self):
        """Move the end point"""
        self.bundle.set_end_point(self.new_end)
        self.bundle_model.end_point = (self.new_end.x(), self.new_end.y())
        self.bundle.update_path()
    
    def undo(self):
        """Revert the move"""
        self.bundle.set_end_point(self.old_end)
        self.bundle_model.end_point = (self.old_end.x(), self.old_end.y())
        self.bundle.update_path()
    
    def redo(self):
        """Override to use the new pattern"""
        if not self._initialized:
            self._initialized = True
            self._execute()
        else:
            self._redo()


class AssignWireToBundleCommand(BaseCommand):
    """Assign a wire to a bundle"""
    
    def __init__(self, bundle, wire_id):
        super().__init__("Assign Wire to Bundle")
        self.bundle = bundle
        self.bundle_model = bundle.model
        self.wire_id = wire_id
        self._initialized = False
    
    def _initialize(self):
        """First time execution"""
        self._execute()
    
    def _redo(self):
        """Subsequent redos"""
        self._execute()
    
    def _execute(self):
        """Assign the wire"""
        self.bundle.assign_wire(self.wire_id)
        self._update_tree_color()
    
    def undo(self):
        """Remove the wire assignment"""
        if self.wire_id in self.bundle.wire_ids:
            self.bundle.wire_ids.remove(self.wire_id)
            self.bundle.wire_count = len(self.bundle.wire_ids)
            self.bundle_model.wire_ids = self.bundle.wire_ids.copy()
            self.bundle_model.wire_count = self.bundle.wire_count
            self.bundle.update_appearance()
        self._update_tree_color()
    
    def _update_tree_color(self):
        """Update tree item color based on wire count"""
        if self.bundle.tree_item:
            if self.bundle.wire_count > 0:
                self.bundle.tree_item.setForeground(0, Qt.darkGreen)
                # Update wire count column
                tree = self.bundle.tree_item.treeWidget()
                if tree and tree.columnCount() > 2:
                    self.bundle.tree_item.setText(2, str(self.bundle.wire_count))
            else:
                self.bundle.tree_item.setForeground(0, Qt.black)
    
    def redo(self):
        """Override to use the new pattern"""
        if not self._initialized:
            self._initialized = True
            self._execute()
        else:
            self._redo()


class RouteWiresThroughBundlesCommand(CompoundCommand):
    """Command for routing wires through bundles"""
    
    def __init__(self, main_window, original_wires, routed_wires, 
                 created_segments, bundles):
        super().__init__("Route Wires Through Bundles")
        self.main_window = main_window
        self.original_wires = original_wires
        self.routed_wires = routed_wires
        self.created_segments = created_segments
        self.bundles = bundles
        self._initialized = False
        
        # Store original visibility
        self.original_visibility = [w.isVisible() for w in original_wires]
        
        # Store bundle wire assignments
        self.bundle_assignments = {}
        for bundle in bundles:
            self.bundle_assignments[bundle] = bundle.get_wire_ids().copy()
    
    def _initialize(self):
        """First time execution"""
        self._execute()
    
    def _redo(self):
        """Subsequent redos"""
        self._execute()
    
    def _execute(self):
        """Execute the routing"""
        # Hide original wires
        for wire, visible in zip(self.original_wires, self.original_visibility):
            wire.setVisible(False)
        
        # Show routed wires
        for wire in self.routed_wires:
            if wire.scene() is None:
                self.main_window.scene.addItem(wire)
            wire.setVisible(True)
            
            # Register with graphics repository
            if self.main_window:
                self.main_window.register_graphics_item(wire, 'routed_wires')
        
        # Ensure segments are in scene
        for item in self.created_segments:
            if item.scene() is None:
                self.main_window.scene.addItem(item)
        
        # Restore bundle wire assignments
        for bundle, wire_ids in self.bundle_assignments.items():
            bundle.wire_ids = wire_ids.copy()
            bundle.wire_count = len(wire_ids)
            bundle.model.wire_ids = wire_ids.copy()
            bundle.model.wire_count = len(wire_ids)
            bundle.update_appearance()
        
        # Update lists
        if not hasattr(self.main_window, 'routed_wire_items'):
            self.main_window.routed_wire_items = []
        
        for wire in self.routed_wires:
            if wire not in self.main_window.routed_wire_items:
                self.main_window.routed_wire_items.append(wire)
        
        # Refresh views
        self.main_window.refresh_tree_views()
        self.main_window.refresh_bundle_tree()
        
        if hasattr(self.main_window, 'viz_manager'):
            self.main_window.viz_manager.update_visibility()
    
    def undo(self):
        """Undo the routing"""
        # Show original wires
        for wire, visible in zip(self.original_wires, self.original_visibility):
            wire.setVisible(visible)
        
        # Hide routed wires
        for wire in self.routed_wires:
            if wire.scene():
                self.main_window.scene.removeItem(wire)
            
            # Unregister from graphics repository
            if self.main_window:
                self.main_window.unregister_graphics_item(wire, 'routed_wires')
        
        # Remove created segments
        for item in self.created_segments:
            if item.scene():
                self.main_window.scene.removeItem(item)
        
        # Clear bundle wire assignments
        for bundle in self.bundles:
            bundle.wire_ids = []
            bundle.wire_count = 0
            bundle.model.wire_ids = []
            bundle.model.wire_count = 0
            bundle.update_appearance()
        
        # Clear from lists
        if hasattr(self.main_window, 'routed_wire_items'):
            self.main_window.routed_wire_items = [
                w for w in self.main_window.routed_wire_items 
                if w not in self.routed_wires
            ]
        
        # Refresh views
        self.main_window.refresh_tree_views()
        self.main_window.refresh_bundle_tree()
        
        if hasattr(self.main_window, 'viz_manager'):
            self.main_window.viz_manager.update_visibility()
    
    def redo(self):
        """Override to use the new pattern"""
        if not self._initialized:
            self._initialized = True
            self._execute()
        else:
            super().redo()  # For CompoundCommand, this executes all child commands
