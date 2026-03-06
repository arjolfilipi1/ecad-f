"""
Import and routing toolbar
"""

from PyQt5.QtWidgets import QToolBar, QAction
from PyQt5.QtCore import QSize


class ImportToolbar(QToolBar):
    """Import and routing tools toolbar"""
    
    def __init__(self, main_window):
        super().__init__("Import & Routing")
        self.main_window = main_window
        self.setObjectName("ImportToolBar")
        self.setIconSize(QSize(24, 24))
        self.setMovable(True)
        
        self.setup_actions()
    
    def setup_actions(self):
        """Setup toolbar actions"""
        # Import button
        import_btn = QAction("📥 Import Excel", self)
        import_btn.triggered.connect(self.main_window.import_from_excel)
        self.addAction(import_btn)
        
        # Auto-route button
        route_btn = QAction("🔄 Create Branches", self)
        route_btn.triggered.connect(self.main_window.auto_route_wires)
        self.addAction(route_btn)
        
        # Clear topology button
        clear_btn = QAction("🗑️ Clear Topology", self)
        clear_btn.triggered.connect(self.main_window.clear_topology)
        self.addAction(clear_btn)
