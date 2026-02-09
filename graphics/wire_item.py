from PyQt5.QtWidgets import QGraphicsPathItem
from PyQt5.QtGui import QPainterPath, QPen, QColor
from model.models import CombinedWireColor

class WireItem(QGraphicsPathItem):
    def __init__(self, wid, start_pin, end_pin,color_txt = "SW"):
        super().__init__()
        self.wid = wid
        self.start_pin = start_pin
        self.end_pin = end_pin
        
        self.color_data = CombinedWireColor(color_txt)
        self.color = QColor(self.color_data.rgb[0],self.color_data.rgb[1],self.color_data.rgb[2])
        self.setPen(QPen(self.color,2))
        self.setFlag(self.ItemIsSelectable)

        start_pin.wires.append(self)
        end_pin.wires.append(self)

        self.update_path()
        
        

    def update_path(self):
        p1 = self.start_pin.scene_position()
        p2 = self.end_pin.scene_position()

        mid_x = (p1.x() + p2.x()) / 2

        path = QPainterPath(p1)
        path.lineTo(mid_x, p1.y())
        path.lineTo(mid_x, p2.y())
        path.lineTo(p2)

        self.setPath(path)
        
    def set_color(self, color: QColor):
        self.color = QColor(color)
        self.setPen(QPen(self.color, 2))