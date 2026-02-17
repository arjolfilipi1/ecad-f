from .base_command import BaseCommand, CompoundCommand

class AddBranchPointCommand(BaseCommand):
    """Add a branch point to the scene"""
    
    def __init__(self, scene, branch_point_item, pos: tuple):
        super().__init__("Add Branch Point")
        self.scene = scene
        self.branch_point = branch_point_item
        self.pos = pos
        self.bp_id = branch_point_item.branch_node.id
    
    def redo(self):
        if self.first_redo:
            self.first_redo = False
            return
        
        self.branch_point.setPos(*self.pos)
        self.scene.addItem(self.branch_point)
    
    def undo(self):
        self.scene.removeItem(self.branch_point)


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
