from PyQt5.QtWidgets import QGraphicsEllipseItem
from PyQt5.QtCore import QPointF
from PyQt5.QtGui import QBrush

class PinItem(QGraphicsEllipseItem):
    def __init__(self, pid, offset: QPointF, parent):
        super().__init__(-3, -3, 6, 6, parent)
        self.pid = pid
        self.offset = offset
        self.wires = []

        self.setPos(offset)
        self.setBrush(QBrush())
        self.setFlag(self.ItemIsSelectable)

    def scene_position(self):
        return self.scenePos()
