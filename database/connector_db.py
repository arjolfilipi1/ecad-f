import sqlite3
import json
import ezdxf
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple, Any
from enum import Enum
import uuid

class ConnectorGender(Enum):
    MALE = "male"
    FEMALE = "female"

class SealType(Enum):
    UNSEALED = "unsealed"
    CONNECTOR_SEALED = "connector_sealed"
    FULLY_SEALED = "fully_sealed"

@dataclass
class Cavity:
    """Represents a single cavity in a connector"""
    number: str  # e.g., "1", "A1", "2B"
    position_x: float  # DXF coordinate
    position_y: float  # DXF coordinate
    terminal_type: Optional[str] = None  # e.g., "0.5mm", "1.5mm", "2.8mm"
    seal_required: bool = False
    min_wire_gauge: float = 0.35  # mm²
    max_wire_gauge: float = 2.5  # mm²
    color_suggestions: List[str] = field(default_factory=list)  # e.g., ["RT", "SW"]
    
    def to_dict(self) -> dict:
        return {
            'number': self.number,
            'position_x': self.position_x,
            'position_y': self.position_y,
            'terminal_type': self.terminal_type,
            'seal_required': self.seal_required,
            'min_wire_gauge': self.min_wire_gauge,
            'max_wire_gauge': self.max_wire_gauge,
            'color_suggestions': self.color_suggestions
        }

@dataclass
class ConnectorPart:
    """Complete connector definition"""
    part_number: str
    manufacturer: str
    series: str
    description: str
    gender: ConnectorGender
    seal_type: SealType
    cavity_count: int
    cavities: Dict[str, Cavity]  # keyed by cavity number
    dxf_path: Optional[Path] = None
    housing_color: Optional[str] = None
    datasheet_url: Optional[str] = None
    notes: Optional[str] = None
    
    def to_dict(self) -> dict:
        return {
            'part_number': self.part_number,
            'manufacturer': self.manufacturer,
            'series': self.series,
            'description': self.description,
            'gender': self.gender.value,
            'seal_type': self.seal_type.value,
            'cavity_count': self.cavity_count,
            'cavities': {k: v.to_dict() for k, v in self.cavities.items()},
            'dxf_path': str(self.dxf_path) if self.dxf_path else None,
            'housing_color': self.housing_color,
            'datasheet_url': self.datasheet_url,
            'notes': self.notes
        }
from utils.settings_manager import SettingsManager

class ConnectorDatabase:
    """SQLite database for connector parts"""
    
    def __init__(self, db_path: str = None, dxf_dir: str = "dxf_library",main = None):
        self.main_window = main
        self.db_path = db_path if db_path else self.main_window.settings_manager.settings.database_path+"connectors.db"
        # self.db_path = db_path if db_path else SettingsManager.settings.database_path 
        self.dxf_dir = Path(dxf_dir)
        self.dxf_dir.mkdir(exist_ok=True)
        self._init_database()
    
    def _init_database(self):
        """Create tables if they don't exist"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Main connectors table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS connectors (
                part_number TEXT PRIMARY KEY,
                manufacturer TEXT NOT NULL,
                series TEXT NOT NULL,
                description TEXT,
                gender TEXT NOT NULL,
                seal_type TEXT NOT NULL,
                cavity_count INTEGER NOT NULL,
                dxf_file TEXT,
                housing_color TEXT,
                datasheet_url TEXT,
                notes TEXT,
                created_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                modified_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        
        # Cavities table (one row per cavity)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS cavities (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                part_number TEXT NOT NULL,
                cavity_number TEXT NOT NULL,
                position_x REAL NOT NULL,
                position_y REAL NOT NULL,
                terminal_type TEXT,
                seal_required INTEGER DEFAULT 0,
                min_wire_gauge REAL DEFAULT 0.35,
                max_wire_gauge REAL DEFAULT 2.5,
                color_suggestions TEXT,  -- JSON array
                FOREIGN KEY (part_number) REFERENCES connectors(part_number),
                UNIQUE(part_number, cavity_number)
            )
        ''')
        
        # Manufacturers table for dropdowns
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS manufacturers (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT UNIQUE NOT NULL
            )
        ''')
        
        # Series table for dropdowns
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS series (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                manufacturer TEXT NOT NULL,
                name TEXT NOT NULL,
                UNIQUE(manufacturer, name)
            )
        ''')
        
        # Insert some default manufacturers
        default_manuf = ['TE', 'Molex', 'Yazaki', 'Aptiv', 'JAE', 'Hirose', 'Amphenol']
        for m in default_manuf:
            cursor.execute('INSERT OR IGNORE INTO manufacturers (name) VALUES (?)', (m,))
        
        conn.commit()
        conn.close()
    
    def add_connector(self, connector: ConnectorPart, dxf_content: Optional[bytes] = None):
        """Add a new connector to the database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Save DXF file if provided
        dxf_filename = None
        if dxf_content:
            dxf_filename = f"{connector.manufacturer}_{connector.part_number}_back.dxf"
            dxf_path = self.dxf_dir / dxf_filename
            with open(dxf_path, 'wb') as f:
                f.write(dxf_content)
        
        # Insert connector
        cursor.execute('''
            INSERT OR REPLACE INTO connectors (
                part_number, manufacturer, series, description, gender,
                seal_type, cavity_count, dxf_file, housing_color,
                datasheet_url, notes, modified_date
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
        ''', (
            connector.part_number, connector.manufacturer, connector.series,
            connector.description, connector.gender.value, connector.seal_type.value,
            connector.cavity_count, dxf_filename, connector.housing_color,
            connector.datasheet_url, connector.notes
        ))
        
        # Insert cavities
        for cavity in connector.cavities.values():
            color_json = json.dumps(cavity.color_suggestions)
            cursor.execute('''
                INSERT OR REPLACE INTO cavities (
                    part_number, cavity_number, position_x, position_y,
                    terminal_type, seal_required, min_wire_gauge, max_wire_gauge,
                    color_suggestions
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                connector.part_number, cavity.number, cavity.position_x, cavity.position_y,
                cavity.terminal_type, 1 if cavity.seal_required else 0,
                cavity.min_wire_gauge, cavity.max_wire_gauge, color_json
            ))
        
        # Ensure manufacturer and series exist in lookup tables
        cursor.execute('INSERT OR IGNORE INTO manufacturers (name) VALUES (?)', 
                      (connector.manufacturer,))
        cursor.execute('INSERT OR IGNORE INTO series (manufacturer, name) VALUES (?, ?)',
                      (connector.manufacturer, connector.series))
        
        conn.commit()
        conn.close()
    
    def get_connector(self, part_number: str) -> Optional[ConnectorPart]:
        """Retrieve a connector by part number"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get connector data
        cursor.execute('''
            SELECT part_number, manufacturer, series, description, gender,
                   seal_type, cavity_count, dxf_file, housing_color,
                   datasheet_url, notes
            FROM connectors WHERE part_number = ?
        ''', (part_number,))
        
        row = cursor.fetchone()
        if not row:
            conn.close()
            return None
        
        # Parse connector data
        connector = ConnectorPart(
            part_number=row[0],
            manufacturer=row[1],
            series=row[2],
            description=row[3],
            gender=ConnectorGender(row[4]),
            seal_type=SealType(row[5]),
            cavity_count=row[6],
            cavities={},
            dxf_path=self.dxf_dir / row[7] if row[7] else None,
            housing_color=row[8],
            datasheet_url=row[9],
            notes=row[10]
        )
        
        # Get cavities
        cursor.execute('''
            SELECT cavity_number, position_x, position_y, terminal_type,
                   seal_required, min_wire_gauge, max_wire_gauge, color_suggestions
            FROM cavities WHERE part_number = ?
        ''', (part_number,))
        
        for c_row in cursor.fetchall():
            color_suggestions = json.loads(c_row[7]) if c_row[7] else []
            cavity = Cavity(
                number=c_row[0],
                position_x=c_row[1],
                position_y=c_row[2],
                terminal_type=c_row[3],
                seal_required=bool(c_row[4]),
                min_wire_gauge=c_row[5],
                max_wire_gauge=c_row[6],
                color_suggestions=color_suggestions
            )
            connector.cavities[c_row[0]] = cavity
        
        conn.close()
        return connector
    
    def search_connectors(self, manufacturer: str = None, series: str = None,
                          part_number_contains: str = None,
                          min_cavities: int = None, max_cavities: int = None,all_cons = False) -> List[dict]:
        """Search for connectors with filters"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        query = "SELECT part_number, manufacturer, series, description, cavity_count FROM connectors WHERE 1=1"
        params = []
        
        if manufacturer:
            query += " AND manufacturer = ?"
            params.append(manufacturer)
        
        if series:
            query += " AND series = ?"
            params.append(series)
        
        if part_number_contains:
            query += " AND part_number LIKE ?"
            params.append(f"%{part_number_contains}%")
        
        if min_cavities is not None:
            query += " AND cavity_count >= ?"
            params.append(min_cavities)
        
        if max_cavities is not None:
            query += " AND cavity_count <= ?"
            params.append(max_cavities)
        
        query += " ORDER BY manufacturer, series, part_number"
        if all_cons == False:
            cursor.execute(query, params)
        else:
            cursor.execute("SELECT part_number, manufacturer, series, description, cavity_count FROM connectors")

            
        results = []
        for row in cursor.fetchall():
            results.append({
                'part_number': row[0],
                'manufacturer': row[1],
                'series': row[2],
                'description': row[3],
                'cavity_count': row[4]
            })
        
        conn.close()
        return results
    
    def get_manufacturers(self) -> List[str]:
        """Get list of all manufacturers"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT name FROM manufacturers ORDER BY name")
        results = [row[0] for row in cursor.fetchall()]
        conn.close()
        return results
    
    def get_series(self, manufacturer: str = None) -> List[str]:
        """Get list of series, optionally filtered by manufacturer"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        if manufacturer:
            cursor.execute("SELECT name FROM series WHERE manufacturer = ? ORDER BY name", 
                          (manufacturer,))
        else:
            cursor.execute("SELECT name FROM series ORDER BY name")
        
        results = [row[0] for row in cursor.fetchall()]
        conn.close()
        return results
    
    def import_from_dxf(self, dxf_path: Path, part_number: str, manufacturer: str,
                        series: str, description: str, gender: ConnectorGender,
                        seal_type: SealType) -> ConnectorPart:
        """
        Import connector definition from DXF file.
        Expects DXF with:
        - Layer "CAVITY_OUTLINE": circles for cavities
        - Layer "CAVITY_TEXT": text for cavity numbers
        """
        doc = ezdxf.readfile(str(dxf_path))
        msp = doc.modelspace()
        
        cavities = {}
        
        # Find all cavity circles
        cavity_layer = doc.layers.get('CAVITY_OUTLINE')
        if cavity_layer:
            for entity in msp.query('CIRCLE'):
                if entity.dxf.layer == 'CAVITY_OUTLINE':
                    # Use center point as cavity position
                    x = entity.dxf.center.x
                    y = entity.dxf.center.y
                    
                    # Look for corresponding text
                    cavity_num = None
                    for text in msp.query('TEXT MTEXT'):
                        if text.dxf.layer == 'CAVITY_TEXT':
                            # Simple proximity check - find closest text
                            tx, ty = text.dxf.insert.x, text.dxf.insert.y
                            if abs(tx - x) < 10 and abs(ty - y) < 10:
                                cavity_num = text.plain_text() if hasattr(text, 'plain_text') else text.dxf.text
                                break
                    
                    if cavity_num:
                        cavities[cavity_num] = Cavity(
                            number=cavity_num,
                            position_x=x,
                            position_y=y
                        )
        
        # Create connector part
        connector = ConnectorPart(
            part_number=part_number,
            manufacturer=manufacturer,
            series=series,
            description=description,
            gender=gender,
            seal_type=seal_type,
            cavity_count=len(cavities),
            cavities=cavities,
            dxf_path=dxf_path
        )
        
        return connector
