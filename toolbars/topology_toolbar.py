"""
Topology tools toolbar (branch points, junctions, etc.)
"""

from PyQt5.QtWidgets import QToolBar, QAction
from PyQt5.QtCore import QSize
from PyQt5.QtGui import QCursor

class TopologyToolbar(QToolBar):
    """Topology and routing tools toolbar"""
    
    def __init__(self, main_window):
        super().__init__("Topology Tools")
        self.main_window = main_window
        self.setObjectName("TopologyToolBar")
        self.setIconSize(QSize(24, 24))
        self.setMovable(True)
        
        self.setup_actions()
    
    def setup_actions(self):
        """Setup toolbar actions"""
        self.addSeparator()
        
        # Add fastener node
        add_fastener_action = QAction("📌 Add Fastener", self)
        add_fastener_action.triggered.connect(self.main_window.add_fastener_node)
        self.addAction(add_fastener_action)
        
        # Add branch point tool
        add_branch = QAction("⬤ Branch Point", self)
        add_branch.triggered.connect(self.main_window.add_branch_point)
        self.addAction(add_branch)
        
        # Add junction tool
        add_junction = QAction("◉ Junction", self)
        add_junction.triggered.connect(self.main_window.add_junction)
        self.addAction(add_junction)
        
        # Add split segment tool
        split_segment = QAction("✂️ Split", self)
        split_segment.triggered.connect(self.split_segment)
        self.addAction(split_segment)
        
        # Add smart wire tool
        smart_wire = QAction("⚡ Smart Wire", self)
        smart_wire.triggered.connect(self.main_window.create_smart_wire)
        self.addAction(smart_wire)
    
    def split_segment(self):
        """Placeholder for split segment functionality"""
        pass
