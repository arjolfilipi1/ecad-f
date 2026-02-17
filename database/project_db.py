
import sqlite3
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Any
import uuid

from model.models import (
    WiringHarness, Connector, Wire, Node, HarnessBranch, 
    Pin, CombinedWireColor, Gender, SealType, ConnectorType, 
    WireType, NodeType
)

class ProjectDatabase:
    """SQLite database for saving/loading harness projects"""
    
    def __init__(self, project_path: str = None):
        self.project_path = project_path
        self.conn = None
        
        if project_path:
            self.open(project_path)
    
    def open(self, project_path: str):
        """Open or create project database"""
        self.project_path = project_path
        self.conn = sqlite3.connect(project_path)
        self.conn.row_factory = sqlite3.Row
        self._create_tables()
    
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
            self.conn = None
    
    def _create_tables(self):
        """Create all necessary tables if they don't exist"""
        cursor = self.conn.cursor()
        
        # Project metadata
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS project_info (
                key TEXT PRIMARY KEY,
                value TEXT
            )
        ''')
        
        # Connectors
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS connectors (
                id TEXT PRIMARY KEY,
                part_number TEXT,
                name TEXT,
                manufacturer TEXT,
                series TEXT,
                description TEXT,
                gender TEXT,
                seal_type TEXT,
                housing_color TEXT,
                position_x REAL,
                position_y REAL,
                rotation REAL,
                created_date TIMESTAMP,
                modified_date TIMESTAMP
            )
        ''')
        
        # Pins
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS pins (
                id TEXT PRIMARY KEY,
                connector_id TEXT,
                pin_number TEXT,
                original_id TEXT,
                wire_id TEXT,
                FOREIGN KEY (connector_id) REFERENCES connectors(id)
            )
        ''')
        
        # Nodes
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS nodes (
                id TEXT PRIMARY KEY,
                name TEXT,
                node_type TEXT,
                connector_id TEXT,
                position_x REAL,
                position_y REAL,
                branch_type TEXT,
                properties TEXT,
                FOREIGN KEY (connector_id) REFERENCES connectors(id)
            )
        ''')
        
        # Wires
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS wires (
                id TEXT PRIMARY KEY,
                name TEXT,
                signal_name TEXT,
                wire_type TEXT,
                cross_section REAL,
                base_color TEXT,
                stripe_color TEXT,
                from_node_id TEXT,
                to_node_id TEXT,
                from_pin TEXT,
                to_pin TEXT,
                calculated_length REAL,
                part_number TEXT,
                notes TEXT,
                FOREIGN KEY (from_node_id) REFERENCES nodes(id),
                FOREIGN KEY (to_node_id) REFERENCES nodes(id)
            )
        ''')
        
        # Segments
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS segments (
                id TEXT PRIMARY KEY,
                name TEXT,
                start_node_id TEXT,
                end_node_id TEXT,
                path_points TEXT,
                FOREIGN KEY (start_node_id) REFERENCES nodes(id),
                FOREIGN KEY (end_node_id) REFERENCES nodes(id)
            )
        ''')
        
        # Wire-Segment relationships
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS wire_segments (
                wire_id TEXT,
                segment_id TEXT,
                PRIMARY KEY (wire_id, segment_id),
                FOREIGN KEY (wire_id) REFERENCES wires(id),
                FOREIGN KEY (segment_id) REFERENCES segments(id)
            )
        ''')
        
        self.conn.commit()
    
    def save_project(self, harness: WiringHarness) -> bool:
        """Save complete harness project to database"""
        try:
            cursor = self.conn.cursor()
            
            # Clear existing data
            cursor.execute("DELETE FROM wire_segments")
            cursor.execute("DELETE FROM segments")
            cursor.execute("DELETE FROM wires")
            cursor.execute("DELETE FROM pins")
            cursor.execute("DELETE FROM nodes")
            cursor.execute("DELETE FROM connectors")
            cursor.execute("DELETE FROM project_info")
            
            # Save project info
            project_info = {
                'id': harness.id,
                'name': harness.name,
                'part_number': harness.part_number,
                'revision': harness.revision,
                'created_date': harness.created_date.isoformat(),
                'modified_date': datetime.now().isoformat()
            }
            
            for key, value in project_info.items():
                cursor.execute('''
                    INSERT INTO project_info (key, value)
                    VALUES (?, ?)
                ''', (key, str(value)))
            
            # Save connectors
            for conn in harness.connectors.values():
                self._save_connector(cursor, conn)
            
            # Save nodes
            for node in harness.nodes.values():
                self._save_node(cursor, node)
            
            # Save wires
            for wire in harness.wires.values():
                self._save_wire(cursor, wire)
            
            # Save segments
            for segment in harness.branches.values():
                self._save_segment(cursor, segment)
            
            self.conn.commit()
            return True
            
        except Exception as e:
            print(f"Error saving project: {e}")
            self.conn.rollback()
            return False
    
    def _save_connector(self, cursor, connector: Connector):
        """Save a connector to database"""
        cursor.execute('''
            INSERT INTO connectors (
                id, part_number, name, manufacturer, series, description,
                gender, seal_type, housing_color, position_x, position_y,
                rotation, created_date, modified_date
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            connector.id,
            connector.part_number,
            connector.name,
            getattr(connector, 'manufacturer', None),
            getattr(connector, 'series', None),
            connector.description or '',
            connector.gender.value if connector.gender else None,
            connector.seal.value if connector.seal else None,
            getattr(connector, 'housing_color', None),
            connector.position[0] if connector.position else 0,
            connector.position[1] if connector.position else 0,
            0,  # rotation
            datetime.now().isoformat(),
            datetime.now().isoformat()
        ))
        
        # Save pins
        for pin in connector.pins.values():
            cursor.execute('''
                INSERT INTO pins (
                    id, connector_id, pin_number, original_id, wire_id
                ) VALUES (?, ?, ?, ?, ?)
            ''', (
                f"{connector.id}_{pin.number}",
                connector.id,
                pin.number,
                pin.number,
                pin.wire_id
            ))
    
    def _save_node(self, cursor, node):
        """Save a topology node"""
        cursor.execute('''
            INSERT INTO nodes (
                id, name, node_type, connector_id,
                position_x, position_y, branch_type, properties
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            node.id,
            node.name,
            node.type.value if hasattr(node.type, 'value') else str(node.type),
            node.connector_id,
            node.position[0],
            node.position[1],
            getattr(node, 'branch_type', None),
            json.dumps(getattr(node, 'properties', {}))
        ))
    
    def _save_wire(self, cursor, wire: Wire):
        """Save a wire"""
        cursor.execute('''
            INSERT INTO wires (
                id, name, signal_name, wire_type, cross_section,
                base_color, stripe_color, from_node_id, to_node_id,
                from_pin, to_pin, calculated_length, part_number, notes
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            wire.id,
            wire.id,
            wire.signal_name,
            wire.type.value if wire.type else None,
            getattr(wire, 'cross_section', 0.5),
            wire.color.base_color if hasattr(wire, 'color') else 'SW',
            wire.color.stripe_color if hasattr(wire, 'color') else None,
            wire.from_node_id,
            wire.to_node_id,
            wire.from_pin,
            wire.to_pin,
            wire.calculated_length_mm,
            wire.part_number,
            wire.notes
        ))
    
    def _save_segment(self, cursor, segment: HarnessBranch):
        """Save a branch/segment"""
        path_json = json.dumps(segment.path_points)
        
        nodes = segment.node_ids
        start_node = nodes[0] if nodes else None
        end_node = nodes[-1] if len(nodes) > 1 else None
        
        cursor.execute('''
            INSERT INTO segments (
                id, name, start_node_id, end_node_id, path_points
            ) VALUES (?, ?, ?, ?, ?)
        ''', (
            segment.id,
            segment.name,
            start_node,
            end_node,
            path_json
        ))
        
        # Save wire-segment relationships
        for wire_id in segment.wire_ids:
            cursor.execute('''
                INSERT INTO wire_segments (wire_id, segment_id)
                VALUES (?, ?)
            ''', (wire_id, segment.id))
    
    def load_project(self) -> Optional[WiringHarness]:
        """Load a project from database"""
        try:
            cursor = self.conn.cursor()
            
            # Load project info
            cursor.execute("SELECT key, value FROM project_info")
            info = {row['key']: row['value'] for row in cursor.fetchall()}
            
            if not info:
                return None
            
            # Create harness
            from model.models import WiringHarness
            harness = WiringHarness(
                id=info.get('id', str(uuid.uuid4())),
                name=info.get('name', 'Unnamed Project'),
                part_number=info.get('part_number', ''),
                revision=info.get('revision', '1.0')
            )
            
            # Load connectors
            cursor.execute("SELECT * FROM connectors")
            for row in cursor.fetchall():
                connector = self._load_connector(row)
                if connector:
                    harness.connectors[connector.id] = connector
            
            # Load nodes
            cursor.execute("SELECT * FROM nodes")
            for row in cursor.fetchall():
                node = self._load_node(row)
                if node:
                    harness.nodes[node.id] = node
            
            # Load wires
            cursor.execute("SELECT * FROM wires")
            for row in cursor.fetchall():
                wire = self._load_wire(row, harness)
                if wire:
                    harness.wires[wire.id] = wire
            
            # Load segments
            cursor.execute("SELECT * FROM segments")
            for row in cursor.fetchall():
                segment = self._load_segment(row, harness)
                if segment:
                    harness.branches[segment.id] = segment
            
            return harness
            
        except Exception as e:
            print(f"Error loading project: {e}")
            return None
    
    def _load_connector(self, row) -> Optional[Connector]:
        """Load a connector from database row"""
        from model.models import Connector, Gender, SealType, ConnectorType, Pin
        
        connector = Connector(
            id=row['id'],
            name=row['name'] or row['part_number'],
            type=ConnectorType.OTHER,
            gender=Gender(row['gender']) if row['gender'] else Gender.FEMALE,
            seal=SealType(row['seal_type']) if row['seal_type'] else SealType.UNSEALED,
            part_number=row['part_number'],
            manufacturer=row['manufacturer'],
            position=(row['position_x'], row['position_y'])
        )
        
        # Load pins
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM pins WHERE connector_id = ?", (row['id'],))
        for pin_row in cursor.fetchall():
            pin = Pin(
                number=pin_row['pin_number'],
                gender=connector.gender,
                seal=connector.seal,
                wire_id=pin_row['wire_id']
            )
            connector.pins[pin.number] = pin
        
        return connector
    
    def _load_node(self, row):
        """Load a node from database row"""
        from model.models import Node, NodeType
        
        node = Node(
            id=row['id'],
            harness_id='',
            name=row['name'],
            type=NodeType(row['node_type']) if row['node_type'] else NodeType.CONNECTOR,
            connector_id=row['connector_id'],
            position=(row['position_x'], row['position_y'])
        )
        return node
    
    def _load_wire(self, row, harness):
        """Load a wire from database row"""
        from model.models import Wire, WireType, CombinedWireColor
        
        wire = Wire(
            id=row['id'],
            harness_id=harness.id,
            type=WireType(row['wire_type']) if row['wire_type'] else WireType.FLRY_B_0_5,
            color=CombinedWireColor(
                base_color=row['base_color'] or 'SW',
                stripe_color=row['stripe_color']
            ),
            from_node_id=row['from_node_id'],
            to_node_id=row['to_node_id'],
            from_pin=row['from_pin'],
            to_pin=row['to_pin'],
            calculated_length_mm=row['calculated_length'],
            signal_name=row['signal_name'],
            part_number=row['part_number'],
            notes=row['notes']
        )
        return wire
    
    def _load_segment(self, row, harness):
        """Load a segment from database row"""
        from model.models import HarnessBranch
        
        path_points = json.loads(row['path_points']) if row['path_points'] else []
        
        # Get wire IDs from wire_segments
        cursor = self.conn.cursor()
        cursor.execute("SELECT wire_id FROM wire_segments WHERE segment_id = ?", (row['id'],))
        wire_ids = [r['wire_id'] for r in cursor.fetchall()]
        
        segment = HarnessBranch(
            id=row['id'],
            harness_id=harness.id,
            name=row['name'] or f"Segment_{row['id'][:8]}",
            protection_id=None,
            path_points=path_points,
            node_ids=[row['start_node_id'], row['end_node_id']] if row['start_node_id'] and row['end_node_id'] else [],
            wire_ids=wire_ids
        )
        return segment
    
    def list_projects(self) -> List[Dict[str, Any]]:
        """List all saved projects in this database"""
        cursor = self.conn.cursor()
        cursor.execute("SELECT key, value FROM project_info")
        
        info = {}
        for row in cursor.fetchall():
            info[row['key']] = row['value']
        
        return [info] if info else []
    
    def delete_project(self) -> bool:
        """Delete current project from database"""
        try:
            cursor = self.conn.cursor()
            cursor.execute("DELETE FROM wire_segments")
            cursor.execute("DELETE FROM wires")
            cursor.execute("DELETE FROM segments")
            cursor.execute("DELETE FROM pins")
            cursor.execute("DELETE FROM nodes")
            cursor.execute("DELETE FROM connectors")
            cursor.execute("DELETE FROM project_info")
            self.conn.commit()
            return True
        except Exception as e:
            print(f"Error deleting project: {e}")
            return False
class ProjectFileHandler:
    """Handles project file operations with .ecad extension"""
    
    def __init__(self):
        self.current_project = None
        self.current_path = None
        self.modified = False
    
    def new_project(self, name: str = "New Project") -> WiringHarness:
        """Create a new project"""
        from model.models import WiringHarness
        self.current_project = WiringHarness(name=name)
        self.current_path = None
        self.modified = True
        return self.current_project
    
    def open_project(self, filepath: str) -> Optional[WiringHarness]:
        """Open a .ecad project file"""
        db = ProjectDatabase(filepath)
        self.current_project = db.load_project()
        db.close()
        
        if self.current_project:
            self.current_path = filepath
            self.modified = False
        
        return self.current_project
    
    def save_project(self, filepath: str = None) -> bool:
        """Save project to file"""
        if not self.current_project:
            return False
        
        save_path = filepath or self.current_path
        if not save_path:
            return False
        
        # Ensure .ecad extension
        if not save_path.endswith('.ecad'):
            save_path += '.ecad'
        
        db = ProjectDatabase(save_path)
        success = db.save_project(self.current_project)
        db.close()
        
        if success:
            self.current_path = save_path
            self.modified = False
        
        return success
    
    def export_to_excel(self, filepath: str) -> bool:
        """Export harness data to Excel"""
        try:
            import pandas as pd
            from pathlib import Path
            
            if not self.current_project:
                return False
            
            with pd.ExcelWriter(filepath, engine='openpyxl') as writer:
                # Wires sheet
                wires_data = []
                for wire in self.current_project.wires.values():
                    wires_data.append({
                        'Wire ID': wire.id,
                        'Signal': wire.signal_name or '',
                        'Type': wire.type.value if wire.type else '',
                        'Cross Section': getattr(wire, 'cross_section', 0.5),
                        'Color': wire.color.code if hasattr(wire, 'color') else 'SW',
                        'From': wire.from_node_id,
                        'From Pin': wire.from_pin,
                        'To': wire.to_node_id,
                        'To Pin': wire.to_pin,
                        'Length (mm)': wire.calculated_length_mm or 0,
                        'Part Number': wire.part_number or ''
                    })
                
                if wires_data:
                    pd.DataFrame(wires_data).to_excel(writer, sheet_name='Wires', index=False)
                
                # Connectors sheet
                conn_data = []
                for conn in self.current_project.connectors.values():
                    conn_data.append({
                        'ID': conn.id,
                        'Part Number': conn.part_number or '',
                        'Name': conn.name,
                        'Type': conn.type.value if hasattr(conn.type, 'value') else str(conn.type),
                        'Gender': conn.gender.value if conn.gender else '',
                        'Pin Count': len(conn.pins),
                        'Position X': conn.position[0],
                        'Position Y': conn.position[1]
                    })
                
                if conn_data:
                    pd.DataFrame(conn_data).to_excel(writer, sheet_name='Connectors', index=False)
                
                # Pins sheet
                pins_data = []
                for conn in self.current_project.connectors.values():
                    for pin_num, pin in conn.pins.items():
                        pins_data.append({
                            'Connector': conn.id,
                            'Pin': pin_num,
                            'Wire ID': pin.wire_id or ''
                        })
                
                if pins_data:
                    pd.DataFrame(pins_data).to_excel(writer, sheet_name='Pins', index=False)
            
            return True
            
        except Exception as e:
            print(f"Error exporting to Excel: {e}")
            return False

