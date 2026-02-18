from PyQt5.QtWidgets import QDockWidget, QListWidget, QListWidgetItem, QPushButton, QVBoxLayout, QWidget, QHBoxLayout, QLabel
from PyQt5.QtCore import Qt

class BranchListDock(QDockWidget):
    """Dock widget showing all created branches"""
    
    def __init__(self, main_window):
        super().__init__("Branches", main_window)
        self.main_window = main_window
        
        # Create main widget
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Branch list
        self.branch_list = QListWidget()
        self.branch_list.itemClicked.connect(self.on_branch_selected)
        layout.addWidget(self.branch_list)
        
        # Buttons
        btn_layout = QHBoxLayout()
        
        show_btn = QPushButton("Show")
        show_btn.clicked.connect(self.show_selected_branch)
        btn_layout.addWidget(show_btn)
        
        hide_btn = QPushButton("Hide")
        hide_btn.clicked.connect(self.hide_selected_branch)
        btn_layout.addWidget(hide_btn)
        
        delete_btn = QPushButton("Delete")
        delete_btn.clicked.connect(self.delete_selected_branch)
        btn_layout.addWidget(delete_btn)
        
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        
        # Info label
        self.info_label = QLabel("No branch selected")
        layout.addWidget(self.info_label)
        
        self.setWidget(widget)
    
    def update_list(self):
        """Update branch list from topology manager"""
        self.branch_list.clear()
        
        for branch_id, branch in self.main_window.topology_manager.branches.items():
            # Calculate length
            length = branch.calculate_length() if hasattr(branch, 'calculate_length') else 0
            
            item = QListWidgetItem(f"{branch.name} - {length:.1f} mm")
            item.setData(Qt.UserRole, branch_id)
            self.branch_list.addItem(item)
    
    def on_branch_selected(self, item):
        """Handle branch selection"""
        branch_id = item.data(Qt.UserRole)
        branch = self.main_window.topology_manager.branches.get(branch_id)
        
        if branch:
            length = branch.calculate_length() if hasattr(branch, 'calculate_length') else 0
            self.info_label.setText(
                f"ID: {branch_id}\n"
                f"Name: {branch.name}\n"
                f"Length: {length:.1f} mm\n"
                f"Points: {len(branch.path_points)}\n"
                f"Wires: {len(branch.wire_ids)}"
            )
    
    def show_selected_branch(self):
        """Highlight selected branch in scene"""
        current = self.branch_list.currentItem()
        if not current:
            return
        
        branch_id = current.data(Qt.UserRole)
        # Find segment graphics for this branch and highlight
        for item in self.main_window.scene.items():
            if hasattr(item, 'segment') and item.segment.id in branch_id:
                item.setSelected(True)
                self.main_window.view.centerOn(item)
                break
    
    def hide_selected_branch(self):
        """Hide selected branch"""
        current = self.branch_list.currentItem()
        if not current:
            return
        
        branch_id = current.data(Qt.UserRole)
        for item in self.main_window.scene.items():
            if hasattr(item, 'segment') and item.segment.id in branch_id:
                item.setVisible(not item.isVisible())
                break
    
    def delete_selected_branch(self):
        """Delete selected branch"""
        current = self.branch_list.currentItem()
        if not current:
            return
        
        branch_id = current.data(Qt.UserRole)
        
        # Confirm
        from PyQt5.QtWidgets import QMessageBox
        reply = QMessageBox.question(
            self,
            "Delete Branch",
            f"Delete branch {branch_id}?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            # Remove from topology manager
            if branch_id in self.main_window.topology_manager.branches:
                del self.main_window.topology_manager.branches[branch_id]
            
            # Remove graphics
            for item in self.main_window.scene.items():
                if hasattr(item, 'segment') and item.segment.id in branch_id:
                    self.main_window.scene.removeItem(item)
                    break
            
            self.update_list()
