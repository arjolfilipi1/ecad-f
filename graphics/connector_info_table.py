from PyQt5.QtWidgets import (
    QGraphicsProxyWidget, QTableWidget, QTableWidgetItem,
    QHeaderView
)
from PyQt5.QtCore import Qt, QPointF
from PyQt5.QtGui import QBrush, QCursor


class ConnectorInfoTable(QGraphicsProxyWidget):
    """Table-based connector information display"""

    def __init__(self, connector):
        super().__init__()

        self.connector = connector

        # Flags
        self.setFlag(self.ItemIsSelectable, True)
        self.setFlag(self.ItemSendsGeometryChanges, True)
        self.setZValue(10)

        # ---- OFFSET (LOCAL SPACE ONLY) ----
        if hasattr(connector.model, 'table_pos'):
            self.offset = QPointF(*connector.model.table_pos)
        else:
            self.offset = QPointF(25, -15)
            connector.model.table_pos = (25, -15)

        # ---- TABLE ----
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["Pin", "Wire ID", "Color"])

        self.table.setStyleSheet("""
            QTableWidget {
                background-color: rgba(255, 255, 255, 230);
                border: 1px solid #888;
                font-size: 8pt;
                gridline-color: #ccc;
            }
            QTableWidget::item {
                padding: 2px;
                margin: 2px;
            }
            QHeaderView::section {
                background-color: #e0e0e0;
                padding: 4px;
                border: 1px solid #aaa;
                font-weight: bold;
                font-size: 8pt;
            }
        """)

        self.table.setAlternatingRowColors(True)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.verticalHeader().setVisible(False)

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(QHeaderView.ResizeToContents)

        self.setWidget(self.table)

        # ---- PARENTING ----
        self.setParentItem(connector)

        # Apply position + rotation
        self.update_position()

        # Initial data
        self.update_table()

    # ------------------------------------------------------------------
    # POSITION / ROTATION (CLEAN)
    # ------------------------------------------------------------------

    def update_position(self):
        if not self.connector:
            return

        # Local position relative to connector
        self.setPos(self.offset)

        # Keep table upright
        self.setRotation(-self.connector.rotation())

    # ------------------------------------------------------------------
    # TABLE DATA
    # ------------------------------------------------------------------

    def update_table(self):
        if not self.connector or not hasattr(self.connector, 'model'):
            return

        pins = self.connector.model.pins

        self.table.blockSignals(True)
        self.table.setRowCount(len(pins))

        for row, (_, pin) in enumerate(pins.items()):
            # Pin number
            pin_item = QTableWidgetItem(str(pin.number))
            pin_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 0, pin_item)

            # Wire ID
            if pin.wire_ids:
                wire_id = pin.wire_ids[0] if isinstance(pin.wire_ids, list) else pin.wire_ids
                wire_item = QTableWidgetItem(str(wire_id))
            else:
                wire_item = QTableWidgetItem("—")
                wire_item.setForeground(QBrush(Qt.gray))

            self.table.setItem(row, 1, wire_item)

            # Color placeholder
            color_item = QTableWidgetItem("—")
            color_item.setForeground(QBrush(Qt.gray))
            color_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 2, color_item)

        self.table.resizeRowsToContents()
        self.table.blockSignals(False)

        # Resize widget
        total_width = sum(self.table.columnWidth(i) for i in range(3)) + 25
        total_height = (
            self.table.horizontalHeader().height() +
            sum(self.table.rowHeight(i) for i in range(self.table.rowCount())) + 10
        )

        self.table.setFixedSize(total_width, total_height)
        self.resize(total_width - 20, total_height - 8)

    # ------------------------------------------------------------------
    # DRAGGING (FIXED)
    # ------------------------------------------------------------------

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.drag_start_offset = QPointF(self.offset)
            self.setCursor(QCursor(Qt.ClosedHandCursor))
            self.setSelected(True)

        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if event.buttons() & Qt.LeftButton:
            # 1. Movement in scene space (always correct)
            scene_delta = event.scenePos() - event.lastScenePos()

            # 2. Convert scene delta → parent (connector) local space
            parent = self.parentItem()
            if parent:
                local_delta = parent.mapFromScene(event.scenePos()) - parent.mapFromScene(event.lastScenePos())
            else:
                local_delta = scene_delta  # fallback (shouldn't happen)

            # 3. Apply to offset
            self.offset += local_delta

            # 4. Update position
            self.setPos(self.offset)

        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if event.button() == Qt.LeftButton:
            self.setCursor(QCursor(Qt.ArrowCursor))

            # Save to model
            if hasattr(self.connector, 'model'):
                self.connector.model.table_pos = (self.offset.x(), self.offset.y())

        super().mouseReleaseEvent(event)
    def refresh(self):
        """Public method to refresh the table"""
        self.update_table()
        