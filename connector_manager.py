import sys
import os
from pathlib import Path
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QTableWidget, QTableWidgetItem,
                             QHeaderView, QMessageBox, QToolBar, QAction, QFileDialog,
                             QLabel, QSplitter, QTabWidget, QGroupBox, QFormLayout,
                             QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox, QCheckBox,
                             QTextEdit, QDialog, QDialogButtonBox, QMenuBar, QMenu,
                             QStatusBar, QProgressBar, QTreeWidget, QTreeWidgetItem,
                             QMessageBox)
from PyQt5.QtCore import Qt, pyqtSignal, QSize
from PyQt5.QtGui import QIcon, QFont, QColor

# Import our database modules
from database.connector_db import ConnectorDatabase, ConnectorPart, Cavity, ConnectorGender, SealType
from utils.settings_manager import SettingsManager

class ConnectorManagerMainWindow(QMainWindow):
    """Main window for connector database management"""
    
    def __init__(self, db_path=None):
        super().__init__()
        self.settings_manager = SettingsManager("ECAD")
        
        # Use provided db path or from settings
        if db_path:
            self.db_path = db_path
        else:
            self.db_path = self.settings_manager.get('database_path', 'connectors.db')+ "connectors.db"
        print(self.db_path)
        self.db = ConnectorDatabase(db_path = self.db_path)
        self.current_connector = None
        
        self.setWindowTitle("Connector Database Manager")
        self.setMinimumSize(1200, 800)
        
        # Apply theme from settings
        self.setStyleSheet(self.settings_manager.get_theme_stylesheet())
        
        self.setup_ui()
        
        self.create_menus()
        self.create_toolbars()
        self.load_connector_list()
        self.statusBar().showMessage(f"Database: {self.db_path}", 3000)

    def setup_ui(self):
        """Setup the main UI layout"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QVBoxLayout(central_widget)
        
        # Create splitter for left/right panels
        splitter = QSplitter(Qt.Horizontal)
        
        # Left panel - Connector list
        left_panel = self.create_left_panel()
        splitter.addWidget(left_panel)
        
        # Right panel - Tabs for details
        right_panel = self.create_right_panel()
        splitter.addWidget(right_panel)
        
        # Set initial sizes (30% left, 70% right)
        splitter.setSizes([300, 700])
        
        main_layout.addWidget(splitter)
    
    def create_left_panel(self) -> QWidget:
        """Create left panel with connector list and filters"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(5, 5, 5, 5)
        
        # Search/filter group
        filter_group = QGroupBox("Filter")
        filter_layout = QFormLayout(filter_group)
        
        self.filter_manufacturer = QComboBox()
        self.filter_manufacturer.addItem("All", None)
        self.filter_manufacturer.currentIndexChanged.connect(self.apply_filters)
        filter_layout.addRow("Manufacturer:", self.filter_manufacturer)
        
        self.filter_series = QComboBox()
        self.filter_series.blockSignals(True)
        self.filter_series.addItem("All", None)
        self.filter_series.currentIndexChanged.connect(self.apply_filters)
        filter_layout.addRow("Series:", self.filter_series)
        
        self.filter_part = QLineEdit()
        self.filter_part.setPlaceholderText("Part number contains...")
        self.filter_part.textChanged.connect(self.apply_filters)
        filter_layout.addRow("Part #:", self.filter_part)
        
        layout.addWidget(filter_group)
        
        # Connector list
        list_group = QGroupBox("Connectors")
        list_layout = QVBoxLayout(list_group)
        
        self.connector_tree = QTreeWidget()
        self.connector_tree.setHeaderLabels(["Part Number", "Manufacturer", "Series", "Cavities"])
        self.connector_tree.header().setSectionResizeMode(0, QHeaderView.Stretch)
        self.connector_tree.header().setSectionResizeMode(1, QHeaderView.ResizeToContents)
        self.connector_tree.header().setSectionResizeMode(2, QHeaderView.ResizeToContents)
        self.connector_tree.header().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.connector_tree.itemSelectionChanged.connect(self.on_connector_selected)
        list_layout.addWidget(self.connector_tree)
        
        # List buttons
        btn_layout = QHBoxLayout()
        
        add_btn = QPushButton("Add New")
        add_btn.clicked.connect(self.add_connector)
        btn_layout.addWidget(add_btn)
        
        edit_btn = QPushButton("Edit")
        edit_btn.clicked.connect(self.edit_connector)
        btn_layout.addWidget(edit_btn)
        
        delete_btn = QPushButton("Delete")
        delete_btn.clicked.connect(self.delete_connector)
        btn_layout.addWidget(delete_btn)
        
        btn_layout.addStretch()
        list_layout.addLayout(btn_layout)
        
        layout.addWidget(list_group)
        self.filter_series.blockSignals(False)
        return widget
    
    def create_right_panel(self) -> QWidget:
        """Create right panel with tabs for connector details"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(5, 5, 5, 5)
        
        self.tabs = QTabWidget()
        
        # Overview tab
        self.tabs.addTab(self.create_overview_tab(), "Overview")
        
        # Cavities tab
        self.tabs.addTab(self.create_cavities_tab(), "Cavities")
        
        # DXF tab
        self.tabs.addTab(self.create_dxf_tab(), "DXF Layout")
        
        # Specifications tab
        self.tabs.addTab(self.create_specs_tab(), "Specifications")
        
        layout.addWidget(self.tabs)
        
        return widget
    
    def create_overview_tab(self) -> QWidget:
        """Create overview tab with basic connector info"""
        widget = QWidget()
        layout = QFormLayout(widget)
        layout.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)
        
        # Read-only fields for display
        self.overview_part = QLineEdit()
        self.overview_part.setReadOnly(True)
        layout.addRow("Part Number:", self.overview_part)
        
        self.overview_manufacturer = QLineEdit()
        self.overview_manufacturer.setReadOnly(True)
        layout.addRow("Manufacturer:", self.overview_manufacturer)
        
        self.overview_series = QLineEdit()
        self.overview_series.setReadOnly(True)
        layout.addRow("Series:", self.overview_series)
        
        self.overview_description = QTextEdit()
        self.overview_description.setReadOnly(True)
        self.overview_description.setMaximumHeight(80)
        layout.addRow("Description:", self.overview_description)
        
        self.overview_gender = QLineEdit()
        self.overview_gender.setReadOnly(True)
        layout.addRow("Gender:", self.overview_gender)
        
        self.overview_seal = QLineEdit()
        self.overview_seal.setReadOnly(True)
        layout.addRow("Seal Type:", self.overview_seal)
        
        self.overview_cavities = QLineEdit()
        self.overview_cavities.setReadOnly(True)
        layout.addRow("Cavity Count:", self.overview_cavities)
        
        self.overview_color = QLineEdit()
        self.overview_color.setReadOnly(True)
        layout.addRow("Housing Color:", self.overview_color)
        
        self.overview_dxf = QLineEdit()
        self.overview_dxf.setReadOnly(True)
        layout.addRow("DXF File:", self.overview_dxf)
        
        self.overview_datasheet = QLineEdit()
        self.overview_datasheet.setReadOnly(True)
        layout.addRow("Datasheet URL:", self.overview_datasheet)
        
        return widget
    
    def create_cavities_tab(self) -> QWidget:
        """Create tab for cavity management"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Cavity table
        self.cavity_table = QTableWidget()
        self.cavity_table.setColumnCount(7)
        self.cavity_table.setHorizontalHeaderLabels([
            "Cavity", "X Position", "Y Position", "Terminal Type",
            "Seal Required", "Min Gauge", "Max Gauge"
        ])
        self.cavity_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        layout.addWidget(self.cavity_table)
        
        return widget
    
    def create_dxf_tab(self) -> QWidget:
        """Create tab for DXF preview"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        self.dxf_label = QLabel("No DXF file loaded")
        self.dxf_label.setAlignment(Qt.AlignCenter)
        self.dxf_label.setStyleSheet("border: 1px solid gray; background-color: #f0f0f0;")
        self.dxf_label.setMinimumHeight(300)
        layout.addWidget(self.dxf_label)
        
        btn_layout = QHBoxLayout()
        
        self.load_dxf_btn = QPushButton("Load DXF")
        self.load_dxf_btn.clicked.connect(self.load_dxf_for_current)
        btn_layout.addWidget(self.load_dxf_btn)
        
        self.view_dxf_btn = QPushButton("View Full Size")
        self.view_dxf_btn.clicked.connect(self.view_dxf_full)
        btn_layout.addWidget(self.view_dxf_btn)
        
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        
        return widget
    
    def create_specs_tab(self) -> QWidget:
        """Create tab for detailed specifications"""
        widget = QWidget()
        layout = QFormLayout(widget)
        
        self.spec_notes = QTextEdit()
        self.spec_notes.setReadOnly(True)
        layout.addRow("Notes:", self.spec_notes)
        
        return widget
    
    def create_menus(self):
        """Create menu bar"""
        menubar = self.menuBar()
        
        # File menu
        file_menu = menubar.addMenu("&File")
        
        change_db_action = QAction("Change Database...", self)
        change_db_action.triggered.connect(self.change_database)
        file_menu.addAction(change_db_action)
        
        file_menu.addSeparator()
        
        import_action = QAction("Import from DXF...", self)
        import_action.triggered.connect(self.import_from_dxf)
        file_menu.addAction(import_action)
        
        export_action = QAction("Export to CSV...", self)
        export_action.triggered.connect(self.export_to_csv)
        file_menu.addAction(export_action)
        
        file_menu.addSeparator()
        
        exit_action = QAction("Exit", self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)
        
        # Edit menu
        edit_menu = menubar.addMenu("&Edit")
        
        add_action = QAction("Add Connector", self)
        add_action.triggered.connect(self.add_connector)
        edit_menu.addAction(add_action)
        
        edit_action = QAction("Edit Connector", self)
        edit_action.triggered.connect(self.edit_connector)
        edit_menu.addAction(edit_action)
        
        delete_action = QAction("Delete Connector", self)
        delete_action.triggered.connect(self.delete_connector)
        edit_menu.addAction(delete_action)
        
        # View menu
        view_menu = menubar.addMenu("&View")
        
        refresh_action = QAction("Refresh", self)
        refresh_action.triggered.connect(self.load_connector_list)
        view_menu.addAction(refresh_action)
        
        # Help menu
        help_menu = menubar.addMenu("&Help")
        
        about_action = QAction("About", self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)
    
    def create_toolbars(self):
        """Create toolbars"""
        # Main toolbar
        toolbar = QToolBar("Main")
        toolbar.setIconSize(QSize(24, 24))
        self.addToolBar(toolbar)
        
        # Add actions
        add_action = QAction("➕ Add", self)
        add_action.triggered.connect(self.add_connector)
        toolbar.addAction(add_action)
        
        edit_action = QAction("✏️ Edit", self)
        edit_action.triggered.connect(self.edit_connector)
        toolbar.addAction(edit_action)
        
        delete_action = QAction("🗑️ Delete", self)
        delete_action.triggered.connect(self.delete_connector)
        toolbar.addAction(delete_action)
        
        toolbar.addSeparator()
        
        import_action = QAction("📥 Import DXF", self)
        import_action.triggered.connect(self.import_from_dxf)
        toolbar.addAction(import_action)
        
        toolbar.addSeparator()
        
        refresh_action = QAction("🔄 Refresh", self)
        refresh_action.triggered.connect(self.load_connector_list)
        toolbar.addAction(refresh_action)
    
    def load_connector_list(self):
        """Load connectors into tree view"""
        self.connector_tree.clear()
        self.filter_series.blockSignals(True)
        # Load manufacturers for filter
        manufacturers = self.db.get_manufacturers()
        self.filter_manufacturer.blockSignals(True)
        self.filter_manufacturer.clear()
        self.filter_manufacturer.addItem("All", None)
        for m in manufacturers:
            self.filter_manufacturer.addItem(m, m)
        self.filter_manufacturer.blockSignals(False)
        
        # Get all connectors
        print("load_connector_list")
        results = self.db.search_connectors(all_cons = True)
        
        for conn in results:
            item = QTreeWidgetItem([
                conn['part_number'],
                conn['manufacturer'],
                conn['series'],
                str(conn['cavity_count'])
            ])
            item.setData(0, Qt.UserRole, conn['part_number'])
            self.connector_tree.addTopLevelItem(item)
        self.filter_series.blockSignals(False)
    def apply_filters(self):
        """Apply filters to connector list"""
        manufacturer = self.filter_manufacturer.currentData()
        series = self.filter_series.currentData()
        part_filter = self.filter_part.text() or None
        self.filter_series.blockSignals(True)
        # Update series filter based on manufacturer
        if manufacturer:
            print("here")
            series_list = self.db.get_series(manufacturer)
            self.filter_series.clear()
            self.filter_series.addItem("All", None)
            for s in series_list:
                self.filter_series.addItem(s, s)
        print("filter")
        # Apply filters
        results = self.db.search_connectors(
            manufacturer=manufacturer,
            series=series,
            part_number_contains=part_filter
        )
        
        self.connector_tree.clear()
        for conn in results:
            item = QTreeWidgetItem([
                conn['part_number'],
                conn['manufacturer'],
                conn['series'],
                str(conn['cavity_count'])
            ])
            item.setData(0, Qt.UserRole, conn['part_number'])
            self.connector_tree.addTopLevelItem(item)
        self.filter_series.blockSignals(False)
    def on_connector_selected(self):
        """Handle connector selection"""
        selected = self.connector_tree.selectedItems()
        if not selected:
            self.clear_details()
            return
        
        part_number = selected[0].data(0, Qt.UserRole)
        self.current_connector = self.db.get_connector(part_number)
        self.display_connector_details()
    
    def display_connector_details(self):
        """Display current connector details in tabs"""
        if not self.current_connector:
            return
        
        conn = self.current_connector
        
        # Overview tab
        self.overview_part.setText(conn.part_number)
        self.overview_manufacturer.setText(conn.manufacturer)
        self.overview_series.setText(conn.series)
        self.overview_description.setText(conn.description)
        self.overview_gender.setText(conn.gender.value)
        self.overview_seal.setText(conn.seal_type.value)
        self.overview_cavities.setText(str(conn.cavity_count))
        self.overview_color.setText(conn.housing_color or "")
        self.overview_dxf.setText(str(conn.dxf_path) if conn.dxf_path else "")
        self.overview_datasheet.setText(conn.datasheet_url or "")
        
        # Cavities tab
        self.cavity_table.setRowCount(len(conn.cavities))
        for i, (num, cavity) in enumerate(conn.cavities.items()):
            self.cavity_table.setItem(i, 0, QTableWidgetItem(num))
            self.cavity_table.setItem(i, 1, QTableWidgetItem(f"{cavity.position_x:.2f}"))
            self.cavity_table.setItem(i, 2, QTableWidgetItem(f"{cavity.position_y:.2f}"))
            self.cavity_table.setItem(i, 3, QTableWidgetItem(cavity.terminal_type or ""))
            self.cavity_table.setItem(i, 4, QTableWidgetItem("Yes" if cavity.seal_required else "No"))
            self.cavity_table.setItem(i, 5, QTableWidgetItem(f"{cavity.min_wire_gauge:.2f}"))
            self.cavity_table.setItem(i, 6, QTableWidgetItem(f"{cavity.max_wire_gauge:.2f}"))
        
        # DXF tab
        if conn.dxf_path and Path(conn.dxf_path).exists():
            self.dxf_label.setText(f"DXF file: {Path(conn.dxf_path).name}")
        else:
            self.dxf_label.setText("No DXF file loaded")
        
        # Specs tab
        self.spec_notes.setText(conn.notes or "")
    
    def clear_details(self):
        """Clear all detail displays"""
        self.current_connector = None
        
        # Clear overview
        self.overview_part.clear()
        self.overview_manufacturer.clear()
        self.overview_series.clear()
        self.overview_description.clear()
        self.overview_gender.clear()
        self.overview_seal.clear()
        self.overview_cavities.clear()
        self.overview_color.clear()
        self.overview_dxf.clear()
        self.overview_datasheet.clear()
        
        # Clear cavities
        self.cavity_table.setRowCount(0)
        
        # Clear DXF
        self.dxf_label.setText("No connector selected")
        
        # Clear specs
        self.spec_notes.clear()
    
    def add_connector(self):
        """Add new connector"""
        dialog = ConnectorEditDialog(self.db, None, self)
        if dialog.exec_():
            self.load_connector_list()
            self.statusBar().showMessage("Connector added successfully", 3000)
    
    def edit_connector(self):
        """Edit current connector"""
        if not self.current_connector:
            QMessageBox.warning(self, "No Selection", "Please select a connector to edit")
            return
        
        dialog = ConnectorEditDialog(self.db, self.current_connector, self)
        if dialog.exec_():
            self.load_connector_list()
            self.on_connector_selected()  # Refresh display
            self.statusBar().showMessage("Connector updated successfully", 3000)
    
    def delete_connector(self):
        """Delete current connector"""
        if not self.current_connector:
            QMessageBox.warning(self, "No Selection", "Please select a connector to delete")
            return
        
        reply = QMessageBox.question(
            self,
            "Confirm Delete",
            f"Are you sure you want to delete {self.current_connector.part_number}?",
            QMessageBox.Yes | QMessageBox.No
        )
        
        if reply == QMessageBox.Yes:
            # Implement delete in database
            self.statusBar().showMessage("Delete not yet implemented", 3000)
    
    def change_database(self):
        """Change database file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select Database",
            str(Path(self.db_path).parent),
            "Database Files (*.db);;All Files (*)"
        )
        
        if file_path:
            self.db_path = file_path
            self.db = ConnectorDatabase(self.db_path)
            self.load_connector_list()
            self.statusBar().showMessage(f"Switched to database: {file_path}", 3000)
    
    def import_from_dxf(self):
        """Import connector from DXF file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select DXF File",
            str(Path.home()),
            "DXF Files (*.dxf);;All Files (*)"
        )
        
        if file_path:
            # Show import dialog
            dialog = DXFImportDialog(file_path, self)
            if dialog.exec_():
                self.load_connector_list()
                self.statusBar().showMessage("Connector imported from DXF", 3000)
    
    def export_to_csv(self):
        """Export connectors to CSV"""
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Save CSV File",
            str(Path.home() / "connectors.csv"),
            "CSV Files (*.csv);;All Files (*)"
        )
        
        if file_path:
            # Implement CSV export
            self.statusBar().showMessage(f"Exporting to {file_path}", 3000)
    
    def load_dxf_for_current(self):
        """Load DXF file for current connector"""
        if not self.current_connector:
            return
        
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select DXF File",
            str(Path.home()),
            "DXF Files (*.dxf);;All Files (*)"
        )
        
        if file_path:
            # Update connector with DXF path
            self.current_connector.dxf_path = Path(file_path)
            self.display_connector_details()
            self.statusBar().showMessage(f"DXF loaded: {Path(file_path).name}", 3000)
    
    def view_dxf_full(self):
        """View DXF in full size window"""
        if not self.current_connector or not self.current_connector.dxf_path:
            QMessageBox.warning(self, "No DXF", "No DXF file available for this connector")
            return
        
        # Open in external viewer or create preview window
        self.statusBar().showMessage("Full DXF view - to be implemented", 3000)
    
    def show_about(self):
        """Show about dialog"""
        QMessageBox.about(
            self,
            "About Connector Database Manager",
            "ECAD Connector Database Manager\n\n"
            "Version 1.0\n\n"
            "Manage your connector library with DXF cavity layouts."
        )


class ConnectorEditDialog(QDialog):
    """Dialog for adding/editing connectors"""
    
    def __init__(self, db, connector=None, parent=None):
        super().__init__(parent)
        self.db = db
        self.connector = connector
        self.cavities = []
        
        self.setWindowTitle("Edit Connector" if connector else "Add New Connector")
        self.setMinimumSize(600, 500)
        
        self.setup_ui()
        
        if connector:
            self.load_connector_data()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Create tabs
        tabs = QTabWidget()
        
        # Basic info tab
        basic_tab = self.create_basic_tab()
        tabs.addTab(basic_tab, "Basic Info")
        
        # Cavities tab
        self.cavities_tab = self.create_cavities_tab()
        tabs.addTab(self.cavities_tab, "Cavities")
        
        # DXF tab
        dxf_tab = self.create_dxf_tab()
        tabs.addTab(dxf_tab, "DXF")
        
        layout.addWidget(tabs)
        
        # Buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
    
    def create_basic_tab(self) -> QWidget:
        """Create basic info tab"""
        widget = QWidget()
        layout = QFormLayout(widget)
        layout.setFieldGrowthPolicy(QFormLayout.ExpandingFieldsGrow)
        
        self.edit_part = QLineEdit()
        layout.addRow("Part Number:*", self.edit_part)
        
        self.edit_manufacturer = QComboBox()
        self.edit_manufacturer.setEditable(True)
        manufacturers = self.db.get_manufacturers()
        self.edit_manufacturer.addItems(manufacturers)
        layout.addRow("Manufacturer:*", self.edit_manufacturer)
        
        self.edit_series = QLineEdit()
        layout.addRow("Series:*", self.edit_series)
        
        self.edit_description = QTextEdit()
        self.edit_description.setMaximumHeight(80)
        layout.addRow("Description:", self.edit_description)
        
        self.edit_gender = QComboBox()
        self.edit_gender.addItems([g.value for g in ConnectorGender])
        layout.addRow("Gender:", self.edit_gender)
        
        self.edit_seal = QComboBox()
        self.edit_seal.addItems([s.value for s in SealType])
        layout.addRow("Seal Type:", self.edit_seal)
        
        self.edit_color = QLineEdit()
        self.edit_color.setPlaceholderText("e.g., Gray, Black")
        layout.addRow("Housing Color:", self.edit_color)
        
        self.edit_datasheet = QLineEdit()
        layout.addRow("Datasheet URL:", self.edit_datasheet)
        
        self.edit_notes = QTextEdit()
        self.edit_notes.setMaximumHeight(80)
        layout.addRow("Notes:", self.edit_notes)
        
        return widget
    
    def create_cavities_tab(self) -> QWidget:
        """Create cavities management tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Cavity table
        self.cavity_edit_table = QTableWidget()
        self.cavity_edit_table.setColumnCount(7)
        self.cavity_edit_table.setHorizontalHeaderLabels([
            "Cavity", "X", "Y", "Terminal Type", "Seal", "Min Gauge", "Max Gauge"
        ])
        layout.addWidget(self.cavity_edit_table)
        
        # Buttons for cavity management
        btn_layout = QHBoxLayout()
        
        add_cavity_btn = QPushButton("Add Cavity")
        add_cavity_btn.clicked.connect(self.add_cavity_row)
        btn_layout.addWidget(add_cavity_btn)
        
        remove_cavity_btn = QPushButton("Remove Selected")
        remove_cavity_btn.clicked.connect(self.remove_selected_cavity)
        btn_layout.addWidget(remove_cavity_btn)
        
        import_from_dxf_btn = QPushButton("Import from DXF")
        import_from_dxf_btn.clicked.connect(self.import_cavities_from_dxf)
        btn_layout.addWidget(import_from_dxf_btn)
        
        btn_layout.addStretch()
        layout.addLayout(btn_layout)
        
        return widget
    
    def create_dxf_tab(self) -> QWidget:
        """Create DXF import tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        self.dxf_file_path = QLineEdit()
        self.dxf_file_path.setReadOnly(True)
        layout.addWidget(self.dxf_file_path)
        
        browse_btn = QPushButton("Browse DXF File...")
        browse_btn.clicked.connect(self.browse_dxf)
        layout.addWidget(browse_btn)
        
        preview_label = QLabel("DXF preview will appear here")
        preview_label.setAlignment(Qt.AlignCenter)
        preview_label.setMinimumHeight(200)
        preview_label.setStyleSheet("border: 1px solid gray;")
        layout.addWidget(preview_label)
        
        return widget
    
    def load_connector_data(self):
        """Load existing connector data into form"""
        if not self.connector:
            return
        
        self.edit_part.setText(self.connector.part_number)
        
        idx = self.edit_manufacturer.findText(self.connector.manufacturer)
        if idx >= 0:
            self.edit_manufacturer.setCurrentIndex(idx)
        else:
            self.edit_manufacturer.setEditText(self.connector.manufacturer)
        
        self.edit_series.setText(self.connector.series)
        self.edit_description.setText(self.connector.description)
        
        gender_idx = self.edit_gender.findText(self.connector.gender.value)
        if gender_idx >= 0:
            self.edit_gender.setCurrentIndex(gender_idx)
        
        seal_idx = self.edit_seal.findText(self.connector.seal_type.value)
        if seal_idx >= 0:
            self.edit_seal.setCurrentIndex(seal_idx)
        
        self.edit_color.setText(self.connector.housing_color or "")
        self.edit_datasheet.setText(self.connector.datasheet_url or "")
        self.edit_notes.setText(self.connector.notes or "")
        
        # Load cavities
        self.cavities = list(self.connector.cavities.values())
        self.refresh_cavity_table()
    
    def refresh_cavity_table(self):
        """Refresh cavity table from self.cavities"""
        self.cavity_edit_table.setRowCount(len(self.cavities))
        for i, cavity in enumerate(self.cavities):
            self.cavity_edit_table.setItem(i, 0, QTableWidgetItem(cavity.number))
            self.cavity_edit_table.setItem(i, 1, QTableWidgetItem(f"{cavity.position_x:.2f}"))
            self.cavity_edit_table.setItem(i, 2, QTableWidgetItem(f"{cavity.position_y:.2f}"))
            self.cavity_edit_table.setItem(i, 3, QTableWidgetItem(cavity.terminal_type or ""))
            
            seal_item = QTableWidgetItem()
            seal_item.setFlags(seal_item.flags() | Qt.ItemIsUserCheckable)
            seal_item.setCheckState(Qt.Checked if cavity.seal_required else Qt.Unchecked)
            self.cavity_edit_table.setItem(i, 4, seal_item)
            
            self.cavity_edit_table.setItem(i, 5, QTableWidgetItem(f"{cavity.min_wire_gauge:.2f}"))
            self.cavity_edit_table.setItem(i, 6, QTableWidgetItem(f"{cavity.max_wire_gauge:.2f}"))
    
    def add_cavity_row(self):
        """Add a new empty cavity row"""
        self.cavities.append(Cavity(
            number=f"{(len(self.cavities) + 1)}",
            position_x=0,
            position_y=0
        ))
        self.refresh_cavity_table()
    
    def remove_selected_cavity(self):
        """Remove selected cavity rows"""
        selected = self.cavity_edit_table.selectedIndexes()
        rows = sorted(set(idx.row() for idx in selected), reverse=True)
        
        for row in rows:
            if row < len(self.cavities):
                del self.cavities[row]
        
        self.refresh_cavity_table()
    
    def browse_dxf(self):
        """Browse for DXF file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select DXF File",
            str(Path.home()),
            "DXF Files (*.dxf);;All Files (*)"
        )
        
        if file_path:
            self.dxf_file_path.setText(file_path)
    
    def import_cavities_from_dxf(self):
        """Import cavity positions from DXF"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select DXF File for Cavity Import",
            str(Path.home()),
            "DXF Files (*.dxf);;All Files (*)"
        )
        
        if file_path:
            # This would parse DXF and populate cavities
            QMessageBox.information(self, "Import", "DXF import to be implemented")
    
    def accept(self):
        """Save connector data"""
        # Validate required fields
        if not self.edit_part.text():
            QMessageBox.warning(self, "Validation Error", "Part Number is required")
            return
        
        if not self.edit_manufacturer.currentText():
            QMessageBox.warning(self, "Validation Error", "Manufacturer is required")
            return
        
        if not self.edit_series.text():
            QMessageBox.warning(self, "Validation Error", "Series is required")
            return
        
        # Create connector object
        from database.connector_db import ConnectorPart, ConnectorGender, SealType
        
        # Get gender enum
        gender = ConnectorGender.FEMALE
        if self.edit_gender.currentText() == "male":
            gender = ConnectorGender.MALE
        
        # Get seal enum
        seal = SealType.UNSEALED
        seal_text = self.edit_seal.currentText()
        for s in SealType:
            if s.value == seal_text:
                seal = s
                break
        
        # Build cavities dictionary
        cavities = {}
        for i in range(self.cavity_edit_table.rowCount()):
            num_item = self.cavity_edit_table.item(i, 0)
            if not num_item or not num_item.text():
                continue
            
            cavity = Cavity(
                number=num_item.text(),
                position_x=float(self.cavity_edit_table.item(i, 1).text() or "0"),
                position_y=float(self.cavity_edit_table.item(i, 2).text() or "0"),
                terminal_type=self.cavity_edit_table.item(i, 3).text() or None,
                seal_required=self.cavity_edit_table.item(i, 4).checkState() == Qt.Checked,
                min_wire_gauge=float(self.cavity_edit_table.item(i, 5).text() or "0.35"),
                max_wire_gauge=float(self.cavity_edit_table.item(i, 6).text() or "2.5")
            )
            cavities[num_item.text()] = cavity
        
        connector = ConnectorPart(
            part_number=self.edit_part.text(),
            manufacturer=self.edit_manufacturer.currentText(),
            series=self.edit_series.text(),
            description=self.edit_description.toPlainText(),
            gender=gender,
            seal_type=seal,
            cavity_count=len(cavities),
            cavities=cavities,
            dxf_path=Path(self.dxf_file_path.text()) if self.dxf_file_path.text() else None,
            housing_color=self.edit_color.text() or None,
            datasheet_url=self.edit_datasheet.text() or None,
            notes=self.edit_notes.toPlainText() or None
        )
        
        # Save to database
        try:
            with open(self.dxf_file_path.text(), 'rb') as f:
                dxf_content = f.read()
        except:
            dxf_content = None
        
        self.db.add_connector(connector, dxf_content)
        
        super().accept()


class DXFImportDialog(QDialog):
    """Dialog for importing connectors from DXF"""
    
    def __init__(self, dxf_path, parent=None):
        super().__init__(parent)
        self.dxf_path = dxf_path
        self.setWindowTitle("Import from DXF")
        self.setMinimumSize(500, 400)
        
        layout = QVBoxLayout(self)
        
        layout.addWidget(QLabel(f"Importing: {Path(dxf_path).name}"))
        
        # Form for connector data
        form = QFormLayout()
        
        self.import_part = QLineEdit()
        self.import_part.setText(Path(dxf_path).stem)
        form.addRow("Part Number:", self.import_part)
        
        self.import_manufacturer = QComboBox()
        self.import_manufacturer.setEditable(True)
        # Would load manufacturers from DB
        form.addRow("Manufacturer:", self.import_manufacturer)
        
        self.import_series = QLineEdit()
        form.addRow("Series:", self.import_series)
        
        self.import_description = QLineEdit()
        form.addRow("Description:", self.import_description)
        
        self.import_gender = QComboBox()
        self.import_gender.addItems([g.value for g in ConnectorGender])
        form.addRow("Gender:", self.import_gender)
        
        layout.addLayout(form)
        
        # Preview of detected cavities
        layout.addWidget(QLabel("Detected Cavities:"))
        self.cavity_preview = QTableWidget()
        self.cavity_preview.setColumnCount(2)
        self.cavity_preview.setHorizontalHeaderLabels(["Cavity", "Position"])
        layout.addWidget(self.cavity_preview)
        
        # Buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)


def main():
    """Main entry point"""
    app = QApplication(sys.argv)
    
    # Allow command line argument for database path
    db_path = sys.argv[1] if len(sys.argv) > 1 else None
    try:
        if db_path[-3:] != '.db':
            db_path += 'connectors.db'
            print(db_path[-3:])
    except:
        pass
    print("!!",db_path)
    window = ConnectorManagerMainWindow(db_path)
    window.show()
    
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
