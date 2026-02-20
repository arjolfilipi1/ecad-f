from typing import List, Dict, Optional, Tuple
from PyQt5.QtCore import QPointF
import math
from graphics.visualization_manager import VisualizationMode


class BundleRouter:
    """Route wires through manually drawn bundles using node connections"""
    
    def __init__(self, main_window):
        self.main_window = main_window
        self.topology_manager = main_window.topology_manager
        self.scene = main_window.scene
        
    def route_wires_through_bundles(self) -> bool:
        """
        Route all imported wires through the drawn bundles
        Uses bundle.start_node and bundle.end_node for routing
        """
        # Get all bundles
        bundles = getattr(self.main_window, 'bundles', [])
        if not bundles:
            self.main_window.statusBar().showMessage("No bundles to route through", 3000)
            return False
        
        # Get all wires to route
        wires = getattr(self.main_window, 'imported_wire_items', [])
        if not wires:
            self.main_window.statusBar().showMessage("No wires to route", 3000)
            return False
        
        print(f"\n=== BUNDLE ROUTING STARTED ===")
        print(f"Bundles: {len(bundles)}")
        print(f"Wires: {len(wires)}")
        
        # First, ensure all bundles have proper node connections
        self._ensure_bundle_nodes(bundles)
        
        # Build node graph from bundles
        node_graph = self._build_bundle_graph(bundles)
        
        # Store created elements for undo
        created_segments = []
        routed_wires = []
        
        # Route each wire through the bundle graph
        routed_count = 0
        for wire in wires:
            if self._route_single_wire(wire, bundles, node_graph, created_segments, routed_wires):
                routed_count += 1
        
        if routed_count > 0:
            # Hide original direct wires
            for wire in wires:
                wire.setVisible(False)
                wire.setSelected(False)
            
            # Store routed wires
            if not hasattr(self.main_window, 'routed_wire_items'):
                self.main_window.routed_wire_items = []
            self.main_window.routed_wire_items.extend(routed_wires)
            
            # Update wires list
            self.main_window.wires = [item.wire for item in routed_wires if hasattr(item, 'wire')]
            
            # Create segments if they don't exist
            self._create_missing_segments(bundles, created_segments)
            
            # Refresh views
            self.main_window.refresh_tree_views()
            
            # Update visualization
            if hasattr(self.main_window, 'viz_manager'):
                self.main_window.viz_manager.set_mode(VisualizationMode.ALL)
                self.main_window.viz_manager.show_direct_wires = False
                self.main_window.viz_manager.update_visibility()
            
            # Create undo command    main_window, original_wires, routed_wires, branch_points, segments, bundles
            from commands.bundle_commands import RouteWiresThroughBundlesCommand
            cmd = RouteWiresThroughBundlesCommand(
                main_window = self.main_window,
                original_wires = wires,
                routed_wires = routed_wires,
                branch_points = [],
                segments = created_segments,
                bundles =bundles
            )
            self.main_window.undo_manager.push(cmd)
            
            print(f"=== BUNDLE ROUTING COMPLETED: {routed_count} wires routed ===\n")
            self.main_window.statusBar().showMessage(f"Routed {routed_count} wires through bundles", 3000)
            return True
        else:
            print("=== BUNDLE ROUTING FAILED ===\n")
            self.main_window.statusBar().showMessage("No wires could be routed through bundles", 3000)
            return False
    
    def _ensure_bundle_nodes(self, bundles):
        """Ensure all bundles have valid start_node and end_node references"""
        for bundle in bundles:
            if not bundle.start_node:
                # Try to find or create start node
                if bundle.start_item and hasattr(bundle.start_item, 'topology_node'):
                    bundle.start_node = bundle.start_item.topology_node
                else:
                    # Create a new branch point
                    from model.topology import BranchPointNode
                    from graphics.topology_item import BranchPointGraphicsItem
                    
                    node = BranchPointNode((bundle.start_point.x(), bundle.start_point.y()), "junction")
                    graphics = BranchPointGraphicsItem(node)
                    self.scene.addItem(graphics)
                    self.topology_manager.nodes[node.id] = node
                    bundle.start_node = node
                    bundle.start_item = graphics
            
            if not bundle.end_node:
                # Try to find or create end node
                if bundle.end_item and hasattr(bundle.end_item, 'topology_node'):
                    bundle.end_node = bundle.end_item.topology_node
                else:
                    # Create a new branch point
                    from model.topology import BranchPointNode
                    from graphics.topology_item import BranchPointGraphicsItem
                    
                    node = BranchPointNode((bundle.end_point.x(), bundle.end_point.y()), "junction")
                    graphics = BranchPointGraphicsItem(node)
                    self.scene.addItem(graphics)
                    self.topology_manager.nodes[node.id] = node
                    bundle.end_node = node
                    bundle.end_item = graphics
    
    def _build_bundle_graph(self, bundles):
        """
        Build a graph of nodes connected by bundles
        Returns: {
            node: [connected_nodes]
        }
        """
        graph = {}
        
        for bundle in bundles:
            if bundle.start_node and bundle.end_node:
                # Add forward connection
                if bundle.start_node not in graph:
                    graph[bundle.start_node] = []
                if bundle.end_node not in graph[bundle.start_node]:
                    graph[bundle.start_node].append(bundle.end_node)
                
                # Add reverse connection
                if bundle.end_node not in graph:
                    graph[bundle.end_node] = []
                if bundle.start_node not in graph[bundle.end_node]:
                    graph[bundle.end_node].append(bundle.start_node)
        
        return graph
    
    def _find_path_through_bundles(self, start_node, end_node, graph):
        """
        Find a path through the bundle graph from start_node to end_node
        Returns list of nodes in the path
        """
        if start_node == end_node:
            return [start_node]
        
        # BFS to find path
        from collections import deque
        
        visited = {start_node}
        queue = deque([(start_node, [start_node])])
        
        while queue:
            current, path = queue.popleft()
            
            for neighbor in graph.get(current, []):
                if neighbor == end_node:
                    return path + [neighbor]
                
                if neighbor not in visited:
                    visited.add(neighbor)
                    queue.append((neighbor, path + [neighbor]))
        
        return []  # No path found
    
    def _route_single_wire(self, wire, bundles, graph, created_segments, routed_wires):
        """Route a single wire through the bundle graph and assign to bundles"""
        
        # Get the connectors
        from_conn = wire.start_pin.parent
        to_conn = wire.end_pin.parent
        
        if not from_conn.topology_node or not to_conn.topology_node:
            print(f"Wire {wire.wid}: Missing connector topology nodes")
            return False
        
        # Find which bundles connect to the from_connector
        start_bundles = []
        for bundle in bundles:
            if bundle.start_node == from_conn.topology_node or bundle.end_node == from_conn.topology_node:
                start_bundles.append(bundle)
        
        # Find which bundles connect to the to_connector
        end_bundles = []
        for bundle in bundles:
            if bundle.start_node == to_conn.topology_node or bundle.end_node == to_conn.topology_node:
                end_bundles.append(bundle)
        
        if not start_bundles or not end_bundles:
            print(f"Wire {wire.wid}: No bundles connected to connectors")
            return False
        
        # Try each possible start bundle
        for start_bundle in start_bundles:
            # Get the node that connects to from_connector
            start_node = (start_bundle.end_node if start_bundle.start_node == from_conn.topology_node 
                         else start_bundle.start_node)
            
            # Try each possible end bundle
            for end_bundle in end_bundles:
                # Get the node that connects to to_connector
                end_node = (end_bundle.end_node if end_bundle.start_node == to_conn.topology_node 
                           else end_bundle.start_node)
                
                # Find path through bundle graph
                path_nodes = self._find_path_through_bundles(start_node, end_node, graph)
                
                if path_nodes:
                    # Build complete node path including connectors
                    full_path = [from_conn.topology_node] + path_nodes + [to_conn.topology_node]
                    
                    # Find which bundles are used in this path
                    used_bundles = self._find_bundles_in_path(path_nodes, bundles)
                    print("used",path_nodes,used_bundles,bundles)
                    # Create the routed wire and assign to bundles
                    return self._create_routed_wire(wire, full_path, used_bundles, 
                                                    created_segments, routed_wires)
        
        print(f"Wire {wire.wid}: No bundle path found")
        return False
    def _find_bundles_in_path(self, path_nodes, bundles) -> List:
        """
        Find which bundles are used in the node path
        Returns list of bundles that connect consecutive nodes in the path
        """
        used_bundles = []
        
        for i in range(len(path_nodes) - 1):
            node1 = path_nodes[i]
            node2 = path_nodes[i + 1]
            
            # Find bundle connecting these two nodes
            # add check if conn is start and nodes match
            for bundle in bundles:
                if (bundle.start_node == node1 and bundle.end_node == node2) or \
                   (bundle.start_node == node2 and bundle.end_node == node1):
                    if bundle not in used_bundles:
                        used_bundles.append(bundle)
                    break
        
        return used_bundles

    
    def _create_routed_wire(self, original_wire, node_path, used_bundles, 
                           created_segments, routed_wires):
        """Create a routed wire along the given node path and assign to bundles"""
        from graphics.wire_item import SegmentedWireItem
        from model.wire import Wire
        
        # Find or create segments along the path
        path_segments = []
        
        for i in range(len(node_path) - 1):
            start_node = node_path[i]
            end_node = node_path[i + 1]
            
            # Check if segment already exists
            segment = self._find_segment_between_nodes(start_node, end_node)
            
            if not segment:
                # Create new segment
                from model.topology import WireSegment
                from graphics.segment_item import SegmentGraphicsItem
                
                segment = WireSegment(
                    start_node=start_node,
                    end_node=end_node,
                    wires=[]
                )
                self.topology_manager.segments[segment.id] = segment
                
                segment_graphics = SegmentGraphicsItem(segment, self.topology_manager)
                self.scene.addItem(segment_graphics)
                created_segments.append(segment_graphics)
            
            path_segments.append(segment)
        
        # Create wire object
        wire_id = f"ROUTE_{original_wire.wid}"
        
        wire = Wire(
            wire_id,
            original_wire.start_pin,
            original_wire.end_pin,
            original_wire.color_data.code if hasattr(original_wire, 'color_data') else 'SW'
        )
        wire.cross_section = getattr(original_wire, 'cross_section', 0.5)
        wire.color_data = original_wire.color_data
        
        # Add wire to segments
        for segment in path_segments:
            wire.add_segment(segment)
            if wire not in segment.wires:
                segment.wires.append(wire)
        
        # Create graphics
        wire_graphics = SegmentedWireItem(wire)
        wire_graphics.set_main_window(self.main_window)
        self.scene.addItem(wire_graphics)
        wire.graphics_item = wire_graphics
        
        routed_wires.append(wire_graphics)
        
        # ASSIGN WIRE TO BUNDLES - THIS IS THE KEY PART
        for bundle in used_bundles:
            bundle.assign_wire(original_wire.wid)
            print(f"Assigned wire {original_wire.wid} to bundle {bundle.bundle_id}")
        
        # Link back to original wire
        if not hasattr(original_wire, 'routed_visualization'):
            original_wire.routed_visualization = []
        original_wire.routed_visualization.append(wire_graphics)
        
        # Store which bundles this wire uses
        wire_graphics.used_bundles = used_bundles
        
        # Update segment appearances
        for segment in path_segments:
            if hasattr(segment, 'graphics_item'):
                segment.graphics_item.update_appearance()
        
        return True

    
    def _find_segment_between_nodes(self, node1, node2):
        """Find existing segment between two nodes"""
        for segment in self.topology_manager.segments.values():
            if (segment.start_node == node1 and segment.end_node == node2) or \
               (segment.start_node == node2 and segment.end_node == node1):
                return segment
        return None
    
    def _create_missing_segments(self, bundles, created_segments):
        """Create segments for bundles that don't have them"""
        for bundle in bundles:
            if not hasattr(bundle, 'segment') or not bundle.segment:
                if bundle.start_node and bundle.end_node:
                    # Check if segment already exists
                    segment = self._find_segment_between_nodes(bundle.start_node, bundle.end_node)
                    
                    if not segment:
                        # Create new segment
                        from model.topology import WireSegment
                        from graphics.segment_item import SegmentGraphicsItem
                        
                        segment = WireSegment(
                            start_node=bundle.start_node,
                            end_node=bundle.end_node,
                            wires=[]
                        )
                        self.topology_manager.segments[segment.id] = segment
                        
                        segment_graphics = SegmentGraphicsItem(segment, self.topology_manager)
                        self.scene.addItem(segment_graphics)
                        created_segments.append(segment_graphics)
                        
                        bundle.segment = segment
                        bundle.segment_graphics = segment_graphics

