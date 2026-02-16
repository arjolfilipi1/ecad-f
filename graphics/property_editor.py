from PyQt5.QtWidgets import (QWidget, QVBoxLayout, QFormLayout, QLineEdit, 
                             QComboBox, QSpinBox, QDoubleSpinBox, QCheckBox,
                             QGroupBox, QPushButton, QLabel, QScrollArea,
                             QTabWidget, QTextEdit,QHBoxLayout)
from PyQt5.QtCore import Qt, pyqtSignal
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
        if self.current_item:
            # Store the new value in the item
            setattr(self.current_item, property_name, value)
            # Emit signal for undo/redo
            self.property_changed.emit(property_name, value)
    
    def on_position_change(self, coord, value):
        """Handle position changes"""
        if self.current_item:
            pos = self.current_item.pos()
            if coord == 'x':
                self.current_item.setPos(value, pos.y())
            else:
                self.current_item.setPos(pos.x(), value)
            self.property_changed.emit(f'pos_{coord}', value)

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
