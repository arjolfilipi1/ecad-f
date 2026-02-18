#model/topology_manager
from typing import List, Dict, Optional, Set
from model.topology import TopologyNode, JunctionNode, BranchPointNode, WireSegment, Bundle
from model.wire import Wire
from graphics.pin_item import PinItem
from graphics.connection_point import ConnectionPoint
from PyQt5.QtCore import QPointF
import uuid

class TopologyManager:
    def __init__(self):
        self.nodes: Dict[str, TopologyNode] = {}
        self.segments: Dict[str, WireSegment] = {}
        self.branches: Dict[str, HarnessBranch] = {}  # NEW
        self.bundles: Dict[str, Bundle] = {}
        self.wires: Dict[str, Wire] = {}
        self.connection_points: Dict[str, ConnectionPoint] = {}
        self.netlist = None  # Will be set from main window
        
    def set_netlist(self, netlist):
        """Set the netlist for creating nets"""
        self.netlist = netlist
    
    def create_connector_node(self, connector) -> TopologyNode:
        """Create a topology node for a connector"""
        node = TopologyNode(
            node_id=f"CONN_{connector.cid}",
            position=(connector.pos().x(), connector.pos().y())
        )
        node.node_type = "connector"
        node.connector_ref = connector  # Store reference
        self.nodes[node.id] = node
        connector.topology_node = node
        return node
    
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
    
    def create_segment(self, start_node: TopologyNode, end_node: TopologyNode) -> WireSegment:
        """Create a wire segment between two nodes"""
        segment_id = f"SEG_{len(self.segments) + 1}"
        segment = WireSegment(segment_id, start_node, end_node)
        self.segments[segment.id] = segment
        return segment
    
    def find_path(self, start_node: TopologyNode, end_node: TopologyNode) -> List[WireSegment]:
        """Find shortest path between two nodes using BFS"""
        if start_node == end_node:
            return []
        
        visited = set()
        queue = [(start_node, [])]
        
        while queue:
            current_node, path = queue.pop(0)
            
            if current_node == end_node:
                return path
            
            if current_node.id in visited:
                continue
                
            visited.add(current_node.id)
            
            # Check all segments connected to current node
            for segment in self.segments.values():
                next_node = None
                if segment.start_node == current_node:
                    next_node = segment.end_node
                elif segment.end_node == current_node:
                    next_node = segment.start_node
                
                if next_node and next_node.id not in visited:
                    queue.append((next_node, path + [segment]))
        
        return []  # No path found
    
    def route_wire(self, from_pin: PinItem, to_pin: PinItem, 
                   via_nodes: List[TopologyNode] = None,wid:str=None,import_wire = None) -> Optional[Wire]:
        """Route a wire through the topology graph"""
        from_connector = from_pin.parent
        to_connector = to_pin.parent
        
        # Get connector nodes
        from_node = from_connector.topology_node
        to_node = to_connector.topology_node
        
        if not from_node or not to_node:
            print("Connector missing topology node")
            return None
        
        # Build path nodes
        path_nodes = []
        path_nodes.append(from_node)
        if via_nodes:
            path_nodes.extend(via_nodes)
        if to_node != from_node:
            path_nodes.append(to_node)
        
        # Find segments between consecutive nodes
        wire_segments = []
        for i in range(len(path_nodes) - 1):
            path = self.find_path(path_nodes[i], path_nodes[i + 1])
            if not path:
                # No path exists - create direct segment
                print(f"Creating direct segment between nodes")
                segment = self.create_segment(path_nodes[i], path_nodes[i + 1])
                path = [segment]
            wire_segments.extend(path)
        
        if not wire_segments:
            print("No path found")
            return None
        
        # Create wire
        wire_id = f"W{len(self.wires) + 1}"
        
        # Import here to avoid circular imports
        from model.wire import Wire
        if not import_wire:
            wire = Wire(wire_id, from_pin, to_pin,wid)
        else:
            wire = Wire(wire_id =wire_id, from_pin=from_pin, to_pin =to_pin, color_txt = import_wire.color,cross_section= import_wire.cross_section)
            
        # Add wire to each segment
        for segment in wire_segments:
            wire.add_segment(segment)
            if wire not in segment.wires:
                segment.wires.append(wire)
        
        self.wires[wire.id] = wire
        
        # Create net if netlist exists
        if self.netlist:
            net = self.netlist.connect(from_pin, to_pin)
            wire.net = net
        

        return wire
    
    def split_segment(self, segment: WireSegment, split_position, create_junction=True) -> List[WireSegment]:
        """Split a segment at a position"""
        if create_junction:
            # Create junction at split point
            junction = self.create_junction(split_position)
            
            # Create two new segments
            seg1 = self.create_segment(segment.start_node, junction)
            seg2 = self.create_segment(junction, segment.end_node)
            
            # Transfer wires from old segment to new segments
            for wire in segment.wires[:]:  # Copy list
                wire.segments.remove(segment)
                wire.add_segment(seg1)
                wire.add_segment(seg2)
                seg1.wires.append(wire)
                seg2.wires.append(wire)
            
            # Remove old segment
            if segment.id in self.segments:
                del self.segments[segment.id]
            
            return [seg1, seg2]
        return [segment]
    def create_fastener_node(self, position, fastener_type="cable_tie", part_number=None):
        """Create a new fastener node"""
        from model.topology import FastenerNode
        fastener = FastenerNode(position, fastener_type, part_number)
        self.nodes[fastener.id] = fastener
        return fastener