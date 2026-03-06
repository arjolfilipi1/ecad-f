"""
Objects dock widget containing connectors and wires trees
"""

from PyQt5.QtWidgets import QDockWidget, QTabWidget, QTreeWidget, QTreeWidgetItem, QHeaderView, QWidget, QVBoxLayout
from PyQt5.QtCore import Qt
from PyQt5 import sip

from ui.wires_tab import WiresTab


class ObjectsDock(QDockWidget):
    """Dock widget containing connectors and wires tabs"""
    
    def __init__(self, main_window):
        super().__init__("Objects", main_window)
        self.main_window = main_window
        
        self.tabs = QTabWidget()
        self.tabs.setTabsClosable(False)
        
        # Connector tree
        self.connectors_tree = QTreeWidget()
        self.connectors_tree.setHeaderLabels(["Connector"])
        self.connectors_tree.itemClicked.connect(self.main_window.on_tree_clicked)
        
        # Wires tab with add button
        self.wires_tab = WiresTab(main_window)
        
        self.tabs.addTab(self.connectors_tree, "Connectors")
        self.tabs.addTab(self.wires_tab, "Wires")
        
        self.setWidget(self.tabs)
    
    def refresh_trees(self, connectors, wire_items):
        """Refresh tree widget contents"""
        self.connectors_tree.blockSignals(True)
        self.wires_tab.wires_tree.blockSignals(True)
        
        self.connectors_tree.clear()
        self.wires_tab.wires_tree.clear()
        
        # Show connectors
        for conn in connectors:
            if conn and conn.scene() == self.main_window.scene:
                try:
                    item = QTreeWidgetItem([conn.model.id])
                    item.setData(0, Qt.UserRole, conn)
                    self.connectors_tree.addTopLevelItem(item)
                    conn.tree_item = item
                except RuntimeError:
                    pass
        
        # Show wires
        for wire_graphics in wire_items:
            try:
                if wire_graphics and wire_graphics.scene() == self.main_window.scene:
                    if hasattr(wire_graphics, 'wire') and wire_graphics.wire:
                        display_name = wire_graphics.wire.id
                    elif hasattr(wire_graphics, 'wid'):
                        display_name = wire_graphics.wid
                    else:
                        display_name = "Wire"
                    
                    item = QTreeWidgetItem([display_name])
                    item.setData(0, Qt.UserRole, wire_graphics)
                    self.wires_tab.wires_tree.addTopLevelItem(item)
                    wire_graphics.tree_item = item
            except RuntimeError:
                pass
        
        self.connectors_tree.blockSignals(False)
        self.wires_tab.wires_tree.blockSignals(False)
