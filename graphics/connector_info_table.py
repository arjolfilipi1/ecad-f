# graphics/connector_info_table.py
from PyQt5.QtWidgets import QGraphicsProxyWidget, QTableWidget, QTableWidgetItem, QHeaderView, QSizePolicy
from PyQt5.QtCore import Qt, QPointF
from PyQt5.QtGui import QColor, QBrush, QFont, QCursor
from PyQt5.QtWidgets import QMenu, QAction

class ConnectorInfoTable(QGraphicsProxyWidget):
    """Table-based connector information display (like Excel)"""
    
    def __init__(self, connector):
        super().__init__()
        self.connector = connector
        self.setFlag(self.ItemIsMovable, False)
        self.setFlag(self.ItemIsSelectable, True)
        self.setFlag(self.ItemSendsGeometryChanges, True)
        self.setZValue(10)
        
        # Store the offset from connector (in local coordinates)
        if hasattr(connector.model, 'table_pos'):
            self.offset = QPointF(connector.model.table_pos[0], connector.model.table_pos[1])
        else:
            self.offset = QPointF(25, -15)
            connector.model.table_pos = (25, -15)
        
        # Create the table widget
        self.table = QTableWidget()
        self.table.setColumnCount(3)
        self.table.setHorizontalHeaderLabels(["Pin", "Wire ID", "Color"])
        
        # Style the table
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
        
        # Set table properties
        self.table.setAlternatingRowColors(True)
        self.table.setEditTriggers(QTableWidget.NoEditTriggers)
        self.table.setSelectionBehavior(QTableWidget.SelectRows)
        self.table.setSelectionMode(QTableWidget.SingleSelection)
        self.table.verticalHeader().setVisible(False)
        
        # Set column resize mode
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        
        # Set the widget
        self.setWidget(self.table)
        
        # Set initial position
        self.setParentItem(connector)  # Make it a child of the connector
        self.setPos(self.offset)  # Position relative to connector
        # Counter-rotate to keep upright
        self.setRotation(-connector.rotation())
        # Initial update
        self.update_table()
        

    
    def update_position(self):
        """Update position and rotation based on connector"""
        if not self.connector:
            return
        ori = self.connector.scenePos()
        print(self.parent())
        # Position relative to connector
        self.setPos(QPointF(ori.x() + self.offset.x(),ori.y() + self.offset.y() ))
        
        # Counter-rotate to stay upright
        self.setRotation(-self.connector.rotation())
    
    def refresh(self):
        """Public method to refresh the table"""
        self.update_table()
        
    def update_table(self):
        """Update the table with current pin information"""
        if not self.connector or not hasattr(self.connector, 'model'):
            return
            
        pins = self.connector.model.pins

        # Block signals to prevent unwanted updates
        self.table.blockSignals(True)
        
        # Set row count
        self.table.setRowCount(len(pins))
        
        # Populate rows
        for row, (pin_num, pin) in enumerate(pins.items()):
            # Pin number
            pin_item = QTableWidgetItem(str(pin.number))
            pin_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 0, pin_item)
            
            # Wire ID
            if pin.wire_ids:
                if isinstance(pin.wire_ids, list) and pin.wire_ids:
                    wire_id = str(pin.wire_ids[0])
                else:
                    wire_id = str(pin.wire_ids)
                
                wire_item = QTableWidgetItem(wire_id)
            else:
                wire_item = QTableWidgetItem("—")
                wire_item.setForeground(QBrush(Qt.gray))
            
            self.table.setItem(row, 1, wire_item)
            
            # Color
            color_item = QTableWidgetItem("—")
            color_item.setForeground(QBrush(Qt.gray))
            color_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 2, color_item)
        
        # Resize rows to content
        self.table.resizeRowsToContents()
        
        self.table.blockSignals(False)
        
        # Adjust overall size
        total_width = self.table.columnWidth(0) + self.table.columnWidth(1) + self.table.columnWidth(2) + 25
        total_height = self.table.rowHeight(0) * self.table.rowCount() + self.table.horizontalHeader().height() + 10
        
        self.table.setFixedSize(total_width, total_height)
        self.resize(total_width-23, total_height-9)
        

    
    def mousePressEvent(self, event):
        """Handle mouse press for dragging"""
        if event.button() == Qt.LeftButton:
            self.drag_start_offset = self.offset
            self.drag_start_pos = self.pos()  # Store initial position
            self.setCursor(QCursor(Qt.ClosedHandCursor))
            self.setSelected(True)  # Select the table when clicking
        
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        """Handle mouse move for dragging with rotation compensation"""
        if event.buttons() & Qt.LeftButton:
            # Get the movement in scene coordinates
            scene_delta = event.scenePos() - event.lastScenePos()
            
            # Move the table in scene coordinates
            new_pos = self.pos() + scene_delta
            self.setPos(new_pos)
            
            # Calculate new offset accounting for connector rotation
            if self.connector:
                # Get connector's position and rotation
                connector_pos = self.connector.scenePos()
                connector_rotation = self.connector.rotation()
                
                # Calculate vector from connector to table in scene coordinates
                scene_offset = new_pos - connector_pos
                
                # Transform scene offset to local connector coordinates (account for rotation)
                import math
                angle = math.radians(connector_rotation)
                cos_a = math.cos(angle)
                sin_a = math.sin(angle)
                
                # Rotate the scene offset by -angle to get local offset
                local_x = scene_offset.x() * cos_a + scene_offset.y() * sin_a
                local_y = -scene_offset.x() * sin_a + scene_offset.y() * cos_a
                
                # Update offset
                self.offset = QPointF(local_x, local_y)
        
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        """Handle mouse release"""
        if event.button() == Qt.LeftButton:
            self.setCursor(QCursor(Qt.ArrowCursor))
            
            # Update model if position changed
            if hasattr(self, 'drag_start_offset') and self.drag_start_offset != self.offset:
                if self.connector and hasattr(self.connector, 'model'):
                    # Save to model
                    self.connector.model.table_pos = (self.offset.x(), self.offset.y())
                    
                    # Create undo command if main window exists
                    if hasattr(self, 'connector') and hasattr(self.connector, 'main_window'):
                        self._create_position_undo_command(
                            self.drag_start_offset, 
                            self.offset
                        )
        self.update_position()
        super().mouseReleaseEvent(event)

    def _create_position_undo_command(self, old_offset, new_offset):
        """Create undo command for table position change"""
        if not self.connector or not self.connector.main_window:
            return
        
        from commands.connector_commands import UpdateConnectorPropertiesCommand
        
        old_props = {'table_pos': (old_offset.x(), old_offset.y())}
        new_props = {'table_pos': (new_offset.x(), new_offset.y())}
        
        cmd = UpdateConnectorPropertiesCommand(
            self.connector,
            old_props,
            new_props
        )
        self.connector.main_window.undo_manager.push(cmd)