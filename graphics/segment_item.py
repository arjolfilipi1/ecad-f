#graphics/segment_item
from PyQt5.QtWidgets import QGraphicsPathItem, QStyle
from PyQt5.QtCore import  QPointF,Qt
from PyQt5.QtGui import QPainterPath,QPen, QColor, QPainter

class SegmentGraphicsItem(QGraphicsPathItem):
    def __init__(self, segment, topology_manager=None,broken = False):
        super().__init__()
        pass