from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QFormLayout,
                             QLineEdit, QComboBox, QPushButton, QTableWidget,
                             QTableWidgetItem, QHeaderView, QLabel, QSpinBox,
                             QDialogButtonBox, QGroupBox, QSplitter, QWidget)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QColor
from database.connector_db import ConnectorDatabase, ConnectorGender, SealType

class ConnectorSelectorDialog(QDialog):
    """Dialog for selecting connectors from database"""
    
    connector_selected = pyqtSignal(dict)  # Emits selected connector data
    
    def __init__(self, db: ConnectorDatabase, parent=None):
        super().__init__(parent)
        self.db = db
        self.selected_connector = None
        self.setWindowTitle("Select Connector from Database")
        self.setMinimumSize(900, 600)
        
        self.setup_ui()
        self.load_manufacturers()
        self.search()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Search filters group
        filter_group = QGroupBox("Search Filters")
        filter_layout = QFormLayout(filter_group)
        
        # Manufacturer combo
        self.manufacturer_combo = QComboBox()
        self.manufacturer_combo.addItem("All", None)
        self.manufacturer_combo.currentIndexChanged.connect(self.on_filter_changed)
        filter_layout.addRow("Manufacturer:", self.manufacturer_combo)
        
        # Series combo
        self.series_combo = QComboBox()
        self.series_combo.addItem("All", None)
        self.series_combo.currentIndexChanged.connect(self.on_filter_changed)
        filter_layout.addRow("Series:", self.series_combo)
        
        # Part number search
        self.part_search = QLineEdit()
        self.part_search.setPlaceholderText("Enter part number...")
        self.part_search.textChanged.connect(self.on_filter_changed)
        filter_layout.addRow("Part Number:", self.part_search)
        
        # Cavity count range
        cavity_layout = QHBoxLayout()
        self.min_cavities = QSpinBox()
        self.min_cavities.setRange(0, 100)
        self.min_cavities.setSpecialValueText("Min")
        self.min_cavities.valueChanged.connect(self.on_filter_changed)
        cavity_layout.addWidget(self.min_cavities)
        
        cavity_layout.addWidget(QLabel("to"))
        
        self.max_cavities = QSpinBox()
        self.max_cavities.setRange(0, 100)
        self.max_cavities.setSpecialValueText("Max")
        self.max_cavities.valueChanged.connect(self.on_filter_changed)
        cavity_layout.addWidget(self.max_cavities)
        
        filter_layout.addRow("Cavities:", cavity_layout)
        
        # Search button
        search_btn = QPushButton("Search")
        search_btn.clicked.connect(self.search)
        filter_layout.addRow("", search_btn)
        
        layout.addWidget(filter_group)
        
        # Results table
        self.results_table = QTableWidget()
        self.results_table.setColumnCount(5)
        self.results_table.setHorizontalHeaderLabels([
            "Part Number", "Manufacturer", "Series", "Description", "Cavities"
        ])
        self.results_table.horizontalHeader().setSectionResizeMode(QHeaderView.Stretch)
        self.results_table.setSelectionBehavior(QTableWidget.SelectRows)
        self.results_table.setSelectionMode(QTableWidget.SingleSelection)
        self.results_table.itemSelectionChanged.connect(self.on_selection_changed)
        self.results_table.doubleClicked.connect(self.accept)
        
        layout.addWidget(self.results_table)
        
        # Preview area
        preview_group = QGroupBox("Preview")
        preview_layout = QHBoxLayout(preview_group)
        preview_layout.addWidget(QLabel("Selected connector details will appear here"))
        layout.addWidget(preview_group)
        self.populate()
        # Dialog buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        layout.addWidget(button_box)
    
    def load_manufacturers(self):
        """Populate manufacturer dropdown"""
        manufacturers = self.db.get_manufacturers()
        self.manufacturer_combo.clear()
        self.manufacturer_combo.addItem("All", None)
        for m in manufacturers:
            self.manufacturer_combo.addItem(m, m)
    
    def load_series(self, manufacturer: str = None):
        """Populate series dropdown"""
        self.series_combo.clear()
        self.series_combo.addItem("All", None)
        
        series_list = self.db.get_series(manufacturer)
        for s in series_list:
            self.series_combo.addItem(s, s)
    
    def on_filter_changed(self):
        """Handle filter changes"""
        # Update series when manufacturer changes
        if self.sender() == self.manufacturer_combo:
            manuf = self.manufacturer_combo.currentData()
            self.load_series(manuf)
        
        self.search()
    
    def populate(self):
        results = self.db.search_connectors(
            
        )
        self.results_table.setRowCount(len(results))
        for i, row in enumerate(results):
            self.results_table.setItem(i, 0, QTableWidgetItem(row['part_number']))
            self.results_table.setItem(i, 1, QTableWidgetItem(row['manufacturer']))
            self.results_table.setItem(i, 2, QTableWidgetItem(row['series']))
            self.results_table.setItem(i, 3, QTableWidgetItem(row['description']))
            self.results_table.setItem(i, 4, QTableWidgetItem(str(row['cavity_count'])))
    def search(self):
        """Execute search with current filters"""
        manufacturer = self.manufacturer_combo.currentData()
        series = self.series_combo.currentData()
        part_search = self.part_search.text() or None
        min_cav = self.min_cavities.value() if self.min_cavities.value() > 0 else None
        max_cav = self.max_cavities.value() if self.max_cavities.value() > 0 else None
        
        results = self.db.search_connectors(
            manufacturer=manufacturer,
            series=series,
            part_number_contains=part_search,
            min_cavities=min_cav,
            max_cavities=max_cav
        )
        
        self.results_table.setRowCount(len(results))
        for i, row in enumerate(results):
            self.results_table.setItem(i, 0, QTableWidgetItem(row['part_number']))
            self.results_table.setItem(i, 1, QTableWidgetItem(row['manufacturer']))
            self.results_table.setItem(i, 2, QTableWidgetItem(row['series']))
            self.results_table.setItem(i, 3, QTableWidgetItem(row['description']))
            self.results_table.setItem(i, 4, QTableWidgetItem(str(row['cavity_count'])))
    
    def on_selection_changed(self):
        """Handle selection change in results table"""
        selected = self.results_table.selectedItems()
        if selected:
            row = selected[0].row()
            part_number = self.results_table.item(row, 0).text()
            
            # Load full connector data
            self.selected_connector = self.db.get_connector(part_number)
    
    def get_selected_connector(self):
        """Return the selected connector data"""
        return self.selected_connector
