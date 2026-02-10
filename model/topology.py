from dataclasses import dataclass, field
from typing import List, Dict, Optional, Set
import uuid

class TopologyNode:
    """Base class for nodes in the topology graph (connectors, junctions, branch points)"""
    def __init__(self, node_id: str = None, position=(0, 0)):
        self.id = node_id or str(uuid.uuid4())
        self.position = position  # (x, y)
        self.connected_segments: List[WireSegment] = []

class JunctionNode(TopologyNode):
    """Represents a junction where multiple wire segments meet"""
    def __init__(self, position=(0, 0)):
        super().__init__(f"J_{uuid.uuid4().hex[:8]}", position)
        self.type = "junction"

class BranchPointNode(TopologyNode):
    """Represents a branch point (like a splice or tie point)"""
    def __init__(self, position=(0, 0), bp_type="split"):
        super().__init__(f"BP_{uuid.uuid4().hex[:8]}", position)
        self.type = "branch_point"
        self.branch_type = bp_type  # "split", "merge", "splice"
        self.splice_info = None  # For splice details

class WireSegment:
    """A segment of wire between two topology nodes"""
    def __init__(self, segment_id: str = None, 
                 start_node: TopologyNode = None,
                 end_node: TopologyNode = None,
                 net=None,
                 wires: List = None):
        self.id = segment_id or f"SEG_{uuid.uuid4().hex[:8]}"
        self.start_node = start_node
        self.end_node = end_node
        self.net = net
        self.wires: List[Wire] = wires or []  # Actual wires in this segment
        self.bundle = None  # For grouping wires
        
        # Connect nodes
        if start_node:
            start_node.connected_segments.append(self)
        if end_node:
            end_node.connected_segments.append(self)

class Bundle:
    """Groups multiple wires together in a segment"""
    def __init__(self, bundle_id: str = None):
        self.id = bundle_id or f"BND_{uuid.uuid4().hex[:8]}"
        self.wires: List[Wire] = []
        self.diameter: float = 0.0
        self.color: str = "BLK"  # Default bundle color
        self.protection: str = None  # "sleeving", "conduit", etc.
