"""
Wires tab widget with inline wire creation form
"""

from PyQt5.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QTreeWidget,
    QTreeWidgetItem, QComboBox, QLineEdit, QDoubleSpinBox,
    QLabel, QGroupBox, QFormLayout, QMessageBox
)
from PyQt5.QtCore import Qt
from PyQt5.QtGui import QColor

from graphics.wire_item import WireItem
from model.netlist import Netlist
from utils.excel_import import ImportedWire


class WiresTab(QWidget):
    """Wires tab with add wire button and inline input"""
    
    def __init__(self, main_window):
        super().__init__()
        self.main_window = main_window
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(2, 2, 2, 2)
        layout.setSpacing(2)
        
        # Add Wire button
        self.add_wire_btn = QPushButton("➕ Add Wire")
        self.add_wire_btn.clicked.connect(self.toggle_wire_input)
        layout.addWidget(self.add_wire_btn)
        
        # Inline input container (initially hidden)
        self.wire_input_container = QWidget()
        self.wire_input_container.setVisible(False)
        self.setup_input_form()
        layout.addWidget(self.wire_input_container)
        
        # Wire tree
        self.wires_tree = QTreeWidget()
        self.wires_tree.setHeaderLabels(["Wire"])
        self.wires_tree.itemClicked.connect(self.on_tree_clicked)
        layout.addWidget(self.wires_tree)
    
    def setup_input_form(self):
        """Setup the inline input form"""
        input_layout = QVBoxLayout(self.wire_input_container)
        input_layout.setContentsMargins(5, 5, 5, 5)
        input_layout.setSpacing(3)
        
        self.wire_input_container.setStyleSheet("""
            QWidget {
                background-color: #f0f0f0;
                border: 1px solid #c0c0c0;
                border-radius: 3px;
            }
            QLabel {
                font-size: 10px;
                font-weight: bold;
                color: #333;
            }
            QComboBox, QLineEdit, QDoubleSpinBox {
                background-color: white;
                border: 1px solid #c0c0c0;
                border-radius: 2px;
                padding: 3px;
                font-size: 10px;
                min-height: 18px;
            }
            QPushButton {
                background-color: #0078d4;
                color: white;
                border: none;
                border-radius: 2px;
                padding: 5px;
                font-size: 10px;
                font-weight: bold;
                min-height: 20px;
            }
            QPushButton:hover {
                background-color: #106ebe;
            }
            QPushButton:pressed {
                background-color: #005a9e;
            }
            QPushButton#cancelBtn {
                background-color: #6c757d;
            }
            QPushButton#cancelBtn:hover {
                background-color: #5a6268;
            }
        """)
        
        # Title
        title = QLabel("Add New Wire")
        title.setAlignment(Qt.AlignCenter)
        input_layout.addWidget(title)
        
        # From connector selection
        from_layout = QHBoxLayout()
        from_layout.addWidget(QLabel("From:"))
        self.from_connector_combo = QComboBox()
        self.from_connector_combo.currentIndexChanged.connect(self.update_from_pins)
        from_layout.addWidget(self.from_connector_combo)
        input_layout.addLayout(from_layout)
        
        # From pin selection
        from_pin_layout = QHBoxLayout()
        from_pin_layout.addWidget(QLabel("Pin:"))
        self.from_pin_combo = QComboBox()
        from_pin_layout.addWidget(self.from_pin_combo)
        input_layout.addLayout(from_pin_layout)
        
        # To connector selection
        to_layout = QHBoxLayout()
        to_layout.addWidget(QLabel("To:"))
        self.to_connector_combo = QComboBox()
        self.to_connector_combo.currentIndexChanged.connect(self.update_to_pins)
        to_layout.addWidget(self.to_connector_combo)
        input_layout.addLayout(to_layout)
        
        # To pin selection
        to_pin_layout = QHBoxLayout()
        to_pin_layout.addWidget(QLabel("Pin:"))
        self.to_pin_combo = QComboBox()
        to_pin_layout.addWidget(self.to_pin_combo)
        input_layout.addLayout(to_pin_layout)
        
        # Wire properties
        props_group = QGroupBox("Wire Properties")
        props_group.setStyleSheet("QGroupBox { font-weight: bold; font-size: 10px; }")
        props_layout = QFormLayout(props_group)
        props_layout.setSpacing(3)
        props_layout.setContentsMargins(5, 10, 5, 5)
        
        # Signal name
        self.wire_signal = QLineEdit()
        self.wire_signal.setPlaceholderText("e.g., ABS_Sensor")
        props_layout.addRow("Signal:", self.wire_signal)
        
        # Wire color
        color_layout = QHBoxLayout()
        self.wire_color = QComboBox()
        colors = ['SW', 'RT', 'GN', 'BL', 'GE', 'BR', 'WS', 'GR', 'VT', 'OR', 'RS']
        self.wire_color.addItems(colors)
        self.wire_color.setEditable(True)
        color_layout.addWidget(self.wire_color)
        
        # Color preview
        self.color_preview = QLabel("   ")
        self.color_preview.setFixedSize(20, 16)
        self.color_preview.setStyleSheet("background-color: black; border: 1px solid gray;")
        self.wire_color.currentTextChanged.connect(self.update_color_preview)
        color_layout.addWidget(self.color_preview)
        props_layout.addRow("Color:", color_layout)
        
        # Cross section
        self.wire_cross_section = QDoubleSpinBox()
        self.wire_cross_section.setRange(0.1, 10.0)
        self.wire_cross_section.setValue(0.5)
        self.wire_cross_section.setSingleStep(0.1)
        self.wire_cross_section.setSuffix(" mm²")
        props_layout.addRow("Cross Section:", self.wire_cross_section)
        
        # Part number (optional)
        self.wire_part_number = QLineEdit()
        self.wire_part_number.setPlaceholderText("Optional")
        props_layout.addRow("Part #:", self.wire_part_number)
        
        input_layout.addWidget(props_group)
        
        # Buttons
        btn_layout = QHBoxLayout()
        
        self.create_wire_btn = QPushButton("Create Wire")
        self.create_wire_btn.clicked.connect(self.create_new_wire)
        btn_layout.addWidget(self.create_wire_btn)
        
        self.cancel_wire_btn = QPushButton("Cancel")
        self.cancel_wire_btn.setObjectName("cancelBtn")
        self.cancel_wire_btn.clicked.connect(self.toggle_wire_input)
        btn_layout.addWidget(self.cancel_wire_btn)
        
        input_layout.addLayout(btn_layout)
    
    def toggle_wire_input(self):
        """Toggle the wire input container visibility"""
        self.wire_input_container.setVisible(not self.wire_input_container.isVisible())
        
        if self.wire_input_container.isVisible():
            self.update_connector_combo_boxes()
            self.add_wire_btn.setText("✖ Cancel")
        else:
            self.add_wire_btn.setText("➕ Add Wire")
    
    def update_connector_combo_boxes(self):
        """Update connector combo boxes with current connectors"""
        self.from_connector_combo.clear()
        self.to_connector_combo.clear()
        
        for conn in self.main_window.conns:
            if conn and conn.scene() == self.main_window.scene:
                display_text = f"{conn.model.id}"
                if hasattr(conn, 'part_number') and conn.part_number:
                    display_text += f" ({conn.part_number})"
                
                self.from_connector_combo.addItem(display_text, conn)
                self.to_connector_combo.addItem(display_text, conn)
    
    def update_from_pins(self):
        """Update from pin combo box based on selected connector"""
        self.from_pin_combo.clear()
        
        conn = self.from_connector_combo.currentData()
        if conn and hasattr(conn.model, 'pins'):
            for i,pin in conn.model.pins.items():
                # is_used = len(pin.wires) > 0
                display_text = str(pin.number)
                if hasattr(pin, 'original_id') and pin.original_id:
                    display_text = str(pin.original_id)
                
                if pin.is_used():
                    display_text += " (used)"
                
                self.from_pin_combo.addItem(display_text, pin)
    
    def update_to_pins(self):
        """Update to pin combo box based on selected connector"""
        self.to_pin_combo.clear()
        
        conn = self.to_connector_combo.currentData()
        if conn and hasattr(conn, 'pins'):
            for i,pin in conn.model.pins.items():
                # is_used = len(pin.wires) > 0
                display_text = str(pin.number)
                if hasattr(pin, 'original_id') and pin.original_id:
                    display_text = str(pin.original_id)
                
                if pin.is_used():
                    display_text += " (used)"
                
                self.to_pin_combo.addItem(display_text, pin)
    
    def update_color_preview(self, color_text):
        """Update color preview based on selected color"""
        color_map = {
            'SW': QColor(0, 0, 0), 'RT': QColor(255, 0, 0),
            'GN': QColor(0, 255, 0), 'BL': QColor(0, 0, 255),
            'GE': QColor(255, 255, 0), 'BR': QColor(165, 42, 42),
            'WS': QColor(255, 255, 255), 'GR': QColor(128, 128, 128),
            'VT': QColor(128, 0, 128), 'OR': QColor(255, 165, 0),
            'RS': QColor(255, 192, 203),
        }
        color = color_map.get(color_text, QColor(200, 200, 200))
        self.color_preview.setStyleSheet(f"background-color: {color.name()}; border: 1px solid gray;")
    
    def create_new_wire(self):
        """Create a new wire between selected connectors and pins"""
        from_conn = self.from_connector_combo.currentData()
        to_conn = self.to_connector_combo.currentData()
        from_pin = self.from_pin_combo.currentData()
        to_pin = self.to_pin_combo.currentData()
        from_pin_item = from_conn.get_pin_by_id(from_pin.pid)
        to_pin_item = to_conn.get_pin_by_id(to_pin.pid)
       
        if not from_conn or not to_conn or not from_pin or not to_pin:
            QMessageBox.warning(self, "Invalid Selection", 
                               "Please select both connectors and pins")
            return
        
        if from_conn == to_conn:
            QMessageBox.warning(self, "Invalid Selection", 
                               "From and To connectors cannot be the same")
            return
        
        wire_count = len(self.main_window.imported_wire_items) if hasattr(self.main_window, 'imported_wire_items') else 0
        wire_id = f"W{wire_count + 1}"
        
        signal_name = self.wire_signal.text() or f"Signal_{wire_id}"
        color = self.wire_color.currentText()
        cross_section = self.wire_cross_section.value()
        part_number = self.wire_part_number.text() or None
        
        wire_data = ImportedWire(
            wire_id=wire_id,
            part_number=part_number,
            cross_section=cross_section,
            color=color,
            from_node_id=from_conn.model.id,
            from_pin=from_pin.original_id if hasattr(from_pin, 'original_id') else from_pin.pid,
            to_node_id=to_conn.model.id,
            to_pin=to_pin.original_id if hasattr(to_pin, 'original_id') else to_pin.pid,
            signal_name=signal_name
        )
        
        netlist = Netlist()
        self.main_window.topology_manager.set_netlist(netlist)
        net = netlist.connect(from_pin.pid, to_pin.pid)
        
        wire = WireItem(wire_id, from_pin_item, to_pin_item, color, net)
        wire.wire_data = wire_data
        wire.net = net
        wire.signal_name = signal_name
        wire.cross_section = cross_section
        
        self.main_window.scene.addItem(wire)
        
        if not hasattr(self.main_window, 'imported_wire_items'):
            self.main_window.imported_wire_items = []
        self.main_window.imported_wire_items.append(wire)
        
        if not hasattr(self.main_window, 'imported_wires_data'):
            self.main_window.imported_wires_data = []
        self.main_window.imported_wires_data.append(wire_data)
        
        from commands.wire_commands import AddWireCommand
        cmd = AddWireCommand(self.main_window.scene, wire, from_pin_item, to_pin_item, main_window=self.main_window)
        self.main_window.undo_manager.push(cmd)
        

        from_conn.info_table.update_table()
        to_conn.info_table.update_table()
        
        self.main_window.refresh_tree_views()
        self.toggle_wire_input()
        self.main_window.statusBar().showMessage(f"Wire {wire_id} created successfully", 3000)
        
        if hasattr(self.main_window, 'bundles') and self.main_window.bundles:
            reply = QMessageBox.question(
                self,
                "Route Through Bundles",
                f"Wire created. Would you like to route it through existing bundles?",
                QMessageBox.Yes | QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                self.route_single_wire_through_bundles(wire, wire_data)
    
    def route_single_wire_through_bundles(self, wire_item, wire_data):
        """Route a single wire through existing bundles"""
        from utils.bundle_router import BundleRouter
        
        router = BundleRouter(self.main_window)
        wire_item.setVisible(False)
        
        wires = [wire_item]
        bundles = getattr(self.main_window, 'bundles', [])
        
        router._ensure_bundle_nodes(bundles)
        graph = router._build_bundle_graph(bundles)
        
        created_segments = []
        routed_wires = []
        
        success = router._route_single_wire(wire_item, bundles, graph, created_segments, routed_wires)
        
        if success and routed_wires:
            if not hasattr(self.main_window, 'routed_wire_items'):
                self.main_window.routed_wire_items = []
            self.main_window.routed_wire_items.extend(routed_wires)
            
            self.main_window.wires = [item.wire for item in self.main_window.routed_wire_items if hasattr(item, 'wire')]
            self.main_window.statusBar().showMessage(f"Wire routed through bundles", 3000)
            
            if hasattr(self.main_window, 'viz_manager'):
                self.main_window.viz_manager.update_visibility()
        else:
            wire_item.setVisible(True)
            QMessageBox.information(
                self,
                "No Bundle Path",
                "Could not find a bundle path connecting these connectors. Wire remains direct."
            )
    
    def on_tree_clicked(self, item):
        """Forward tree click to main window"""
        self.main_window.on_tree_clicked(item)
