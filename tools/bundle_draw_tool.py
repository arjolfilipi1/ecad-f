from PyQt5.QtWidgets import QGraphicsItem, QGraphicsEllipseItem
from PyQt5.QtCore import Qt, QPointF, QLineF, QEvent
from PyQt5.QtGui import QPen, QColor, QBrush, QCursor
from graphics.bundle_item import BundleItem
from graphics.connector_item import ConnectorItem
from graphics.topology_item import BranchPointGraphicsItem, JunctionGraphicsItem
from tools.floating_input import FloatingInputWindow
import math
from PyQt5.QtCore import QObject
from graphics.topology_item import FastenerGraphicsItem
class BundleDrawTool(QObject):
    """Interactive tool for drawing bundle segments"""
    
    # Snap modes
    SNAP_GRID = 1
    SNAP_CONNECTOR = 2
    SNAP_BRANCH = 3
    SNAP_NODE = 4
    SNAP_FASTENER = 5

    
    def __init__(self, view, main_window):
        super().__init__()
        self.view = view
        self.main_window = main_window
        self.scene = view.scene()
        
        # Drawing state
        self.is_drawing = False
        self.current_bundle = None
        self.start_point = None
        
        self.start_node = None   # The topology node of the start item
        self.temp_preview = None
        
        # Snap settings
        self.snap_enabled = True
        self.snap_modes = [self.SNAP_CONNECTOR, self.SNAP_BRANCH, self.SNAP_NODE, self.SNAP_FASTENER, self.SNAP_GRID]
        self.snap_tolerance = 15  # pixels
        
        # Preview line for current segment
        self.preview_line = None
        
        # Node creation - ONLY at end, never at start
        self.auto_create_nodes = True
        
        # Length input
        self.pending_length = None
        self.pending_end_pos = None
        
        # Floating input window
        self.input_window = None
        
        # Store original cursor
        self.original_cursor = None
        
        # Valid start item types
        self.valid_start_types = (ConnectorItem, BranchPointGraphicsItem, JunctionGraphicsItem, FastenerGraphicsItem)

    
    def activate(self):
        """Activate the bundle drawing tool"""
        # Store original cursor
        self.original_cursor = self.view.cursor()
        self.view.viewport().setCursor(Qt.CrossCursor)
        self.is_drawing = False
        
        # Install event filter on the view
        self.view.viewport().installEventFilter(self)
        
        # Update tool label in SchematicView
        if hasattr(self.view, 'tool_label'):
            self.view.tool_label.setText("DRAW BUNDLE")
            self.view.tool_label.setStyleSheet("""
                QLabel {
                    background-color: rgba(0, 120, 215, 200);
                    color: white;
                    padding: 5px;
                    border-radius: 5px;
                    font-weight: bold;
                }
            """)
    
    def deactivate(self):
        """Deactivate the bundle drawing tool"""
        # Restore cursor
        if self.original_cursor:
            self.view.viewport().setCursor(self.original_cursor)
        else:
            self.view.viewport().setCursor(Qt.ArrowCursor)
        
        # Remove event filter
        self.view.viewport().removeEventFilter(self)
        
        self.cancel_drawing()
        
        # Restore tool label
        if hasattr(self.view, 'tool_label'):
            self.view.tool_label.setText("SELECT")
            self.view.tool_label.setStyleSheet("""
                QLabel {
                    background-color: rgba(0, 0, 0, 150);
                    color: white;
                    padding: 5px;
                    border-radius: 5px;
                    font-weight: bold;
                }
            """)
        
        # Hide input window if visible
        if self.input_window and self.input_window.isVisible():
            self.input_window.hide()
    
    def eventFilter(self, obj, event):
        """Filter events for the view"""
        if obj != self.view.viewport():
            return super().eventFilter(obj, event)
        
        # Handle mouse press
        if event.type() == QEvent.MouseButtonPress:
            self.handle_mouse_press(event)
            return True
        
        # Handle mouse move
        elif event.type() == QEvent.MouseMove:
            self.handle_mouse_move(event)
            return True
        
        # Handle key press for Escape
        elif event.type() == QEvent.KeyPress:
            if event.key() == Qt.Key_Escape:
                self.cancel_drawing()
                return True
        
        return False
    
    def handle_mouse_press(self, event):
        """Handle mouse press events"""
        pos = self.view.mapToScene(event.pos())
        
        if event.button() == Qt.LeftButton:
            if not self.is_drawing:
                # Try to start drawing on an existing item
                self.try_start_drawing(pos)
            else:
                # End current bundle segment - prompt for length
                self.prompt_for_length_before_end(pos)
        
        elif event.button() == Qt.RightButton:
            # Cancel drawing
            self.cancel_drawing()
    
    def try_start_drawing(self, pos):
        """Try to start drawing on an existing item"""
        # Find item at position
        items = self.scene.items(pos)
        
        start_item = None
        for item in items:
            if isinstance(item, self.valid_start_types):
                start_item = item
                break
        
        if start_item:
            # Valid start point found
            self.start_drawing(pos, start_item)
        else:
            # Invalid start point - show message
            self.main_window.statusBar().showMessage(
                "Must start on a connector, branch point, or fastener", 2000
            )
            # Keep cursor as cross, don't enter drawing mode
    
    def start_drawing(self, pos, start_item):
        """Start drawing a new bundle from an existing item"""
        # Snap to the item's position
        if isinstance(start_item, ConnectorItem):
            start_pos = start_item.pos()
            self.start_node = start_item.topology_node
        elif isinstance(start_item, BranchPointGraphicsItem):
            start_pos = start_item.pos()
            self.start_node = start_item.branch_node
        elif isinstance(start_item, JunctionGraphicsItem):
            start_pos = start_item.pos()
            self.start_node = start_item.junction_node
        elif isinstance(start_item, FastenerGraphicsItem):
            start_pos = start_item.pos()
            self.start_node = start_item.fastener_node
        else:
            # Fallback to snapped position
            start_pos, _ = self.get_snapped_position(pos)
            self.start_node = None
        
        self.is_drawing = True
        self.start_point = start_pos
        self.start_item = start_item
        
        # Create preview line
        self.preview_line = self.scene.addLine(
            start_pos.x(), start_pos.y(), 
            start_pos.x(), start_pos.y(),
            QPen(QColor(100, 100, 255, 128), 2, Qt.DashLine)
        )
        
        self.main_window.statusBar().showMessage(
            "Click end point to set bundle length (can be anywhere)", 0
        )
    
    def handle_mouse_move(self, event):
        """Handle mouse move events"""
        if not self.is_drawing:
            return
        
        raw_pos = self.view.mapToScene(event.pos())
        
        # Apply snapping (optional, can snap to grid but not required)
        snap_pos, snap_type = self.get_snapped_position(raw_pos)
        
        # Update preview
        self.update_preview(snap_pos)
        
        # Show snap hint in status bar
        if snap_type:
            hint = self.get_snap_hint(snap_type)
            self.main_window.statusBar().showMessage(f"Snap to: {hint}", 100)
    
    def prompt_for_length_before_end(self, end_pos):
        """Show floating input to get length before ending the bundle"""
        self.pending_end_pos = end_pos
        
        if not self.input_window:
            from tools.floating_input import FloatingInputWindow
            self.input_window = FloatingInputWindow(self.main_window, "Enter bundle length:")
            self.input_window.value_entered.connect(self.on_length_entered)
            self.input_window.cancelled.connect(self.on_length_cancelled)
        
        self.input_window.show_at_cursor()
    def on_length_entered(self, length):
        print("on_length_entered",self.start_point)
        if self.start_point is not None:
            """Handle length entered from floating input"""
            self.pending_length = length
            self.complete_drawing(self.pending_end_pos)
            self.start_point = self.pending_end_pos
        else:
            self.pending_length = None
            self.pending_end_pos = None
            self.main_window.statusBar().showMessage(
                "Length cancelled - click end point again", 2000
            )
    
    def on_length_cancelled(self):
        """Handle cancellation of length input"""
        self.pending_length = None
        self.pending_end_pos = None
        self.main_window.statusBar().showMessage(
            "Length cancelled - click end point again", 2000
        )
    
    def complete_drawing(self, end_pos):
        """Complete the bundle drawing with the specified length"""
        # Snap end point (optional)
        end_pos, snap_type = self.get_snapped_position(end_pos)
        
        # Don't create zero-length bundles
        if self.start_point == end_pos:
            self.main_window.statusBar().showMessage("Zero-length bundle ignored", 2000)
            return
        
        # CREATE NODE AT END if needed (auto-create enabled and not on existing item)
        end_node = None
        end_item = None
        
        # Check if end point is on an existing item
        items = self.scene.items(end_pos)
        for item in items:
            if isinstance(item, self.valid_start_types):
                end_item = item
                break
        
        if end_item:
            from graphics.topology_item import BranchPointGraphicsItem
            # End on existing item - use its node
            if isinstance(end_item, ConnectorItem):
                end_node = end_item.topology_node
            elif isinstance(end_item, BranchPointGraphicsItem):
                end_node = end_item.branch_node
            elif isinstance(end_item, JunctionGraphicsItem):
                end_node = end_item.junction_node
            elif isinstance(end_item, FastenerGraphicsItem):
                end_node = end_item.fastener_node
        elif self.auto_create_nodes:
            # Create new node at end point
            from model.topology import BranchPointNode
            from graphics.topology_item import BranchPointGraphicsItem
            
            node = BranchPointNode((end_pos.x(), end_pos.y()), "junction")
            graphics = BranchPointGraphicsItem(node)
            self.scene.addItem(graphics)
            self.main_window.topology_manager.nodes[node.id] = node
            end_node = node
        

        bundle = BundleItem(self.start_point, end_pos)
        
        # Set length if specified
        if self.pending_length is not None:
            bundle.set_specified_length(self.pending_length)
        
        # Store node references
        bundle.start_node = self.start_node
        bundle.end_node = end_node
        bundle.start_item = self.start_item
        bundle.end_item = end_item
        
        # Add to scene
        self.scene.addItem(bundle)
        
        # Store in main window
        if not hasattr(self.main_window, 'bundles'):
            self.main_window.bundles = []
        self.main_window.bundles.append(bundle)
        
        # Connect to nodes if they exist
        if self.start_node and hasattr(self.start_node, 'connected_bundles'):
            self.start_node.connected_bundles.append(bundle)
        
        if end_node and hasattr(end_node, 'connected_bundles'):
            end_node.connected_bundles.append(bundle)
        
        # Clear pending length
        self.pending_length = None
        
        # If end was on an item, start new bundle from there
        if end_item:
            self.start_drawing(end_pos, end_item)
            self.start_point = end_pos
        else:
            # End in empty space - stay in drawing mode but don't auto-start
            self.is_drawing = False
            self.start_point = None
            self.start_item = None
            self.start_node = None
            
            if self.preview_line and self.preview_line.scene():
                self.scene.removeItem(self.preview_line)
                self.preview_line = None
            
            self.main_window.statusBar().showMessage(
                "Click on a connector, branch point, or fastener to start a new bundle", 0
            )
    
    def update_preview(self, pos):
        """Update preview line"""
        if self.preview_line and self.start_point:
            self.preview_line.setLine(
                self.start_point.x(), self.start_point.y(),
                pos.x(), pos.y()
            )
    
    def cancel_drawing(self):
        """Cancel current drawing operation"""
        if self.preview_line and self.preview_line.scene():
            self.scene.removeItem(self.preview_line)
            self.preview_line = None
        
        self.is_drawing = False
        self.start_point = None
        self.start_item = None
        self.start_node = None
        self.pending_length = None
        self.pending_end_pos = None
        
        if self.input_window and self.input_window.isVisible():
            self.input_window.hide()
        
        self.view.setCursor(Qt.CrossCursor)
        
        self.main_window.statusBar().showMessage(
            "Click on a connector, branch point, or fastener to start a bundle", 0
        )
    
    def get_snapped_position(self, pos):
        """Get snapped position based on current snap modes"""
        if not self.snap_enabled:
            return pos, None
        
        best_pos = pos
        best_dist = float('inf')
        snap_type = None
        
        # Check for connectors
        if self.SNAP_CONNECTOR in self.snap_modes:
            for item in self.scene.items(pos):
                if isinstance(item, ConnectorItem):
                    center = item.pos()
                    dist = math.sqrt((center.x() - pos.x())**2 + (center.y() - pos.y())**2)
                    if dist < self.snap_tolerance and dist < best_dist:
                        best_pos = center
                        best_dist = dist
                        snap_type = self.SNAP_CONNECTOR
        
        # Check for branch points
        if self.SNAP_BRANCH in self.snap_modes:
            for item in self.scene.items(pos):
                if isinstance(item, BranchPointGraphicsItem):
                    center = item.pos()
                    dist = math.sqrt((center.x() - pos.x())**2 + (center.y() - pos.y())**2)
                    if dist < self.snap_tolerance and dist < best_dist:
                        best_pos = center
                        best_dist = dist
                        snap_type = self.SNAP_BRANCH
        
        # Check for junctions
        if self.SNAP_NODE in self.snap_modes:
            for item in self.scene.items(pos):
                if isinstance(item, JunctionGraphicsItem):
                    center = item.pos()
                    dist = math.sqrt((center.x() - pos.x())**2 + (center.y() - pos.y())**2)
                    if dist < self.snap_tolerance and dist < best_dist:
                        best_pos = center
                        best_dist = dist
                        snap_type = self.SNAP_NODE
        
        # Check for fasteners
        if self.SNAP_FASTENER in self.snap_modes:
            for item in self.scene.items(pos):
                if isinstance(item, FastenerGraphicsItem):
                    center = item.pos()
                    dist = math.sqrt((center.x() - pos.x())**2 + (center.y() - pos.y())**2)
                    if dist < self.snap_tolerance and dist < best_dist:
                        best_pos = center
                        best_dist = dist
                        snap_type = self.SNAP_FASTENER
        
        # Grid snap (lowest priority)
        if self.SNAP_GRID in self.snap_modes and best_dist > self.snap_tolerance:
            grid_size = self.main_window.settings_manager.get('grid_size', 50)
            grid_x = round(pos.x() / grid_size) * grid_size
            grid_y = round(pos.y() / grid_size) * grid_size
            grid_pos = QPointF(grid_x, grid_y)
            
            dist = math.sqrt((grid_x - pos.x())**2 + (grid_y - pos.y())**2)
            if dist < self.snap_tolerance:
                best_pos = grid_pos
                snap_type = self.SNAP_GRID
        
        return best_pos, snap_type
    
    def get_snap_hint(self, snap_type):
        """Get human-readable snap hint"""
        hints = {
            self.SNAP_GRID: "Grid",
            self.SNAP_CONNECTOR: "Connector",
            self.SNAP_BRANCH: "Branch Point",
            self.SNAP_NODE: "Junction",
            self.SNAP_FASTENER: "Fastener"
        }
        return hints.get(snap_type, "None")
    
    def set_snap_mode(self, mode, enabled):
        """Enable/disable snap mode"""
        if enabled and mode not in self.snap_modes:
            self.snap_modes.append(mode)
        elif not enabled and mode in self.snap_modes:
            self.snap_modes.remove(mode)

