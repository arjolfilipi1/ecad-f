import sys
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QGraphicsView, QGraphicsScene,
    QGraphicsLineItem, QGraphicsEllipseItem, QToolBar, QAction
)
from PyQt5.QtGui import QPen, QBrush, QPainter
from PyQt5.QtCore import Qt, QPointF, QLineF


# ---------------------------
# Connection Node
# ---------------------------
class ConnectionNode(QGraphicsEllipseItem):
    RADIUS = 5

    def __init__(self, pos: QPointF):
        super().__init__(
            -self.RADIUS, -self.RADIUS,
            self.RADIUS * 2, self.RADIUS * 2
        )
        self.setPos(pos)
        self.setBrush(QBrush(Qt.darkBlue))
        self.setZValue(10)

        self.connections = []

        self.setFlags(
            QGraphicsEllipseItem.ItemIsMovable |
            QGraphicsEllipseItem.ItemIsSelectable
        )

    def connect(self, wire, end: str):
        self.connections.append((wire, end))

    def itemChange(self, change, value):
        if change == QGraphicsEllipseItem.ItemPositionChange:
            for wire, _ in self.connections:
                wire.update_geometry()
        return super().itemChange(change, value)


# ---------------------------
# Wire
# ---------------------------
class Wire(QGraphicsLineItem):
    def __init__(self, start_node, end_node):
        super().__init__()

        self.start_node = start_node
        self.end_node = end_node

        self.start_node.connect(self, "start")
        self.end_node.connect(self, "end")

        self.setPen(QPen(Qt.black, 2))
        self.setZValue(1)
        self.setFlags(QGraphicsLineItem.ItemIsSelectable)

        self.update_geometry()

    def update_geometry(self):
        self.setLine(QLineF(
            self.start_node.scenePos(),
            self.end_node.scenePos()
        ))


class Branch(Wire):
    def __init__(self, start_node, end_node):
        super().__init__(start_node, end_node)
        self.setPen(QPen(Qt.darkGreen, 2, Qt.DashLine))


# ---------------------------
# Graphics View with Grid
# ---------------------------
class ECADView(QGraphicsView):
    GRID = 50

    def __init__(self, scene):
        super().__init__(scene)
        self.setRenderHint(QPainter.Antialiasing)
        self.setDragMode(QGraphicsView.ScrollHandDrag)
        self.setTransformationAnchor(QGraphicsView.AnchorUnderMouse)

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


# ---------------------------
# Main Window
# ---------------------------
class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("ECAD Harness Prototype")

        self.scene = QGraphicsScene(-2000, -2000, 4000, 4000)
        self.view = ECADView(self.scene)
        self.setCentralWidget(self.view)

        self._create_toolbar()

    def _create_toolbar(self):
        tb = QToolBar("Tools")
        self.addToolBar(tb)

        add_wire = QAction("Add Wire", self)
        add_wire.triggered.connect(self.add_wire)
        tb.addAction(add_wire)

        add_branch = QAction("Add Branch", self)
        add_branch.triggered.connect(self.add_branch)
        tb.addAction(add_branch)

    def add_wire(self):
        n1 = ConnectionNode(QPointF(0, 0))
        n2 = ConnectionNode(QPointF(300, 0))

        self.scene.addItem(n1)
        self.scene.addItem(n2)
        self.scene.addItem(Wire(n1, n2))

    def add_branch(self):
        selected = self.scene.selectedItems()
        node = next((i for i in selected if isinstance(i, ConnectionNode)), None)
        if not node:
            return

        new_node = ConnectionNode(node.scenePos() + QPointF(0, 200))
        self.scene.addItem(new_node)
        self.scene.addItem(Branch(node, new_node))


# ---------------------------
# Run
# ---------------------------
if __name__ == "__main__":
    app = QApplication(sys.argv)
    win = MainWindow()
    win.resize(1200, 800)
    win.show()
    sys.exit(app.exec_())
