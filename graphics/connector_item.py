from PyQt5.QtWidgets import QGraphicsRectItem,QGraphicsSimpleTextItem,QGraphicsItem,QGraphicsTextItem
from PyQt5.QtCore import QRectF, QPointF
from PyQt5.QtGui import QBrush,QFont
from .pin_item import PinItem
from PyQt5.QtCore import Qt
from itertools import count
class ConnectorItem(QGraphicsRectItem):
    _ids = count(0)
    def __init__(self,  x, y, pin_count=2):
        super().__init__(QRectF(-20, -10, 40, 20))
        self.cid = "C"+str(next(self._ids))
        self.pins = []
        self.tree_item = None
        self.rotation_angle = 0
        self.wires = []
        self.setBrush(QBrush())
        self.setFlag(self.ItemIsMovable)
        self.setFlag(self.ItemIsSelectable)
        self.setFlag(self.ItemSendsGeometryChanges)
        self.setBrush(Qt.lightGray)
        self.setTransformOriginPoint(0, 0)
        self.setPos(x, y)
        self.label = QGraphicsSimpleTextItem(self.cid, self)
        self.label.setFlag(QGraphicsItem.ItemIgnoresTransformations)
        self.update_label_pos()
        spacing = 20 / (pin_count + 1)
        for i in range(pin_count):
            pin = PinItem(
                f"{self.cid}_P{i+1}",
                QPointF(-20, -10 + spacing * (i + 1)),
                self
            )
            self.pins.append(pin)
        self.info = ConnectorInfoItem(self)

    def scene_position(self):
        return self.pos()
    def itemChange(self, change, value):
        if change == self.ItemPositionHasChanged:
            for pin in list(self.pins):
                for wire in list(pin.wires):
                    wire.update_path()
        return super().itemChange(change, value)
    def update_label_pos(self):
        self.label.setPos(
            self.rect().center().x() - self.label.boundingRect().width() / 2,
            -self.label.boundingRect().height() - 10
        )
    def rotate_90(self):
        self.rotation_angle = (self.rotation_angle + 90) % 360
        for pin in list(self.pins):
            self.setFlag(QGraphicsItem.ItemIgnoresTransformations)
        self.setRotation(self.rotation_angle)
        for pin in list(self.pins):
            self.setFlag(QGraphicsItem.ItemIgnoresTransformations,False)
            for wire in list(pin.wires):
                wire.update_path()

class ConnectorInfoItem(QGraphicsTextItem):
    def __init__(self, connector):
        super().__init__(connector)
        self.connector = connector

        self.setFont(QFont("Consolas", 8))
        self.setDefaultTextColor(Qt.darkGray)
        self.setFlag(self.ItemIgnoresTransformations)  # stays readable
        self.setZValue(10)

        self.setPos(25, -15)  # offset to the right of connector
        self.update_text()

    def update_text(self):
        lines = [f"{self.connector.cid}"]
        for pin in self.connector.pins:
            nets = {w.wid for w in getattr(pin, "wires", []) if hasattr(w, "net")}
            net_name = ",".join(nets) if nets else "—"
            lines.append(f"{pin.pid}: {net_name}")

        self.setPlainText("\n".join(lines))
