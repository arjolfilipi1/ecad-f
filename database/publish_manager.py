import sqlite3
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Optional, Any
import uuid
import os

class PublishManager:
    """Manages publishing projects to central database"""
    
    def __init__(self, central_db_path: str):
        self.central_db_path = central_db_path
        self.conn = None
        self._ensure_db_exists()
    
    def _ensure_db_exists(self):
        """Ensure database exists with proper tables"""
        self.conn = sqlite3.connect(self.central_db_path)
        self.conn.row_factory = sqlite3.Row
        self._create_tables()
    
    def _create_tables(self):
        """Create publish tables if they don't exist"""
        cursor = self.conn.cursor()
        
        # Published projects table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS published_projects (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                part_number TEXT,
                revision TEXT,
                version INTEGER DEFAULT 1,
                status TEXT DEFAULT 'Draft',
                author TEXT,
                created_date TIMESTAMP,
                published_date TIMESTAMP,
                modified_date TIMESTAMP,
                file_path TEXT,
                description TEXT,
                tags TEXT,
                thumbnail BLOB,
                comments TEXT
            )
        ''')
        
        # Project versions (history)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS project_versions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                project_id TEXT,
                version INTEGER,
                revision TEXT,
                status TEXT,
                published_date TIMESTAMP,
                published_by TEXT,
                comments TEXT,
                file_path TEXT,
                FOREIGN KEY (project_id) REFERENCES published_projects(id)
            )
        ''')
        
        # Published connectors
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS published_connectors (
                id TEXT PRIMARY KEY,
                project_id TEXT,
                part_number TEXT,
                name TEXT,
                manufacturer TEXT,
                series TEXT,
                gender TEXT,
                seal_type TEXT,
                position_x REAL,
                position_y REAL,
                rotation REAL,
                FOREIGN KEY (project_id) REFERENCES published_projects(id)
            )
        ''')
        
        # Published pins
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS published_pins (
                id TEXT PRIMARY KEY,
                connector_id TEXT,
                pin_number TEXT,
                wire_id TEXT,
                FOREIGN KEY (connector_id) REFERENCES published_connectors(id)
            )
        ''')
        
        # Published wires
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS published_wires (
                id TEXT PRIMARY KEY,
                project_id TEXT,
                wire_name TEXT,
                signal_name TEXT,
                wire_type TEXT,
                cross_section REAL,
                base_color TEXT,
                stripe_color TEXT,
                from_connector_id TEXT,
                from_pin TEXT,
                to_connector_id TEXT,
                to_pin TEXT,
                length_mm REAL,
                part_number TEXT,
                FOREIGN KEY (project_id) REFERENCES published_projects(id),
                FOREIGN KEY (from_connector_id) REFERENCES published_connectors(id),
                FOREIGN KEY (to_connector_id) REFERENCES published_connectors(id)
            )
        ''')
        
        # Published bundles
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS published_bundles (
                id TEXT PRIMARY KEY,
                project_id TEXT,
                name TEXT,
                start_node_id TEXT,
                end_node_id TEXT,
                start_point_x REAL,
                start_point_y REAL,
                end_point_x REAL,
                end_point_y REAL,
                specified_length REAL,
                wire_count INTEGER,
                wire_ids TEXT,
                FOREIGN KEY (project_id) REFERENCES published_projects(id)
            )
        ''')
        
        # Published segments
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS published_segments (
                id TEXT PRIMARY KEY,
                project_id TEXT,
                name TEXT,
                start_node_id TEXT,
                end_node_id TEXT,
                path_points TEXT,
                wire_ids TEXT,
                FOREIGN KEY (project_id) REFERENCES published_projects(id)
            )
        ''')
        
        # Access control
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS project_access (
                project_id TEXT,
                user_name TEXT,
                access_level TEXT,
                granted_date TIMESTAMP,
                granted_by TEXT,
                PRIMARY KEY (project_id, user_name),
                FOREIGN KEY (project_id) REFERENCES published_projects(id)
            )
        ''')
        
        self.conn.commit()
    
    def publish_project(self, harness: WiringHarness, 
                        bundles: list = None,
                        imported_wires: list = None,
                        status: str = "Released",
                        comments: str = "",
                        author: str = None,
                        archive_local_file: str = None) -> bool:
        """
        Publish a project to central database
        """
        try:
            cursor = self.conn.cursor()
            
            # Check if project already exists
            cursor.execute('''
                SELECT id, version FROM published_projects WHERE id = ?
            ''', (harness.id,))
            
            existing = cursor.fetchone()
            
            if existing:
                # Update existing project (new version)
                project_id = existing[0]
                old_version = existing[1]
                new_version = old_version + 1
                
                # Archive old version
                cursor.execute('''
                    INSERT INTO project_versions (
                        project_id, version, revision, status,
                        published_date, comments, file_path
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    project_id, old_version, harness.revision,
                    status, datetime.now(), comments, archive_local_file
                ))
                
                # Update main project
                cursor.execute('''
                    UPDATE published_projects SET
                        revision = ?,
                        version = ?,
                        status = ?,
                        modified_date = ?,
                        published_date = ?,
                        file_path = ?,
                        description = ?,
                        comments = ?
                    WHERE id = ?
                ''', (
                    harness.revision, new_version, status,
                    datetime.now(), datetime.now(),
                    archive_local_file, harness.name, comments,
                    project_id
                ))
                
                # Delete old components
                cursor.execute('DELETE FROM published_wires WHERE project_id = ?', (project_id,))
                cursor.execute('DELETE FROM published_bundles WHERE project_id = ?', (project_id,))
                cursor.execute('DELETE FROM published_segments WHERE project_id = ?', (project_id,))
                cursor.execute('DELETE FROM published_pins WHERE connector_id IN '
                              '(SELECT id FROM published_connectors WHERE project_id = ?)', 
                              (project_id,))
                cursor.execute('DELETE FROM published_connectors WHERE project_id = ?', (project_id,))
                
            else:
                # New project
                project_id = harness.id
                cursor.execute('''
                    INSERT INTO published_projects (
                        id, name, part_number, revision, version,
                        status, author, created_date, published_date,
                        modified_date, file_path, description, comments
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    project_id, harness.name, harness.part_number,
                    harness.revision, 1, status, author,
                    harness.created_date.isoformat() if harness.created_date else datetime.now().isoformat(),
                    datetime.now().isoformat(), datetime.now().isoformat(),
                    archive_local_file, harness.name, comments
                ))
            
            # Publish connectors
            conn_id_map = {} # Map old ID to new published ID
            for conn in harness.connectors.values():
                pub_conn_id = f"PUB_{conn.id}"
                conn_id_map[conn.id] = pub_conn_id
                
                cursor.execute('''
                    INSERT INTO published_connectors (
                        id, project_id, part_number, name, manufacturer,
                        series, gender, seal_type, position_x, position_y, rotation
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    pub_conn_id, project_id, conn.part_number, conn.name,
                    conn.manufacturer, conn.series,
                    conn.gender.value if conn.gender else None,
                    conn.seal.value if conn.seal else None,
                    conn.position[0], conn.position[1], 0
                ))
                
                # Publish pins
                for pin_num, pin in conn.pins.items():
                    cursor.execute('''
                        INSERT INTO published_pins (
                            id, connector_id, pin_number, wire_id
                        ) VALUES (?, ?, ?, ?)
                    ''', (
                        f"{pub_conn_id}_{pin_num}",
                        pub_conn_id,
                        pin_num,
                        pin.wire_id
                    ))
            
            # Publish wires (from harness model)
            for wire in harness.wires.values():
                # Find which connectors this wire connects
                from_conn_id = None
                to_conn_id = None
                
                for node_id in [wire.from_node_id, wire.to_node_id]:
                    for orig_id, pub_id in conn_id_map.items():
                        if orig_id in node_id:
                            if not from_conn_id:
                                from_conn_id = pub_id
                            else:
                                to_conn_id = pub_id
                
                cursor.execute('''
                    INSERT INTO published_wires (
                        id, project_id, wire_name, signal_name, wire_type,
                        cross_section, base_color, stripe_color,
                        from_connector_id, from_pin, to_connector_id, to_pin,
                        length_mm, part_number
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ''', (
                    wire.id, project_id, wire.id, wire.signal_name,
                    wire.type.value if wire.type else None,
                    getattr(wire, 'cross_section', 0.5),
                    wire.color.base_color if hasattr(wire, 'color') else 'SW',
                    wire.color.stripe_color if hasattr(wire, 'color') else None,
                    from_conn_id, wire.from_pin,
                    to_conn_id, wire.to_pin,
                    wire.calculated_length_mm,
                    wire.part_number
                ))
            
            # Publish imported wires (graphics items)
            if imported_wires:
                for wire_item in imported_wires:
                    if hasattr(wire_item, 'wire_data'):
                        wd = wire_item.wire_data
                        cursor.execute('''
                            INSERT OR IGNORE INTO published_wires (
                                id, project_id, wire_name, signal_name,
                                cross_section, base_color,
                                from_connector_id, from_pin, to_connector_id, to_pin,
                                length_mm, part_number
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                        ''', (
                            wire_item.wid, project_id, wire_item.wid,
                            wd.signal_name if hasattr(wd, 'signal_name') else '',
                            wd.cross_section if hasattr(wd, 'cross_section') else 0.5,
                            wd.color if hasattr(wd, 'color') else 'SW',
                            conn_id_map.get(f"CONN_{wd.from_device}"),
                            wd.from_pin,
                            conn_id_map.get(f"CONN_{wd.to_device}"),
                            wd.to_pin,
                            0.0,
                            wd.part_number if hasattr(wd, 'part_number') else None
                        ))
            
            # Publish bundles
            if bundles:
                for bundle in bundles:
                    # Get connector IDs
                    from_conn_id = None
                    to_conn_id = None
                    
                    if bundle.start_node:
                        for orig_id, pub_id in conn_id_map.items():
                            if orig_id in str(bundle.start_node.id):
                                from_conn_id = pub_id
                                break
                    
                    if bundle.end_node:
                        for orig_id, pub_id in conn_id_map.items():
                            if orig_id in str(bundle.end_node.id):
                                to_conn_id = pub_id
                                break
                    
                    cursor.execute('''
                        INSERT INTO published_bundles (
                            id, project_id, name,
                            start_node_id, end_node_id,
                            start_point_x, start_point_y,
                            end_point_x, end_point_y,
                            specified_length, wire_count, wire_ids
                        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ''', (
                        bundle.bundle_id, project_id,
                        getattr(bundle, 'name', bundle.bundle_id),
                        from_conn_id, to_conn_id,
                        bundle.start_point.x(), bundle.start_point.y(),
                        bundle.end_point.x(), bundle.end_point.y(),
                        bundle.specified_length,
                        bundle.wire_count,
                        json.dumps(bundle.wire_ids)
                    ))
            
            # Publish segments
            for segment in harness.branches.values():
                cursor.execute('''
                    INSERT INTO published_segments (
                        id, project_id, name, start_node_id, end_node_id,
                        path_points, wire_ids
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                ''', (
                    segment.id, project_id, segment.name,
                    None, None,
                    json.dumps(segment.path_points),
                    json.dumps(segment.wire_ids)
                ))
            
            self.conn.commit()
            return True
            
        except Exception as e:
            print(f"Error publishing project: {e}")
            import traceback
            traceback.print_exc()
            self.conn.rollback()
            return False
    
    def search_projects(self, status: str = None, 
                        part_number: str = None,
                        name_contains: str = None,
                        date_from: datetime = None,
                        date_to: datetime = None) -> List[dict]:
        """Search published projects"""
        cursor = self.conn.cursor()
        
        query = "SELECT * FROM published_projects WHERE 1=1"
        params = []
        
        if status:
            query += " AND status = ?"
            params.append(status)
        
        if part_number:
            query += " AND part_number LIKE ?"
            params.append(f"%{part_number}%")
        
        if name_contains:
            query += " AND name LIKE ?"
            params.append(f"%{name_contains}%")
        
        if date_from:
            query += " AND published_date >= ?"
            params.append(date_from.isoformat())
        
        if date_to:
            query += " AND published_date <= ?"
            params.append(date_to.isoformat())
        
        query += " ORDER BY published_date DESC"
        
        cursor.execute(query, params)
        
        results = []
        for row in cursor.fetchall():
            results.append(dict(row))
        
        return results
    
    def get_project(self, project_id: str) -> Optional[Dict[str, Any]]:
        """Load a published project from database"""
        cursor = self.conn.cursor()
        
        # Get project info
        cursor.execute('SELECT * FROM published_projects WHERE id = ?', (project_id,))
        proj_row = cursor.fetchone()
        
        if not proj_row:
            return None
        
        project_data = dict(proj_row)
        
        # Get connectors
        cursor.execute('SELECT * FROM published_connectors WHERE project_id = ?', (project_id,))
        project_data['connectors'] = [dict(row) for row in cursor.fetchall()]
        
        # Get wires
        cursor.execute('SELECT * FROM published_wires WHERE project_id = ?', (project_id,))
        project_data['wires'] = [dict(row) for row in cursor.fetchall()]
        
        # Get bundles
        cursor.execute('SELECT * FROM published_bundles WHERE project_id = ?', (project_id,))
        project_data['bundles'] = [dict(row) for row in cursor.fetchall()]
        
        # Get segments
        cursor.execute('SELECT * FROM published_segments WHERE project_id = ?', (project_id,))
        project_data['segments'] = [dict(row) for row in cursor.fetchall()]
        
        return project_data
    
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
            self.conn = None