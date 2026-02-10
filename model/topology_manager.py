from .topology import BranchPointNode,JunctionNode,TopologyNode,WireSegment
from typing import List,Optional
from graphics.pin_item import PinItem
from .wire import Wire
class TopologyManager:
    """Manages the complete harness topology"""
    def __init__(self):
        self.nodes: Dict[str, TopologyNode] = {}
        self.segments: Dict[str, WireSegment] = {}
        self.bundles: Dict[str, Bundle] = {}
        self.wires: Dict[str, Wire] = {}
        
    def create_branch_point(self, position, bp_type="split") -> BranchPointNode:
        """Create a new branch point"""
        bp = BranchPointNode(position, bp_type)
        self.nodes[bp.id] = bp
        return bp
        
    def create_junction(self, position) -> JunctionNode:
        """Create a new junction"""
        junction = JunctionNode(position)
        self.nodes[junction.id] = junction
        return junction
        
    def create_segment(self, start_node: TopologyNode, end_node: TopologyNode, net=None) -> WireSegment:
        """Create a wire segment between two nodes"""
        segment = WireSegment(start_node=start_node, end_node=end_node, net=net)
        self.segments[segment.id] = segment
        return segment
        
    def split_segment(self, segment: WireSegment, split_position, create_junction=True) -> List[WireSegment]:
        """Split a segment at a position"""
        if create_junction:
            # Create junction at split point
            junction = self.create_junction(split_position)
            
            # Create two new segments
            seg1 = self.create_segment(segment.start_node, junction, segment.net)
            seg2 = self.create_segment(junction, segment.end_node, segment.net)
            
            # Transfer wires from old segment to new segments
            for wire in segment.wires:
                wire.segments.remove(segment)
                wire.add_segment(seg1)
                wire.add_segment(seg2)
            
            # Remove old segment
            del self.segments[segment.id]
            
            return [seg1, seg2]
        return [segment]
        
    def create_wire_path(self, from_pin: PinItem, to_pin: PinItem, 
                         via_nodes: List[TopologyNode] = None) -> Wire:
        """Create a wire that goes through specific nodes"""
        wire = Wire(f"W{len(self.wires)+1}", from_pin, to_pin)
        
        # Get start and end connector nodes
        start_node = from_pin.parent.topology_node
        end_node = to_pin.parent.topology_node
        
        # Create path through nodes
        all_nodes = [start_node] + (via_nodes or []) + [end_node]
        
        # Create or reuse segments between nodes
        for i in range(len(all_nodes) - 1):
            node1 = all_nodes[i]
            node2 = all_nodes[i + 1]
            
            # Check if segment already exists
            existing_segment = self.find_segment_between(node1, node2)
            if existing_segment:
                wire.add_segment(existing_segment)
            else:
                # Create new segment
                segment = self.create_segment(node1, node2)
                wire.add_segment(segment)
        
        self.wires[wire.id] = wire
        return wire
        
    def find_segment_between(self, node1: TopologyNode, node2: TopologyNode) -> Optional[WireSegment]:
        """Find segment connecting two nodes (in either direction)"""
        for segment in self.segments.values():
            if (segment.start_node == node1 and segment.end_node == node2) or \
               (segment.start_node == node2 and segment.end_node == node1):
                return segment
        return None