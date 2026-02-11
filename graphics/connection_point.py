from PyQt5.QtWidgets import QGraphicsEllipseItem, QGraphicsItem
from PyQt5.QtGui import QBrush
from PyQt5.QtCore import QPointF, Qt

class ConnectionPoint(QGraphicsEllipseItem):
    """
    Represents a topological node in the schematic.
    Can connect wire segments and pins.
    """

    RADIUS = 3

    def __init__(self, pos: QPointF, net, show_dot=True):
        super().__init__(
            -self.RADIUS,
            -self.RADIUS,
            self.RADIUS * 2,
            self.RADIUS * 2
        )

        self.setPos(pos)
        self.net = net
        self.segments = []
        self.pins = []
        self.node = None  # Add this for topology node reference
        self.pin_ref = None  # Add this for pin reference

        self.setZValue(2)

        self.setFlag(QGraphicsItem.ItemIsMovable)
        self.setFlag(QGraphicsItem.ItemSendsGeometryChanges)
        self.setFlag(QGraphicsItem.ItemIsSelectable)

        if show_dot:
            self.setBrush(QBrush(net.color))
        else:
            self.setBrush(Qt.NoBrush)

        net.connection_points.append(self)

    def add_segment(self, segment):
        if segment not in self.segments:
            self.segments.append(segment)

    def add_pin(self, pin):
        if pin not in self.pins:
            self.pins.append(pin)
            self.pin_ref = pin

    def itemChange(self, change, value):
        if change == QGraphicsItem.ItemPositionHasChanged:
            self._update_segments()
        return super().itemChange(change, value)

    def _update_segments(self):
        for seg in self.segments:
            if hasattr(seg, 'start_point') and seg.start_point == self:
                if hasattr(seg, 'update_start'):
                    seg.update_start(self.scenePos())
            elif hasattr(seg, 'end_point') and seg.end_point == self:
                if hasattr(seg, 'update_end'):
                    seg.update_end(self.scenePos())
