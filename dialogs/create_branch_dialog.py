# dialogs/create_branch_dialog.py
from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
                             QLineEdit, QComboBox, QPushButton, QListWidget,
                             QListWidgetItem, QLabel, QDialogButtonBox, QGroupBox)
from PyQt5.QtCore import Qt

class CreateBranchDialog(QDialog):
    """Dialog for creating a new branch from selected nodes"""
    
    def __init__(self, main_window, selected_nodes, parent=None):
        super().__init__(parent)
        self.main_window = main_window
        self.selected_nodes = selected_nodes  # List of selected node items
        self.setWindowTitle("Create Branch")
        self.setMinimumWidth(400)
        
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Branch name
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("Branch Name:"))
        self.name_edit = QLineEdit()
        self.name_edit.setText(f"Branch_{len(self.main_window.topology_manager.branches) + 1}")
        name_layout.addWidget(self.name_edit)
        layout.addLayout(name_layout)
        
        # Protection type
        protect_layout = QHBoxLayout()
        protect_layout.addWidget(QLabel("Protection:"))
        self.protection_combo = QComboBox()
        self.protection_combo.addItems(["None", "Braided Sleeve", "Heat Shrink", "Conduit", "Tape"])
        protect_layout.addWidget(self.protection_combo)
        layout.addLayout(protect_layout)
        
        # Selected nodes list
        nodes_group = QGroupBox("Nodes in Branch (in order)")
        nodes_layout = QVBoxLayout(nodes_group)
        
        self.nodes_list = QListWidget()
        for node in self.selected_nodes:
            node_name = self._get_node_name(node)
            item = QListWidgetItem(node_name)
            item.setData(Qt.UserRole, node)
            self.nodes_list.addItem(item)
        nodes_layout.addWidget(self.nodes_list)
        
        # Reorder buttons
        reorder_layout = QHBoxLayout()
        move_up_btn = QPushButton("↑ Move Up")
        move_up_btn.clicked.connect(self.move_selected_up)
        reorder_layout.addWidget(move_up_btn)
        
        move_down_btn = QPushButton("↓ Move Down")
        move_down_btn.clicked.connect(self.move_selected_down)
        reorder_layout.addWidget(move_down_btn)
        reorder_layout.addStretch()
        nodes_layout.addLayout(reorder_layout)
        
        layout.addWidget(nodes_group)
        
        # Path preview
        preview_label = QLabel("Path will be created between consecutive nodes")
        preview_label.setStyleSheet("color: gray; font-style: italic;")
        layout.addWidget(preview_label)
        
        # Buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
    
    def _get_node_name(self, node):
        """Get display name for a node"""
        if hasattr(node, 'cid'):  # Connector
            return f"Connector: {node.cid}"
        elif hasattr(node, 'branch_node'):  # Branch point
            return f"Branch Point: {node.branch_node.id[:8]}"
        elif hasattr(node, 'fastener_node'):  # Fastener
            return f"Fastener: {node.fastener_node.fastener_type}"
        elif hasattr(node, 'junction_node'):  # Junction
            return f"Junction: {node.junction_node.id[:8]}"
        return str(node)
    
    def move_selected_up(self):
        """Move selected node up in order"""
        current_row = self.nodes_list.currentRow()
        if current_row > 0:
            item = self.nodes_list.takeItem(current_row)
            self.nodes_list.insertItem(current_row - 1, item)
            self.nodes_list.setCurrentRow(current_row - 1)
    
    def move_selected_down(self):
        """Move selected node down in order"""
        current_row = self.nodes_list.currentRow()
        if current_row < self.nodes_list.count() - 1:
            item = self.nodes_list.takeItem(current_row)
            self.nodes_list.insertItem(current_row + 1, item)
            self.nodes_list.setCurrentRow(current_row + 1)
    
    def get_branch_data(self):
        """Return branch data for creation"""
        nodes = []
        for i in range(self.nodes_list.count()):
            item = self.nodes_list.item(i)
            nodes.append(item.data(Qt.UserRole))
        
        return {
            'name': self.name_edit.text(),
            'protection': self.protection_combo.currentText(),
            'nodes': nodes
        }