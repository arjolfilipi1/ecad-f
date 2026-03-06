"""
File menu creation
"""

from PyQt5.QtWidgets import QMenu, QAction, QFileDialog, QInputDialog, QMessageBox
from PyQt5.QtCore import Qt
from pathlib import Path


class FileMenu:
    """Creates and manages the File menu"""
    
    def __init__(self, main_window):
        self.main_window = main_window
        self.menu = main_window.menuBar().addMenu("&File")
        self.setup_actions()
    
    def setup_actions(self):
        """Setup all file menu actions"""
        # New project
        new_action = QAction("&New Project", self.main_window)
        new_action.setShortcut("Ctrl+N")
        new_action.triggered.connect(self.main_window.new_project)
        self.menu.addAction(new_action)
        
        # Open project
        open_action = QAction("&Open Project...", self.main_window)
        open_action.setShortcut("Ctrl+O")
        open_action.triggered.connect(self.main_window.open_project)
        self.menu.addAction(open_action)
        
        self.menu.addSeparator()
        
        # Save
        save_action = QAction("&Save", self.main_window)
        save_action.setShortcut("Ctrl+S")
        save_action.triggered.connect(self.main_window.save_project)
        self.menu.addAction(save_action)
        
        # Save As
        save_as_action = QAction("Save &As...", self.main_window)
        save_as_action.setShortcut("Ctrl+Shift+S")
        save_as_action.triggered.connect(self.main_window.save_project_as)
        self.menu.addAction(save_as_action)
        
        # PUBLISH
        publish_action = QAction("📤 &Publish to Database...", self.main_window)
        publish_action.setShortcut("Ctrl+P")
        publish_action.triggered.connect(self.main_window.publish_project)
        self.menu.addAction(publish_action)
        
        self.menu.addSeparator()
        
        # Open from Database
        open_from_db_action = QAction("📂 Open from Database...", self.main_window)
        open_from_db_action.triggered.connect(self.main_window.open_from_database)
        self.menu.addAction(open_from_db_action)
        
        self.menu.addSeparator()
        
        # Recent files
        self.main_window.recent_menu = self.menu.addMenu("Recent Projects")
        self._update_recent_menu()
        
        self.menu.addSeparator()
        
        # Export submenu
        export_menu = self.menu.addMenu("Export")
        
        export_excel = QAction("Export to Excel...", self.main_window)
        export_excel.triggered.connect(self.main_window.export_to_excel)
        export_menu.addAction(export_excel)
        
        export_hdt = QAction("Harness Drawing Table...", self.main_window)
        export_hdt.triggered.connect(self.main_window.export_hdt)
        export_menu.addAction(export_hdt)
        
        self.menu.addSeparator()
        
        # Exit
        exit_action = QAction("E&xit", self.main_window)
        exit_action.setShortcut("Ctrl+Q")
        exit_action.triggered.connect(self.main_window.close)
        self.menu.addAction(exit_action)
    
    def _update_recent_menu(self):
        """Update recent files menu"""
        self.main_window.recent_menu.clear()
        
        recent_files = self.main_window.settings_manager.get_recent_files()
        
        if not recent_files:
            action = self.main_window.recent_menu.addAction("(No recent files)")
            action.setEnabled(False)
            return
        
        for filepath in recent_files:
            action = self.main_window.recent_menu.addAction(Path(filepath).name)
            action.setData(filepath)
            action.triggered.connect(lambda checked, f=filepath: self.open_recent(f))
    
    def open_recent(self, filepath):
        """Open a recent file"""
        from controllers.project_controller import ProjectController
        
        if Path(filepath).exists():
            ProjectController.open_project(self.main_window, filepath)
        else:
            QMessageBox.warning(self.main_window, "File Not Found", f"File not found:\n{filepath}")
