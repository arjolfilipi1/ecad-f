# graphics/connector_info_table.py
from PyQt5.QtWidgets import QGraphicsProxyWidget, QTableWidget, QTableWidgetItem, QHeaderView
from PyQt5.QtCore import Qt, QPointF
from PyQt5.QtGui import QColor, QBrush, QFont

class ConnectorInfoTable(QGraphicsProxyWidget):
    """Table-based connector information display (like Excel)"""
    
    def __init__(self, connector):
        super().__init__(connector)
        self.connector = connector
        self.setFlag(self.ItemIgnoresTransformations, True)
        self.setZValue(10)
        
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
        
        # Set column resize mode - FIX for growing columns
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        
        # Prevent automatic column resizing on updates
        self.table.horizontalHeader().setStretchLastSection(False)
        
        # Set the widget
        self.setWidget(self.table)
        
        # Initial position (to the right of connector)
        self.setPos(25, -15)
        
        # Track if we need to resize
        self.content_changed = True
        
        # Initial update
        self.update_table()
    def refresh(self):
        """Public method to refresh the table - call this when wires change"""
        self.update_table()
    def update_table(self):
        """Update the table with current pin information"""
        pins = self.connector.pins
        
        # Remember current column widths
        col0_width = self.table.columnWidth(0)
        col2_width = self.table.columnWidth(2)
        
        # Block signals to prevent unwanted updates
        self.table.blockSignals(True)
        
        # Set row count
        self.table.setRowCount(len(pins))
        
        # Populate rows
        max_wire_length = 0
        for row, pin in enumerate(pins):
            # Pin number
            pin_item = QTableWidgetItem(pin.pid)
            pin_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 0, pin_item)
            
            # Wire ID
            if pin.wires:
                wire = pin.wires[0]
                wire_id = wire.wid if hasattr(wire, 'wid') else str(wire)
                
                wire_item = QTableWidgetItem(wire_id)
                max_wire_length = max(max_wire_length, len(wire_id))
                
                # Color the cell based on wire color
                if hasattr(wire, 'color_data'):
                    color = QColor(*wire.color_data.rgb)
                    # Lighten the color for background
                    color.setAlpha(100)
                    wire_item.setBackground(QBrush(color))
                    
                    # Set text color for contrast
                    if wire.color_data.rgb[0] + wire.color_data.rgb[1] + wire.color_data.rgb[2] < 384:
                        wire_item.setForeground(QBrush(Qt.white))
            else:
                wire_item = QTableWidgetItem("—")
                wire_item.setForeground(QBrush(Qt.gray))
            
            self.table.setItem(row, 1, wire_item)
            
            # Color
            if pin.wires and hasattr(pin.wires[0], 'color_data'):
                color_code = pin.wires[0].color_data.code
                color_item = QTableWidgetItem(color_code)
                
                # Show actual color in background
                color = QColor(*pin.wires[0].color_data.rgb)
                color_item.setBackground(QBrush(color))
                
                # Set text color for contrast
                if pin.wires[0].color_data.rgb[0] + pin.wires[0].color_data.rgb[1] + pin.wires[0].color_data.rgb[2] < 384:
                    color_item.setForeground(QBrush(Qt.white))
            else:
                color_item = QTableWidgetItem("—")
                color_item.setForeground(QBrush(Qt.gray))
            
            color_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 2, color_item)
        
        # Resize rows to content
        self.table.resizeRowsToContents()
        
        # Restore column widths if they were larger
        if col0_width > self.table.columnWidth(0):
            self.table.setColumnWidth(0, col0_width)
        if col2_width > self.table.columnWidth(2):
            self.table.setColumnWidth(2, col2_width)
        
        self.table.blockSignals(False)
        
        # Adjust overall size - FIXED sizing
        total_width = self.table.columnWidth(0) + self.table.columnWidth(1) + self.table.columnWidth(2) + 25
        total_height = self.table.rowHeight(0) * self.table.rowCount() + self.table.horizontalHeader().height() + 10
        
        self.table.setFixedSize(total_width, total_height)
        self.table.updateGeometry()
        
        self.content_changed = False
    
    def mousePressEvent(self, event):
        """Handle mouse press to select corresponding pin"""
        # Convert scene position to local widget coordinates
        scene_pos = event.scenePos()
        
        # Map from scene to this proxy's coordinate system
        local_pos = self.mapFromScene(scene_pos)
        
        # Convert to QPoint for QWidget methods
        widget_pos = local_pos.toPoint()
        
        # Find which row was clicked
        row = self.table.rowAt(widget_pos.y())
        if row >= 0 and row < len(self.connector.pins):
            # Select the corresponding pin
            pin = self.connector.pins[row]
            scene = self.connector.scene()
            if scene:
                scene.clearSelection()
                pin.setSelected(True)
        
        super().mousePressEvent(event)
    
    def resize_to_content(self):
        """Resize table to fit content"""
        self.table.resizeColumnsToContents()
        
        total_width = self.table.columnWidth(0) + self.table.columnWidth(1) + self.table.columnWidth(2) + 25
        total_height = self.table.rowHeight(0) * self.table.rowCount() + self.table.horizontalHeader().height() + 10
        
        self.table.setFixedSize(total_width, total_height)


class CompactConnectorInfoTable(ConnectorInfoTable):
    """More compact version - shows only essential info"""
    
    def __init__(self, connector):
        super().__init__(connector)
        
        # Reduce to 2 columns
        self.table.setColumnCount(2)
        self.table.setHorizontalHeaderLabels(["Pin", "Wire"])
        
        # Adjust column resize modes
        self.table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        
        # Update
        self.update_table()
    
    def update_table(self):
        """Update with compact format"""
        pins = self.connector.pins
        
        # Remember current column widths
        col0_width = self.table.columnWidth(0)
        
        self.table.blockSignals(True)
        self.table.setRowCount(len(pins))
        
        max_wire_length = 0
        for row, pin in enumerate(pins):
            # Pin number
            pin_item = QTableWidgetItem(pin.pid)
            pin_item.setTextAlignment(Qt.AlignCenter)
            self.table.setItem(row, 0, pin_item)
            
            # Wire info (combined)
            if pin.wires:
                wire = pin.wires[0]
                wire_text = f"{wire.wid} ({wire.color_data.code})"
                wire_item = QTableWidgetItem(wire_text)
                max_wire_length = max(max_wire_length, len(wire_text))
                
                # Color background
                color = QColor(*wire.color_data.rgb)
                color.setAlpha(100)
                wire_item.setBackground(QBrush(color))
                
                # Set text color for contrast
                if wire.color_data.rgb[0] + wire.color_data.rgb[1] + wire.color_data.rgb[2] < 384:
                    wire_item.setForeground(QBrush(Qt.white))
            else:
                wire_item = QTableWidgetItem("—")
                wire_item.setForeground(QBrush(Qt.gray))
            
            self.table.setItem(row, 1, wire_item)
        
        self.table.resizeRowsToContents()
        
        # Restore column width if it was larger
        if col0_width > self.table.columnWidth(0):
            self.table.setColumnWidth(0, col0_width)
        
        self.table.blockSignals(False)
        
        # Resize overall widget
        total_width = self.table.columnWidth(0) + self.table.columnWidth(1) + 25
        total_height = self.table.rowHeight(0) * self.table.rowCount() + self.table.horizontalHeader().height() + 10
        
        self.table.setFixedSize(total_width, total_height)
    
    def mousePressEvent(self, event):
        """Handle mouse press for compact table"""
        # Same as parent but with 2 columns
        scene_pos = event.scenePos()
        local_pos = self.mapFromScene(scene_pos)
        widget_pos = local_pos.toPoint()
        
        row = self.table.rowAt(widget_pos.y())
        if row >= 0 and row < len(self.connector.pins):
            pin = self.connector.pins[row]
            scene = self.connector.scene()
            if scene:
                scene.clearSelection()
                pin.setSelected(True)
        
        super().mousePressEvent(event)