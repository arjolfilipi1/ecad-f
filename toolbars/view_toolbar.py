"""
View and visualization toolbar
"""

from PyQt5.QtWidgets import QToolBar, QAction
from PyQt5.QtCore import QSize


class ViewToolbar(QToolBar):
    """View and visualization tools toolbar"""
    
    def __init__(self, main_window):
        super().__init__("View Tools")
        self.main_window = main_window
        self.setObjectName("ViewToolBar")
        self.setIconSize(QSize(24, 24))
        self.setMovable(True)
        
        self.setup_actions()
    
    def setup_actions(self):
        """Setup toolbar actions using visualization manager"""
        if hasattr(self.main_window, 'viz_manager'):
            viz_actions = self.main_window.viz_manager.create_toolbar_actions()
            for action in viz_actions:
                self.addAction(action)
