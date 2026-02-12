# graphics/visualization_manager.py
from PyQt5.QtWidgets import QAction, QToolBar, QActionGroup
from PyQt5.QtCore import Qt
from enum import Enum, auto
from graphics.wire_item import SegmentedWireItem, WireItem
from graphics.topology_item import (
    JunctionGraphicsItem, BranchPointGraphicsItem
)
from graphics.segment_item import SegmentGraphicsItem
from graphics.connector_item import ConnectorItem

class VisualizationMode(Enum):
    """Visualization modes for the harness view"""
    ALL = auto()              # Show everything: bundles, routed wires, branch points
    BUNDLES_ONLY = auto()     # Show only bundle segments
    ROUTED_WIRES_ONLY = auto() # Show only routed wires (no bundles)
    DIRECT_WIRES_ONLY = auto() # Show only original direct wires (no topology)
    MANUFACTURING = auto()    # Show formboard style with dimensions
    DEBUG = auto()           # Show all including connection points


class VisualizationManager:
    """
    Manages visibility of all graphics items in the schematic/harness view.
    
    Provides:
    - Toggle switches for different element types
    - Preset visualization modes
    - Smart visibility rules (e.g., hide direct wires when routed wires are shown)
    - Debug visualization options
    """
    
    def __init__(self, main_window):
        self.main_window = main_window
        self.scene = main_window.scene
        
        # Visibility flags
        self.show_bundles = True
        self.show_routed_wires = True
        self.show_direct_wires = False  # Hidden by default after routing
        self.show_branch_points = True
        self.show_junctions = True
        self.show_connector_labels = True
        self.show_grid = True
        self.show_debug = False
        
        # Current mode
        self.mode = VisualizationMode.ALL
        
        # Action references for state updates
        self.actions = {}
        
    def create_toolbar(self) -> QToolBar:
        """Create visualization toggle toolbar"""
        toolbar = QToolBar("Visualization")
        self.main_window.addToolBar(toolbar)
        
        # ============ ELEMENT TOGGLES ============
        toolbar.addAction(self._create_action(
            "Show Bundles", 
            "Show bundle segments",
            self.toggle_bundles,
            checkable=True, 
            checked=True,
            icon="📦"
        ))
        
        toolbar.addAction(self._create_action(
            "Show Routed Wires", 
            "Show routed wires (through topology)",
            self.toggle_routed_wires,
            checkable=True, 
            checked=True,
            icon="🔄"
        ))
        
        toolbar.addAction(self._create_action(
            "Show Original Wires", 
            "Show original direct wires (imported)",
            self.toggle_direct_wires,
            checkable=True, 
            checked=False,
            icon="📏"
        ))
        
        toolbar.addAction(self._create_action(
            "Show Branch Points", 
            "Show branch points and junctions",
            self.toggle_branch_points,
            checkable=True, 
            checked=True,
            icon="⬤"
        ))
        
        toolbar.addAction(self._create_action(
            "Show Connector Info", 
            "Show connector information labels",
            self.toggle_connector_info,
            checkable=True, 
            checked=True,
            icon="ℹ️"
        ))
        
        toolbar.addSeparator()
        
        # ============ PRESET MODES ============
        mode_group = QActionGroup(self.main_window)
        mode_group.setExclusive(True)
        
        # Create mode actions
        mode_all = self._create_action(
            "All", "Show all elements",
            lambda: self.set_mode(VisualizationMode.ALL),
            checkable=True, checked=True,
            icon="👁️"
        )
        mode_group.addAction(mode_all)
        toolbar.addAction(mode_all)
        
        mode_bundles = self._create_action(
            "Bundles Only", "Show only bundle segments",
            lambda: self.set_mode(VisualizationMode.BUNDLES_ONLY),
            checkable=True, checked=False,
            icon="📦"
        )
        mode_group.addAction(mode_bundles)
        toolbar.addAction(mode_bundles)
        
        mode_routed = self._create_action(
            "Routed Wires", "Show only routed wires",
            lambda: self.set_mode(VisualizationMode.ROUTED_WIRES_ONLY),
            checkable=True, checked=False,
            icon="🔄"
        )
        mode_group.addAction(mode_routed)
        toolbar.addAction(mode_routed)
        
        mode_direct = self._create_action(
            "Direct Wires", "Show only original direct wires",
            lambda: self.set_mode(VisualizationMode.DIRECT_WIRES_ONLY),
            checkable=True, checked=False,
            icon="📏"
        )
        mode_group.addAction(mode_direct)
        toolbar.addAction(mode_direct)
        
        mode_manufacturing = self._create_action(
            "Manufacturing", "Manufacturing formboard view",
            lambda: self.set_mode(VisualizationMode.MANUFACTURING),
            checkable=True, checked=False,
            icon="🏭"
        )
        mode_group.addAction(mode_manufacturing)
        toolbar.addAction(mode_manufacturing)
        
        toolbar.addSeparator()
        
        # ============ UTILITIES ============
        toolbar.addAction(self._create_action(
            "Toggle Grid", "Show/hide background grid",
            self.toggle_grid,
            checkable=True, checked=True,
            icon="▦"
        ))
        
        toolbar.addAction(self._create_action(
            "Debug View", "Show debug information",
            self.toggle_debug,
            checkable=True, checked=False,
            icon="🐛"
        ))
        
        return toolbar
    
    def _create_action(self, text, tooltip, slot, checkable=False, checked=False, icon=None):
        """Helper to create consistent actions"""
        action = QAction(text, self.main_window)
        action.setToolTip(tooltip)
        action.setStatusTip(tooltip)
        action.setCheckable(checkable)
        if checkable:
            action.setChecked(checked)
        action.triggered.connect(slot)
        if icon:
            action.setText(f"{icon} {text}")
        self.actions[text] = action
        return action
    
    # ============ TOGGLE METHODS ============
    
    def toggle_bundles(self, checked):
        """Toggle bundle segment visibility"""
        self.show_bundles = checked
        self.update_visibility()
    
    def toggle_routed_wires(self, checked):
        """Toggle routed wire visibility"""
        self.show_routed_wires = checked
        self.update_visibility()
    
    def toggle_direct_wires(self, checked):
        """Toggle original direct wire visibility"""
        self.show_direct_wires = checked
        self.update_visibility()
    
    def toggle_branch_points(self, checked):
        """Toggle branch point and junction visibility"""
        self.show_branch_points = checked
        self.show_junctions = checked
        self.update_visibility()
    
    def toggle_connector_info(self, checked):
        """Toggle connector information labels"""
        self.show_connector_labels = checked
        self._update_connector_labels()
    
    def toggle_grid(self, checked):
        """Toggle background grid visibility"""
        self.show_grid = checked
        self.main_window.view.update()  # Force redraw
    
    def toggle_debug(self, checked):
        """Toggle debug visualization"""
        self.show_debug = checked
        self.update_visibility()
        if checked:
            self._show_debug_info()
        else:
            self._hide_debug_info()
    
    # ============ MODE SETUP ============
    
    def set_mode(self, mode: VisualizationMode):
        """Set a predefined visualization mode"""
        self.mode = mode
        
        # Reset all flags to defaults
        self.show_bundles = False
        self.show_routed_wires = False
        self.show_direct_wires = False
        self.show_branch_points = False
        self.show_junctions = False
        
        # Configure based on mode
        if mode == VisualizationMode.ALL:
            self.show_bundles = True
            self.show_routed_wires = True
            self.show_branch_points = True
            self.show_junctions = True
            self.show_direct_wires = False
            
        elif mode == VisualizationMode.BUNDLES_ONLY:
            self.show_bundles = True
            self.show_routed_wires = False
            self.show_branch_points = False
            self.show_junctions = False
            self.show_direct_wires = False
            
        elif mode == VisualizationMode.ROUTED_WIRES_ONLY:
            self.show_bundles = False
            self.show_routed_wires = True
            self.show_branch_points = False
            self.show_junctions = False
            self.show_direct_wires = False
            
        elif mode == VisualizationMode.DIRECT_WIRES_ONLY:
            self.show_bundles = False
            self.show_routed_wires = False
            self.show_branch_points = False
            self.show_junctions = False
            self.show_direct_wires = True
            
        elif mode == VisualizationMode.MANUFACTURING:
            self.show_bundles = True
            self.show_routed_wires = False
            self.show_branch_points = True
            self.show_junctions = True
            self.show_direct_wires = False
            self._apply_manufacturing_style()
        
        # Update action states
        self._update_action_states()
        
        # Apply visibility
        self.update_visibility()
        
        print(f"Visualization mode set to: {mode.name}")
    
    def _update_action_states(self):
        """Update all toggle action states to match current flags"""
        if 'Show Bundles' in self.actions:
            self.actions['Show Bundles'].setChecked(self.show_bundles)
        if 'Show Routed Wires' in self.actions:
            self.actions['Show Routed Wires'].setChecked(self.show_routed_wires)
        if 'Show Original Wires' in self.actions:
            self.actions['Show Original Wires'].setChecked(self.show_direct_wires)
        if 'Show Branch Points' in self.actions:
            self.actions['Show Branch Points'].setChecked(self.show_branch_points)
    
    # ============ VISIBILITY APPLICATION ============
    
    def update_visibility(self):
        """Apply current visibility settings to all items in scene"""
        if not self.scene:
            return
        
        for item in self.scene.items():
            self._apply_item_visibility(item)
    
    def _apply_item_visibility(self, item):
        """Determine and apply visibility for a single item"""
        
        # 1. BUNDLE SEGMENTS
        if isinstance(item, SegmentGraphicsItem):
            item.setVisible(self.show_bundles)
            return
        
        # 2. ROUTED WIRES (through topology)
        if isinstance(item, SegmentedWireItem):
            item.setVisible(self.show_routed_wires)
            return
        
        # 3. DIRECT WIRES (original import)
        if isinstance(item, WireItem):
            item.setVisible(self.show_direct_wires)
            return
        
        # 4. BRANCH POINTS
        if isinstance(item, BranchPointGraphicsItem):
            item.setVisible(self.show_branch_points)
            return
        
        # 5. JUNCTIONS
        if isinstance(item, JunctionGraphicsItem):
            item.setVisible(self.show_junctions)
            return
        
        # 6. CONNECTOR LABELS (info panels)
        if hasattr(item, 'connector') and hasattr(item, 'setVisible'):
            # This is ConnectorInfoItem
            item.setVisible(self.show_connector_labels)
            return
        
        # 7. DEBUG ITEMS
        if hasattr(item, 'debug_item') or hasattr(item, 'is_debug_item'):
            item.setVisible(self.show_debug)
    
    # ============ SPECIALIZED VIEWS ============
    
    def _apply_manufacturing_style(self):
        """Apply manufacturing formboard style"""
        # Make bundles thicker, add dimensions
        for item in self.scene.items():
            if isinstance(item, SegmentGraphicsItem):
                # Make segments thicker and add measurement lines
                pen = item.pen()
                pen.setWidth(pen.width() + 2)
                pen.setColor(Qt.darkBlue)
                item.setPen(pen)
    
    def show_direct_wires_mode(self):
        """Convenience method to show only direct wires"""
        self.set_mode(VisualizationMode.DIRECT_WIRES_ONLY)
    
    def show_routed_wires_mode(self):
        """Convenience method to show only routed wires"""
        self.set_mode(VisualizationMode.ROUTED_WIRES_ONLY)
    
    def show_bundles_mode(self):
        """Convenience method to show only bundles"""
        self.set_mode(VisualizationMode.BUNDLES_ONLY)
    
    def show_all_mode(self):
        """Convenience method to show everything"""
        self.set_mode(VisualizationMode.ALL)
    
    # ============ CONNECTOR LABELS ============
    
    def _update_connector_labels(self):
        """Update connector info label visibility"""
        for item in self.scene.items():
            if hasattr(item, 'info') and hasattr(item.info, 'setVisible'):
                item.info.setVisible(self.show_connector_labels)
    
    # ============ DEBUG UTILITIES ============
    
    def _show_debug_info(self):
        """Show debug visualization elements"""
        # Show connection points
        if hasattr(self.main_window, 'topology_manager'):
            tm = self.main_window.topology_manager
            if hasattr(tm, 'connection_points'):
                for cp in tm.connection_points.values():
                    if hasattr(cp, 'setVisible'):
                        cp.setVisible(True)
        
        # Show wire counts on segments
        for item in self.scene.items():
            if isinstance(item, SegmentGraphicsItem):
                wire_count = len(item.segment.wires)
                if wire_count > 0 and not hasattr(item, '_debug_label'):
                    from PyQt5.QtWidgets import QGraphicsTextItem
                    label = QGraphicsTextItem(f"{wire_count}", item)
                    label.setPos(10, -15)
                    label.setScale(0.8)
                    label.setDefaultTextColor(Qt.red)
                    label.debug_item = True
                    item._debug_label = label
    
    def _hide_debug_info(self):
        """Hide debug visualization elements"""
        # Hide connection points
        if hasattr(self.main_window, 'topology_manager'):
            tm = self.main_window.topology_manager
            if hasattr(tm, 'connection_points'):
                for cp in tm.connection_points.values():
                    if hasattr(cp, 'setVisible'):
                        cp.setVisible(False)
        
        # Remove debug labels
        for item in self.scene.items():
            if hasattr(item, '_debug_label'):
                if item._debug_label.scene():
                    self.scene.removeItem(item._debug_label)
                delattr(item, '_debug_label')
    
    # ============ STATE PRESERVATION ============
    
    def save_state(self) -> dict:
        """Save current visualization state"""
        return {
            'mode': self.mode.name,
            'show_bundles': self.show_bundles,
            'show_routed_wires': self.show_routed_wires,
            'show_direct_wires': self.show_direct_wires,
            'show_branch_points': self.show_branch_points,
            'show_connector_labels': self.show_connector_labels,
            'show_grid': self.show_grid,
            'show_debug': self.show_debug
        }
    
    def restore_state(self, state: dict):
        """Restore visualization state"""
        if 'mode' in state:
            mode_name = state['mode']
            for mode in VisualizationMode:
                if mode.name == mode_name:
                    self.set_mode(mode)
                    break
        
        self.show_bundles = state.get('show_bundles', True)
        self.show_routed_wires = state.get('show_routed_wires', True)
        self.show_direct_wires = state.get('show_direct_wires', False)
        self.show_branch_points = state.get('show_branch_points', True)
        self.show_connector_labels = state.get('show_connector_labels', True)
        self.show_grid = state.get('show_grid', True)
        self.show_debug = state.get('show_debug', False)
        
        self._update_action_states()
        self.update_visibility()
        self._update_connector_labels()
    
    # ============ AUTO-ROUTING INTEGRATION ============
    
    def on_auto_route_complete(self):
        """Called after auto-routing completes"""
        # Hide direct wires, show routed wires and bundles
        self.show_direct_wires = False
        self.show_routed_wires = True
        self.show_bundles = True
        self.show_branch_points = True
        
        self._update_action_states()
        self.update_visibility()
        
        # Switch to ALL mode
        self.mode = VisualizationMode.ALL
    
    def on_clear_topology(self):
        """Called when topology is cleared"""
        # Show direct wires again
        self.show_direct_wires = True
        self.show_routed_wires = False
        self.show_bundles = False
        self.show_branch_points = False
        
        self._update_action_states()
        self.update_visibility()
        
        # Switch to DIRECT_WIRES mode
        self.mode = VisualizationMode.DIRECT_WIRES_ONLY


# ============ CONVENIENCE FUNCTION FOR MAIN WINDOW ============

def setup_visualization(main_window):
    """Setup visualization manager and connect signals"""
    viz_manager = VisualizationManager(main_window)
    main_window.viz_manager = viz_manager
    
    # Create toolbar
    viz_manager.create_toolbar()
    
    # Set initial mode
    viz_manager.set_mode(VisualizationMode.DIRECT_WIRES_ONLY)
    
    return viz_manager
