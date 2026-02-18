from PyQt5.QtWidgets import QToolBar, QAction, QDoubleSpinBox, QLabel, QWidget, QHBoxLayout
from PyQt5.QtCore import Qt, QPointF, pyqtSignal,QPointF, QLineF
from PyQt5.QtGui import QCursor
from enum import Enum

class BranchDrawMode(Enum):
    """Drawing modes for branch creation"""
    IDLE = 0
    PLACING_START = 1
    PLACING_END = 2
    ADJUSTING_LENGTH = 3

class BranchDrawingTool:
    """Tool for manually drawing branches before routing"""
    
    def __init__(self, main_window):
        self.main_window = main_window
        self.mode = BranchDrawMode.IDLE
        self.current_branch = None
        self.start_node = None
        self.temp_line = None
        self.snap_to_grid = True
        self.snap_to_connectors = True
        self.snap_to_branch_points = True
        
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
        
        # Snap options
        self.snap_grid_action = QAction("▦ Snap to Grid", self.main_window)
        self.snap_grid_action.setCheckable(True)
        self.snap_grid_action.setChecked(True)
        self.snap_grid_action.triggered.connect(lambda c: setattr(self, 'snap_to_grid', c))
        toolbar.addAction(self.snap_grid_action)
        
        self.snap_conn_action = QAction("🔌 Snap to Connectors", self.main_window)
        self.snap_conn_action.setCheckable(True)
        self.snap_conn_action.setChecked(True)
        self.snap_conn_action.triggered.connect(lambda c: setattr(self, 'snap_to_connectors', c))
        toolbar.addAction(self.snap_conn_action)
        
        self.snap_bp_action = QAction("⬤ Snap to Branch Points", self.main_window)
        self.snap_bp_action.setCheckable(True)
        self.snap_bp_action.setChecked(True)
        self.snap_bp_action.triggered.connect(lambda c: setattr(self, 'snap_to_branch_points', c))
        toolbar.addAction(self.snap_bp_action)
        
        toolbar.addSeparator()
        
        # Length input widget
        length_widget = QWidget()
        length_layout = QHBoxLayout(length_widget)
        length_layout.setContentsMargins(2, 2, 2, 2)
        
        length_layout.addWidget(QLabel("Length:"))
        self.length_spin = QDoubleSpinBox()
        self.length_spin.setRange(1, 10000)
        self.length_spin.setSuffix(" mm")
        self.length_spin.setValue(100)
        self.length_spin.setEnabled(False)
        self.length_spin.valueChanged.connect(self.on_length_changed)
        length_layout.addWidget(self.length_spin)
        
        toolbar.addWidget(length_widget)
        
        # Apply length button
        self.apply_length_action = QAction("✓ Apply Length", self.main_window)
        self.apply_length_action.setEnabled(False)
        self.apply_length_action.triggered.connect(self.apply_current_length)
        toolbar.addAction(self.apply_length_action)
        
        toolbar.addSeparator()
        
        # Clear/Finish
        self.finish_action = QAction("✅ Finish Branch", self.main_window)
        self.finish_action.setEnabled(False)
        self.finish_action.triggered.connect(self.finish_current_branch)
        toolbar.addAction(self.finish_action)
        
        self.cancel_action = QAction("❌ Cancel", self.main_window)
        self.cancel_action.setEnabled(False)
        self.cancel_action.triggered.connect(self.cancel_drawing)
        toolbar.addAction(self.cancel_action)
        self.main_window.addToolBar(toolbar)
        return toolbar
    
    def toggle_draw_mode(self, checked):
        """Toggle branch drawing mode"""
        if checked:
            self.start_drawing()
        else:
            self.exit_drawing_mode()
    
    def start_drawing(self):
        """Enter branch drawing mode"""
        self.mode = BranchDrawMode.PLACING_START
        self.main_window.statusBar().showMessage(
            "Click on a connector, branch point, or empty space to start branch", 0
        )
        self.main_window.view.viewport().setCursor(QCursor(Qt.CrossCursor))

    
    def exit_drawing_mode(self):
        """Exit branch drawing mode"""
        self.mode = BranchDrawMode.IDLE
        self.cancel_drawing()
        self.draw_action.setChecked(False)
        self.main_window.view.viewport().setCursor(QCursor(Qt.ArrowCursor))
        self.main_window.statusBar().clearMessage()
    
    def cancel_drawing(self):
        """Cancel current drawing operation"""
        if self.temp_line and self.temp_line.scene():
            self.main_window.scene.removeItem(self.temp_line)
            self.temp_line = None
        
        self.current_branch = None
        self.start_node = None
        self.mode = BranchDrawMode.IDLE
        self.finish_action.setEnabled(False)
        self.cancel_action.setEnabled(False)
        self.length_spin.setEnabled(False)
        self.apply_length_action.setEnabled(False)
        
        self.main_window.statusBar().showMessage("Drawing cancelled", 2000)
    
    def finish_current_branch(self):
        """Finish current branch and create it"""
        if not self.current_branch:
            return
        
        # Create the actual branch in topology manager
        from model.models import HarnessBranch
        
        branch = HarnessBranch(
            id=f"BRANCH_{len(self.main_window.topology_manager.branches) + 1}",
            harness_id=self.main_window.project_handler.current_project.id if self.main_window.project_handler.current_project else "temp",
            name=f"Branch_{len(self.main_window.topology_manager.branches) + 1}",
            path_points=self.current_branch['points'],
            node_ids=self.current_branch['node_ids']
        )
        
        # Add to topology manager
        self.main_window.topology_manager.branches[branch.id] = branch
        
        # Create visual segment
        from graphics.segment_item import SegmentGraphicsItem
        from model.topology import WireSegment
        
        # Create segment between nodes
        if len(self.current_branch['node_ids']) >= 2:
            for i in range(len(self.current_branch['node_ids']) - 1):
                start_node = self.main_window.topology_manager.nodes.get(self.current_branch['node_ids'][i])
                end_node = self.main_window.topology_manager.nodes.get(self.current_branch['node_ids'][i + 1])
                
                if start_node and end_node:
                    segment = self.main_window.topology_manager.create_segment(start_node, end_node)
                    segment_graphics = SegmentGraphicsItem(segment, self.main_window.topology_manager)
                    self.main_window.scene.addItem(segment_graphics)
        
        # Clear temporary items
        if self.temp_line and self.temp_line.scene():
            self.main_window.scene.removeItem(self.temp_line)
            self.temp_line = None
        
        self.main_window.statusBar().showMessage(f"Branch created: {branch.name}", 3000)
        
        # Reset for next branch
        self.current_branch = None
        self.start_node = None
        self.mode = BranchDrawMode.PLACING_START
        self.finish_action.setEnabled(False)
        self.cancel_action.setEnabled(False)
        self.length_spin.setEnabled(False)
        self.apply_length_action.setEnabled(False)
    
    def on_mouse_press(self, event):
        """Handle mouse press in branch drawing mode"""
        if self.mode == BranchDrawMode.IDLE:
            return
        
        pos = self.main_window.view.mapToScene(event.pos())
        
        # Snap to grid if enabled
        if self.snap_to_grid:
            grid_size = self.main_window.settings_manager.get('grid_size', 50)
            pos.setX(round(pos.x() / grid_size) * grid_size)
            pos.setY(round(pos.y() / grid_size) * grid_size)
        
        # Check for snapping to connectors or branch points
        snapped_node = None
        if self.snap_to_connectors or self.snap_to_branch_points:
            snapped_node = self._find_snappable_node(pos)
            if snapped_node:
                pos = QPointF(*snapped_node.position)
        
        if self.mode == BranchDrawMode.PLACING_START:
            # Start a new branch
            print("start")
            self._start_new_branch(pos, snapped_node)
            
        elif self.mode == BranchDrawMode.PLACING_END:
            print(snapped_node)
            # Add a point to current branch
            self._add_branch_point(pos, snapped_node)
    
    def _find_snappable_node(self, pos: QPointF, tolerance: float = 20.0):
        """Find a node (connector or branch point) near the given position"""
        closest_node = None
        min_dist = tolerance
        
        # Check all topology nodes
        for node in self.main_window.topology_manager.nodes.values():
            node_pos = QPointF(*node.position)
            dist = (node_pos - pos).manhattanLength()
            
            if dist < min_dist:
                min_dist = dist
                closest_node = node
        
        return closest_node
    
    def _start_new_branch(self, pos: QPointF, start_node):
        """Start a new branch at the given position"""
        self.start_node = start_node
        self.current_branch = {
            'points': [(pos.x(), pos.y())],
            'node_ids': [start_node.id] if start_node else []
        }
        
        # Create temporary line for visualization
        from PyQt5.QtWidgets import QGraphicsLineItem
        from PyQt5.QtGui import QPen
        from PyQt5.QtCore import QLineF
        
        self.temp_line = QGraphicsLineItem()
        self.temp_line.setPen(QPen(Qt.blue, 2, Qt.DashLine))
        self.temp_line.setLine(QLineF(pos, pos))
        self.main_window.scene.addItem(self.temp_line)
        
        self.mode = BranchDrawMode.PLACING_END
        self.finish_action.setEnabled(True)
        self.cancel_action.setEnabled(True)
        self.length_spin.setEnabled(True)
        self.apply_length_action.setEnabled(True)
        
        self.main_window.statusBar().showMessage(
            "Click to add points, double-click to finish, or enter length", 0
        )
    
    def _add_branch_point(self, pos: QPointF, snapped_node):
        """Add a point to the current branch"""
        if not self.current_branch:
            print("no current node")
            return
        
        self.current_branch['points'].append((pos.x(), pos.y()))
        print(self.current_branch)
        if snapped_node and snapped_node.id not in self.current_branch['node_ids']:
            self.current_branch['node_ids'].append(snapped_node.id)
        
        # Update temporary line
        if self.temp_line:
            last_point = self.current_branch['points'][-2]
            self.temp_line.setLine(QLineF(
                QPointF(*last_point),
                QPointF(*self.current_branch['points'][-1])
            ))
    
    def on_mouse_move(self, event):
        """Handle mouse move for preview"""
        if self.mode != BranchDrawMode.PLACING_END or not self.temp_line or not self.current_branch:
            return
        
        pos = self.main_window.view.mapToScene(event.pos())
        
        # Snap preview
        if self.snap_to_grid:
            grid_size = self.main_window.settings_manager.get('grid_size', 50)
            pos.setX(round(pos.x() / grid_size) * grid_size)
            pos.setY(round(pos.y() / grid_size) * grid_size)
        
        # Update temp line to show potential next segment
        last_point = self.current_branch['points'][-1]
        self.temp_line.setLine(QLineF(
            QPointF(*last_point),
            pos
        ))
        
        # Update length display
        length = self._calculate_branch_length(self.current_branch['points'] + [(pos.x(), pos.y())])
        self.length_spin.blockSignals(True)
        self.length_spin.setValue(length)
        self.length_spin.blockSignals(False)
    
    def on_mouse_double_click(self, event):
        """Finish branch on double click"""
        if self.mode == BranchDrawMode.PLACING_END and self.current_branch:
            print("finishing")
            self.finish_current_branch()
    
    def _calculate_branch_length(self, points):
        """Calculate total length of a branch from points"""
        if len(points) < 2:
            return 0
        
        import math
        total = 0
        for i in range(len(points) - 1):
            dx = points[i+1][0] - points[i][0]
            dy = points[i+1][1] - points[i][1]
            total += math.sqrt(dx*dx + dy*dy)
        return total
    
    def on_length_changed(self, value):
        """Handle length spinbox changes"""
        if not self.current_branch or len(self.current_branch['points']) < 2:
            return
        
        # Calculate current length
        current_length = self._calculate_branch_length(self.current_branch['points'])
        
        # Update preview line to show target length
        if self.temp_line and current_length > 0:
            # Scale factor
            scale = value / current_length
            # This would need more sophisticated geometry handling
            # For now, just update the status
            self.main_window.statusBar().showMessage(
                f"Current: {current_length:.1f} mm, Target: {value:.1f} mm", 0
            )
    
    def apply_current_length(self):
        """Apply the specified length to the current branch"""
        if not self.current_branch or len(self.current_branch['points']) < 2:
            return
        
        target_length = self.length_spin.value()
        current_length = self._calculate_branch_length(self.current_branch['points'])
        
        if abs(current_length - target_length) < 0.1:
            # Already at target length
            self.finish_current_branch()
            return
        
        # For a simple straight line, we can adjust the last point
        if len(self.current_branch['points']) == 2:
            start = self.current_branch['points'][0]
            end = self.current_branch['points'][1]
            
            # Direction vector
            dx = end[0] - start[0]
            dy = end[1] - start[1]
            
            if abs(dx) < 0.01 and abs(dy) < 0.01:
                return
            
            # Normalize and scale to target length
            import math
            current = math.sqrt(dx*dx + dy*dy)
            if current < 0.01:
                return
            
            scale = target_length / current
            new_end = (start[0] + dx * scale, start[1] + dy * scale)
            self.current_branch['points'][1] = new_end
            
            # Update temp line
            if self.temp_line:
                self.temp_line.setLine(QLineF(
                    QPointF(*start),
                    QPointF(*new_end)
                ))
            
            self.main_window.statusBar().showMessage(
                f"Branch length set to {target_length:.1f} mm", 2000
            )
        else:
            # For multi-point branches, more complex geometry needed
            self.main_window.statusBar().showMessage(
                "Length adjustment for multi-point branches not yet implemented", 3000
            )
    
    def add_to_main_toolbar(self):
        """Add branch drawing button to main toolbar"""
        # Find main toolbar or create if needed
        main_toolbar = None
        for toolbar in self.main_window.findChildren(QToolBar):
            if toolbar.objectName() == "MainToolBar":
                main_toolbar = toolbar
                break
        
        if not main_toolbar:
            main_toolbar = QToolBar("Main Tools")
            main_toolbar.setObjectName("MainToolBar")
            self.main_window.addToolBar(main_toolbar)
        
        # Add separator and button
        main_toolbar.addSeparator()
        main_toolbar.addAction(self.draw_action)
    def create_branch_point_at_position(self, pos: QPointF):
        """Create a branch point at the given position"""
        from graphics.topology_item import BranchPointGraphicsItem
        from model.topology import BranchPointNode
        
        # Create branch point node
        bp_node = self.main_window.topology_manager.create_branch_point((pos.x(), pos.y()), "split")
        
        # Create graphics
        bp_graphics = BranchPointGraphicsItem(bp_node)
        self.main_window.scene.addItem(bp_graphics)
        
        return bp_node

