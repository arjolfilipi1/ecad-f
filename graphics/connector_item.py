from PyQt5.QtWidgets import QGraphicsRectItem,QGraphicsSimpleTextItem,QGraphicsItem
from PyQt5.QtCore import QRectF, QPointF
from PyQt5.QtGui import QBrush
from .pin_item import PinItem
from PyQt5.QtCore import Qt
class ConnectorItem(QGraphicsRectItem):
    def __init__(self, cid, x, y, pin_count=2):
        super().__init__(QRectF(-20, -10, 40, 20))
        self.cid = cid
        self.pins = []
        self.wires = []
        self.setBrush(QBrush())
        self.setFlag(self.ItemIsMovable)
        self.setFlag(self.ItemIsSelectable)
        self.setFlag(self.ItemSendsGeometryChanges)
        self.setBrush(Qt.lightGray)
        self.setPos(x, y)
        self.label = QGraphicsSimpleTextItem(self.cid, self)
        self.label.setFlag(QGraphicsItem.ItemIgnoresTransformations)
        self.update_label_pos()
        
        spacing = 20 / (pin_count + 1)
        for i in range(pin_count):
            pin = PinItem(
                f"{cid}_P{i+1}",
                QPointF(-20, -10 + spacing * (i + 1)),
                self
            )
            self.pins.append(pin)
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