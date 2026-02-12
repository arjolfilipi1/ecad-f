#utils/update_duscpatcher
from PyQt5.QtCore import QObject, pyqtSignal

class UpdateDispatcher(QObject):
    """Central dispatcher for topology updates"""
    
    # Signals
    connector_moved = pyqtSignal(object) # ConnectorItem
    connector_rotated = pyqtSignal(object) # ConnectorItem
    segment_updated = pyqtSignal(object) # WireSegment
    wire_updated = pyqtSignal(object) # Wire
    
    def __init__(self):
        super().__init__()
        
    def notify_connector_moved(self, connector):
        """Notify that a connector has moved"""
        self.connector_moved.emit(connector)
        
    def notify_connector_rotated(self, connector):
        """Notify that a connector has rotated"""
        self.connector_rotated.emit(connector)