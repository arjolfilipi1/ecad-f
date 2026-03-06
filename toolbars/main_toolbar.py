"""
Main editing toolbar
"""

from PyQt5.QtWidgets import QToolBar, QAction
from PyQt5.QtCore import QSize


class MainToolbar(QToolBar):
    """Main editing toolbar with basic tools"""
    
    def __init__(self, main_window):
        super().__init__("Main Tools")
        self.main_window = main_window
        self.setObjectName("MainToolBar")
        self.setIconSize(QSize(24, 24))
        self.setMovable(True)
        
        self.setup_actions()
    
    def setup_actions(self):
        """Setup toolbar actions"""
        # Add existing tools from view
        self.addActions(self.main_window.view.tool_group.actions())
        
        # Add connector button
        add_connector = QAction("➕ Connector", self)
        add_connector.triggered.connect(self.show_custom_dialog)
        self.addAction(add_connector)
        
        # Rotate button
        rotate = QAction("🔄 Rotate", self)
        rotate.triggered.connect(self.main_window.rotate_selected)
        self.addAction(rotate)
        
        # Toggle info table
        toggle_table = QAction("📊 Show Pin Table", self)
        toggle_table.triggered.connect(self.main_window.toggle_connector_info)
        self.addAction(toggle_table)
        
        # Compact mode toggle
        toggle_compact = QAction("📋 Compact View", self)
        toggle_compact.triggered.connect(self.main_window.toggle_compact_mode)
        self.addAction(toggle_compact)
        
        self.addSeparator()
        
        # Settings button
        settings_btn = QAction("⚙️ Settings", self)
        settings_btn.triggered.connect(self.main_window.show_settings)
        self.addAction(settings_btn)
    
    def show_custom_dialog(self):
        """Show custom dialog (placeholder)"""
        from PyQt5.QtWidgets import QDialog, QVBoxLayout, QLabel
        dialog = QDialog(self.main_window)
        dialog.setWindowTitle("Settings Dialog")
        layout = QVBoxLayout()
        layout.addWidget(QLabel("Configure your view settings here."))
        dialog.setLayout(layout)
        dialog.exec_()
