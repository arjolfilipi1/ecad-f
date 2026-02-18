from PyQt5.QtWidgets import QToolBar, QAction, QDoubleSpinBox, QLabel, QWidget, QHBoxLayout, QLineEdit, QPushButton
from PyQt5.QtCore import Qt, QPointF, pyqtSignal,QLineF
from PyQt5.QtGui import QCursor, QPen, QColor, QFont
from enum import Enum
import math

class BranchDrawMode(Enum):
    """Drawing modes for branch creation"""
    IDLE = 0
    WAITING_FIRST_CLICK = 1      # Waiting for user to click first connector
    SEGMENT_ACTIVE = 2            # Currently drawing a segment
    AWAITING_LENGTH = 3           # Segment drawn, waiting for length input

class BranchDrawingTool:
    """Tool for manually drawing branches with length specification"""
    
    def __init__(self, main_window):
        self.main_window = main_window
        self.mode = BranchDrawMode.IDLE
        self.current_segment = None
        self.current_start_node = None
        self.current_end_node = None
        self.temp_line = None
        self.segments = []  # Store completed segments
        self.nodes = []     # Store created nodes in order
        
        # Create toolbar
        self.toolbar = self._create_toolbar()
        
    def _create_toolbar(self) -> QToolBar:
        """Create branch drawing toolbar"""
        toolbar = QToolBar("Branch Drawing")
        toolbar.setObjectName("BranchDrawingToolBar")
        
        # Draw branch button
        self.draw_action = QAction("✏️ Draw Branch", self.main_window)
        self.draw_action.setCheckable(True)
        self.draw_action.triggered.connect(self.toggle_draw_mode)
        toolbar.addAction(self.draw_action)
        
        toolbar.addSeparator()
        
        # Length input widget
        length_widget = QWidget()
        length_layout = QHBoxLayout(length_widget)
        length_layout.setContentsMargins(2, 2, 2, 2)
        
        length_layout.addWidget(QLabel("Length:"))
        self.length_input = QLineEdit()
        self.length_input.setPlaceholderText("undefined")
        self.length_input.setEnabled(False)
        self.length_input.returnPressed.connect(self.apply_length)
        length_layout.addWidget(self.length_input)
        
        self.apply_btn = QPushButton("✓ Apply")
        self.apply_btn.setEnabled(False)
        self.apply_btn.clicked.connect(self.apply_length)
        length_layout.addWidget(self.apply_btn)
        
        toolbar.addWidget(length_widget)
        
        toolbar.addSeparator()
        
        # Cancel button
        self.cancel_btn = QAction("❌ Cancel", self.main_window)
        self.cancel_btn.setEnabled(False)
        self.cancel_btn.triggered.connect(self.cancel_drawing)
        toolbar.addAction(self.cancel_btn)
        
        return toolbar
    
    def toggle_draw_mode(self, checked):
        """Enter or exit branch drawing mode"""
        if checked:
            self.start_drawing()
        else:
            self.exit_drawing_mode()
    
    def start_drawing(self):
        """Start the branch drawing workflow"""
        self.mode = BranchDrawMode.WAITING_FIRST_CLICK
        self.segments = []
        self.nodes = []
        self.current_segment = None
        self.current_start_node = None
        self.current_end_node = None
        
        self.cancel_btn.setEnabled(True)
        self.main_window.view.viewport().setCursor(QCursor(Qt.CrossCursor))
        self.main_window.statusBar().showMessage(
            "Click on a connector to start drawing branch", 0
        )
    
    def exit_drawing_mode(self):
        """Exit drawing mode and clean up"""
        self.mode = BranchDrawMode.IDLE
        
        # Remove temp line if it exists
        if self.temp_line and self.temp_line.scene():
            self.main_window.scene.removeItem(self.temp_line)
            self.temp_line = None
        
        self.cancel_btn.setEnabled(False)
        self.length_input.setEnabled(False)
        self.length_input.clear()
        self.length_input.setPlaceholderText("undefined")
        self.apply_btn.setEnabled(False)
        
        self.draw_action.setChecked(False)
        self.main_window.view.viewport().setCursor(QCursor(Qt.ArrowCursor))
        self.main_window.statusBar().clearMessage()
    
    def cancel_drawing(self):
        """Cancel current drawing operation"""
        # Remove any incomplete segment
        if self.temp_line and self.temp_line.scene():
            self.main_window.scene.removeItem(self.temp_line)
            self.temp_line = None
        
        # Clear any created nodes from this session
        # (Nodes from previous completed segments remain)
        
        self.mode = BranchDrawMode.WAITING_FIRST_CLICK
        self.current_segment = None
        self.current_start_node = None
        self.current_end_node = None
        
        self.length_input.setEnabled(False)
        self.length_input.clear()
        self.length_input.setPlaceholderText("undefined")
        self.apply_btn.setEnabled(False)
        
        self.main_window.statusBar().showMessage(
            "Drawing cancelled - click a connector to start new branch", 0
        )
    
    def on_mouse_press(self, event):
        """Handle mouse press based on current mode"""
        if self.mode == BranchDrawMode.IDLE:
            return
        print("start")
        pos = self.main_window.view.mapToScene(event.pos())
        
        # Check if we clicked on a connector
        clicked_item = self.main_window.view.itemAt(event.pos())
        from graphics.connector_item import ConnectorItem
        
        if self.mode == BranchDrawMode.WAITING_FIRST_CLICK:
            # First click must be on a connector
            if isinstance(clicked_item, ConnectorItem):
                self._start_from_connector(clicked_item, pos)
            else:
                self.main_window.statusBar().showMessage(
                    "Please click on a connector to start", 2000
                )
        
        elif self.mode == BranchDrawMode.SEGMENT_ACTIVE:
            # Click can be on empty space (creates node) or on connector
            if isinstance(clicked_item, ConnectorItem):
                self._finish_at_connector(clicked_item, pos)
            else:
                self._create_node_at_position(pos)
    
    def on_mouse_move(self, event):
        """Update temporary line preview"""
        if self.mode != BranchDrawMode.SEGMENT_ACTIVE or not self.current_start_node:
            return
        
        pos = self.main_window.view.mapToScene(event.pos())
        
        # Update temp line
        if not self.temp_line:
            from PyQt5.QtWidgets import QGraphicsLineItem
            from PyQt5.QtCore import QLineF
            
            self.temp_line = QGraphicsLineItem()
            
            # Create dashed line style
            pen = QPen(QColor(100, 100, 255), 2)
            pen.setStyle(Qt.DashDotLine)  # " _ . _ . _ " style
            self.temp_line.setPen(pen)
            
            self.main_window.scene.addItem(self.temp_line)
        from PyQt5.QtCore import QLineF, QPointF
        # Update line position
        start_pos = QPointF(*self.current_start_node.position)
        self.temp_line.setLine(QLineF(start_pos, pos))
        
        # Calculate and display temporary length
        dx = pos.x() - start_pos.x()
        dy = pos.y() - start_pos.y()
        temp_length = math.sqrt(dx*dx + dy*dy)
        
        self.main_window.statusBar().showMessage(
            f"Current length: {temp_length:.1f} mm - Click to place node or connector", 0
        )
    
    def _start_from_connector(self, connector_item, pos):
        """Start a new branch from a connector"""
        # Get the connector's topology node
        start_node = connector_item.topology_node
        
        if not start_node:
            print("Connector has no topology node")
            return
        
        self.current_start_node = start_node
        self.nodes = [start_node]  # Start with this node
        
        self.mode = BranchDrawMode.SEGMENT_ACTIVE
        
        self.main_window.statusBar().showMessage(
            "Click on empty space to create a node, or on another connector to finish", 0
        )
    
    def _create_node_at_position(self, pos):
        """Create a new branch point node at the clicked position"""
        from model.topology import BranchPointNode
        from graphics.topology_item import BranchPointGraphicsItem
        
        # Create the node
        node = BranchPointNode((pos.x(), pos.y()), "split")
        self.main_window.topology_manager.nodes[node.id] = node
        
        # Create graphics
        node_graphics = BranchPointGraphicsItem(node)
        self.main_window.scene.addItem(node_graphics)
        
        # This will be the end of current segment
        self.current_end_node = node
        
        # Create temporary segment (will be finalized after length input)
        self._create_temporary_segment()
    
    def _finish_at_connector(self, connector_item, pos):
        """Finish the branch at a connector"""
        end_node = connector_item.topology_node
        
        if not end_node:
            print("Connector has no topology node")
            return
        
        self.current_end_node = end_node
        self.nodes.append(end_node)
        
        # Create temporary segment
        self._create_temporary_segment()
        
        # Branch is complete!
        self._finalize_branch()
    
    def _create_temporary_segment(self):
        """Create a temporary segment that needs length specification"""
        if not self.current_start_node or not self.current_end_node:
            return
        
        # Calculate current length
        p1 = self.current_start_node.position
        p2 = self.current_end_node.position
        dx = p2[0] - p1[0]
        dy = p2[1] - p1[1]
        current_length = math.sqrt(dx*dx + dy*dy)
        
        # Store segment info
        self.current_segment = {
            'start': self.current_start_node,
            'end': self.current_end_node,
            'length': current_length,
            'graphics': None
        }
        
        # Create visual segment with dashed line
        from PyQt5.QtWidgets import QGraphicsLineItem
        from PyQt5.QtCore import QLineF
        
        line_item = QGraphicsLineItem()
        pen = QPen(QColor(100, 100, 255), 2)
        pen.setStyle(Qt.DashDotLine)  # " _ . _ . _ " style
        line_item.setPen(pen)
        line_item.setLine(QLineF(
            QPointF(*p1),
            QPointF(*p2)
        ))
        self.main_window.scene.addItem(line_item)
        
        # Add length label
        from PyQt5.QtWidgets import QGraphicsTextItem
        
        mid_x = (p1[0] + p2[0]) / 2
        mid_y = (p1[1] + p2[1]) / 2
        
        label = QGraphicsTextItem(f"{current_length:.1f} mm", line_item)
        label.setPos(mid_x - 20, mid_y - 15)
        label.setDefaultTextColor(QColor(100, 100, 255))
        label.setFont(QFont("Arial", 8))
        label.setFlag(label.ItemIgnoresTransformations)
        
        self.current_segment['graphics'] = line_item
        
        # Switch to awaiting length mode
        self.mode = BranchDrawMode.AWAITING_LENGTH
        
        # Enable length input
        self.length_input.setEnabled(True)
        self.length_input.setText(f"{current_length:.1f}")
        self.length_input.selectAll()
        self.length_input.setFocus()
        self.apply_btn.setEnabled(True)
        
        self.main_window.statusBar().showMessage(
            f"Enter desired length and press Enter, or keep {current_length:.1f} mm", 0
        )
    
    def apply_length(self):
        """Apply the entered length to the current segment"""
        if self.mode != BranchDrawMode.AWAITING_LENGTH or not self.current_segment:
            return
        
        # Get entered length
        try:
            new_length = float(self.length_input.text())
        except ValueError:
            self.main_window.statusBar().showMessage("Invalid length", 2000)
            return
        
        # Update segment length if different
        if abs(new_length - self.current_segment['length']) > 0.1:
            self._adjust_segment_length(new_length)
        
        # Finalize this segment
        self._finalize_segment()
    
    def _adjust_segment_length(self, new_length):
        """Adjust the segment to the specified length"""
        start = self.current_segment['start']
        end = self.current_segment['end']
        
        p1 = QPointF(*start.position)
        p2 = QPointF(*end.position)
        
        # Calculate direction vector
        dx = p2.x() - p1.x()
        dy = p2.y() - p1.y()
        current = math.sqrt(dx*dx + dy*dy)
        
        if current < 0.01:
            return
        
        # Scale to new length
        scale = new_length / current
        new_p2 = QPointF(
            p1.x() + dx * scale,
            p1.y() + dy * scale
        )
        
        # Update end node position
        end.position = (new_p2.x(), new_p2.y())
        
        # Update graphics position if node has graphics
        for item in self.main_window.scene.items():
            if hasattr(item, 'branch_node') and item.branch_node.id == end.id:
                item.setPos(new_p2)
                break
        
        # Update segment graphics
        if self.current_segment['graphics']:
            self.current_segment['graphics'].setLine(QLineF(p1, new_p2))
            
            # Update label
            mid_x = (p1.x() + new_p2.x()) / 2
            mid_y = (p1.y() + new_p2.y()) / 2
            
            # Find and update label
            for child in self.current_segment['graphics'].childItems():
                if isinstance(child, QGraphicsTextItem):
                    child.setPlainText(f"{new_length:.1f} mm")
                    child.setPos(mid_x - 20, mid_y - 15)
                    break
        
        self.current_segment['length'] = new_length
    
    def _finalize_segment(self):
        """Finalize the current segment and prepare for next"""
        if not self.current_segment:
            return
        
        # Create permanent segment in topology manager
        from model.topology import WireSegment
        from graphics.segment_item import SegmentGraphicsItem
        
        segment = WireSegment(
            start_node=self.current_segment['start'],
            end_node=self.current_segment['end']
        )
        self.main_window.topology_manager.segments[segment.id] = segment
        
        # Replace temporary line with permanent segment
        if self.current_segment['graphics']:
            self.main_window.scene.removeItem(self.current_segment['graphics'])
        
        # Create permanent segment graphics
        segment_graphics = SegmentGraphicsItem(segment, self.main_window.topology_manager)
        self.main_window.scene.addItem(segment_graphics)
        
        # Add to nodes list
        self.nodes.append(self.current_segment['end'])
        
        # Prepare for next segment
        self.current_start_node = self.current_segment['end']
        self.current_segment = None
        
        # Clear temp line
        if self.temp_line and self.temp_line.scene():
            self.main_window.scene.removeItem(self.temp_line)
            self.temp_line = None
        
        # Disable length input for next segment
        self.length_input.setEnabled(False)
        self.length_input.clear()
        self.length_input.setPlaceholderText("undefined")
        self.apply_btn.setEnabled(False)
        
        # Go back to segment active mode
        self.mode = BranchDrawMode.SEGMENT_ACTIVE
        
        self.main_window.statusBar().showMessage(
            "Continue drawing: click on empty space for new node, or on connector to finish", 0
        )
    
    def _finalize_branch(self):
        """Create the final HarnessBranch from all segments"""
        if len(self.nodes) < 2:
            return
        
        from model.models import HarnessBranch
        import uuid
        
        # Collect path points from all segments
        path_points = []
        node_ids = []
        
        for node in self.nodes:
            node_ids.append(node.id)
            
            # Get node position
            if hasattr(node, 'position'):
                path_points.append(node.position)
        
        # Create branch
        branch = HarnessBranch(
            id=f"BRANCH_{uuid.uuid4().hex[:8]}",
            harness_id=self.main_window.project_handler.current_project.id if self.main_window.project_handler.current_project else "temp",
            name=f"Branch_{len(self.main_window.topology_manager.branches) + 1}",
            path_points=path_points,
            node_ids=node_ids,
            wire_ids=[]
        )
        
        # Store in topology manager
        self.main_window.topology_manager.branches[branch.id] = branch
        
        # Update branch list if exists
        if hasattr(self.main_window, 'branch_dock'):
            self.main_window.branch_dock.update_list()
        
        self.main_window.statusBar().showMessage(
            f"Branch completed with {len(self.nodes)} nodes", 3000
        )
        
        # Exit drawing mode or start new branch?
        reply = QMessageBox.question(
            self.main_window,
            "Branch Complete",
            "Branch finished. Draw another branch?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            # Start new branch
            self.start_drawing()
        else:
            # Exit drawing mode
            self.exit_drawing_mode()