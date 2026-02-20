from PyQt5.QtCore import QPointF, Qt
from PyQt5.QtWidgets import QTreeWidgetItem
from .base_command import BaseCommand, CompoundCommand

class AddBundleCommand(BaseCommand):
    """Add a new bundle to the scene"""
    
    def __init__(self, scene, bundle_item, start_point, end_point, main_window=None):
        super().__init__("Add Bundle")
        self.scene = scene
        self.bundle = bundle_item
        self.start_point = start_point
        self.end_point = end_point
        self.main_window = main_window
        self.bundle_id = bundle_item.bundle_id
        self.specified_length = bundle_item.specified_length
        self.start_node = bundle_item.start_node
        self.end_node = bundle_item.end_node

        self.main_window.refresh_bundle_tree()
    
    def redo(self):
        if self.first_redo:
            self.first_redo = False
            return
        
        self.scene.addItem(self.bundle)
        # Add to main window bundles list
        if hasattr(self.main_window, 'bundles'):
            self.main_window.bundles.append(self.bundle)
        
        
        self.main_window.refresh_bundle_tree()
    
    def undo(self):
     
        self.scene.removeItem(self.bundle)
        
        # Remove from main window bundles list
        if hasattr(self.main_window, 'bundles') and self.bundle in self.main_window.bundles:
            self.main_window.bundles.remove(self.bundle)
        
        self.main_window.refresh_bundle_tree()
 

class DeleteBundleCommand(BaseCommand):
    """Delete a bundle"""
    
    def __init__(self, scene, bundle_item, main_window=None):
        super().__init__("Delete Bundle")
        self.scene = scene
        self.bundle = bundle_item
        self.main_window = main_window
        self.bundle_id = bundle_item.bundle_id
        self.start_point = bundle_item.start_point
        self.end_point = bundle_item.end_point
        self.specified_length = bundle_item.specified_length
        self.start_node = bundle_item.start_node
        self.end_node = bundle_item.end_node
        self.wire_count = bundle_item.wire_count
        self.wire_ids = bundle_item.wire_ids.copy()
        
        # Store tree item text for recreation
        if bundle_item.tree_item:
            self.tree_item_text = bundle_item.tree_item.text(0)
        else:
            self.tree_item_text = None
    
    def redo(self):
        # Remove from main window bundles list
        if hasattr(self.main_window, 'bundles') and self.bundle in self.main_window.bundles:
            self.main_window.bundles.remove(self.bundle)
        
        self.scene.removeItem(self.bundle)
        
        # Refresh tree to reflect removal
        self.main_window.refresh_bundle_tree()
    
    def undo(self):
        # Recreate bundle
        from graphics.bundle_item import BundleItem
        new_bundle = BundleItem(self.start_point, self.end_point, self.bundle_id)
        new_bundle.set_specified_length(self.specified_length)
        new_bundle.start_node = self.start_node
        new_bundle.end_node = self.end_node
        new_bundle.wire_count = self.wire_count
        new_bundle.wire_ids = self.wire_ids.copy()
        
        self.scene.addItem(new_bundle)
        self.bundle = new_bundle
        
        # Add to main window
        if hasattr(self.main_window, 'bundles'):
            self.main_window.bundles.append(new_bundle)
        
        # Refresh tree to show restored bundle
        self.main_window.refresh_bundle_tree()



class UpdateBundleLengthCommand(BaseCommand):
    """Update bundle length"""
    
    def __init__(self, bundle, old_length, new_length):
        super().__init__("Update Bundle Length")
        self.bundle = bundle
        self.old_length = old_length
        self.new_length = new_length
    
    def redo(self):
        self.bundle.set_specified_length(self.new_length)
        self._update_tree_text()
    
    def undo(self):
        self.bundle.set_specified_length(self.old_length)
        self._update_tree_text()
    
    def _update_tree_text(self):
        """Update tree item text"""
        if self.bundle.tree_item:
            display_text = f"{self.bundle.bundle_id}"
            if self.bundle.specified_length:
                display_text += f" ({self.bundle.specified_length:.0f} mm)"
            self.bundle.tree_item.setText(0, display_text)


class MoveBundleEndCommand(BaseCommand):
    """Move bundle end point"""
    
    def __init__(self, bundle, old_end, new_end):
        super().__init__("Move Bundle End")
        self.bundle = bundle
        self.old_end = old_end
        self.new_end = new_end
    
    def redo(self):
        self.bundle.set_end_point(self.new_end)
    
    def undo(self):
        self.bundle.set_end_point(self.old_end)


class AssignWireToBundleCommand(BaseCommand):
    """Assign a wire to a bundle"""
    
    def __init__(self, bundle, wire_id):
        super().__init__("Assign Wire to Bundle")
        self.bundle = bundle
        self.wire_id = wire_id
    
    def redo(self):
        self.bundle.assign_wire(self.wire_id)
        self._update_tree_color()
    
    def undo(self):
        if self.wire_id in self.bundle.wire_ids:
            self.bundle.wire_ids.remove(self.wire_id)
            self.bundle.wire_count = len(self.bundle.wire_ids)
            self.bundle.update_appearance()
        self._update_tree_color()
    
    def _update_tree_color(self):
        """Update tree item color based on wire count"""
        if self.bundle.tree_item:
            if self.bundle.wire_count > 0:
                self.bundle.tree_item.setForeground(0, Qt.darkGreen)
            else:
                self.bundle.tree_item.setForeground(0, Qt.black)
class RouteWiresThroughBundlesCommand(BaseCommand):
    """Command for routing wires through bundles"""
    
    def __init__(self, main_window, original_wires, routed_wires, 
                 created_segments, bundles):
        super().__init__("Route Wires Through Bundles")
        self.main_window = main_window
        self.original_wires = original_wires
        self.routed_wires = routed_wires
        self.created_segments = created_segments
        self.bundles = bundles
        self.original_visibility = [w.isVisible() for w in original_wires]
        
        # Store bundle wire assignments
        self.bundle_assignments = {}
        for bundle in bundles:
            self.bundle_assignments[bundle] = bundle.get_wire_ids().copy()
    
    def redo(self):
        # Hide original wires
        for wire, visible in zip(self.original_wires, self.original_visibility):
            wire.setVisible(False)
        
        # Show routed wires
        for wire in self.routed_wires:
            if wire.scene() is None:
                self.main_window.scene.addItem(wire)
            wire.setVisible(True)
        
        # Ensure segments are in scene
        for item in self.created_segments:
            if item.scene() is None:
                self.main_window.scene.addItem(item)
        
        # Restore bundle wire assignments
        for bundle, wire_ids in self.bundle_assignments.items():
            bundle.wire_ids = wire_ids.copy()
            bundle.wire_count = len(wire_ids)
            bundle.update_appearance()
        
        # Update lists
        if not hasattr(self.main_window, 'routed_wire_items'):
            self.main_window.routed_wire_items = []
        
        for wire in self.routed_wires:
            if wire not in self.main_window.routed_wire_items:
                self.main_window.routed_wire_items.append(wire)
        
        self.main_window.wires = [w.wire for w in self.routed_wires if hasattr(w, 'wire')]
        
        # Refresh views
        self.main_window.refresh_tree_views()
        self.main_window.refresh_bundle_tree()
        
        if hasattr(self.main_window, 'viz_manager'):
            self.main_window.viz_manager.update_visibility()
    
    def undo(self):
        # Show original wires
        for wire, visible in zip(self.original_wires, self.original_visibility):
            wire.setVisible(visible)
        
        # Hide routed wires
        for wire in self.routed_wires:
            if wire.scene():
                self.main_window.scene.removeItem(wire)
        
        # Remove created segments
        for item in self.created_segments:
            if item.scene():
                self.main_window.scene.removeItem(item)
        
        # Clear bundle wire assignments
        for bundle in self.bundles:
            bundle.wire_ids = []
            bundle.wire_count = 0
            bundle.update_appearance()
        
        # Clear from lists
        if hasattr(self.main_window, 'routed_wire_items'):
            self.main_window.routed_wire_items = [
                w for w in self.main_window.routed_wire_items 
                if w not in self.routed_wires
            ]
        
        self.main_window.wires = []
        
        # Refresh views
        self.main_window.refresh_tree_views()
        self.main_window.refresh_bundle_tree()
        
        if hasattr(self.main_window, 'viz_manager'):
            self.main_window.viz_manager.update_visibility()

