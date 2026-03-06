"""
Tools menu creation
"""

from PyQt5.QtWidgets import QMenu, QAction


class ToolsMenu:
    """Creates and manages the Tools menu"""
    
    def __init__(self, main_window):
        self.main_window = main_window
        
        menubar = main_window.menuBar()
        
        # Find or create Tools menu
        tools_menu = None
        for action in menubar.actions():
            if action.text() == "&Tools":
                tools_menu = action.menu()
                break
        
        if not tools_menu:
            tools_menu = menubar.addMenu("&Tools")
        
        self.menu = tools_menu
        self.setup_actions()
    
    def setup_actions(self):
        """Setup all tools menu actions"""
        # Add connector database action
        db_action = QAction("Connector Database Manager", self.main_window)
        db_action.triggered.connect(self.main_window.launch_connector_manager)
        self.menu.addAction(db_action)
        
        # Add separator and settings
        self.menu.addSeparator()
        settings_action = QAction("Settings...", self.main_window)
        settings_action.triggered.connect(self.main_window.show_settings)
        self.menu.addAction(settings_action)
