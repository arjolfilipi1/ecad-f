"""
Edit menu creation
"""

from PyQt5.QtWidgets import QMenu, QAction


class EditMenu:
    """Creates and manages the Edit menu"""
    
    def __init__(self, main_window):
        self.main_window = main_window
        
        menubar = main_window.menuBar()
        
        # Find or create Edit menu
        edit_menu = None
        for action in menubar.actions():
            if action.text() == "&Edit":
                edit_menu = action.menu()
                break
        
        if not edit_menu:
            edit_menu = menubar.addMenu("&Edit")
        
        self.menu = edit_menu
        self.setup_actions()
    
    def setup_actions(self):
        """Setup all edit menu actions"""
        # Add existing undo/redo
        self.menu.addAction(self.main_window.undo_action)
        self.menu.addAction(self.main_window.redo_action)
        self.menu.addSeparator()
        
        # Add bundle actions
        select_all_bundles = QAction("Select All Bundles", self.main_window)
        select_all_bundles.triggered.connect(self.main_window.select_all_bundles)
        self.menu.addAction(select_all_bundles)
        
        delete_bundles = QAction("Delete Selected Bundles", self.main_window)
        delete_bundles.setShortcut("Del")
        delete_bundles.triggered.connect(self.main_window.delete_selected_bundles)
        self.menu.addAction(delete_bundles)
        
        self.menu.addSeparator()
        
        # Add existing select all
        self.menu.addAction(self.main_window.select_all_action)
        self.menu.addAction(self.main_window.clear_selection_action)
