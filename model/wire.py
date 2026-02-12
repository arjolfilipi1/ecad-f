#model/wire
from graphics.pin_item import PinItem
from .topology import WireSegment,TopologyNode
from typing import List,Optional
from model.models import CombinedWireColor
class Wire:
    """A complete wire that can pass through multiple segments"""
    def __init__(self, wire_id: str, 
                 from_pin: PinItem = None,
                 to_pin: PinItem = None,
                 color_txt: str = "SW",cross_section:float = 1.0):
        self.id = wire_id
        self.from_pin = from_pin
        self.to_pin = to_pin
        self.cross_section = cross_section
        self.color_data = CombinedWireColor(color_txt)
        self.segments: List[WireSegment] = []  # Path through segments
        self.net = None
        self.length: float = 0.0
        self.cut_length: float = 0.0
        
    def add_segment(self, segment: WireSegment):
        """Add a segment to this wire's path"""
        self.segments.append(segment)
        segment.wires.append(self)
        
    def get_path_nodes(self) -> List[TopologyNode]:
        """Get all nodes this wire passes through, in order"""
        if not self.segments:
            return []
            
        # Reconstruct the path from segments
        nodes = []
        current_node = self.from_pin.parent_item().topology_node
        nodes.append(current_node)
        
        for segment in self.segments:
            next_node = segment.end_node if segment.start_node == current_node else segment.start_node
            if next_node not in nodes:
                nodes.append(next_node)
                current_node = next_node
                
        return nodes