from PyQt5.QtWidgets import QGraphicsView, QGraphicsScene,QLabel,QDialog
from PyQt5.QtWidgets import QDockWidget
from PyQt5.QtGui import QPen, QBrush, QPainter
from .pin_item import PinItem
from .wire_item import WireItem
from PyQt5.QtCore import Qt, QPointF, QLineF


class SchematicView(QGraphicsView):
    GRID = 50
    def __init__(self,scene):
        super().__init__(scene)
        self.setRenderHint(QPainter.Antialiasing)
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)
        self.setResizeAnchor(QGraphicsView.AnchorUnderMouse)
        self._scene = scene
        self._current_zoom = 1.0
        # Initialize the Overlay Label
        self.setup_ui_overlay()
    def resizeEvent(self, event):
        # Reposition the label when the window is resized
        super().resizeEvent(event)
        self.update_label_position()

    def wheelEvent(self, event):
        zoom_in_factor = 1.25
        zoom_out_factor = 1 / zoom_in_factor

        if event.angleDelta().y() > 0:
            zoom_factor = zoom_in_factor
        else:
            zoom_factor = zoom_out_factor

        # Calculate new zoom level
        self._current_zoom *= zoom_factor

        # Apply scaling and update label
        self.scale(zoom_factor, zoom_factor)
        self.label.setText(f"Zoom: {int(self._current_zoom * 100)}%")
        self.label.adjustSize()
        self.update_label_position()
    def setup_ui_overlay(self):
        # Create label and style it
        self.label = QLabel("Zoom: 100%", self)
        self.label.setStyleSheet("""
            QLabel {
                background-color: rgba(0, 0, 0, 150);
                color: white;
                padding: 5px;
                border-radius: 5px;
                font-weight: bold;
            }
        """)
        self.update_label_position()
    def update_label_position(self):
        # Keep the label at the bottom-left corner
        margin = 30
        self.label.move(margin, self.height() - self.label.height() - margin)
    def drawBackground(self, painter, rect):
        painter.setPen(QPen(Qt.lightGray, 0))

        left = rect.left() - (rect.left() % self.GRID)
        top = rect.top() - (rect.top() % self.GRID)

        x = left
        while x < rect.right():
            painter.drawLine(QLineF(x, rect.top(), x, rect.bottom()))
            x += self.GRID

        y = top
        while y < rect.bottom():
            painter.drawLine(QLineF(rect.left(), y, rect.right(), y))
            y += self.GRID

        # origin cross
        painter.setPen(QPen(Qt.red, 1))
        painter.drawLine(QLineF(-20, 0, 20, 0))
        painter.drawLine(QLineF(0, -20, 0, 20))

    def mousePressEvent(self, event):
        item = self.itemAt(event.pos())
        if isinstance(item, PinItem):
            self.active_pin = item
        super().mousePressEvent(event)

    def mouseReleaseEvent(self, event):
        item = self.itemAt(event.pos())
        if isinstance(item, PinItem) and self.active_pin:
            wire = WireItem("W_NEW", self.active_pin, item)
            self.scene().addItem(wire)
            self.netlist.connect(self.active_pin, item)
            self.active_pin = None
        super().mouseReleaseEvent(event)
from PyQt5.QtWidgets import QWidget, QFormLayout, QLineEdit

class PropertiesWidget(QWidget):
    def __init__(self):
        super().__init__()
        self.layout = QFormLayout(self)
        self.current_item = None

        self.id_edit = QLineEdit()
        self.layout.addRow("ID", self.id_edit)

        self.id_edit.textChanged.connect(self.update_item)

    def set_item(self, item):
        self.current_item = item
        if hasattr(item, "cid"):
            self.id_edit.setText(item.cid)
        elif hasattr(item, "wid"):
            self.id_edit.setText(item.wid)

    def update_item(self, text):
        if self.current_item:
            if hasattr(self.current_item, "cid"):
                self.current_item.cid = text
            elif hasattr(self.current_item, "wid"):
                self.current_item.wid = text





class PropertiesDock(QDockWidget):
    def __init__(self):
        super().__init__("Properties")
        self.widget = PropertiesWidget()
        self.setWidget(self.widget)
