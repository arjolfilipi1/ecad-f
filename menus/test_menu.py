"""
Test menu for debugging
"""

from PyQt5.QtWidgets import QMenu, QAction


class TestMenu:
    """Creates and manages the Test menu for debugging"""
    
    def __init__(self, main_window):
        self.main_window = main_window
        
        menubar = main_window.menuBar()
        # Create Test menu
        test_menu = menubar.addMenu("&Test")
        self.menu = test_menu
        self.setup_actions()
    
    def log_to_console(self):
        print("test")
        print("self.log_to_console")
    def setup_actions(self):
        """Setup test menu actions"""
        import_action = QAction("Log to console", self.main_window)
        import_action.triggered.connect(self.main_window.log_to_console)
        self.menu.addAction(import_action)

    