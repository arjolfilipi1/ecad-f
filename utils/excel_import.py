#utils/excel_import
import pandas as pd
import numpy as np
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from uuid import uuid4
from graphics.topology_item import (
    JunctionGraphicsItem, BranchPointGraphicsItem
)
from graphics.connector_item import ConnectorItem
from graphics.segment_item import SegmentGraphicsItem
@dataclass
class ImportedWire:
    """Wire data extracted from Excel"""
    wire_id: str
    part_number: str = ""
    cross_section: float = 0.5
    color: str = "BLK"
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
        'Pin_right': 'to_pin'
        # Add more columns as needed
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
        
    def load_excel(self) -> bool:
        """Load Excel file into pandas DataFrame"""
        try:
            # Try different engines based on file extension
            if self.filepath.endswith('.xlsx'):
                self.df = pd.read_excel(self.filepath, sheet_name=self.sheet_name, engine='openpyxl')
            elif self.filepath.endswith('.xls'):
                self.df = pd.read_excel(self.filepath, sheet_name=self.sheet_name, engine='xlrd')
            else:
                # Try CSV
                self.df = pd.read_csv(self.filepath, sep=';')
            
            #print(f"Loaded {len(self.df)} rows from {self.filepath}")
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
        
        # Forward fill certain columns if needed
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
            return "BLK", None
        
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
        #print(f"Extracted {len(wires)} wires")
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

            connector.pin_count = list(connector.pins.keys())
            
        self.connectors = connectors
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
    
    def to_e3_format(self) -> Dict:
        """Convert to format compatible with your E3-like system"""
        return {
            'wires': [
                {
                    'id': w.wire_id,
                    'name': f"{w.from_node_id}_{w.from_pin}_to_{w.to_node_id}_{w.to_pin}",
                    'signal_name': w.signal_name,
                    'cross_section': w.cross_section,
                    'color': w.color,
                    'stripe_color': w.stripe_color,
                    'from_connection': f"{w.from_node_id}:{w.from_pin}",
                    'to_connection': f"{w.to_node_id}:{w.to_pin}",
                    'part_number': w.part_number,
                }
                for w in self.wires
            ],
            'connectors': [
                {
                    'name': name,
                    'part_number': conn.part_number,
                    'pin_count': conn.pin_count,
                    'pins': [
                        {
                            'number': pin_num,
                            'wire_id': info['wire_id'],
                            'color': info['color'],
                            'cross_section': info['cross_section']
                        }
                        for pin_num, info in conn.pins.items()
                    ]
                }
                for name, conn in self.connectors.items()
            ]
        }

# ==================== INTEGRATION WITH YOUR SYSTEM ====================

def import_from_excel_to_topology(filepath, topology_manager, main_window, auto_route=False):
    """
    Import Excel data into topology system
    """
    importer = ExcelHarnessImporter(filepath)
    if not importer.load_excel():
        return False
    
    importer.clean_dataframe()
    wires_data = importer.extract_wires()
    connectors_data = importer.extract_connectors()
    
    # Store import data for later routing
    main_window.imported_wires_data = wires_data
    main_window.imported_connectors = connectors_data
    
    x_pos, y_pos = 100, 100
    
    # 1. CREATE CONNECTOR MODELS AND GRAPHICS
    for device_name, conn_data in connectors_data.items():
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
            position=(x_pos, y_pos)
        )
        
        # Add to harness
        main_window.wiringharness.add_connector(connector_model)
        
        # Create graphics item
        connector = ConnectorItem(connector_model)
        connector.set_topology_manager(topology_manager)
        connector.set_main_window(main_window)
        connector.create_topology_node()
        
        main_window.scene.addItem(connector)
        
        x_pos += 200
        if x_pos > 800:
            x_pos = 100
            y_pos += 200
    
    # 2. CREATE WIRE MODELS AND GRAPHICS
    from model.netlist import Netlist
    
    netlist = Netlist()
    topology_manager.set_netlist(netlist)
    
    for wd in wires_data:
        # Find connector models
        from_conn_model = main_window.wiringharness.connectors.get(wd.from_node_id)
        to_conn_model = main_window.wiringharness.connectors.get(wd.to_node_id)
        
        if not from_conn_model or not to_conn_model:
            continue
        
        # Find pin models
        from_pin_model = from_conn_model.pins.get(wd.from_pin)
        to_pin_model = to_conn_model.pins.get(wd.to_pin)
        
        if not from_pin_model or not to_pin_model:
            continue
        
        # Get graphics items
        from_conn_graphics = from_conn_model.graphics_item
        to_conn_graphics = to_conn_model.graphics_item
        
        if not from_conn_graphics or not to_conn_graphics:
            continue
        
        from_pin_graphics = from_conn_graphics.get_pin_by_id(from_pin_model.pid)
        to_pin_graphics = to_conn_graphics.get_pin_by_id(to_pin_model.pid)
        
        # Determine wire type
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
        wire.connect_to_pins(from_pin_graphics, to_pin_graphics)
        wire.net = net
        
        main_window.scene.addItem(wire)
    
    print(f"\n=== IMPORT COMPLETE ===")
    print(f"Connectors: {len(main_window.wiringharness.connectors)}")
    print(f"Wires: {len(main_window.wiringharness.wires)}")
    
    return True



