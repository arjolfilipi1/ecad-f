#utils/excel_import.py
import pandas as pd
import numpy as np
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from uuid import uuid4
from PyQt5.QtCore import QPointF
from PyQt5.QtWidgets import QTreeWidgetItem
from PyQt5.QtCore import Qt

from graphics.connector_item import ConnectorItem
from graphics.wire_item import WireItem
from graphics.topology_item import (
    JunctionGraphicsItem, BranchPointGraphicsItem, FastenerGraphicsItem
)
from model.models import (
    Connector, Pin, Gender, SealType, ConnectorType,
    Wire, CombinedWireColor, WireType
)
from model.netlist import Netlist


@dataclass
class ImportedWire:
    """Wire data extracted from Excel"""
    wire_id: str
    part_number: str = ""
    cross_section: float = 0.5
    color: str = "SW"
    stripe_color: Optional[str] = None
    
    # From side
    from_node_id: str = ""
    from_pin: str = ""
    from_contact: str = ""
    from_seal: str = ""
    from_strip_length: float = 0.0
    from_tool: str = ""
    
    # To side
    to_node_id: str = ""
    to_pin: str = ""
    to_contact: str = ""
    to_seal: str = ""
    to_strip_length: float = 0.0
    to_tool: str = ""
    
    # Additional
    signal_name: str = ""
    length: float = 0.0
    bundle_id: Optional[str] = None


@dataclass
class ImportedConnector:
    """Connector data extracted from Excel"""
    device_name: str
    part_number: str = ""
    pin_count: int = 0
    pins: Dict[str, Dict] = field(default_factory=dict)
    position: Optional[str] = None
    x_pos: float = 100.0
    y_pos: float = 100.0


class ExcelHarnessImporter:
    """Import harness data from client Excel files"""
    
    # Column name mapping (adjust based on your actual Excel headers)
    COLUMN_MAPPING = {
        'Preass': 'preass',
        'Position': 'position',
        'Print_text': 'print_text',
        'Material': 'material',
        'Cross_section': 'cross_section',
        'Color': 'color',
        'From': 'from_node_id',
        'Pin_left': 'from_pin',
        'Contact_left': 'from_contact',
        'Seal_left': 'from_seal',
        'Strip_left': 'from_strip',
        'Adress_left': 'from_address',
        'Tool_left': 'from_tool',
        'To': 'to_node_id',
        'Pin_right': 'to_pin',
        'Contact_right': 'to_contact',
        'Seal_right': 'to_seal',
        'Strip_right': 'to_strip',
        'Tool_right': 'to_tool'
    }
    
    # Color code mapping (common automotive colors)
    COLOR_CODES = {
        'SW': (0, 0, 0),      # Black
        'RT': (255, 0, 0),    # Red
        'BL': (0, 0, 255),    # Blue
        'GN': (0, 255, 0),    # Green
        'GE': (255, 255, 0),  # Yellow
        'BR': (165, 42, 42),  # Brown
        'WS': (255, 255, 255), # White
        'GR': (128, 128, 128), # Gray
        'VT': (128, 0, 128),  # Violet
        'OR': (255, 165, 0),  # Orange
        'RS': (255, 192, 203), # Pink
        'TR': (0, 255, 255),  # Turquoise
    }
    
    def __init__(self, filepath: str, sheet_name: str = 0):
        self.filepath = filepath
        self.sheet_name = sheet_name
        self.df = None
        self.wires: List[ImportedWire] = []
        self.connectors: Dict[str, ImportedConnector] = {}
        self.errors: List[str] = []
        self.warnings: List[str] = []
        
        # Track created items for undo grouping
        self.created_connectors = []
        self.created_wires = []
        
    def load_excel(self) -> bool:
        """Load Excel file into pandas DataFrame"""
        try:
            # Try different engines based on file extension
            if self.filepath.endswith('.xlsx'):
                self.df = pd.read_excel(self.filepath, sheet_name=self.sheet_name, engine='openpyxl')
            elif self.filepath.endswith('.xls'):
                self.df = pd.read_excel(self.filepath, sheet_name=self.sheet_name, engine='xlrd')
            else:
                # Try CSV with semicolon separator
                self.df = pd.read_csv(self.filepath, sep=';')
            
            print(f"Loaded {len(self.df)} rows from {self.filepath}")
            return True
        except Exception as e:
            self.errors.append(f"Failed to load Excel: {str(e)}")
            return False
    
    def clean_dataframe(self):
        """Clean and prepare DataFrame"""
        if self.df is None:
            return
        
        # Strip whitespace from column names
        self.df.columns = [str(col).strip() for col in self.df.columns]
        
        # Drop completely empty rows
        self.df = self.df.dropna(how='all')
        
        # Forward fill certain columns if needed (commented out by default)
        # self.df['From'] = self.df['From'].fillna(method='ffill')
        
    def parse_cross_section(self, value) -> float:
        """Parse cross section value to float"""
        try:
            if pd.isna(value):
                return 0.5  # Default
            if isinstance(value, (int, float)):
                return float(value)
            # Handle strings like "0.5 mm²" or "0,5"
            value_str = str(value).replace(',', '.').strip()
            # Extract first number
            import re
            match = re.search(r'(\d+\.?\d*)', value_str)
            if match:
                return float(match.group(1))
            return 0.5
        except:
            return 0.5
    
    def parse_color(self, color_str) -> Tuple[str, Optional[str]]:
        """Parse color string into base color and stripe"""
        if pd.isna(color_str):
            return "SW", None
        
        color_str = str(color_str).strip().upper()
        
        # Check for stripe pattern: e.g., "RT/SW" or "RT-SW"
        if '/' in color_str or '-' in color_str:
            separator = '/' if '/' in color_str else '-'
            parts = color_str.split(separator)
            if len(parts) >= 2:
                return parts[0].strip(), parts[1].strip()
        
        return color_str, None
    
    def extract_wires(self) -> List[ImportedWire]:
        """Extract wire information from DataFrame"""
        if self.df is None:
            return []
        
        wires = []
        wire_counter = 1
        
        for idx, row in self.df.iterrows():
            try:
                # Skip rows that don't have essential wire data
                if pd.isna(row.get('From')) and pd.isna(row.get('To')):
                    continue
                
                # Parse color
                color_str = row.get('Color', 'SW')
                base_color, stripe = self.parse_color(color_str)
                
                # Parse cross section
                cross_section = self.parse_cross_section(row.get('Cross_section', 0.5))
                
                # Generate wire ID if not present
                wire_id = row.get('Position')
                if pd.isna(wire_id) or not wire_id:
                    wire_id = f"W{wire_counter:04d}"
                
                # Extract from side information
                from_node_id = str(row.get('From', '')).strip()
                from_pin = str(row.get('Pin_left', '')).strip()
                
                # Extract to side information
                to_node_id = str(row.get('To', '')).strip()
                to_pin = str(row.get('Pin_right', '')).strip()
                
                # Skip if missing critical information
                if not from_node_id or not to_node_id:
                    self.warnings.append(f"Row {idx}: Missing from/to device")
                    continue
                
                # Create wire object
                wire = ImportedWire(
                    wire_id=wire_id,
                    part_number=str(row.get('Material', '')).strip(),
                    cross_section=cross_section,
                    color=base_color,
                    stripe_color=stripe,
                    from_node_id=from_node_id,
                    from_pin=from_pin,
                    from_contact=str(row.get('Contact_left', '')).strip(),
                    from_seal=str(row.get('Seal_left', '')).strip(),
                    from_strip_length=self.parse_cross_section(row.get('Strip_left', 0)),
                    from_tool=str(row.get('Tool_left', '')).strip(),
                    to_node_id=to_node_id,
                    to_pin=to_pin,
                    to_contact=str(row.get('Contact_right', '')).strip() if 'Contact_right' in row else '',
                    to_seal=str(row.get('Seal_right', '')).strip() if 'Seal_right' in row else '',
                    to_strip_length=self.parse_cross_section(row.get('Strip_right', 0)),
                    to_tool=str(row.get('Tool_right', '')).strip() if 'Tool_right' in row else '',
                    signal_name=str(row.get('Print_text', '')).strip(),
                    length=0.0  # Will be calculated later
                )
                
                wires.append(wire)
                wire_counter += 1
                
            except Exception as e:
                self.errors.append(f"Row {idx}: Failed to parse - {str(e)}")
        
        self.wires = wires
        print(f"Extracted {len(wires)} wires")
        return wires
    
    def extract_connectors(self) -> Dict[str, ImportedConnector]:
        """Extract connector information from wires"""
        connectors = {}
        
        for wire in self.wires:
            # Process from side connector
            if wire.from_node_id:
                if wire.from_node_id not in connectors:
                    connectors[wire.from_node_id] = ImportedConnector(
                        device_name=wire.from_node_id,
                        part_number=self._find_part_number(wire.from_node_id),
                        pins={}
                    )
                
                # Add pin information
                if wire.from_pin:
                    if wire.from_pin not in connectors[wire.from_node_id].pins:
                        connectors[wire.from_node_id].pins[wire.from_pin] = {
                            'contact': wire.from_contact,
                            'seal': wire.from_seal,
                            'strip_length': wire.from_strip_length,
                            'tool': wire.from_tool,
                            'wire_id': wire.wire_id,
                            'color': wire.color,
                            'cross_section': wire.cross_section
                        }
            
            # Process to side connector
            if wire.to_node_id:
                if wire.to_node_id not in connectors:
                    connectors[wire.to_node_id] = ImportedConnector(
                        device_name=wire.to_node_id,
                        part_number=self._find_part_number(wire.to_node_id),
                        pins={}
                    )
                
                # Add pin information
                if wire.to_pin:
                    if wire.to_pin not in connectors[wire.to_node_id].pins:
                        connectors[wire.to_node_id].pins[wire.to_pin] = {
                            'contact': wire.to_contact,
                            'seal': wire.to_seal,
                            'strip_length': wire.to_strip_length,
                            'tool': wire.to_tool,
                            'wire_id': wire.wire_id,
                            'color': wire.color,
                            'cross_section': wire.cross_section
                        }
        
        # Update pin counts
        for connector in connectors.values():
            connector.pin_count = len(connector.pins)
            # Sort pins for consistent ordering
            connector.pins = dict(sorted(connector.pins.items()))
            
        self.connectors = connectors
        print(f"Extracted {len(connectors)} connectors")
        return connectors
    
    def _find_part_number(self, device_name: str) -> str:
        """Try to find part number for a device (override in subclass)"""
        # This would typically look up in a database
        # For now, return empty string
        return ""
    
    def generate_summary(self) -> Dict:
        """Generate import summary"""
        return {
            'total_wires': len(self.wires),
            'total_connectors': len(self.connectors),
            'unique_materials': len(set(w.part_number for w in self.wires if w.part_number)),
            'cross_sections': list(set(w.cross_section for w in self.wires)),
            'colors': list(set(w.color for w in self.wires)),
            'errors': self.errors,
            'warnings': self.warnings
        }


# ==================== INTEGRATION WITH MAIN WINDOW ====================

def import_from_excel_to_scene(filepath, main_window, auto_route=False):
    """
    Import Excel data into the scene with proper undo/redo support
    
    Args:
        filepath: Path to Excel file
        main_window: MainWindow instance
        auto_route: Whether to auto-route wires after import
    
    Returns:
        bool: Success status
    """
    from commands.base_command import CompoundCommand
    from commands.connector_commands import AddConnectorCommand
    from commands.wire_commands import AddWireCommand
    
    importer = ExcelHarnessImporter(filepath)
    
    # Load and parse Excel
    if not importer.load_excel():
        main_window.statusBar().showMessage(f"Import failed: {importer.errors[0] if importer.errors else 'Unknown error'}", 5000)
        return False
    
    importer.clean_dataframe()
    importer.extract_wires()
    importer.extract_connectors()
    
    # Store import data for later use
    main_window.imported_wires_data = importer.wires
    main_window.imported_connectors = importer.connectors
    
    # Start undo macro for entire import
    main_window.undo_manager.begin_macro(f"Import from {filepath}")
    
    x_pos, y_pos = 100, 100
    max_x = 100
    row_height = 150
    col_width = 200
    
    # Track created items
    created_connectors = []
    created_wires = []
    
    # 1. CREATE CONNECTOR MODELS AND GRAPHICS
    for device_name, conn_data in importer.connectors.items():
        # Get pin IDs and sort them
        pin_ids = list(conn_data.pins.keys())
        pin_ids.sort()
        
        # Create pin models
        pins_dict = {}
        for pin_id in pin_ids:
            pin = Pin(
                pid=f"{device_name}_{pin_id}",
                number=pin_id,
                gender=Gender.FEMALE,
                seal=SealType.UNSEALED
            )
            pins_dict[pin_id] = pin
        
        # Create connector model
        connector_model = Connector(
            id=device_name,
            name=device_name,
            type=ConnectorType.OTHER,
            gender=Gender.FEMALE,
            seal=SealType.UNSEALED,
            pins=pins_dict,
            position=(x_pos, y_pos),
            part_number=conn_data.part_number,
            manufacturer=""
        )
        
        # Add to harness
        main_window.wiringharness.add_connector(connector_model)
        
        # Create graphics item
        connector = ConnectorItem(connector_model)
        connector.set_topology_manager(main_window.topology_manager)
        connector.set_main_window(main_window)
        connector.create_topology_node()
        
        # Register with main window's graphics repository
        main_window.register_graphics_item(connector, 'connectors')
        
        # Create tree item
        item = QTreeWidgetItem([connector.model.id])
        item.setData(0, Qt.UserRole, connector)
        main_window.objects_dock.connectors_tree.addTopLevelItem(item)
        connector.tree_item = item
        
        # Add with undo (but command will handle the actual scene addition)
        from commands.connector_commands import AddConnectorCommand
        cmd = AddConnectorCommand(
            main_window.scene, 
            connector, 
            QPointF(x_pos, y_pos), 
            main_window=main_window
        )
        main_window.undo_manager.push(cmd)
        
        created_connectors.append(connector)
        
        # Update position for next connector
        x_pos += col_width
        if x_pos > 800:
            x_pos = 100
            y_pos += row_height
    
    # 2. CREATE WIRE MODELS AND GRAPHICS
    netlist = Netlist()
    main_window.topology_manager.set_netlist(netlist)
    
    for wd in importer.wires:
        # Find connector models
        from_conn_model = main_window.wiringharness.connectors.get(wd.from_node_id)
        to_conn_model = main_window.wiringharness.connectors.get(wd.to_node_id)
        
        if not from_conn_model or not to_conn_model:
            importer.warnings.append(f"Wire {wd.wire_id}: Could not find connectors {wd.from_node_id} or {wd.to_node_id}")
            continue
        
        # Find pin models
        from_pin_model = from_conn_model.pins.get(wd.from_pin)
        to_pin_model = to_conn_model.pins.get(wd.to_pin)
        
        if not from_pin_model or not to_pin_model:
            importer.warnings.append(f"Wire {wd.wire_id}: Could not find pins {wd.from_pin} or {wd.to_pin}")
            continue
        
        # Get graphics items from repository
        from_conn_graphics = main_window.get_graphics_item(from_conn_model.id, 'connectors')
        to_conn_graphics = main_window.get_graphics_item(to_conn_model.id, 'connectors')
        
        if not from_conn_graphics or not to_conn_graphics:
            importer.warnings.append(f"Wire {wd.wire_id}: Could not find connector graphics")
            continue
        
        from_pin_graphics = from_conn_graphics.get_pin_by_id(from_pin_model.pid)
        to_pin_graphics = to_conn_graphics.get_pin_by_id(to_pin_model.pid)
        
        if not from_pin_graphics or not to_pin_graphics:
            importer.warnings.append(f"Wire {wd.wire_id}: Could not find pin graphics")
            continue
        
        # Determine wire type based on cross section
        if wd.cross_section <= 0.35:
            wire_type = WireType.FLRY_B_0_35
        elif wd.cross_section <= 0.5:
            wire_type = WireType.FLRY_B_0_5
        elif wd.cross_section <= 0.75:
            wire_type = WireType.FLRY_B_0_75
        elif wd.cross_section <= 1.0:
            wire_type = WireType.FLRY_B_1_0
        elif wd.cross_section <= 1.5:
            wire_type = WireType.FLRY_B_1_5
        else:
            wire_type = WireType.FLRY_B_2_5
        
        # Create wire model
        wire_model = Wire(
            id=wd.wire_id,
            harness_id=main_window.wiringharness.id,
            type=wire_type,
            color=CombinedWireColor(wd.color, wd.stripe_color),
            from_node_id=wd.from_node_id,
            to_node_id=wd.to_node_id,
            from_pin=wd.from_pin,
            to_pin=wd.to_pin,
            signal_name=wd.signal_name,
            part_number=wd.part_number,
            cross_section=wd.cross_section
        )
        
        # Add to harness
        main_window.wiringharness.add_wire(wire_model)
        
        # Create net
        net = netlist.connect(from_pin_model.pid, to_pin_model.pid)
        
        # Create wire graphics
        wire = WireItem(wire_model)
        wire.main_window = (main_window)
        wire.connect_to_pins(from_pin_graphics, to_pin_graphics)
        wire.net = net
        
        # Register with main window's graphics repository
        main_window.register_graphics_item(wire, 'wires')
        
        # Create tree item
        item = QTreeWidgetItem([wire.wid])
        item.setData(0, Qt.UserRole, wire)
        main_window.objects_dock.wires_tab.wires_tree.addTopLevelItem(item)
        wire.tree_item = item
        
        # Add with undo
        from commands.wire_commands import AddWireCommand
        cmd = AddWireCommand(
            main_window.scene,
            wire,
            from_pin_graphics,
            to_pin_graphics,
            main_window=main_window
        )
        main_window.undo_manager.push(cmd)
        
        created_wires.append(wire)
        
        # Update pin models with wire reference
        if not from_pin_model.wire_ids:
            from_pin_model.wire_ids = []
        if isinstance(from_pin_model.wire_ids, list):
            from_pin_model.wire_ids.append(wire.wid)
        
        if not to_pin_model.wire_ids:
            to_pin_model.wire_ids = []
        if isinstance(to_pin_model.wire_ids, list):
            to_pin_model.wire_ids.append(wire.wid)
    
    # End undo macro
    main_window.undo_manager.end_macro()
    
    # Refresh views
    main_window.refresh_tree_views()
    main_window.refresh_connector_labels()
    
    # Print summary
    print(f"\n=== IMPORT COMPLETE ===")
    print(f"Connectors: {len(main_window.wiringharness.connectors)}")
    print(f"Wires: {len(main_window.wiringharness.wires)}")
    print(f"Warnings: {len(importer.warnings)}")
    print(f"Errors: {len(importer.errors)}")
    
    if importer.warnings:
        print("\nWarnings:")
        for w in importer.warnings[:5]:  # Show first 5
            print(f"  - {w}")
    
    if importer.errors:
        print("\nErrors:")
        for e in importer.errors:
            print(f"  - {e}")
    
    # Show status message
    main_window.statusBar().showMessage(
        f"Imported {len(created_connectors)} connectors, {len(created_wires)} wires", 
        5000
    )
    
    # Auto-route if requested
    if auto_route and created_wires:
        from utils.auto_route import HarnessAutoRouter
        router = HarnessAutoRouter(main_window.topology_manager, main_window)
        router.route_from_imported_data()
    
    return True


def import_from_excel_with_preview(filepath, main_window):
    """
    Import Excel data but show preview dialog first
    
    Args:
        filepath: Path to Excel file
        main_window: MainWindow instance
    
    Returns:
        bool: Success status
    """
    from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton, QTableWidget, QTableWidgetItem, QHeaderView, QTextEdit, QGroupBox
    
    importer = ExcelHarnessImporter(filepath)
    
    if not importer.load_excel():
        QMessageBox.critical(main_window, "Import Error", f"Failed to load file:\n{importer.errors[0] if importer.errors else 'Unknown error'}")
        return False
    
    importer.clean_dataframe()
    importer.extract_wires()
    importer.extract_connectors()
    summary = importer.generate_summary()
    
    # Create preview dialog
    dialog = QDialog(main_window)
    dialog.setWindowTitle("Import Preview")
    dialog.setMinimumSize(600, 500)
    
    layout = QVBoxLayout(dialog)
    
    # Summary
    summary_text = QTextEdit()
    summary_text.setReadOnly(True)
    summary_text.setMaximumHeight(150)
    
    summary_html = f"""
    <h3>Import Summary</h3>
    <table>
        <tr><td><b>Wires found:</b></td><td>{summary['total_wires']}</td></tr>
        <tr><td><b>Connectors found:</b></td><td>{summary['total_connectors']}</td></tr>
        <tr><td><b>Unique materials:</b></td><td>{summary['unique_materials']}</td></tr>
        <tr><td><b>Cross sections:</b></td><td>{', '.join(str(x) for x in summary['cross_sections'])}</td></tr>
    </table>
    """
    
    if summary['warnings']:
        summary_html += "<h4>Warnings:</h4><ul>"
        for w in summary['warnings'][:5]:
            summary_html += f"<li>{w}</li>"
        if len(summary['warnings']) > 5:
            summary_html += f"<li>... and {len(summary['warnings']) - 5} more</li>"
        summary_html += "</ul>"
    
    if summary['errors']:
        summary_html += "<h4>Errors:</h4><ul style='color: red;'>"
        for e in summary['errors']:
            summary_html += f"<li>{e}</li>"
        summary_html += "</ul>"
    
    summary_text.setHtml(summary_html)
    layout.addWidget(summary_text)
    
    # Connectors table
    conn_group = QGroupBox("Connectors to be created")
    conn_layout = QVBoxLayout(conn_group)
    
    conn_table = QTableWidget()
    conn_table.setColumnCount(3)
    conn_table.setHorizontalHeaderLabels(["Device Name", "Pin Count", "Part Number"])
    conn_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
    conn_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
    conn_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
    
    conn_table.setRowCount(len(importer.connectors))
    for i, (name, conn) in enumerate(importer.connectors.items()):
        conn_table.setItem(i, 0, QTableWidgetItem(name))
        conn_table.setItem(i, 1, QTableWidgetItem(str(conn.pin_count)))
        conn_table.setItem(i, 2, QTableWidgetItem(conn.part_number))
    
    conn_layout.addWidget(conn_table)
    layout.addWidget(conn_group)
    
    # Buttons
    btn_layout = QHBoxLayout()
    
    import_btn = QPushButton("Import")
    import_btn.clicked.connect(dialog.accept)
    btn_layout.addWidget(import_btn)
    
    cancel_btn = QPushButton("Cancel")
    cancel_btn.clicked.connect(dialog.reject)
    btn_layout.addWidget(cancel_btn)
    
    layout.addLayout(btn_layout)
    
    # Show dialog
    if dialog.exec_() == QDialog.Accepted:
        return import_from_excel_to_scene(filepath, main_window)
    
    return False
