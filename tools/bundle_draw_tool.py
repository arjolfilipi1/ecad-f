from PyQt5.QtWidgets import QGraphicsItem, QGraphicsEllipseItem,QToolBar
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
    """Interactive tool for drawing continuous bundle segments like a polyline"""
    
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
        self.current_segment_start = None
        self.current_start_node = None
        self.current_start_item = None
        self.pending_segments = []  # Store segments waiting for length input
        self.temp_preview = None
        
        # Snap settings
        self.snap_enabled = True
        self.snap_modes = [self.SNAP_CONNECTOR, self.SNAP_BRANCH, self.SNAP_NODE, 
                           self.SNAP_FASTENER, self.SNAP_GRID]
        self.snap_tolerance = 15  # pixels
        
        # Preview line for current segment
        self.preview_line = None
        
        # Node creation
        self.auto_create_nodes = True
        
        # Length input
        self.pending_length = None
        self.pending_end_pos = None
        self.waiting_for_length = False
        
        # Floating input window
        self.input_window = None
        
        # Store original cursor
        self.original_cursor = None
        
        # Valid item types for snapping
        self.valid_start_types = (ConnectorItem, BranchPointGraphicsItem, 
                                   JunctionGraphicsItem, FastenerGraphicsItem)
    
    def activate(self):
        """Activate the bundle drawing tool"""
        # Store original cursor
        self.original_cursor = self.view.cursor()
        self.view.viewport().setCursor(Qt.CrossCursor)
        self.is_drawing = False
        self.current_segment_start = None
        self.current_start_node = None
        self.current_start_item = None
        self.pending_segments = []
        self.waiting_for_length = False
        
        # Install event filter on the view
        self.view.viewport().installEventFilter(self)
        
        # Update tool label in SchematicView
        if hasattr(self.view, 'tool_label'):
            self.view.tool_label.setText("DRAW BUNDLE (Polyline)")
            self.view.tool_label.setStyleSheet("""
                QLabel {
                    background-color: rgba(0, 120, 215, 200);
                    color: white;
                    padding: 5px;
                    border-radius: 5px;
                    font-weight: bold;
                }
            """)
        
        self.main_window.statusBar().showMessage(
            "Bundle polyline mode: Click on a connector/branch point to start, click to add segments, ESC to finish", 0
        )
    
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
        
        # Handle key press
        elif event.type() == QEvent.KeyPress:
            if event.key() == Qt.Key_Escape:
                if self.waiting_for_length:
                    # Cancel length input but stay in drawing mode
                    self.waiting_for_length = False
                    self.pending_length = None
                    self.pending_end_pos = None
                    if self.input_window and self.input_window.isVisible():
                        self.input_window.hide()
                    self.main_window.statusBar().showMessage(
                        "Length cancelled - click to continue drawing", 1000
                    )
                else:
                    # Exit drawing mode completely
                    self.cancel_drawing()
                    self.deactivate()
                return True
            
            elif event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter:
                if self.waiting_for_length and self.input_window:
                    self.input_window.on_enter()
                return True
        
        return False
    
    def handle_mouse_press(self, event):
        """Handle mouse press events"""
        pos = self.view.mapToScene(event.pos())
        
        if event.button() == Qt.LeftButton:
            if not self.is_drawing:
                # Start drawing on an existing item
                self.try_start_drawing(pos)
            else:
                if self.waiting_for_length:
                    # We're waiting for length input - ignore clicks
                    return
                
                # Add a new segment point
                self.add_segment_point(pos)
        
        elif event.button() == Qt.RightButton:
            if self.is_drawing:
                # Finish the polyline (don't create last segment)
                self.finish_polyline()
    
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
    
    def start_drawing(self, pos, start_item):
        """Start drawing a new polyline from an existing item"""
        # Snap to the item's position
        if isinstance(start_item, ConnectorItem):
            start_pos = start_item.pos()
            self.current_start_node = start_item.topology_node
        elif isinstance(start_item, BranchPointGraphicsItem):
            start_pos = start_item.pos()
            self.current_start_node = start_item.branch_node
        elif isinstance(start_item, JunctionGraphicsItem):
            start_pos = start_item.pos()
            self.current_start_node = start_item.junction_node
        elif isinstance(start_item, FastenerGraphicsItem):
            start_pos = start_item.pos()
            self.current_start_node = start_item.fastener_node
        else:
            start_pos, _ = self.get_snapped_position(pos)
            self.current_start_node = None
        
        self.is_drawing = True
        self.current_segment_start = start_pos
        self.current_start_item = start_item
        self.pending_segments = []
        
        # Create preview line
        self.preview_line = self.scene.addLine(
            start_pos.x(), start_pos.y(), 
            start_pos.x(), start_pos.y(),
            QPen(QColor(100, 100, 255, 128), 2, Qt.DashLine)
        )
        
        self.main_window.statusBar().showMessage(
            "Click to add next point, Right-click to finish, ESC to cancel", 0
        )
    
    def add_segment_point(self, pos):
        """Add a new point to the polyline"""
        # Snap end point
        end_pos, snap_type = self.get_snapped_position(pos)
        
        # Don't create zero-length segments
        if self.current_segment_start == end_pos:
            return
        
        # Store the end position and prompt for length
        self.pending_end_pos = end_pos
        self.waiting_for_length = True
        
        # Show floating input for length
        if not self.input_window:
            self.input_window = FloatingInputWindow(self.main_window, "Enter bundle length (mm):")
            self.input_window.value_entered.connect(self.on_length_entered)
            self.input_window.cancelled.connect(self.on_length_cancelled)
        
        self.input_window.show_at_cursor()
        
        # Update preview to show current segment
        if self.preview_line:
            self.preview_line.setLine(
                self.current_segment_start.x(), self.current_segment_start.y(),
                end_pos.x(), end_pos.y()
            )
    
    def on_length_entered(self, length):
        """Handle length entered from floating input"""
        if self.pending_end_pos is None:
            return
        
        # Create the bundle segment with specified length
        self.create_bundle_segment(self.pending_end_pos, length)
        
        # Reset length input state
        self.waiting_for_length = False
        self.pending_length = None
        self.pending_end_pos = None
    
    def on_length_cancelled(self):
        """Handle cancellation of length input"""
        # Create bundle with no specified length (use calculated length)
        if self.pending_end_pos:
            self.create_bundle_segment(self.pending_end_pos, None)
        
        # Reset length input state
        self.waiting_for_length = False
        self.pending_length = None
        self.pending_end_pos = None
    
    def create_bundle_segment(self, end_pos, specified_length=None):
        """Create a bundle segment from current start to end position"""
        
        # Check if end point is on an existing item
        items = self.scene.items(end_pos)
        end_item = None
        end_node = None
        
        for item in items:
            if isinstance(item, self.valid_start_types):
                end_item = item
                break
        
        if end_item:
            # End on existing item - use its node
            if isinstance(end_item, ConnectorItem):
                end_node = end_item.topology_node
            elif isinstance(end_item, BranchPointGraphicsItem):
                end_node = end_item.branch_node
            elif isinstance(end_item, JunctionGraphicsItem):
                end_node = end_item.junction_node
            elif isinstance(end_item, FastenerGraphicsItem):
                end_node = end_item.fastener_node
            end_pos = end_item.pos()  # Use exact position
        elif self.auto_create_nodes:
            # Create new branch point at end position
            from model.topology import BranchPointNode
            from graphics.topology_item import BranchPointGraphicsItem
            
            node = BranchPointNode((end_pos.x(), end_pos.y()), "junction")
            graphics = BranchPointGraphicsItem(node)
            self.scene.addItem(graphics)
            self.main_window.topology_manager.nodes[node.id] = node
            end_node = node
            end_item = graphics
        
        # Create the bundle
        bundle = BundleItem(self.current_segment_start, end_pos)
        
        # Set length if specified
        if specified_length is not None:
            bundle.set_specified_length(specified_length)
        
        # Store node references
        bundle.start_node = self.current_start_node
        bundle.end_node = end_node
        bundle.start_item = self.current_start_item
        bundle.end_item = end_item
        
        # Add to scene using undo command
        from commands.bundle_commands import AddBundleCommand
        cmd = AddBundleCommand(
            self.scene,
            bundle,
            self.current_segment_start,
            end_pos,
            self.main_window
        )
        self.main_window.undo_manager.push(cmd)
        self.main_window.bundles.append(bundle)
        self.main_window.scene.addItem(bundle)
        self.main_window.refresh_bundle_tree()
        
        # Store in pending segments for potential undo grouping
        self.pending_segments.append(bundle)
        
        # Prepare for next segment
        self.current_segment_start = end_pos
        self.current_start_node = end_node
        self.current_start_item = end_item
        
        # Update preview line to start from new position
        if self.preview_line:
            self.preview_line.setLine(
                end_pos.x(), end_pos.y(),
                end_pos.x(), end_pos.y()
            )
        
        self.main_window.statusBar().showMessage(
            f"Bundle segment created - click to continue, Right-click to finish", 1000
        )
    
    def finish_polyline(self):
        """Finish the polyline (don't create last segment)"""
        if self.pending_segments:
            # Group all segments into one undo command
            if len(self.pending_segments) > 1:
                from commands.base_command import CompoundCommand
                compound = CompoundCommand(f"Draw {len(self.pending_segments)} Bundle Segments")
                # Note: AddBundleCommand already pushed individually, but we could
                # restructure to use compound command
                pass
        self.on_length_cancelled()
        if self.input_window and self.input_window.isVisible():
            self.input_window.hide()
        # Clear drawing state but stay in tool mode for next polyline
        self.is_drawing = False
        self.current_segment_start = None
        self.current_start_node = None
        self.current_start_item = None
        self.pending_segments = []
        self.waiting_for_length = False
        
        if self.preview_line and self.preview_line.scene():
            self.scene.removeItem(self.preview_line)
            self.preview_line = None
        
        self.main_window.statusBar().showMessage(
            "Polyline finished - click on a connector/branch point to start new polyline", 0
        )
    
    def handle_mouse_move(self, event):
        """Handle mouse move events"""
        if not self.is_drawing or self.waiting_for_length:
            return
        
        raw_pos = self.view.mapToScene(event.pos())
        
        # Apply snapping
        snap_pos, snap_type = self.get_snapped_position(raw_pos)
        
        # Update preview line
        if self.preview_line and self.current_segment_start:
            self.preview_line.setLine(
                self.current_segment_start.x(), self.current_segment_start.y(),
                snap_pos.x(), snap_pos.y()
            )
        
        # Show snap hint in status bar
        if snap_type:
            hint = self.get_snap_hint(snap_type)
            self.main_window.statusBar().showMessage(f"Snap to: {hint}", 100)
    
    def cancel_drawing(self):
        """Cancel current drawing operation"""
        if self.preview_line and self.preview_line.scene():
            self.scene.removeItem(self.preview_line)
            self.preview_line = None
        
        self.is_drawing = False
        self.current_segment_start = None
        self.current_start_node = None
        self.current_start_item = None
        self.pending_segments = []
        self.waiting_for_length = False
        self.pending_length = None
        self.pending_end_pos = None
        
        if self.input_window and self.input_window.isVisible():
            self.input_window.hide()
    
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

