from typing import List, Dict, Optional, Tuple
from PyQt5.QtCore import QPointF
from PyQt5.QtGui import QCursor
import numpy as np
from collections import defaultdict
from graphics.visualization_manager import VisualizationManager,VisualizationMode
class HarnessAutoRouter:
    """Automatic harness topology router - ADDS topology, DOESN'T DELETE"""
    
    def __init__(self, topology_manager, main_window):
        self.topology_manager = topology_manager
        self.main_window = main_window
        self.segments = []
        self.branch_points = []
        
    def route_from_imported_data(self):
        """
        Add topology to existing wires
        """
        print("\n=== AUTO-ROUTING STARTED ===")
        
        wire_items = getattr(self.main_window, 'imported_wire_items', [])
        if not wire_items:
            print("No imported wires found")
            return False
        
        # Store current topology for undo
        branch_points = []
        segments = []
        
        # HIDE original direct wires
        for wire_item in wire_items:
            wire_item.setVisible(False)
            wire_item.setSelected(False)
        
        # Clear any existing routed wires
        if hasattr(self.main_window, 'routed_wire_items'):
            for item in self.main_window.routed_wire_items:
                if item.scene():
                    self.main_window.scene.removeItem(item)
            self.main_window.routed_wire_items = []
        
        # Clear existing topology
        self.clear_topology()
        
        # Analyze wire patterns
        wire_groups = self._group_wires_by_path(wire_items)
        
        # Create branch points and segments
        self._create_topology_from_groups(wire_groups)
        
        # Add segmented wire visualization
        self._add_segmented_visualization(wire_items)
        
        # Update wires list for tree view
        if hasattr(self.main_window, 'routed_wire_items'):
            self.main_window.wires = [item.wire for item in self.main_window.routed_wire_items 
                                       if hasattr(item, 'wire')]
        
        # Refresh tree view
        self.main_window.refresh_tree_views()
        
        # Update visualization
        if hasattr(self.main_window, 'viz_manager'):
            self.main_window.viz_manager.set_mode(VisualizationMode.ALL)
            self.main_window.viz_manager.show_direct_wires = False
            self.main_window.viz_manager.update_visibility()
        
        # Force update of connectors to refresh wires
        for c in self.main_window.conns:
            c.update()
            c._update_connected_segments()
        
        print("=== AUTO-ROUTING COMPLETED ===\n")
        
        # Create undo command
        from commands.wire_commands import RouteWiresCommand
        cmd = RouteWiresCommand(
            self.main_window,
            wire_items,
            self.branch_points,
            self.segments
        )
        self.main_window.undo_manager.push(cmd)
        
        return True





    
    def _group_wires_by_path(self, wire_items):
        """Group wires that share common paths"""
        from collections import defaultdict
        
        connections = defaultdict(list)
        
        for wire in wire_items:
            from_conn = wire.start_pin.parent
            to_conn = wire.end_pin.parent
            key = (from_conn.cid, to_conn.cid)
            connections[key].append(wire)
        
        # Find connectors that appear frequently (hub candidates)
        connector_frequency = defaultdict(int)
        for (from_id, to_id), wires in connections.items():
            connector_frequency[from_id] += len(wires)
            connector_frequency[to_id] += len(wires)
        
        # Identify central connectors (hubs)
        central_connectors = []
        for conn_id, freq in connector_frequency.items():
            if freq > 2:  # Adjust threshold
                central_connectors.append(conn_id)
        
        print(f"Identified central connectors: {central_connectors}")
        
        # Group wires
        groups = {
            'direct': [],  # Direct connections (no branch needed)
            'via_central': defaultdict(list)  # via_central[central_id] = list of wires
        }
        
        for (from_id, to_id), wires in connections.items():
            if from_id in central_connectors:
                groups['via_central'][from_id].extend(wires)
            elif to_id in central_connectors:
                groups['via_central'][to_id].extend(wires)
            else:
                groups['direct'].extend(wires)
        
        return groups
    
    def _create_topology_from_groups(self, wire_groups):
        """Create branch points and segments - NO WIRE DELETION"""
        
        # Create branch points for central connectors
        central_bps = {}
        
        for central_id, wires in wire_groups['via_central'].items():
            # Find the central connector
            central_conn = None
            for conn in self.main_window.conns:
                if conn.cid == central_id:
                    central_conn = conn
                    break
            
            if not central_conn:
                continue
            
            # Create branch point near the central connector
            pos = (central_conn.pos().x() + 80, central_conn.pos().y() - 20)
            bp = self.topology_manager.create_branch_point(pos, "split")
            
            # Create graphics
            from graphics.topology_item import BranchPointGraphicsItem
            bp_graphics = BranchPointGraphicsItem(bp)
            self.main_window.scene.addItem(bp_graphics)
            self.branch_points.append(bp_graphics)
            
            # Create segment from connector to branch point
            seg = self.topology_manager.create_segment(
                central_conn.topology_node,
                bp
            )
            from graphics.segment_item import SegmentGraphicsItem
            seg_graphics = SegmentGraphicsItem(seg, self.topology_manager)
            self.main_window.scene.addItem(seg_graphics)
            self.segments.append(seg_graphics)
            
            central_bps[central_id] = (bp, seg)
        
        # Create segments from branch points to other connectors
        for central_id, (bp_node, trunk_seg) in central_bps.items():
            central_conn = None
            for conn in self.main_window.conns:
                if conn.cid == central_id:
                    central_conn = conn
                    break
            
            if not central_conn:
                continue
            
            # Find all other connectors that connect to this central
            connected_connectors = set()
            for wire in wire_groups['via_central'][central_id]:
                if wire.start_pin.parent != central_conn:
                    connected_connectors.add(wire.start_pin.parent)
                if wire.end_pin.parent != central_conn:
                    connected_connectors.add(wire.end_pin.parent)
            
            # Create segments to each connected connector
            for other_conn in connected_connectors:
                existing = self._find_segment(bp_node, other_conn.topology_node)
                if not existing:
                    seg = self.topology_manager.create_segment(
                        bp_node,
                        other_conn.topology_node
                    )
                    seg_graphics = SegmentGraphicsItem(seg, self.topology_manager)
                    self.main_window.scene.addItem(seg_graphics)
                    self.segments.append(seg_graphics)
        
        # Handle direct connections (no branch point)
        for wire in wire_groups['direct']:
            self._create_direct_segment(wire)
    
    def _create_direct_segment(self, wire_item):
        """Create direct segment between two connectors"""
        from_node = wire_item.start_pin.parent.topology_node
        to_node = wire_item.end_pin.parent.topology_node
        
        # Check if segment already exists
        existing = self._find_segment(from_node, to_node)
        if existing:
            return existing
        
        segment = self.topology_manager.create_segment(from_node, to_node)
        from graphics.segment_item import SegmentGraphicsItem
        seg_graphics = SegmentGraphicsItem(segment, self.topology_manager)
        self.main_window.scene.addItem(seg_graphics)
        self.segments.append(seg_graphics)
        
        return segment
    
    def _find_segment(self, node1, node2):
        """Find existing segment between two nodes"""
        for seg in self.topology_manager.segments.values():
            if (seg.start_node == node1 and seg.end_node == node2) or \
               (seg.start_node == node2 and seg.end_node == node1):
                return seg
        return None
    
    def _add_segmented_visualization(self, wire_items):
        """
        ADD segmented wire visualization on top of existing topology
        Does NOT delete original wires
        """
        from graphics.wire_item import SegmentedWireItem
        
        # Group wires that share the same path
        wire_paths = {}
        
        for wire_item in wire_items:
            from_pin = wire_item.start_pin
            to_pin = wire_item.end_pin
            
            # Find path through topology
            from_node = from_pin.parent.topology_node
            to_node = to_pin.parent.topology_node
            
            path = self.topology_manager.find_path(from_node, to_node)
            
            if path:
                # Create key from node IDs in path
                path_key = tuple([from_node.id] + [p.id for p in path] + [to_node.id])
                
                if path_key not in wire_paths:
                    wire_paths[path_key] = {
                        'path': path,
                        'from_node': from_node,
                        'to_node': to_node,
                        'wires': []
                    }
                
                wire_paths[path_key]['wires'].append(wire_item)
        
        # Create one SegmentedWireItem per unique path
        for path_key, path_info in wire_paths.items():
            if not path_info['wires']:
                continue
            
            # Use first wire as template
            template_wire = path_info['wires'][0]
            
            # Create a wire object for the segmented path
            from model.wire import Wire
            wire = Wire(
                f"ROUTE_{template_wire.wid}",
                template_wire.start_pin,
                template_wire.end_pin
            )
            
            # Copy properties
            wire.color_data = template_wire.color_data
            wire.color = template_wire.color
            
            # Add segments
            for segment in path_info['path']:
                wire.add_segment(segment)
                if wire not in segment.wires:
                    segment.wires.append(wire)
            
            # Create graphics
            wire_graphics = SegmentedWireItem(wire)
            wire_graphics.set_main_window(self.main_window)
            self.main_window.scene.addItem(wire_graphics)
            wire.graphics_item = wire_graphics
            
            # Store reference
            if not hasattr(self.main_window, 'routed_wire_items'):
                self.main_window.routed_wire_items = []
            self.main_window.routed_wire_items.append(wire_graphics)
            
            # Link back to original wire
            for original_wire in path_info['wires']:
                if not hasattr(original_wire, 'routed_visualization'):
                    original_wire.routed_visualization = []
                original_wire.routed_visualization.append(wire_graphics)
    
    def clear_topology(self):
        """Remove topology elements but KEEP original wires"""
        # Remove segment graphics
        for item in self.segments:
            if item.scene():
                self.main_window.scene.removeItem(item)
        
        # Remove branch point graphics
        for item in self.branch_points:
            if item.scene():
                self.main_window.scene.removeItem(item)
        
        # Remove segmented wire visualizations
        if hasattr(self.main_window, 'routed_wire_items'):
            for item in self.main_window.routed_wire_items:
                if item.scene():
                    self.main_window.scene.removeItem(item)
            self.main_window.routed_wire_items = []
        
        # Clear topology data but KEEP connector nodes
        self.topology_manager.segments.clear()
        self.topology_manager.nodes = {
            k: v for k, v in self.topology_manager.nodes.items()
            if hasattr(v, 'node_type') and v.node_type == "connector"
        }
        self.topology_manager.wires.clear()
        
        self.segments.clear()
        self.branch_points.clear()
        
        print("Topology cleared - original wires preserved")


class ManualRouter:
    """Manual routing tools for user-guided topology creation"""
    
    def __init__(self, topology_manager, main_window):
        self.topology_manager = topology_manager
        self.main_window = main_window
    
    def create_branch_point_at_cursor(self):
        """Create branch point at mouse position"""
        pos = self.main_window.view.mapToScene(
            self.main_window.view.mapFromGlobal(QCursor.pos())
        )
        bp_node = self.topology_manager.create_branch_point((pos.x(), pos.y()))
        from graphics.topology_item import BranchPointGraphicsItem
        bp_graphics = BranchPointGraphicsItem(bp_node)
        self.main_window.scene.addItem(bp_graphics)
        return bp_graphics
    
    def create_segment_between_selected(self):
        """Create segment between two selected nodes"""
        selected = self.main_window.scene.selectedItems()
        nodes = []
        
        for item in selected:
            if hasattr(item, 'topology_node'):
                nodes.append(item.topology_node)
            elif hasattr(item, 'branch_node'):
                nodes.append(item.branch_node)
            elif hasattr(item, 'junction_node'):
                nodes.append(item.junction_node)
        
        if len(nodes) == 2:
            segment = self.topology_manager.create_segment(nodes[0], nodes[1])
            from graphics.segment_item import SegmentGraphicsItem
            seg_graphics = SegmentGraphicsItem(segment, self.topology_manager)
            self.main_window.scene.addItem(seg_graphics)
            return seg_graphics
        return None
    
    def route_selected_wires(self):
        """Route selected wires through topology"""
        selected = self.main_window.scene.selectedItems()
        wires = [item for item in selected if hasattr(item, 'wire')]
        
        from graphics.wire_item import SegmentedWireItem
        
        for wire_item in wires:
            wire = wire_item.wire
            from_node = wire.from_pin.parent.topology_node
            to_node = wire.to_pin.parent.topology_node
            
            path = self.topology_manager.find_path(from_node, to_node)
            if path:
                # Remove old graphics
                self.main_window.scene.removeItem(wire_item)
                
                # Create new segmented wire
                new_wire_graphics = SegmentedWireItem(wire)
                new_wire_graphics.set_main_window(self.main_window)
                self.main_window.scene.addItem(new_wire_graphics)
                wire.graphics_item = new_wire_graphics
class BundleRouter:
    """Route wires through manually drawn bundles"""
    
    def __init__(self, main_window):
        self.main_window = main_window
        self.topology_manager = main_window.topology_manager
    
    def route_wires_through_bundles(self):
        """Assign wires to bundles based on connectivity"""
        
        # Get all bundles
        bundles = getattr(self.main_window, 'bundles', [])
        if not bundles:
            return False
        
        # Get all wires
        wires = getattr(self.main_window, 'imported_wire_items', [])
        if not wires:
            return False
        
        # Group wires by path
        # This is a simplified version - you'd need more sophisticated routing
        
        # Create topology from bundles
        for bundle in bundles:
            # Create nodes at bundle ends
            start_node = self.get_or_create_node(bundle.start_point)
            end_node = self.get_or_create_node(bundle.end_point)
            
            # Create segment
            segment = self.topology_manager.create_segment(start_node, end_node)
            segment.specified_length = bundle.specified_length or bundle.length
            
            # Store in bundle
            bundle.segment = segment
            bundle.start_node = start_node
            bundle.end_node = end_node
        
        # Assign wires to bundles
        for wire in wires:
            # Find which bundles this wire should go through
            # This requires pathfinding from wire.from_pin to wire.to_pin
            pass
        
        return True
