"""
Project controller handling file operations and database interactions
"""

import os
import json
from pathlib import Path
from datetime import datetime
from PyQt5.QtWidgets import QFileDialog, QMessageBox, QInputDialog, QDialog,QWidget,QTableWidgetItem
from PyQt5.QtCore import Qt

from database.publish_manager import PublishManager
from database.project_db import ProjectDatabase
from model.models import WiringHarness


class ProjectController:
    """Handles project file operations and database interactions"""
    
    @staticmethod
    def open_project(main_window, filepath=None):
        """Open an existing project from .ecad file"""
        if filepath is None:
            filepath, _ = QFileDialog.getOpenFileName(
                main_window,
                "Open Project",
                str(main_window.settings_manager.settings.default_path),
                "ECAD Projects (*.ecad);;All Files (*)"
            )
        
        if filepath:
            print(f"Opening project: {filepath}")
            
            main_window.clear_scene()
            
            project = main_window.project_handler.open_project(filepath)
            
            if project:
                ProjectController._load_project_to_scene(main_window, project)
                ProjectController._load_bundles_from_project(main_window, filepath)
                
                main_window.setWindowTitle(f"ECAD - {project.name} ({Path(filepath).name})")
                
                main_window.settings_manager.add_recent_file(filepath)
                main_window._update_recent_menu()
                
                main_window.statusBar().showMessage(f"Loaded: {filepath}", 3000)
            else:
                QMessageBox.critical(main_window, "Error", "Failed to load project")
    
    @staticmethod
    def save_project(main_window):
        """Save current project"""
        if main_window.project_handler.current_path:
            success = main_window.project_handler.save_project(
                filepath=main_window.project_handler.current_path,
                main_window=main_window
            )
            if success:
                main_window.undo_manager.set_clean()
                main_window.statusBar().showMessage(f"Saved: {main_window.project_handler.current_path}", 3000)
            else:
                QMessageBox.critical(main_window, "Error", "Failed to save project")
        else:
            ProjectController.save_project_as(main_window)
    
    @staticmethod
    def save_project_as(main_window):
        """Save project with new name"""
        filepath, _ = QFileDialog.getSaveFileName(
            main_window,
            "Save Project As",
            str(main_window.settings_manager.settings.default_path + "/untitled.ecad"),
            "ECAD Projects (*.ecad);;All Files (*)"
        )
        
        if filepath:
            bundles = getattr(main_window, 'bundles', [])
            print(f"ProjectController.save_project_as: Found {len(bundles)} bundles")
            
            if not filepath.endswith('.ecad'):
                filepath += '.ecad'
            
            project = ProjectController._create_project_from_scene(main_window)
            main_window.project_handler.current_project = project
            
            success = main_window.project_handler.save_project(
                filepath=filepath,
                main_window=main_window
            )
            if success:
                main_window.undo_manager.set_clean()
                main_window.setWindowTitle(f"ECAD - {project.name} ({Path(filepath).name})")
                
                main_window.settings_manager.add_recent_file(filepath)
                main_window._update_recent_menu()
                
                main_window.statusBar().showMessage(f"Saved: {filepath}", 3000)
            else:
                QMessageBox.critical(main_window, "Error", "Failed to save project")
    
    @staticmethod
    def publish_project(main_window):
        """Publish current project to central database"""
        if not main_window.project_handler.current_project:
            QMessageBox.warning(main_window, "No Project", "No project to publish")
            return
        
        from PyQt5.QtWidgets import QDialog, QVBoxLayout, QFormLayout, QLineEdit, QComboBox, QTextEdit, QDialogButtonBox, QLabel, QCheckBox
        from datetime import datetime
        
        central_db = main_window.settings_manager.get('database_path', 
                                                      str(main_window.settings_manager.settings.default_path + "/ecad/central.db"),end='\\central.db')
        print(central_db, 'publish_project')
        
        bundles = getattr(main_window, 'bundles', [])
        imported_wires = getattr(main_window, 'imported_wire_items', [])
        print(f"Publishing {len(bundles)} bundles and {len(imported_wires)} wires")
        
        dialog = QDialog(main_window)
        dialog.setWindowTitle("Publish Project")
        dialog.setMinimumWidth(400)
        
        layout = QVBoxLayout(dialog)
        
        layout.addWidget(QLabel(f"<b>Project:</b> {main_window.project_handler.current_project.name}"))
        layout.addWidget(QLabel(f"<b>Part Number:</b> {main_window.project_handler.current_project.part_number or 'N/A'}"))
        
        form = QFormLayout()
        
        status_combo = QComboBox()
        status_combo.addItems(["Draft", "Review", "Released", "Obsolete"])
        form.addRow("Status:", status_combo)
        
        revision_edit = QLineEdit(main_window.project_handler.current_project.revision)
        form.addRow("Revision:", revision_edit)
        
        comments_edit = QTextEdit()
        comments_edit.setPlaceholderText("Enter check-in comments...")
        comments_edit.setMaximumHeight(100)
        form.addRow("Comments:", comments_edit)
        
        layout.addLayout(form)
        
        archive_check = QCheckBox("Archive local .ecad file")
        archive_check.setChecked(True)
        layout.addWidget(archive_check)
        
        routed_wires = getattr(main_window, 'routed_wire_items', [])
        
        stats = QLabel(
            f"<small>"
            f"Connectors: {len(main_window.conns)}<br>"
            f"Direct Wires: {len(imported_wires)}<br>"
            f"Routed Wires: {len(routed_wires) if routed_wires else 0}<br>"
            f"Bundles: {len(bundles)}"
            f"</small>"
        )
        stats.setStyleSheet("color: gray;")
        layout.addWidget(stats)
        
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(dialog.accept)
        button_box.rejected.connect(dialog.reject)
        layout.addWidget(button_box)
        
        if dialog.exec_():
            status = status_combo.currentText()
            revision = revision_edit.text()
            comments = comments_edit.toPlainText()
            
            main_window.project_handler.current_project.revision = revision
            main_window.project_handler.modified = True
            
            archive_path = None
            if archive_check.isChecked():
                archive_dir = main_window.settings_manager.settings.default_path + "/ecad/archive"
                archive_dir = Path(archive_dir)
                archive_dir.mkdir(parents=True, exist_ok=True)
                
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                archive_name = f"{main_window.project_handler.current_project.name}_v{revision}_{timestamp}.ecad"
                archive_path = str(archive_dir / archive_name)
                
                bundles = getattr(main_window, 'bundles', [])
                imported_wires = getattr(main_window, 'imported_wire_items', [])
                
                success = main_window.project_handler.save_project(
                    filepath=archive_path,
                    main_window=main_window
                )
                
                if success:
                    main_window.statusBar().showMessage(f"Archived to: {archive_path}", 3000)
            print(central_db)
            publisher = PublishManager(central_db)
            success = publisher.publish_project(
                main_window.project_handler.current_project,
                bundles=bundles,
                status=status,
                comments=comments,
                author=os.getlogin(),
                archive_local_file=archive_path
            )
            publisher.close()
            
            if success:
                QMessageBox.information(main_window, "Success", "Project published successfully!")
                main_window.statusBar().showMessage(f"Published to database: {central_db}", 5000)
            else:
                QMessageBox.critical(main_window, "Error", "Failed to publish project")
    
    @staticmethod
    def open_from_database(main_window):
        """Open a project from central database"""
        from PyQt5.QtWidgets import QDialog, QVBoxLayout, QHBoxLayout, QTableWidget, QTableWidgetItem, QHeaderView, QPushButton, QLineEdit, QComboBox, QLabel, QMessageBox, QSplitter, QTextEdit, QGroupBox
        
        central_db = main_window.settings_manager.get('database_path', 
                                                      str(main_window.settings_manager.settings.database_path + "/central.db"),end='\\central.db')

        
        dialog = QDialog(main_window)
        dialog.setWindowTitle("Open from Database")
        dialog.setMinimumSize(900, 600)
        
        layout = QVBoxLayout(dialog)
        
        filter_group = QGroupBox("Search Filters")
        filter_layout = QHBoxLayout(filter_group)
        
        filter_layout.addWidget(QLabel("Status:"))
        main_window.db_status_filter = QComboBox()
        main_window.db_status_filter.addItems(["All", "Draft", "Review", "Released", "Obsolete"])
        filter_layout.addWidget(main_window.db_status_filter)
        
        filter_layout.addWidget(QLabel("Name:"))
        main_window.db_name_search = QLineEdit()
        main_window.db_name_search.setPlaceholderText("Project name...")
        filter_layout.addWidget(main_window.db_name_search)
        
        filter_layout.addWidget(QLabel("Part #:"))
        main_window.db_part_search = QLineEdit()
        main_window.db_part_search.setPlaceholderText("Part number...")
        filter_layout.addWidget(main_window.db_part_search)
        
        search_btn = QPushButton("🔍 Search")
        search_btn.clicked.connect(lambda: ProjectController.search_db_projects(main_window, dialog))
        filter_layout.addWidget(search_btn)
        
        layout.addWidget(filter_group)
        
        splitter = QSplitter(Qt.Horizontal)
        
        results_widget = QWidget()
        results_layout = QVBoxLayout(results_widget)
        results_layout.setContentsMargins(0, 0, 0, 0)
        
        results_layout.addWidget(QLabel("<b>Published Projects:</b>"))
        
        main_window.db_results_table = QTableWidget()
        main_window.db_results_table.setColumnCount(6)
        main_window.db_results_table.setHorizontalHeaderLabels(["Project Name", "Part Number", "Revision", "Status", "Version", "Published Date"])
        main_window.db_results_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        main_window.db_results_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        main_window.db_results_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        main_window.db_results_table.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        main_window.db_results_table.horizontalHeader().setSectionResizeMode(4, QHeaderView.ResizeToContents)
        main_window.db_results_table.horizontalHeader().setSectionResizeMode(5, QHeaderView.ResizeToContents)
        main_window.db_results_table.setSelectionBehavior(QTableWidget.SelectRows)
        main_window.db_results_table.setSelectionMode(QTableWidget.SingleSelection)
        main_window.db_results_table.itemSelectionChanged.connect(lambda: ProjectController.on_db_project_selected(main_window, dialog))
        main_window.db_results_table.doubleClicked.connect(lambda: ProjectController.open_selected_db_project(main_window, dialog))
        results_layout.addWidget(main_window.db_results_table)
        
        splitter.addWidget(results_widget)
        
        preview_widget = QWidget()
        preview_layout = QVBoxLayout(preview_widget)
        
        preview_layout.addWidget(QLabel("<b>Project Preview:</b>"))
        
        main_window.db_preview_text = QTextEdit()
        main_window.db_preview_text.setReadOnly(True)
        main_window.db_preview_text.setMaximumHeight(200)
        preview_layout.addWidget(main_window.db_preview_text)
        
        main_window.db_stats_preview = QTableWidget()
        main_window.db_stats_preview.setColumnCount(2)
        main_window.db_stats_preview.setHorizontalHeaderLabels(["Item", "Count"])
        main_window.db_stats_preview.horizontalHeader().setSectionResizeMode(0, QHeaderView.Stretch)
        main_window.db_stats_preview.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        main_window.db_stats_preview.setMaximumHeight(150)
        preview_layout.addWidget(main_window.db_stats_preview)
        
        preview_layout.addWidget(QLabel("<b>Version History:</b>"))
        main_window.db_version_table = QTableWidget()
        main_window.db_version_table.setColumnCount(3)
        main_window.db_version_table.setHorizontalHeaderLabels(["Version", "Date", "Comments"])
        main_window.db_version_table.horizontalHeader().setSectionResizeMode(0, QHeaderView.ResizeToContents)
        main_window.db_version_table.horizontalHeader().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        main_window.db_version_table.horizontalHeader().setSectionResizeMode(2, QHeaderView.Stretch)
        main_window.db_version_table.setMaximumHeight(150)
        preview_layout.addWidget(main_window.db_version_table)
        
        splitter.addWidget(preview_widget)
        splitter.setSizes([500, 400])
        
        layout.addWidget(splitter)
        
        btn_layout = QHBoxLayout()
        open_btn = QPushButton("📂 Open")
        open_btn.clicked.connect(lambda: ProjectController.open_selected_db_project(main_window, dialog))
        open_btn.setDefault(True)
        btn_layout.addWidget(open_btn)
        
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(dialog.reject)
        btn_layout.addWidget(cancel_btn)
        
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        
        ProjectController.search_db_projects(main_window, dialog)
        
        dialog.exec_()
    
    @staticmethod
    def search_db_projects(main_window, dialog):
        """Search for projects in database"""
        from database.publish_manager import PublishManager
        
        central_db = main_window.settings_manager.get('database_path', 
                                                      str(main_window.settings_manager.settings.database_path + "central.db"),end='\\central.db')
        print(central_db, 'search_db_projects')
        
        status = main_window.db_status_filter.currentText()
        if status == "All":
            status = None
        
        name_search = main_window.db_name_search.text() or None
        part_search = main_window.db_part_search.text() or None
        
        publisher = PublishManager(central_db)
        projects = publisher.search_projects(
            status=status,
            name_contains=name_search,
            part_number=part_search
        )
        publisher.close()
        
        main_window.db_results_table.setRowCount(len(projects))
        for i, proj in enumerate(projects):
            main_window.db_results_table.setItem(i, 0, QTableWidgetItem(proj.get('name', '')))
            main_window.db_results_table.setItem(i, 1, QTableWidgetItem(proj.get('part_number', '')))
            main_window.db_results_table.setItem(i, 2, QTableWidgetItem(proj.get('revision', '')))
            main_window.db_results_table.setItem(i, 3, QTableWidgetItem(proj.get('status', '')))
            main_window.db_results_table.setItem(i, 4, QTableWidgetItem(str(proj.get('version', 1))))
            
            pub_date = proj.get('published_date', '')
            if pub_date and len(pub_date) > 10:
                pub_date = pub_date[:10]
            main_window.db_results_table.setItem(i, 5, QTableWidgetItem(pub_date))
            
            main_window.db_results_table.item(i, 0).setData(Qt.UserRole, proj.get('id'))
    
    @staticmethod
    def on_db_project_selected(main_window, dialog):
        """Handle project selection in database dialog"""
        current_row = main_window.db_results_table.currentRow()
        if current_row < 0:
            return
        
        project_id = main_window.db_results_table.item(current_row, 0).data(Qt.UserRole)
        if not project_id:
            return
        
        from database.publish_manager import PublishManager
        
        central_db = main_window.settings_manager.get('database_path', 
                                                      str(main_window.settings_manager.settings.database_path + "central.db"),end='\\central.db')
        print(central_db, 'on_db_project_selected')
        
        publisher = PublishManager(central_db)
        project_data = publisher.get_project(project_id)
        publisher.close()
        
        if not project_data:
            return
        
        preview = f"<b>Project:</b> {project_data.get('name', 'N/A')}<br>"
        preview += f"<b>Part Number:</b> {project_data.get('part_number', 'N/A')}<br>"
        preview += f"<b>Revision:</b> {project_data.get('revision', 'N/A')}<br>"
        preview += f"<b>Status:</b> {project_data.get('status', 'N/A')}<br>"
        preview += f"<b>Version:</b> {project_data.get('version', 1)}<br>"
        preview += f"<b>Published:</b> {project_data.get('published_date', 'N/A')}<br>"
        preview += f"<b>Author:</b> {project_data.get('author', 'N/A')}<br>"
        preview += f"<b>Comments:</b> {project_data.get('comments', 'N/A')}"
        
        main_window.db_preview_text.setHtml(preview)
        
        connectors = project_data.get('connectors', [])
        wires = project_data.get('wires', [])
        bundles = project_data.get('bundles', [])
        
        main_window.db_stats_preview.setRowCount(3)
        main_window.db_stats_preview.setItem(0, 0, QTableWidgetItem("Connectors"))
        main_window.db_stats_preview.setItem(0, 1, QTableWidgetItem(str(len(connectors))))
        main_window.db_stats_preview.setItem(1, 0, QTableWidgetItem("Wires"))
        main_window.db_stats_preview.setItem(1, 1, QTableWidgetItem(str(len(wires))))
        main_window.db_stats_preview.setItem(2, 0, QTableWidgetItem("Bundles"))
        main_window.db_stats_preview.setItem(2, 1, QTableWidgetItem(str(len(bundles))))
        
        main_window.db_version_table.setRowCount(0)
    
    @staticmethod
    def open_selected_db_project(main_window, dialog):
        """Open the selected project from database"""
        current_row = main_window.db_results_table.currentRow()
        if current_row < 0:
            QMessageBox.warning(main_window, "No Selection", "Please select a project to open")
            return
        
        project_id = main_window.db_results_table.item(current_row, 0).data(Qt.UserRole)
        if not project_id:
            return
        
        from database.publish_manager import PublishManager
        
        central_db = main_window.settings_manager.get('database_path', 
                                                      str(main_window.settings_manager.settings.default_path + "/ecad/central.db"),end='\\central.db')
        print(central_db, 'open_selected_db_project')
        
        reply = QMessageBox.question(
            main_window,
            "Open Options",
            "Do you want to:\n\n"
            "Yes: Open as read-only (cannot save changes)\n"
            "No: Check out for editing (creates local copy)\n"
            "Cancel: Cancel operation",
            QMessageBox.Yes | QMessageBox.No | QMessageBox.Cancel
        )
        
        if reply == QMessageBox.Cancel:
            return
        
        read_only = (reply == QMessageBox.Yes)
        
        publisher = PublishManager(central_db)
        project_data = publisher.get_project(project_id)
        publisher.close()
        
        if not project_data:
            QMessageBox.critical(main_window, "Error", "Failed to load project from database")
            return
        
        from model.models import WiringHarness, Connector, Wire, Pin, Node, CombinedWireColor
        from model.models import Gender, SealType, ConnectorType, WireType, NodeType
        
        harness = WiringHarness(
            id=project_data['id'],
            name=project_data['name'],
            part_number=project_data.get('part_number', ''),
            revision=project_data.get('revision', '1.0')
        )
        
        for conn_data in project_data.get('connectors', []):
            connector = Connector(
                id=conn_data['id'],
                name=conn_data['name'],
                type=ConnectorType.OTHER,
                gender=Gender(conn_data['gender']) if conn_data.get('gender') else Gender.FEMALE,
                seal=SealType(conn_data['seal_type']) if conn_data.get('seal_type') else SealType.UNSEALED,
                part_number=conn_data.get('part_number'),
                manufacturer=conn_data.get('manufacturer'),
                position=(conn_data['position_x'], conn_data['position_y'])
            )
            harness.connectors[connector.id] = connector
        
        for wire_data in project_data.get('wires', []):
            wire = Wire(
                id=wire_data['wid'],
                harness_id=harness.id,
                type=WireType.FLRY_B_0_5,
                color=CombinedWireColor(
                    base_color=wire_data.get('base_color', 'SW'),
                    stripe_color=wire_data.get('stripe_color')
                ),
                from_node_id=wire_data.get('from_node_id', ''),
                to_node_id=wire_data.get('to_node_id', ''),
                from_pin=wire_data.get('from_pin'),
                to_pin=wire_data.get('to_pin'),
                signal_name=wire_data.get('signal_name'),
                part_number=wire_data.get('part_number'),
                cross_section=wire_data.get('cross_section', 0.5)
            )
            harness.wires[wire.id] = wire
        
        main_window.clear_scene()
        ProjectController._load_project_to_scene(main_window, harness)
        
        main_window.db_loaded_bundles = project_data.get('bundles', [])
        
        main_window.project_handler.current_project = harness
        main_window.project_handler.current_path = None
        main_window.project_handler.modified = False
        
        mode = " [Read-Only]" if read_only else ""
        main_window.setWindowTitle(f"ECAD - {harness.name} (from database){mode}")
        
        main_window.db_read_only = read_only
        
        if main_window.db_loaded_bundles and not read_only:
            reply = QMessageBox.question(
                main_window,
                "Reconstruct Bundles",
                f"Found {len(main_window.db_loaded_bundles)} bundles in this project.\n"
                "Do you want to reconstruct them?",
                QMessageBox.Yes | QMessageBox.No
            )
            
            if reply == QMessageBox.Yes:
                main_window.reconstruct_bundles_from_data()
        
        dialog.accept()
        main_window.statusBar().showMessage(f"Loaded from database: {harness.name}", 3000)
    
    @staticmethod
    def reconstruct_bundles_from_data(main_window):
        """Reconstruct bundles from loaded database data"""
        if not hasattr(main_window, 'db_loaded_bundles') or not main_window.db_loaded_bundles:
            return
        
        from graphics.bundle_item import BundleItem
        from PyQt5.QtCore import QPointF
        
        print(f"Reconstructing {len(main_window.db_loaded_bundles)} bundles")
        
        for bundle_data in main_window.db_loaded_bundles:
            try:
                start_point = QPointF(
                    bundle_data.get('start_point_x', 0),
                    bundle_data.get('start_point_y', 0)
                )
                end_point = QPointF(
                    bundle_data.get('end_point_x', 0),
                    bundle_data.get('end_point_y', 0)
                )
                
                bundle = BundleItem(
                    start_point=start_point,
                    end_point=end_point,
                    bundle_id=bundle_data['id'],
                    main_window=main_window
                )
                
                if bundle_data.get('specified_length'):
                    bundle.set_specified_length(bundle_data['specified_length'])
                
                start_node = None
                end_node = None
                
                if bundle_data.get('start_node_id'):
                    for node in main_window.topology_manager.nodes.values():
                        if node.id == bundle_data['start_node_id']:
                            start_node = node
                            break
                
                if bundle_data.get('end_node_id'):
                    for node in main_window.topology_manager.nodes.values():
                        if node.id == bundle_data['end_node_id']:
                            end_node = node
                            break
                
                start_item = None
                end_item = None
                
                for conn in main_window.conns:
                    if conn.topology_node == start_node:
                        start_item = conn
                    if conn.topology_node == end_node:
                        end_item = conn
                
                if not start_item and start_node:
                    for item in main_window.scene.items():
                        if hasattr(item, 'branch_node') and item.branch_node == start_node:
                            start_item = item
                            break
                
                if not end_item and end_node:
                    for item in main_window.scene.items():
                        if hasattr(item, 'branch_node') and item.branch_node == end_node:
                            end_item = item
                            break
                
                bundle.set_start_node(start_node, start_item)
                bundle.set_end_node(end_node, end_item)
                
                if bundle_data.get('wire_ids'):
                    wire_ids = bundle_data['wire_ids']
                    if isinstance(wire_ids, str):
                        import json
                        try:
                            wire_ids = json.loads(wire_ids)
                        except:
                            wire_ids = []
                    
                    for wire_id in wire_ids:
                        bundle.assign_wire(wire_id)
                
                main_window.scene.addItem(bundle)
                main_window.bundles.append(bundle)
                
            except Exception as e:
                print(f"Error reconstructing bundle {bundle_data.get('id')}: {e}")
                import traceback
                traceback.print_exc()
        
        main_window.refresh_bundle_tree()
        print(f"Reconstructed {len(main_window.bundles)} bundles")
    
    @staticmethod
    def _load_project_to_scene(main_window, project):
        """Load project data into scene"""
        main_window.scene.clear()
        main_window.conns = []
        main_window.wires = []
        main_window.imported_wire_items = []
        
        for conn_id, connector in project.connectors.items():
            pin_ids = list(connector.pins.keys())
            pin_ids.sort()
            
            from graphics.connector_item import ConnectorItem
            conn_item = ConnectorItem(
                connector.position[0],
                connector.position[1],
                pins=pin_ids
            )
            conn_item.cid = conn_id
            conn_item.part_number = connector.part_number
            conn_item.manufacturer = connector.manufacturer
            
            conn_item.set_topology_manager(main_window.topology_manager)
            conn_item.set_main_window(main_window)
            conn_item.create_topology_node()
            
            main_window.scene.addItem(conn_item)
            main_window.conns.append(conn_item)
        
        from graphics.wire_item import WireItem
        from model.netlist import Netlist
        
        netlist = Netlist()
        main_window.topology_manager.set_netlist(netlist)
        
        for wire_id, wire in project.wires.items():
            from_conn = None
            to_conn = None
            
            for conn in main_window.conns:
                if conn.cid in wire.from_node_id:
                    from_conn = conn
                if conn.cid in wire.to_node_id:
                    to_conn = conn
            
            if not from_conn or not to_conn:
                continue
            
            from_pin = from_conn.get_pin_by_id(wire.from_pin) if wire.from_pin else None
            to_pin = to_conn.get_pin_by_id(wire.to_pin) if wire.to_pin else None
            
            if not from_pin or not to_pin:
                continue
            
            net = netlist.connect(from_pin, to_pin)
            
            wire_item = WireItem(
                wire.id,
                from_pin,
                to_pin,
                wire.color.base_color,
                net
            )
            wire_item.wire_data = wire
            wire_item.net = net
            
            main_window.scene.addItem(wire_item)
            main_window.imported_wire_items.append(wire_item)
            
            from_pin.wires.append(wire_item)
            to_pin.wires.append(wire_item)
        
        main_window.refresh_tree_views()
        main_window.refresh_connector_labels()
    
    @staticmethod
    def _load_bundles_from_project(main_window, filepath):
        """Load bundles from project file"""
        from database.project_db import ProjectDatabase
        
        db = ProjectDatabase(filepath)
        bundles_data = db.load_bundles()
        db.close()
        
        if bundles_data:
            print(f"Found {len(bundles_data)} bundles in project file")
            main_window.db_loaded_bundles = bundles_data
            main_window.reconstruct_bundles_from_data()
    
    @staticmethod
    def _create_project_from_scene(main_window):
        """Create project data from current scene"""
        from model.models import WiringHarness, Connector, Wire, Node, Pin
        from model.models import Gender, SealType, ConnectorType, WireType, NodeType
        from model.models import CombinedWireColor
        
        harness = main_window.project_handler.current_project or WiringHarness(name="Project")
        
        harness.connectors.clear()
        harness.wires.clear()
        harness.nodes.clear()
        harness.branches.clear()
        
        for conn_item in main_window.conns:
            connector = Connector(
                id=conn_item.cid,
                name=conn_item.cid,
                type=ConnectorType.OTHER,
                gender=Gender.FEMALE,
                seal=SealType.UNSEALED,
                part_number=getattr(conn_item, 'part_number', None),
                manufacturer=getattr(conn_item, 'manufacturer', None),
                position=(conn_item.pos().x(), conn_item.pos().y())
            )
            
            for pin_item in conn_item.pins:
                wire_id = None
                if pin_item.wires:
                    wire = pin_item.wires[0]
                    if hasattr(wire, 'wid'):
                        wire_id = wire.wid
                    elif hasattr(wire, 'wire') and hasattr(wire.wire, 'id'):
                        wire_id = wire.wire.id
                
                pin = Pin(
                    number=pin_item.original_id or pin_item.pid,
                    gender=Gender.FEMALE,
                    seal=SealType.UNSEALED,
                    wire_id=wire_id
                )
                connector.pins[pin.number] = pin
            
            harness.connectors[connector.id] = connector
            
            node = Node(
                id=f"NODE_{connector.id}",
                harness_id=harness.id,
                name=connector.id,
                type=NodeType.CONNECTOR,
                connector_id=connector.id,
                position=connector.position
            )
            harness.nodes[node.id] = node
        
        for wire_item in getattr(main_window, 'imported_wire_items', []):
            if hasattr(wire_item, 'wire_data'):
                wd = wire_item.wire_data
                
                wire = Wire(
                    id=wire_item.wid,
                    harness_id=harness.id,
                    type=WireType.FLRY_B_0_5,
                    color=CombinedWireColor(wd.color),
                    from_node_id=f"NODE_{wd.from_device}",
                    to_node_id=f"NODE_{wd.to_device}",
                    from_pin=wd.from_pin,
                    to_pin=wd.to_pin,
                    signal_name=wd.signal_name,
                    part_number=wd.part_number,
                    cross_section=wd.cross_section
                )
                harness.wires[wire.id] = wire
        
        return harness
