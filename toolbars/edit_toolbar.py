"""
Edit operations toolbar (undo/redo, selection)
"""

from PyQt5.QtWidgets import QToolBar, QAction
from PyQt5.QtCore import QSize


class EditToolbar(QToolBar):
    """Edit operations toolbar with undo/redo and selection tools"""
    
    def __init__(self, main_window):
        super().__init__("Edit Tools")
        self.main_window = main_window
        self.setObjectName("EditToolBar")
        self.setIconSize(QSize(24, 24))
        self.setMovable(True)
        
        self.setup_actions()
    
    def setup_actions(self):
        """Setup toolbar actions"""
        # Undo/Redo
        self.main_window.undo_act = QAction("↩ Undo", self)
        self.main_window.undo_act.triggered.connect(self.main_window.undo_manager.undo)
        self.addAction(self.main_window.undo_act)
        
        self.main_window.redo_act = QAction("↪ Redo", self)
        self.main_window.redo_act.triggered.connect(self.main_window.undo_manager.redo)
        self.addAction(self.main_window.redo_act)
        self.main_window.redo_act.setEnabled(False)
        
        self.addSeparator()
        
        # Selection tools
        self.main_window.select_all_action = QAction("🔲 Select All", self)
        self.main_window.select_all_action.triggered.connect(self.main_window.select_all)
        self.addAction(self.main_window.select_all_action)
        
        self.main_window.clear_selection_action = QAction("❌ Clear Selection", self)
        self.main_window.clear_selection_action.triggered.connect(self.main_window.clear_selection)
        self.addAction(self.main_window.clear_selection_action)
