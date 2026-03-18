from .base_command import BaseCommand, CompoundCommand

class DeleteBranchPointCommand(BaseCommand):
    """Delete a branch point and reconnect connected bundles"""
    
    def __init__(self, scene, branch_point, main_window=None):
        super().__init__("Delete Branch Point")
        self.scene = scene
        self.branch_point = branch_point
        self.branch_point_model = branch_point.model
        self.main_window = main_window
        self.position = branch_point.pos()
        self._initialized = False
        
        # Find all bundles connected to this branch point
        self.incoming_bundles = []  # Bundles that end at this branch point
        self.outgoing_bundles = []  # Bundles that start at this branch point
        
        if hasattr(self.main_window, 'bundles'):
            for bundle in self.main_window.bundles:
                if bundle.end_node and bundle.end_node.id == self.branch_point_model.id:
                    self.incoming_bundles.append(bundle)
                if bundle.start_node and bundle.start_node.id == self.branch_point_model.id:
                    self.outgoing_bundles.append(bundle)
        
        # Store original connections for undo
        self.original_connections = []
        for bundle in self.incoming_bundles + self.outgoing_bundles:
            self.original_connections.append({
                'bundle': bundle,
                'start_node': bundle.start_node,
                'start_item': bundle.start_item,
                'end_node': bundle.end_node,
                'end_item': bundle.end_item,
                'start_node_id': bundle.model.start_node_id,
                'end_node_id': bundle.model.end_node_id
            })
        
        # Prepare reconnection pairs (incoming → outgoing)
        self.reconnection_pairs = []
        
        # Simple case: match incoming bundles with outgoing bundles
        # This assumes the branch point is just a connection point
        for incoming in self.incoming_bundles:
            for outgoing in self.outgoing_bundles:
                # Create a pair - we'll reconnect them
                self.reconnection_pairs.append((incoming, outgoing))
        
        # If counts don't match, we'll handle it gracefully
        print(f"Branch point deletion: {len(self.incoming_bundles)} incoming, {len(self.outgoing_bundles)} outgoing")
    
    def _initialize(self):
        """First time execution"""
        self._execute()
    
    def _redo(self):
        """Subsequent redos"""
        self._execute()
    
    def _execute(self):
        """Execute the deletion and reconnect bundles"""
        
        # Reconnect bundles: connect incoming to outgoing
        for incoming, outgoing in self.reconnection_pairs:
            # Create a continuous path: incoming's start → outgoing's end
            # This effectively merges the two bundles into one continuous bundle
            
            # Transfer all wires from outgoing to incoming
            for wire_id in outgoing.wire_ids:
                if wire_id not in incoming.wire_ids:
                    incoming.assign_wire(wire_id)
            
            # Update incoming bundle's end to be outgoing's end
            incoming.set_end_node(outgoing.end_node, outgoing.end_item)
            incoming.model.end_node_id = outgoing.end_node.id if outgoing.end_node else None
            
            # Hide/remove the outgoing bundle
            if outgoing.scene():
                outgoing.setVisible(False)
                self.scene.removeItem(outgoing)
            
            if hasattr(self.main_window, 'bundles') and outgoing in self.main_window.bundles:
                self.main_window.bundles.remove(outgoing)
            
            if hasattr(self.main_window, 'wiringharness'):
                self.main_window.wiringharness.remove_bundle(outgoing.model)
        
        # Remove the branch point
        if self.branch_point.scene() == self.scene:
            self.scene.removeItem(self.branch_point)
        
        if self.main_window and hasattr(self.main_window, 'wiringharness'):
            self.main_window.wiringharness.remove_branch_point(self.branch_point_model)
        
        if self.main_window and hasattr(self.main_window, 'topology_manager'):
            if self.branch_point_model.id in self.main_window.topology_manager.nodes:
                del self.main_window.topology_manager.nodes[self.branch_point_model.id]
        
        if self.main_window:
            self.main_window.unregister_graphics_item(self.branch_point, 'branch_points')
        
        # Update all affected bundles
        for incoming, _ in self.reconnection_pairs:
            incoming.update_path()
        
        self.main_window.refresh_bundle_tree()
        self.main_window.statusBar().showMessage(
            f"Branch point deleted - {len(self.reconnection_pairs)} bundles reconnected", 2000
        )
    
    def undo(self):
        """Undo the deletion - restore branch point and split bundles back"""
        from graphics.topology_item import BranchPointGraphicsItem
        from model.topology import BranchPointNode
        
        # Restore branch point
        new_branch_point = BranchPointGraphicsItem(self.branch_point_model, self.main_window)
        new_branch_point.setPos(self.position)
        
        bp_node = BranchPointNode(
            (self.position.x(), self.position.y()), 
            self.branch_point_model.branch_type
        )
        bp_node.id = self.branch_point_model.id
        new_branch_point.branch_node = bp_node
        
        self.scene.addItem(new_branch_point)
        
        if self.main_window and hasattr(self.main_window, 'wiringharness'):
            self.main_window.wiringharness.add_branch_point(self.branch_point_model)
        
        if self.main_window and hasattr(self.main_window, 'topology_manager'):
            self.main_window.topology_manager.nodes[bp_node.id] = bp_node
        
        if self.main_window:
            self.main_window.register_graphics_item(new_branch_point, 'branch_points')
        
        # Restore original bundles and their connections
        for conn in self.original_connections:
            bundle = conn['bundle']
            
            # Restore bundle to scene if it was removed
            if bundle.scene() is None:
                self.scene.addItem(bundle)
                bundle.setVisible(True)
                if hasattr(self.main_window, 'bundles'):
                    self.main_window.bundles.append(bundle)
                if hasattr(self.main_window, 'wiringharness'):
                    self.main_window.wiringharness.add_bundle(bundle.model)
            
            # Restore original connections
            bundle.set_start_node(conn['start_node'], conn['start_item'])
            bundle.set_end_node(conn['end_node'], conn['end_item'])
            bundle.model.start_node_id = conn['start_node_id']
            bundle.model.end_node_id = conn['end_node_id']
            
            # Restore original wire assignments (they were never lost, just transferred)
            bundle.update_path()
        
        # For bundles that were merged, we need to split them back
        # The wire assignments are already correct because we stored them
        
        self.branch_point = new_branch_point
        self.main_window.refresh_bundle_tree()
        self.main_window.statusBar().showMessage("Branch point and bundle connections restored", 2000)
    
    def redo(self):
        """Override to use the new pattern"""
        if not self._initialized:
            self._initialized = True
            self._execute()
        else:
            self._redo()



            
class MoveBranchPointCommand(BaseCommand):
    """Move a branch point to a new position"""
    
    def __init__(self, branch_point, old_pos, new_pos, main_window=None):
        super().__init__("Move Branch Point")
        self.branch_point = branch_point
        self.branch_point_model = branch_point.model
        self.old_pos = old_pos
        self.new_pos = new_pos
        self.main_window = main_window
        self._initialized = False
    
    def _initialize(self):
        """First time execution"""
        self._execute()
    
    def _redo(self):
        """Subsequent redos"""
        self._execute()
    
    def _execute(self):
        """Move to new position"""
        self.branch_point.setPos(self.new_pos)
        self.branch_point_model.position = (self.new_pos.x(), self.new_pos.y())
        
        # Update topology node if it exists
        if hasattr(self.branch_point, 'branch_node') and self.branch_point.branch_node:
            self.branch_point.branch_node.position = self.branch_point_model.position
        
        # Update connected elements
        self.branch_point._update_connected_segments()
        self.branch_point._update_connected_bundles()
    
    def undo(self):
        """Move back to old position"""
        self.branch_point.setPos(self.old_pos)
        self.branch_point_model.position = (self.old_pos.x(), self.old_pos.y())
        
        # Update topology node if it exists
        if hasattr(self.branch_point, 'branch_node') and self.branch_point.branch_node:
            self.branch_point.branch_node.position = self.branch_point_model.position
        
        # Update connected elements
        self.branch_point._update_connected_segments()
        self.branch_point._update_connected_bundles()
    
    def redo(self):
        """Override to use the new pattern"""
        if not self._initialized:
            self._initialized = True
            self._execute()
        else:
            self._redo()

class AddBranchPointCommand(BaseCommand):
    """Add a new branch point to the scene"""
    
    def __init__(self, scene, branch_point_item, pos: tuple, description="Add Branch Point", main_window=None):
        super().__init__(description)
        self.scene = scene
        self.branch_point = branch_point_item
        self.branch_point_model = branch_point_item.model
        self.pos = pos
        self.main_window = main_window
        self.bp_id = branch_point_item.model.id
        self._initialized = False
    
    def _initialize(self):
        """First time execution"""
        self._execute()
    
    def _redo(self):
        """Subsequent redos"""
        self._execute()
    
    def _execute(self):
        """Common execution logic"""
        # Skip if already in scene
        if self.branch_point.scene() == self.scene:
            return
        
        # Set position
        self.branch_point.setPos(self.pos[0], self.pos[1])
        
        # Add to scene
        self.scene.addItem(self.branch_point)
        
        # Add to topology manager (for backward compatibility)
        if hasattr(self.main_window, 'topology_manager'):
            self.main_window.topology_manager.nodes[self.branch_point_model.id] = self.branch_point.branch_node
        
        # Add to wiring harness
        if hasattr(self.main_window, 'wiringharness'):
            
            self.main_window.wiringharness.add_branch_point(self.branch_point_model)
        
        # Register with main window's graphics repository
        if self.main_window:
            self.main_window.register_graphics_item(self.branch_point, 'branch_points')
        
        self.main_window.statusBar().showMessage(
            f"Branch point added at ({self.pos[0]:.0f}, {self.pos[1]:.0f})", 2000
        )
    
    def undo(self):
        """Undo the command"""
        # Remove from scene
        if self.branch_point.scene() == self.scene:
            self.scene.removeItem(self.branch_point)
        
        # Remove from topology manager
        if hasattr(self.main_window, 'topology_manager'):
            if self.branch_point_model.id in self.main_window.topology_manager.nodes:
                del self.main_window.topology_manager.nodes[self.branch_point_model.id]
        
        # Remove from wiring harness
        if hasattr(self.main_window, 'wiringharness'):
            self.main_window.wiringharness.remove_branch_point(self.branch_point_model)
        
        # Unregister from main window
        if self.main_window:
            self.main_window.unregister_graphics_item(self.branch_point, 'branch_points')
        
        self.main_window.statusBar().showMessage(f"Branch point removed", 2000)
    
    def redo(self):
        """Override to use the new pattern"""
        if not self._initialized:
            self._initialized = True
            self._initialize()
        else:
            self._redo()



class AddSegmentCommand(BaseCommand):
    """Add a segment between two nodes"""
    
    def __init__(self, scene, segment_item, start_node, end_node):
        super().__init__("Add Segment")
        self.scene = scene
        self.segment = segment_item
        self.start_node = start_node
        self.end_node = end_node
        self.segment_id = segment_item.segment.id
    
    def redo(self):
        if self.first_redo:
            self.first_redo = False
            return
        
        self.scene.addItem(self.segment)
    
    def undo(self):
        self.scene.removeItem(self.segment)


class SplitSegmentCommand(CompoundCommand):
    """Split a segment at a point, creating a junction"""
    
    def __init__(self, scene, segment_item, split_pos):
        super().__init__("Split Segment")
        self.scene = scene
        self.old_segment = segment_item
        self.split_pos = split_pos
        self.new_segments = []
        self.junction = None
        
        # Create junction and new segments
        from graphics.topology_item import JunctionGraphicsItem
        from model.topology import JunctionNode
        
        junction_node = JunctionNode(split_pos)
        self.junction = JunctionGraphicsItem(junction_node)
        
        # Create two new segments (will be added by caller)
    
    def redo(self):
        # Remove old segment
        self.scene.removeItem(self.old_segment)
        
        # Add junction
        self.scene.addItem(self.junction)
        
        # Add new segments
        for seg in self.new_segments:
            self.scene.addItem(seg)
    
    def undo(self):
        # Remove new segments
        for seg in self.new_segments:
            self.scene.removeItem(seg)
        
        # Remove junction
        self.scene.removeItem(self.junction)
        
        # Restore old segment
        self.scene.addItem(self.old_segment)
