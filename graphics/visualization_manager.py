from PyQt5.QtWidgets import QAction, QToolBar
from PyQt5.QtCore import Qt
from enum import Enum
from graphics.wire_item import SegmentedWireItem,WireItem
from graphics.topology_item import (
    JunctionGraphicsItem, BranchPointGraphicsItem
)
class VisualizationMode(Enum):
    """Different visualization modes for the harness"""
    BUNDLES_ONLY = 0      # Show only bundle segments (thick lines)
    WIRES_ONLY = 1        # Show only individual wires
    ALL = 2              # Show both bundles and wires
    MANUFACTURING = 3    # Show formboard style with dimensions

class VisualizationManager:
    """Manages what is visible in the schematic/harness view"""
    
    def __init__(self, main_window):
        self.main_window = main_window
        self.mode = VisualizationMode.ALL
        self.show_bundles = True
        self.show_wires = True
        self.show_branch_points = True
        self.show_connector_info = True
        
    def create_toolbar(self):
        """Create visualization toggle toolbar"""
        toolbar = QToolBar("Visualization")
        self.main_window.addToolBar(toolbar)
        
        # Bundle view toggle
        self.bundle_action = QAction("Show Bundles", self.main_window)
        self.bundle_action.setCheckable(True)
        self.bundle_action.setChecked(True)
        self.bundle_action.triggered.connect(self.toggle_bundles)
        toolbar.addAction(self.bundle_action)
        
        # Wire view toggle
        self.wire_action = QAction("Show Wires", self.main_window)
        self.wire_action.setCheckable(True)
        self.wire_action.setChecked(True)
        self.wire_action.triggered.connect(self.toggle_wires)
        toolbar.addAction(self.wire_action)
        
        # Branch points toggle
        self.branch_action = QAction("Show Branch Points", self.main_window)
        self.branch_action.setCheckable(True)
        self.branch_action.setChecked(True)
        self.branch_action.triggered.connect(self.toggle_branch_points)
        toolbar.addAction(self.branch_action)
        
        # Preset modes
        toolbar.addSeparator()
        
        mode_bundles = QAction("Bundles Only", self.main_window)
        mode_bundles.triggered.connect(lambda: self.set_mode(VisualizationMode.BUNDLES_ONLY))
        toolbar.addAction(mode_bundles)
        
        mode_wires = QAction("Wires Only", self.main_window)
        mode_wires.triggered.connect(lambda: self.set_mode(VisualizationMode.WIRES_ONLY))
        toolbar.addAction(mode_wires)
        
        mode_all = QAction("Show All", self.main_window)
        mode_all.triggered.connect(lambda: self.set_mode(VisualizationMode.ALL))
        toolbar.addAction(mode_all)
        
        return toolbar
    
    def toggle_bundles(self, checked):
        """Toggle bundle visibility"""
        self.show_bundles = checked
        self.update_visibility()
    
    def toggle_wires(self, checked):
        """Toggle wire visibility"""
        self.show_wires = checked
        self.update_visibility()
    
    def toggle_branch_points(self, checked):
        """Toggle branch point visibility"""
        self.show_branch_points = checked
        self.update_visibility()
    
    def set_mode(self, mode):
        """Set visualization mode"""
        self.mode = mode
        
        if mode == VisualizationMode.BUNDLES_ONLY:
            self.show_bundles = True
            self.show_wires = False
            self.show_branch_points = False
        elif mode == VisualizationMode.WIRES_ONLY:
            self.show_bundles = False
            self.show_wires = True
            self.show_branch_points = False
        elif mode == VisualizationMode.ALL:
            self.show_bundles = True
            self.show_wires = True
            self.show_branch_points = True
        elif mode == VisualizationMode.MANUFACTURING:
            self.show_bundles = True
            self.show_wires = False
            self.show_branch_points = True
            
        # Update action states
        self.bundle_action.setChecked(self.show_bundles)
        self.wire_action.setChecked(self.show_wires)
        self.branch_action.setChecked(self.show_branch_points)
        
        self.update_visibility()
    
    def update_visibility(self):
        """Apply visibility settings to all items in scene"""
        scene = self.main_window.scene
        
        for item in scene.items():
            # Segment graphics (bundles)
            if hasattr(item, 'segment'):  # SegmentGraphicsItem
                item.setVisible(self.show_bundles)
            
            # Individual wire graphics
            elif isinstance(item, SegmentedWireItem):
                item.setVisible(self.show_wires)
            
            # Branch point graphics
            elif isinstance(item, BranchPointGraphicsItem):
                item.setVisible(self.show_branch_points)
            
            # Junction graphics
            elif isinstance(item, JunctionGraphicsItem):
                item.setVisible(self.show_branch_points)
