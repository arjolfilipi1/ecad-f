
"""
Controller handling selection-related operations
"""

from PyQt5 import sip
from graphics.connector_item import ConnectorItem


class SelectionController:
    """Handles selection synchronization between scene and tree views"""
    
    @staticmethod
    def handle_scene_selection(main_window, obj):
        """Handle scene selection - select corresponding tree item"""
        if hasattr(obj, "tree_item") and obj.tree_item:
            try:
                tree = obj.tree_item.treeWidget()
                
                if tree and not sip.isdeleted(tree):
                    if tree.indexOfTopLevelItem(obj.tree_item) >= 0:
                        tree.setCurrentItem(obj.tree_item)
                    else:
                        obj.tree_item = None
                else:
                    obj.tree_item = None
                    
            except RuntimeError:
                obj.tree_item = None
