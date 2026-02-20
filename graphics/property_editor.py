from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QFormLayout, QLineEdit, 
                             QComboBox, QSpinBox, QDoubleSpinBox, QCheckBox,
                             QGroupBox, QPushButton, QLabel, QScrollArea,
                             QTabWidget, QTextEdit,QHBoxLayout,QTableWidget,QHeaderView)
from PyQt5.QtCore import Qt, pyqtSignal,QPointF
from PyQt5.QtGui import QColor,QPainter
from model.models import Connector, Wire, Pin, CombinedWireColor
from model.models import ConnectorType, Gender, SealType, WireType
from PyQt5 import sip
class PropertyEditor(QWidget):
    """Dynamic property editor that adapts to selected item type"""
    
    property_changed = pyqtSignal(str, object)  # property_name, new_value
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.main_window = parent
        self.current_item = None
        self.current_type = None
        self.setup_ui()
        
    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Scroll area for properties
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        
        self.content = QWidget()
        self.content.setObjectName("properties")
        self.content_layout = QVBoxLayout(self.content)
        self.db_btn = None
        # No selection label
        self.no_selection = QLabel("No item selected")
        self.no_selection.setAlignment(Qt.AlignCenter)
        self.no_selection.setStyleSheet("color: gray; padding: 20px;")
        self.content_layout.addWidget(self.no_selection)
        
        scroll.setWidget(self.content)
        layout.addWidget(scroll)
    
    def set_item(self, item):
        """Set the item to edit"""
        self.current_item = item
        self.clear_content()
        
        if item is None:
            self.no_selection.show()
            return
        
        self.no_selection.hide()
        
        # Determine item type and create appropriate editor
        if hasattr(item, 'cid'):  # ConnectorItem
            self.current_type = 'connector'
            self.create_connector_editor(item)
        elif hasattr(item, 'wid'):  # WireItem
            self.current_type = 'wire'
            self.create_wire_editor(item)
        elif hasattr(item, 'branch_node'):  # BranchPoint
            self.current_type = 'branch'
            self.create_branch_editor(item)
        elif hasattr(item, 'segment'):  # Segment
            self.current_type = 'segment'
            self.create_segment_editor(item)
        elif hasattr(item, 'bundle_id'):  # BundleItem
            self.current_type = 'bundle'
            self.create_bundle_editor(item)

    
    def clear_content(self):
        """Clear all property widgets"""
        for i in reversed(range(self.content_layout.count())):
            widget = self.content_layout.itemAt(i).widget()
            if widget and widget is not self.no_selection:
                widget.deleteLater()
        if self.db_btn is not None and not sip.isdeleted(self.db_btn):
            self.db_btn.deleteLater()
        self.db_btn = None
    def add_property_row(self, layout, label, widget):
        """Helper to add a labeled row"""
        row = QWidget()
        row_layout = QFormLayout(row)
        row_layout.setContentsMargins(5, 2, 5, 2)
        row_layout.addRow(label, widget)
        self.content_layout.addWidget(row)
        return widget
    
    def create_connector_editor(self, connector_item):
        """Create editor for connector properties"""
        
        # Header
        header = QLabel(f"Connector: {connector_item.cid}")
        header.setStyleSheet("font-weight: bold; padding: 5px; background: #e0e0e0;")
        self.content_layout.addWidget(header)
        
        # Basic properties group
        basic_group = QGroupBox("Basic Properties")
        basic_layout = QFormLayout(basic_group)
        
        # ID (read-only)
        id_edit = QLineEdit(connector_item.cid)
        id_edit.setReadOnly(True)
        basic_layout.addRow("ID:", id_edit)
        
        # Name
        name_edit = QLineEdit(getattr(connector_item, 'name', ''))
        name_edit.textChanged.connect(lambda t: self.on_property_change('name', t))
        basic_layout.addRow("Name:", name_edit)
        
        # Part Number
        part_edit = QLineEdit(getattr(connector_item, 'part_number', ''))
        part_edit.textChanged.connect(lambda t: self.on_property_change('part_number', t))
        basic_layout.addRow("Part Number:", part_edit)
        
        # Manufacturer
        mfg_edit = QLineEdit(getattr(connector_item, 'manufacturer', ''))
        mfg_edit.textChanged.connect(lambda t: self.on_property_change('manufacturer', t))
        basic_layout.addRow("Manufacturer:", mfg_edit)
        
        self.content_layout.addWidget(basic_group)
        
        # Type properties group
        type_group = QGroupBox("Type Properties")
        type_layout = QFormLayout(type_group)
        
        # Connector Type
        type_combo = QComboBox()
        for ct in ConnectorType:
            type_combo.addItem(ct.value, ct)
        current_type = getattr(connector_item, 'connector_type', ConnectorType.OTHER)
        type_combo.setCurrentText(current_type.value if hasattr(current_type, 'value') else str(current_type))
        type_combo.currentIndexChanged.connect(lambda i: self.on_property_change('connector_type', type_combo.currentData()))
        type_layout.addRow("Type:", type_combo)
        
        # Gender
        gender_combo = QComboBox()
        for g in Gender:
            gender_combo.addItem(g.value, g)
        current_gender = getattr(connector_item, 'gender', Gender.FEMALE)
        gender_combo.setCurrentText(current_gender.value if hasattr(current_gender, 'value') else str(current_gender))
        gender_combo.currentIndexChanged.connect(lambda i: self.on_property_change('gender', gender_combo.currentData()))
        type_layout.addRow("Gender:", gender_combo)
        
        # Seal Type
        seal_combo = QComboBox()
        for s in SealType:
            seal_combo.addItem(s.value, s)
        current_seal = getattr(connector_item, 'seal', SealType.UNSEALED)
        seal_combo.setCurrentText(current_seal.value if hasattr(current_seal, 'value') else str(current_seal))
        seal_combo.currentIndexChanged.connect(lambda i: self.on_property_change('seal', seal_combo.currentData()))
        type_layout.addRow("Seal:", seal_combo)
        
        self.content_layout.addWidget(type_group)
        
        # Position group
        pos_group = QGroupBox("Position")
        pos_layout = QFormLayout(pos_group)
        
        # X position
        x_spin = QDoubleSpinBox()
        x_spin.setRange(-10000, 10000)
        x_spin.setValue(connector_item.pos().x())
        x_spin.valueChanged.connect(lambda v: self.on_position_change('x', v))
        pos_layout.addRow("X:", x_spin)
        
        # Y position
        y_spin = QDoubleSpinBox()
        y_spin.setRange(-10000, 10000)
        y_spin.setValue(connector_item.pos().y())
        y_spin.valueChanged.connect(lambda v: self.on_position_change('y', v))
        pos_layout.addRow("Y:", y_spin)
        
        # Rotation
        rot_spin = QSpinBox()
        rot_spin.setRange(0, 359)
        rot_spin.setValue(int(connector_item.rotation_angle))
        rot_spin.valueChanged.connect(lambda v: self.on_property_change('rotation', v))
        pos_layout.addRow("Rotation:", rot_spin)
        
        self.content_layout.addWidget(pos_group)
        
        # Pins group
        pins_group = QGroupBox(f"Pins ({len(connector_item.pins)})")
        pins_layout = QVBoxLayout(pins_group)
        
        for pin in connector_item.pins:
            pin_widget = self.create_pin_editor(pin)
            pins_layout.addWidget(pin_widget)
        
        self.content_layout.addWidget(pins_group)
        # Add database selection button
        db_layout = QHBoxLayout()
        self.db_btn = QPushButton("Select from Database")
        self.db_btn.clicked.connect(lambda: self.select_connector_from_db(connector_item))
        db_layout.addWidget(self.db_btn)
        # Add database management button
        db_mgmt_btn = QPushButton("📚 Manage Database")
        db_mgmt_btn.clicked.connect(self.launch_connector_manager)
        self.content_layout.addWidget(db_mgmt_btn)

        # Show current part if assigned
        if hasattr(connector_item, 'part_number') and connector_item.part_number:
            part_label = QLabel(f"Current: {connector_item.part_number}")
            part_label.setStyleSheet("color: green;")
            db_layout.addWidget(part_label)
        
        self.content_layout.addLayout(db_layout)
        
        # Add DXF preview if available
        if hasattr(connector_item, 'dxf_renderer') and connector_item.dxf_renderer:
            from graphics.dxf_cavity_renderer import DXFCavityRenderer
            preview_group = QGroupBox("Cavity Layout")
            preview_layout = QVBoxLayout(preview_group)
            
            # Create a graphics view for the renderer
            from PyQt5.QtWidgets import QGraphicsView, QGraphicsScene
            scene = QGraphicsScene()
            scene.addItem(connector_item.dxf_renderer)
            view = QGraphicsView(scene)
            view.setFixedHeight(200)
            view.setRenderHint(QPainter.Antialiasing)
            preview_layout.addWidget(view)
            
            self.content_layout.addWidget(preview_group)

        # Add stretch at end
        self.content_layout.addStretch()
    def launch_connector_manager(self):
        """Launch connector manager from property editor"""
        if self.main_window:
            self.main_window.launch_connector_manager()

    def create_pin_editor(self, pin):
        """Create editor for a single pin"""
        widget = QWidget()
        layout = QHBoxLayout(widget)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Pin ID
        id_label = QLabel(pin.pid)
        id_label.setMinimumWidth(60)
        layout.addWidget(id_label)
        
        # Wire ID (if connected)
        if pin.wires:
            wire_label = QLabel(f"→ {pin.wires[0].wid}")
            wire_label.setStyleSheet("color: green;")
            layout.addWidget(wire_label)
        else:
            empty_label = QLabel("(no wire)")
            empty_label.setStyleSheet("color: gray;")
            layout.addWidget(empty_label)
        
        layout.addStretch()
        
        return widget
    
    def create_wire_editor(self, wire_item):
        """Create editor for wire properties"""
        
        # Header
        header = QLabel(f"Wire: {wire_item.wid}")
        header.setStyleSheet("font-weight: bold; padding: 5px; background: #e0e0e0;")
        self.content_layout.addWidget(header)
        
        # Basic properties
        basic_group = QGroupBox("Wire Properties")
        basic_layout = QFormLayout(basic_group)
        
        # ID (read-only)
        id_edit = QLineEdit(wire_item.wid)
        id_edit.setReadOnly(True)
        basic_layout.addRow("ID:", id_edit)
        
        # Signal Name
        signal_edit = QLineEdit(getattr(wire_item, 'signal_name', ''))
        signal_edit.textChanged.connect(lambda t: self.on_property_change('signal_name', t))
        basic_layout.addRow("Signal:", signal_edit)
        
        # Wire Type
        type_combo = QComboBox()
        for wt in WireType:
            type_combo.addItem(wt.value, wt)
        type_combo.currentIndexChanged.connect(lambda i: self.on_property_change('wire_type', type_combo.currentData()))
        basic_layout.addRow("Type:", type_combo)
        
        # Cross Section
        cs_spin = QDoubleSpinBox()
        cs_spin.setRange(0.1, 10.0)
        cs_spin.setSingleStep(0.1)
        cs_spin.setValue(getattr(wire_item, 'cross_section', 0.5))
        cs_spin.valueChanged.connect(lambda v: self.on_property_change('cross_section', v))
        basic_layout.addRow("Cross Section (mm²):", cs_spin)
        
        # Color
        color_edit = QLineEdit(wire_item.color_data.code if hasattr(wire_item, 'color_data') else 'SW')
        color_edit.textChanged.connect(lambda t: self.on_property_change('color', t))
        basic_layout.addRow("Color:", color_edit)
        
        self.content_layout.addWidget(basic_group)
        
        # Connection info
        conn_group = QGroupBox("Connections")
        conn_layout = QFormLayout(conn_group)
        
        # From
        from_label = QLabel(f"{wire_item.start_pin.pid}")
        conn_layout.addRow("From:", from_label)
        
        # To
        to_label = QLabel(f"{wire_item.end_pin.pid}")
        conn_layout.addRow("To:", to_label)
        
        self.content_layout.addWidget(conn_group)
        
        # Length info
        length_group = QGroupBox("Length")
        length_layout = QFormLayout(length_group)
        
        # Calculated length
        calc_length = QDoubleSpinBox()
        calc_length.setRange(0, 100000)
        calc_length.setSuffix(" mm")
        calc_length.setValue(getattr(wire_item, 'calculated_length', 0))
        calc_length.valueChanged.connect(lambda v: self.on_property_change('calculated_length', v))
        length_layout.addRow("Length:", calc_length)
        
        self.content_layout.addWidget(length_group)
        
        self.content_layout.addStretch()
    
    def create_branch_editor(self, branch_item):
        """Create editor for branch point properties"""
        header = QLabel(f"Branch Point")
        header.setStyleSheet("font-weight: bold; padding: 5px; background: #e0e0e0;")
        self.content_layout.addWidget(header)
        
        # Basic properties
        basic_group = QGroupBox("Branch Properties")
        basic_layout = QFormLayout(basic_group)
        
        # Type
        type_edit = QLineEdit(branch_item.branch_node.branch_type)
        type_edit.setReadOnly(True)
        basic_layout.addRow("Type:", type_edit)
        
        # Position X
        x_spin = QDoubleSpinBox()
        x_spin.setRange(-10000, 10000)
        x_spin.setValue(branch_item.pos().x())
        x_spin.valueChanged.connect(lambda v: self.on_position_change('x', v))
        basic_layout.addRow("X:", x_spin)
        
        # Position Y
        y_spin = QDoubleSpinBox()
        y_spin.setRange(-10000, 10000)
        y_spin.setValue(branch_item.pos().y())
        y_spin.valueChanged.connect(lambda v: self.on_position_change('y', v))
        basic_layout.addRow("Y:", y_spin)
        
        self.content_layout.addWidget(basic_group)
        
        # Connected segments
        seg_group = QGroupBox("Connected Segments")
        seg_layout = QVBoxLayout(seg_group)
        
        for seg in branch_item.branch_node.connected_segments:
            label = QLabel(f"• {seg.id} ({len(seg.wires)} wires)")
            seg_layout.addWidget(label)
        
        self.content_layout.addWidget(seg_group)
        self.content_layout.addStretch()
    
    def create_segment_editor(self, segment_item):
        """Create editor for segment properties"""
        header = QLabel(f"Segment: {segment_item.segment.id}")
        header.setStyleSheet("font-weight: bold; padding: 5px; background: #e0e0e0;")
        self.content_layout.addWidget(header)
        
        # Basic info
        info_group = QGroupBox("Segment Info")
        info_layout = QFormLayout(info_group)
        
        # Wire count
        wire_count = QLabel(str(len(segment_item.segment.wires)))
        info_layout.addRow("Wires:", wire_count)
        
        # Length (calculated)
        length = QLabel(f"{segment_item.path().length():.1f} mm")
        info_layout.addRow("Length:", length)
        
        self.content_layout.addWidget(info_group)
        
        # Wires in this segment
        wires_group = QGroupBox(f"Wires ({len(segment_item.segment.wires)})")
        wires_layout = QVBoxLayout(wires_group)
        
        for wire in segment_item.segment.wires[:10]:  # Show first 10
            label = QLabel(f"• {wire.id} ({wire.color_data.code})")
            wires_layout.addWidget(label)
        
        if len(segment_item.segment.wires) > 10:
            more = QLabel(f"... and {len(segment_item.segment.wires) - 10} more")
            more.setStyleSheet("color: gray;")
            wires_layout.addWidget(more)
        
        self.content_layout.addWidget(wires_group)
        self.content_layout.addStretch()
    
    def on_property_change(self, property_name, value):
        """Handle property changes"""
        if self.current_item and self.main_window:
            # Store old value
            old_value = getattr(self.current_item, property_name, None)
            
            if old_value == value:
                return
            
            # Apply change immediately (for visual feedback)
            setattr(self.current_item, property_name, value)
            
            # Create undo command
            if hasattr(self.current_item, 'cid'):  # Connector
                from commands.connector_commands import UpdateConnectorPropertiesCommand
                cmd = UpdateConnectorPropertiesCommand(
                    self.current_item,
                    {property_name: old_value},
                    {property_name: value}
                )
            elif hasattr(self.current_item, 'wid'):  # Wire
                from commands.wire_commands import UpdateWirePropertiesCommand
                cmd = UpdateWirePropertiesCommand(
                    self.current_item,
                    {property_name: old_value},
                    {property_name: value}
                )
            else:
                return
            
            self.main_window.undo_manager.push(cmd)

    
    def on_position_change(self, coord, value):
        """Handle position changes"""
        if self.current_item and self.main_window:
            old_pos = self.current_item.pos()
            new_pos = QPointF(
                value if coord == 'x' else old_pos.x(),
                value if coord == 'y' else old_pos.y()
            )
            
            # Create move command
            from commands.connector_commands import MoveConnectorCommand
            cmd = MoveConnectorCommand(self.current_item, old_pos, new_pos)
            self.main_window.undo_manager.push(cmd)


    def select_connector_from_db(self, connector_item):
        """Open database selector and apply selected connector"""
        from dialogs.connector_selector import ConnectorSelectorDialog
        from database.connector_db import ConnectorDatabase
        
        db = ConnectorDatabase(main = self.main_window)
        dialog = ConnectorSelectorDialog(db, self)
        
        if dialog.exec_():
            selected = dialog.get_selected_connector()
            if selected:
                # Apply to connector item
                connector_item.part_number = selected.part_number
                connector_item.manufacturer = selected.manufacturer
                connector_item.connector_type = selected.series
                connector_item.gender = selected.gender
                connector_item.seal = selected.seal_type
                
                # Create DXF renderer
                if selected.dxf_path:
                    from graphics.dxf_cavity_renderer import DXFCavityRenderer
                    
                    # Build cavity data from wires
                    cavity_data = {}
                    for pin in connector_item.pins:
                        if pin.wires:
                            wire = pin.wires[0]
                            cavity_data[pin.original_id] = {
                                'wire_color': wire.color_data.code if hasattr(wire, 'color_data') else 'SW',
                                'wire_id': wire.wid if hasattr(wire, 'wid') else ''
                            }
                    
                    connector_item.dxf_renderer = DXFCavityRenderer(
                        selected.dxf_path,
                        cavity_data
                    )
                    connector_item.dxf_renderer.setPos(0, 0)
                
                # Refresh property editor
                self.set_item(connector_item)
                
                # Update connector info label
                if hasattr(connector_item, 'info'):
                    connector_item.info.update_text()
    def create_bundle_editor(self, bundle_item):
        """Create editor for bundle properties"""
        
        # Header
        header = QLabel(f"Bundle: {bundle_item.bundle_id}")
        header.setStyleSheet("font-weight: bold; padding: 5px; background: #e0e0e0;")
        self.content_layout.addWidget(header)
        
        # Basic properties group
        basic_group = QGroupBox("Basic Properties")
        basic_layout = QFormLayout(basic_group)
        
        # Bundle ID (read-only)
        id_edit = QLineEdit(bundle_item.bundle_id)
        id_edit.setReadOnly(True)
        basic_layout.addRow("ID:", id_edit)
        
        # Bundle Name
        name_edit = QLineEdit(getattr(bundle_item, 'name', bundle_item.bundle_id))
        name_edit.textChanged.connect(lambda t: self.on_bundle_property_change('name', t))
        basic_layout.addRow("Name:", name_edit)
        
        self.content_layout.addWidget(basic_group)
        
        # Length group
        length_group = QGroupBox("Length")
        length_layout = QFormLayout(length_group)
        
        # Actual length (read-only)
        self.bundle_actual_length = QDoubleSpinBox()
        self.bundle_actual_length.setRange(0, 100000)
        self.bundle_actual_length.setSuffix(" units")
        self.bundle_actual_length.setValue(bundle_item.length)
        self.bundle_actual_length.setReadOnly(True)
        self.bundle_actual_length.setButtonSymbols(QDoubleSpinBox.NoButtons)
        length_layout.addRow("Actual:", self.bundle_actual_length)
        
        # Specified length (editable)
        self.bundle_specified_length = QDoubleSpinBox()
        self.bundle_specified_length.setRange(0, 100000)
        self.bundle_specified_length.setSuffix(" mm")
        current_length = bundle_item.specified_length if bundle_item.specified_length is not None else bundle_item.length
        self.bundle_specified_length.setValue(current_length)
        self.bundle_specified_length.valueChanged.connect(self.on_bundle_length_changed)
        length_layout.addRow("Specified:", self.bundle_specified_length)
        
        self.content_layout.addWidget(length_group)
        
        # Nodes group
        nodes_group = QGroupBox("Nodes")
        nodes_layout = QFormLayout(nodes_group)
        
        # Start node
        start_node_text = "None"
        if bundle_item.start_node:
            start_node_text = bundle_item.start_node.id[:16] + "..."
        self.bundle_start_node = QLabel(start_node_text)
        nodes_layout.addRow("Start Node:", self.bundle_start_node)
        
        # End node
        end_node_text = "None"
        if bundle_item.end_node:
            end_node_text = bundle_item.end_node.id[:16] + "..."
        self.bundle_end_node = QLabel(end_node_text)
        nodes_layout.addRow("End Node:", self.bundle_end_node)
        
        # Start item type
        start_type = "None"
        if bundle_item.start_node:
            if hasattr(bundle_item.start_node, 'cid'):
                start_type = "Connector"
            elif hasattr(bundle_item.start_node, 'branch_node'):
                start_type = "Branch Point"
            elif hasattr(bundle_item.start_node, 'junction_node'):
                start_type = "Junction"
            elif hasattr(bundle_item.start_node, 'fastener_node'):
                start_type = "Fastener"
        self.bundle_start_type = QLabel(start_type)
        nodes_layout.addRow("Start Type:", self.bundle_start_type)
        
        # End item type
        end_type = "None"
        if bundle_item.end_node:
            if hasattr(bundle_item.end_node, 'cid'):
                end_type = "Connector"
            elif hasattr(bundle_item.end_node, 'branch_node'):
                end_type = "Branch Point"
            elif hasattr(bundle_item.end_node, 'junction_node'):
                end_type = "Junction"
            elif hasattr(bundle_item.end_node, 'fastener_node'):
                end_type = "Fastener"
        self.bundle_end_type = QLabel(end_type)
        nodes_layout.addRow("End Type:", self.bundle_end_type)
        
        self.content_layout.addWidget(nodes_group)
        
        # Wires group
        wires_group = QGroupBox(f"Wires in Bundle ({bundle_item.wire_count})")
        wires_layout = QVBoxLayout(wires_group)
        
        # Wire count with color indicator
        wire_count_label = QLabel(f"<b>{bundle_item.wire_count}</b> wires assigned")
        if bundle_item.wire_count > 0:
            wire_count_label.setStyleSheet("color: green;")
        else:
            wire_count_label.setStyleSheet("color: gray;")
        wires_layout.addWidget(wire_count_label)
        
        # Wire table
        self.bundle_wire_table = QTableWidget()
        self.bundle_wire_table.setColumnCount(4)
        self.bundle_wire_table.setHorizontalHeaderLabels(["Wire ID", "Color", "Signal", "From→To"])
        self.bundle_wire_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        self.bundle_wire_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.bundle_wire_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        self.bundle_wire_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.bundle_wire_table.setMaximumHeight(200)
        
        # Populate wire table
        self.bundle_wire_table.setRowCount(bundle_item.wire_count)
        
        for i, wire_id in enumerate(bundle_item.wire_ids):
            # Wire ID
            self.bundle_wire_table.setItem(i, 0, QTableWidgetItem(wire_id))
            
            # Look up wire details
            color_text = "?"
            from_to_text = ""
            
            if hasattr(self.main_window, 'imported_wire_items'):
                for wire in self.main_window.imported_wire_items:
                    if wire.wid == wire_id:
                        if hasattr(wire, 'color_data'):
                            color_text = wire.color_data.code
                        
                        # Get from→to info
                        from_pin = f"{wire.start_pin.parent.cid}:{wire.start_pin.original_id}"
                        to_pin = f"{wire.end_pin.parent.cid}:{wire.end_pin.original_id}"
                        from_to_text = f"{from_pin} → {to_pin}"
                        break
            
            # Color
            color_item = QTableWidgetItem(color_text)
            if color_text != "?":
                color_map = {
                    'SW': QColor(0, 0, 0),
                    'RT': QColor(255, 0, 0),
                    'GN': QColor(0, 255, 0),
                    'BL': QColor(0, 0, 255),
                    'GE': QColor(255, 255, 0),
                    'BR': QColor(165, 42, 42),
                    'WS': QColor(255, 255, 255),
                    'GR': QColor(128, 128, 128),
                }
                bg_color = color_map.get(color_text, QColor(200, 200, 200))
                color_item.setBackground(bg_color)
                if color_text in ['SW', 'BR', 'BL']:
                    color_item.setForeground(Qt.white)
            self.bundle_wire_table.setItem(i, 1, color_item)
            
            # Signal
            signal_item = QTableWidgetItem("")  # Add signal lookup if available
            self.bundle_wire_table.setItem(i, 2, signal_item)
            
            # From→To
            self.bundle_wire_table.setItem(i, 3, QTableWidgetItem(from_to_text))
        
        wires_layout.addWidget(self.bundle_wire_table)
        
        # Add assign/unassign buttons
        actions_group = QGroupBox("Actions")
        actions_layout = QHBoxLayout(actions_group)
        
        assign_btn = QPushButton("📎 Add Wires")
        assign_btn.clicked.connect(lambda: self.show_wire_assignment_dialog(bundle_item))
        actions_layout.addWidget(assign_btn)
        
        clear_btn = QPushButton("🗑️ Clear All")
        clear_btn.clicked.connect(lambda: self.clear_bundle_wires(bundle_item))
        actions_layout.addWidget(clear_btn)
        
        wires_layout.addLayout(actions_layout)
        
        self.content_layout.addWidget(wires_group)
        
        
        
        self.highlight_btn = QPushButton("🔍 Highlight")
        self.highlight_btn.clicked.connect(self.on_highlight_bundle)
        actions_layout.addWidget(self.highlight_btn)
        
        self.delete_bundle_btn = QPushButton("🗑️ Delete")
        self.delete_bundle_btn.clicked.connect(self.on_delete_bundle)
        actions_layout.addWidget(self.delete_bundle_btn)
        
        self.content_layout.addWidget(actions_group)
        
        # Add stretch at end
        self.content_layout.addStretch()
    
    def on_bundle_length_changed(self, value):
        """Handle bundle length change"""
        if not self.current_item or self.current_type != 'bundle':
            return
        
        old_length = self.current_item.specified_length
        if old_length == value:
            return
        
        # Create undo command
        from commands.bundle_commands import UpdateBundleLengthCommand
        cmd = UpdateBundleLengthCommand(self.current_item, old_length, value)
        self.main_window.undo_manager.push(cmd)
    
    def on_bundle_property_change(self, property_name, value):
        """Handle bundle property changes"""
        if not self.current_item or self.current_type != 'bundle':
            return
        
        old_value = getattr(self.current_item, property_name, None)
        if old_value == value:
            return
        
        # Apply change immediately
        setattr(self.current_item, property_name, value)
        
        # Create undo command
        from commands.bundle_commands import UpdateBundlePropertiesCommand
        cmd = UpdateBundlePropertiesCommand(
            self.current_item,
            {property_name: old_value},
            {property_name: value}
        )
        self.main_window.undo_manager.push(cmd)
        
        # Update tree item if exists
        if hasattr(self.current_item, 'tree_item') and self.current_item.tree_item:
            display_text = value if property_name == 'name' else self.current_item.tree_item.text(0)
            if property_name == 'specified_length':
                display_text = f"{self.current_item.bundle_id}"
                if value:
                    display_text += f" ({value:.0f} mm)"
                elif self.current_item.length:
                    display_text += f" ({self.current_item.length:.0f} units)"
            self.current_item.tree_item.setText(0, display_text)
    
    def on_assign_wires_to_bundle(self):
        """Open wire assignment dialog for bundle"""
        if not self.current_item or self.current_type != 'bundle':
            return
        
        # This would open a dialog to select wires for this bundle
        from PyQt5.QtWidgets import QMessageBox
        QMessageBox.information(
            self,
            "Wire Assignment",
            f"Wire assignment for {self.current_item.bundle_id} - coming soon"
        )
        self.main_window.statusBar().showMessage(
            f"Wire assignment for {self.current_item.bundle_id} - coming soon", 2000
        )
    
    def on_highlight_bundle(self):
        """Highlight the bundle in scene"""
        if self.current_item is None or self.current_type != 'bundle':
            return
        
        # Clear other selections
        for item in self.main_window.scene.selectedItems():
            item.setSelected(False)
        if self.current_item is not None:
            self.current_item.setSelected(True)
            self.main_window.view.centerOn(self.current_item)
    
    def on_delete_bundle(self):
        """Delete the current bundle"""
        if not self.current_item or self.current_type != 'bundle':
            return
        
        from PyQt5.QtWidgets import QMessageBox
        reply = QMessageBox.question(
            self,
            "Delete Bundle",
            f"Are you sure you want to delete bundle {self.current_item.bundle_id}?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            from commands.bundle_commands import DeleteBundleCommand
            cmd = DeleteBundleCommand(
                self.main_window.scene,
                self.current_item,
                self.main_window
            )
            self.main_window.undo_manager.push(cmd)
