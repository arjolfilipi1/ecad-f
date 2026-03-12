from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
                             QLineEdit, QComboBox, QPushButton, QLabel,
                             QDialogButtonBox, QGroupBox, QTextEdit, QDateTimeEdit)
from PyQt5.QtCore import Qt, QDateTime
from PyQt5.QtGui import QFont
from model.models import WiringHarness


class ProjectPropertiesDialog(QDialog):
    """Dialog for editing project properties"""
    
    def __init__(self, project: WiringHarness, parent=None):
        super().__init__(parent)
        self.project = project
        self.setWindowTitle("Project Properties")
        self.setMinimumWidth(500)
        self.setModal(True)
        
        self.setup_ui()
        self.load_data()
    
    def setup_ui(self):
        """Setup the dialog UI"""
        layout = QVBoxLayout(self)
        
        # Main properties group
        main_group = QGroupBox("Project Information")
        main_layout = QFormLayout(main_group)
        main_layout.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)
        
        # Project ID (read-only)
        self.id_edit = QLineEdit()
        self.id_edit.setReadOnly(True)
        self.id_edit.setStyleSheet("background-color: #f0f0f0;")
        main_layout.addRow("Project ID:", self.id_edit)
        
        # Project Name
        self.name_edit = QLineEdit()
        self.name_edit.setPlaceholderText("Enter project name...")
        main_layout.addRow("Project Name:*", self.name_edit)
        
        # Part Number
        self.part_number_edit = QLineEdit()
        self.part_number_edit.setPlaceholderText("e.g., HARN-001-2024")
        main_layout.addRow("Part Number:", self.part_number_edit)
        
        # Revision
        self.revision_edit = QLineEdit()
        self.revision_edit.setPlaceholderText("e.g., 1.0")
        main_layout.addRow("Revision:", self.revision_edit)
        
        # Created Date (read-only)
        self.created_date = QDateTimeEdit()
        self.created_date.setReadOnly(True)
        self.created_date.setCalendarPopup(True)
        self.created_date.setStyleSheet("background-color: #f0f0f0;")
        main_layout.addRow("Created:", self.created_date)
        
        # Modified Date (read-only)
        self.modified_date = QDateTimeEdit()
        self.modified_date.setReadOnly(True)
        self.modified_date.setCalendarPopup(True)
        self.modified_date.setStyleSheet("background-color: #f0f0f0;")
        main_layout.addRow("Last Modified:", self.modified_date)
        
        layout.addWidget(main_group)
        
        # Description group
        desc_group = QGroupBox("Description")
        desc_layout = QVBoxLayout(desc_group)
        
        self.description_edit = QTextEdit()
        self.description_edit.setPlaceholderText("Enter project description...")
        self.description_edit.setMaximumHeight(100)
        desc_layout.addWidget(self.description_edit)
        
        layout.addWidget(desc_group)
        
        # Statistics group (read-only)
        stats_group = QGroupBox("Statistics")
        stats_layout = QFormLayout(stats_group)
        
        self.connector_count = QLabel("0")
        stats_layout.addRow("Connectors:", self.connector_count)
        
        self.wire_count = QLabel("0")
        stats_layout.addRow("Wires:", self.wire_count)
        
        self.bundle_count = QLabel("0")
        stats_layout.addRow("Bundles:", self.bundle_count)
        
        self.branch_point_count = QLabel("0")
        stats_layout.addRow("Branch Points:", self.branch_point_count)
        
        layout.addWidget(stats_group)
        
        # Buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
        
        # Set tab order
        self.setTabOrder(self.name_edit, self.part_number_edit)
        self.setTabOrder(self.part_number_edit, self.revision_edit)
        self.setTabOrder(self.revision_edit, self.description_edit)
    
    def load_data(self):
        """Load project data into the dialog"""
        self.id_edit.setText(self.project.id)
        self.name_edit.setText(self.project.name)
        self.part_number_edit.setText(self.project.part_number or "")
        self.revision_edit.setText(self.project.revision)
        
        # Format dates
        if self.project.created_date:
            dt = QDateTime.fromString(self.project.created_date.isoformat(), Qt.ISODate)
            self.created_date.setDateTime(dt)
        
        if self.project.modified_date:
            dt = QDateTime.fromString(self.project.modified_date.isoformat(), Qt.ISODate)
            self.modified_date.setDateTime(dt)
        
        # Description (if it exists in the model - you may need to add this field)
        if hasattr(self.project, 'description'):
            self.description_edit.setText(self.project.description)
        
        # Update statistics
        self.connector_count.setText(str(len(self.project.connectors)))
        self.wire_count.setText(str(len(self.project.wires)))
        self.bundle_count.setText(str(len(self.project.bundles)))
        self.branch_point_count.setText(str(len(self.project.branch_points)))
    
    def save_data(self):
        """Save dialog data back to project"""
        self.project.name = self.name_edit.text()
        self.project.part_number = self.part_number_edit.text() or None
        self.project.revision = self.revision_edit.text()
        
        # Save description if field exists
        if hasattr(self.project, 'description'):
            self.project.description = self.description_edit.toPlainText() or None
        
        # Update modified date
        from datetime import datetime
        self.project.modified_date = datetime.now()
    
    def accept(self):
        """Validate and accept"""
        if not self.name_edit.text():
            from PyQt5.QtWidgets import QMessageBox
            QMessageBox.warning(self, "Validation Error", "Project Name is required!")
            return
        
        self.save_data()
        super().accept()
