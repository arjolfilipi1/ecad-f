from .base_command import BaseCommand, CompoundCommand

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
