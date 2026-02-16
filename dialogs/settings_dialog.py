from PyQt5.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QTabWidget,
                             QWidget, QFormLayout, QLineEdit, QComboBox,
                             QSpinBox, QDoubleSpinBox, QCheckBox, QPushButton,
                             QGroupBox, QDialogButtonBox, QFileDialog,
                             QListWidget, QListWidgetItem, QMessageBox,
                             QLabel, QRadioButton, QButtonGroup)
from PyQt5.QtCore import Qt, pyqtSignal
from PyQt5.QtGui import QFont, QColor
from pathlib import Path

class SettingsDialog(QDialog):
    """Settings dialog for application configuration"""
    
    settings_changed = pyqtSignal()
    
    def __init__(self, settings_manager, parent=None):
        super().__init__(parent)
        self.settings_manager = settings_manager
        self.settings = settings_manager.settings
        
        self.setWindowTitle("Settings")
        self.setMinimumSize(800, 600)
        self.setModal(True)
        
        self.setup_ui()
        self.load_settings()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Tab widget for categories
        self.tabs = QTabWidget()
        
        # Create tabs
        self.tabs.addTab(self.create_general_tab(), "General")
        self.tabs.addTab(self.create_paths_tab(), "File Paths")
        self.tabs.addTab(self.create_appearance_tab(), "Appearance")
        self.tabs.addTab(self.create_behavior_tab(), "Behavior")
        self.tabs.addTab(self.create_defaults_tab(), "Defaults")
        self.tabs.addTab(self.create_manufacturing_tab(), "Manufacturing")
        
        layout.addWidget(self.tabs)
        
        # Dialog buttons
        button_box = QDialogButtonBox(QDialogButtonBox.Ok | 
                                      QDialogButtonBox.Cancel | 
                                      QDialogButtonBox.Apply)
        button_box.accepted.connect(self.accept)
        button_box.rejected.connect(self.reject)
        button_box.button(QDialogButtonBox.Apply).clicked.connect(self.apply_settings)
        
        layout.addWidget(button_box)
    
    def create_general_tab(self) -> QWidget:
        """General settings tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Autosave group
        autosave_group = QGroupBox("Autosave")
        autosave_layout = QFormLayout(autosave_group)
        
        self.autosave_interval = QSpinBox()
        self.autosave_interval.setRange(0, 60)
        self.autosave_interval.setSuffix(" minutes")
        self.autosave_interval.setSpecialValueText("Disabled")
        autosave_layout.addRow("Interval:", self.autosave_interval)
        
        self.autosave_path_display = QLineEdit()
        self.autosave_path_display.setReadOnly(True)
        autosave_layout.addRow("Path:", self.autosave_path_display)
        
        layout.addWidget(autosave_group)
        
        # Undo group
        undo_group = QGroupBox("Undo/Redo")
        undo_layout = QFormLayout(undo_group)
        
        self.undo_limit = QSpinBox()
        self.undo_limit.setRange(10, 200)
        undo_layout.addRow("Undo limit:", self.undo_limit)
        
        layout.addWidget(undo_group)
        
        # Recent files group
        recent_group = QGroupBox("Recent Files")
        recent_layout = QVBoxLayout(recent_group)
        
        recent_header = QHBoxLayout()
        recent_header.addWidget(QLabel("Maximum recent files:"))
        
        self.max_recent = QSpinBox()
        self.max_recent.setRange(5, 30)
        recent_header.addWidget(self.max_recent)
        recent_header.addStretch()
        
        recent_layout.addLayout(recent_header)
        
        self.recent_list = QListWidget()
        self.recent_list.setMaximumHeight(150)
        recent_layout.addWidget(self.recent_list)
        
        recent_buttons = QHBoxLayout()
        clear_btn = QPushButton("Clear List")
        clear_btn.clicked.connect(self.clear_recent_files)
        recent_buttons.addWidget(clear_btn)
        recent_buttons.addStretch()
        recent_layout.addLayout(recent_buttons)
        
        layout.addWidget(recent_group)
        
        layout.addStretch()
        return widget
    
    def create_paths_tab(self) -> QWidget:
        """File paths settings tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Database path
        db_group = QGroupBox("Database Location")
        db_layout = QHBoxLayout(db_group)
        
        self.db_path = QLineEdit()
        db_layout.addWidget(self.db_path)
        
        db_browse = QPushButton("Browse...")
        db_browse.clicked.connect(lambda: self.browse_path('db'))
        db_layout.addWidget(db_browse)
        
        layout.addWidget(db_group)
        
        # DXF library path
        dxf_group = QGroupBox("DXF Library")
        dxf_layout = QHBoxLayout(dxf_group)
        
        self.dxf_path = QLineEdit()
        dxf_layout.addWidget(self.dxf_path)
        
        dxf_browse = QPushButton("Browse...")
        dxf_browse.clicked.connect(lambda: self.browse_path('dxf'))
        dxf_layout.addWidget(dxf_browse)
        
        layout.addWidget(dxf_group)
        
        # Autosave path
        autosave_group = QGroupBox("Autosave Directory")
        autosave_layout = QHBoxLayout(autosave_group)
        
        self.autosave_path = QLineEdit()
        autosave_layout.addWidget(self.autosave_path)
        
        autosave_browse = QPushButton("Browse...")
        autosave_browse.clicked.connect(lambda: self.browse_path('autosave'))
        autosave_layout.addWidget(autosave_browse)
        
        layout.addWidget(autosave_group)
        
        # Default project location
        default_group = QGroupBox("Default Project Location")
        default_layout = QHBoxLayout(default_group)
        
        self.default_path = QLineEdit()
        default_layout.addWidget(self.default_path)
        
        default_browse = QPushButton("Browse...")
        default_browse.clicked.connect(lambda: self.browse_path('default'))
        default_layout.addWidget(default_browse)
        
        layout.addWidget(default_group)
        
        # Open buttons
        open_buttons = QHBoxLayout()
        
        open_db = QPushButton("Open Database Folder")
        open_db.clicked.connect(lambda: self.open_folder(self.db_path.text()))
        open_buttons.addWidget(open_db)
        
        open_dxf = QPushButton("Open DXF Library")
        open_dxf.clicked.connect(lambda: self.open_folder(self.dxf_path.text()))
        open_buttons.addWidget(open_dxf)
        
        open_buttons.addStretch()
        layout.addLayout(open_buttons)
        
        layout.addStretch()
        return widget
    
    def create_appearance_tab(self) -> QWidget:
        """Appearance settings tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Theme group
        theme_group = QGroupBox("Theme")
        theme_layout = QVBoxLayout(theme_group)
        
        self.theme_light = QRadioButton("Light")
        self.theme_dark = QRadioButton("Dark")
        self.theme_system = QRadioButton("System Default")
        self.theme_high = QRadioButton("High Contrast")
        
        theme_layout.addWidget(self.theme_light)
        theme_layout.addWidget(self.theme_dark)
        theme_layout.addWidget(self.theme_system)
        theme_layout.addWidget(self.theme_high)
        
        self.theme_group = QButtonGroup()
        self.theme_group.addButton(self.theme_light, 0)
        self.theme_group.addButton(self.theme_dark, 1)
        self.theme_group.addButton(self.theme_system, 2)
        self.theme_group.addButton(self.theme_high, 3)
        
        layout.addWidget(theme_group)
        
        # Grid settings
        grid_group = QGroupBox("Grid")
        grid_layout = QFormLayout(grid_group)
        
        self.show_grid = QCheckBox("Show Grid")
        grid_layout.addRow("", self.show_grid)
        
        self.grid_style = QComboBox()
        self.grid_style.addItems(["Lines", "Dots", "None"])
        grid_layout.addRow("Style:", self.grid_style)
        
        self.grid_size = QSpinBox()
        self.grid_size.setRange(10, 200)
        self.grid_size.setSuffix(" px")
        grid_layout.addRow("Size:", self.grid_size)
        
        layout.addWidget(grid_group)
        
        # Labels group
        labels_group = QGroupBox("Labels")
        labels_layout = QVBoxLayout(labels_group)
        
        self.show_connector_labels = QCheckBox("Show Connector Labels")
        self.show_pin_numbers = QCheckBox("Show Pin Numbers")
        self.antialiasing = QCheckBox("Anti-aliasing (smoother lines)")
        
        labels_layout.addWidget(self.show_connector_labels)
        labels_layout.addWidget(self.show_pin_numbers)
        labels_layout.addWidget(self.antialiasing)
        
        layout.addWidget(labels_group)
        
        # Preview
        preview_btn = QPushButton("Apply Theme Preview")
        preview_btn.clicked.connect(self.preview_theme)
        layout.addWidget(preview_btn)
        
        layout.addStretch()
        return widget
    
    def create_behavior_tab(self) -> QWidget:
        """Behavior settings tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Snapping
        snap_group = QGroupBox("Snapping")
        snap_layout = QVBoxLayout(snap_group)
        
        self.snap_to_grid = QCheckBox("Snap to Grid")
        self.snap_to_pins = QCheckBox("Snap to Pins")
        
        snap_layout.addWidget(self.snap_to_grid)
        snap_layout.addWidget(self.snap_to_pins)
        
        layout.addWidget(snap_group)
        
        # Auto-route
        route_group = QGroupBox("Auto-Routing")
        route_layout = QFormLayout(route_group)
        
        self.route_threshold = QSpinBox()
        self.route_threshold.setRange(1, 20)
        self.route_threshold.setSuffix(" wires")
        route_layout.addRow("Branch threshold:", self.route_threshold)
        
        self.use_curved = QCheckBox("Use curved wires")
        route_layout.addRow("", self.use_curved)
        
        self.bend_radius = QDoubleSpinBox()
        self.bend_radius.setRange(1, 100)
        self.bend_radius.setSuffix(" mm")
        route_layout.addRow("Bend radius:", self.bend_radius)
        
        layout.addWidget(route_group)
        
        # Selection
        select_group = QGroupBox("Selection")
        select_layout = QFormLayout(select_group)
        
        self.hover_highlight = QCheckBox("Highlight on hover")
        select_layout.addRow("", self.hover_highlight)
        
        layout.addWidget(select_group)
        
        layout.addStretch()
        return widget
    
    def create_defaults_tab(self) -> QWidget:
        """Default values tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Wire defaults
        wire_group = QGroupBox("Wire Defaults")
        wire_layout = QFormLayout(wire_group)
        
        self.default_gauge = QDoubleSpinBox()
        self.default_gauge.setRange(0.1, 10)
        self.default_gauge.setSingleStep(0.1)
        self.default_gauge.setSuffix(" mm²")
        wire_layout.addRow("Cross section:", self.default_gauge)
        
        self.default_color = QComboBox()
        colors = ['SW', 'RT', 'GN', 'BL', 'GE', 'BR', 'WS', 'GR']
        self.default_color.addItems(colors)
        wire_layout.addRow("Color:", self.default_color)
        
        layout.addWidget(wire_group)
        
        # Connector defaults
        conn_group = QGroupBox("Connector Defaults")
        conn_layout = QFormLayout(conn_group)
        
        self.default_pin_count = QSpinBox()
        self.default_pin_count.setRange(1, 100)
        conn_layout.addRow("Pin count:", self.default_pin_count)
        
        layout.addWidget(conn_group)
        
        layout.addStretch()
        return widget
    
    def create_manufacturing_tab(self) -> QWidget:
        """Manufacturing settings tab"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Output settings
        output_group = QGroupBox("Output")
        output_layout = QFormLayout(output_group)
        
        self.output_units = QComboBox()
        self.output_units.addItems(["mm", "inch"])
        output_layout.addRow("Units:", self.output_units)
        
        self.service_loop = QDoubleSpinBox()
        self.service_loop.setRange(0, 50)
        self.service_loop.setSuffix("%")
        output_layout.addRow("Service loop:", self.service_loop)
        
        layout.addWidget(output_group)
        
        # Export options
        export_group = QGroupBox("Export Options")
        export_layout = QVBoxLayout(export_group)
        
        self.export_bom = QCheckBox("Include BOM in export")
        self.export_hdt = QCheckBox("Generate Harness Drawing Table")
        self.export_connector_charts = QCheckBox("Generate Connector Charts")
        
        export_layout.addWidget(self.export_bom)
        export_layout.addWidget(self.export_hdt)
        export_layout.addWidget(self.export_connector_charts)
        
        layout.addWidget(export_group)
        
        layout.addStretch()
        return widget
    
    def load_settings(self):
        """Load current settings into UI"""
        # General
        self.autosave_interval.setValue(self.settings.autosave_interval)
        self.autosave_path_display.setText(self.settings.autosave_path)
        self.undo_limit.setValue(self.settings.undo_limit)
        self.max_recent.setValue(self.settings.max_recent_files)
        
        # Recent files
        self.recent_list.clear()
        for file in self.settings.recent_files:
            if Path(file).exists():
                self.recent_list.addItem(file)
        
        # Paths
        self.db_path.setText(self.settings.database_path)
        self.dxf_path.setText(self.settings.dxf_library_path)
        self.autosave_path.setText(self.settings.autosave_path)
        self.default_path.setText(str(Path.home() / "ecad" / "projects"))
        
        # Appearance
        theme_map = {
            'light': 0, 'dark': 1, 'system': 2, 'high_contrast': 3
        }
        self.theme_group.button(theme_map.get(self.settings.theme, 2)).setChecked(True)
        
        self.show_grid.setChecked(self.settings.show_grid)
        grid_map = {'lines': 0, 'dots': 1, 'none': 2}
        self.grid_style.setCurrentIndex(grid_map.get(self.settings.grid_style, 0))
        self.grid_size.setValue(self.settings.grid_size)
        self.show_connector_labels.setChecked(self.settings.show_connector_labels)
        self.show_pin_numbers.setChecked(self.settings.show_pin_numbers)
        self.antialiasing.setChecked(self.settings.antialiasing)
        
        # Behavior
        self.snap_to_grid.setChecked(self.settings.snap_to_grid)
        self.snap_to_pins.setChecked(self.settings.snap_to_pins)
        self.route_threshold.setValue(self.settings.auto_route_threshold)
        self.use_curved.setChecked(self.settings.use_curved_wires)
        self.bend_radius.setValue(self.settings.bend_radius)
        self.hover_highlight.setChecked(True)  # Default
        
        # Defaults
        self.default_gauge.setValue(self.settings.default_wire_gauge)
        idx = self.default_color.findText(self.settings.default_wire_color)
        if idx >= 0:
            self.default_color.setCurrentIndex(idx)
        self.default_pin_count.setValue(self.settings.default_connector_pin_count)
        
        # Manufacturing
        units_map = {'mm': 0, 'inch': 1}
        self.output_units.setCurrentIndex(units_map.get(self.settings.output_units, 0))
        self.service_loop.setValue(self.settings.service_loop_percent)
    
    def apply_settings(self):
        """Apply settings from UI to settings object"""
        # General
        self.settings.autosave_interval = self.autosave_interval.value()
        self.settings.undo_limit = self.undo_limit.value()
        self.settings.max_recent_files = self.max_recent.value()
        
        # Paths
        self.settings.database_path = self.db_path.text()
        self.settings.dxf_library_path = self.dxf_path.text()
        self.settings.autosave_path = self.autosave_path.text()
        
        # Appearance
        theme_map = {0: 'light', 1: 'dark', 2: 'system', 3: 'high_contrast'}
        self.settings.theme = theme_map[self.theme_group.checkedId()]
        
        self.settings.show_grid = self.show_grid.isChecked()
        style_map = {0: 'lines', 1: 'dots', 2: 'none'}
        self.settings.grid_style = style_map[self.grid_style.currentIndex()]
        self.settings.grid_size = self.grid_size.value()
        self.settings.show_connector_labels = self.show_connector_labels.isChecked()
        self.settings.show_pin_numbers = self.show_pin_numbers.isChecked()
        self.settings.antialiasing = self.antialiasing.isChecked()
        
        # Behavior
        self.settings.snap_to_grid = self.snap_to_grid.isChecked()
        self.settings.snap_to_pins = self.snap_to_pins.isChecked()
        self.settings.auto_route_threshold = self.route_threshold.value()
        self.settings.use_curved_wires = self.use_curved.isChecked()
        self.settings.bend_radius = self.bend_radius.value()
        
        # Defaults
        self.settings.default_wire_gauge = self.default_gauge.value()
        self.settings.default_wire_color = self.default_color.currentText()
        self.settings.default_connector_pin_count = self.default_pin_count.value()
        
        # Manufacturing
        units_map = {0: 'mm', 1: 'inch'}
        self.settings.output_units = units_map[self.output_units.currentIndex()]
        self.settings.service_loop_percent = self.service_loop.value()
        
        # Save settings
        self.settings_manager.save()
        
        # Notify
        self.settings_changed.emit()
    
    def accept(self):
        """Accept and apply settings"""
        self.apply_settings()
        super().accept()
    
    def browse_path(self, path_type: str):
        """Browse for directory path"""
        current = getattr(self, f"{path_type}_path").text()
        
        directory = QFileDialog.getExistingDirectory(
            self,
            f"Select {path_type.upper()} Directory",
            current or str(Path.home())
        )
        
        if directory:
            getattr(self, f"{path_type}_path").setText(directory)
    
    def open_folder(self, path: str):
        """Open folder in file explorer"""
        import subprocess
        import platform
        
        path = Path(path)
        if not path.exists():
            path.mkdir(parents=True)
        
        if platform.system() == "Windows":
            subprocess.run(['explorer', str(path)])
        elif platform.system() == "Darwin":
            subprocess.run(['open', str(path)])
        else:
            subprocess.run(['xdg-open', str(path)])
    
    def clear_recent_files(self):
        """Clear recent files list"""
        self.settings.recent_files = []
        self.recent_list.clear()
        self.settings_manager.save()
    
    def preview_theme(self):
        """Preview theme without saving"""
        # Get selected theme
        theme_map = {0: 'light', 1: 'dark', 2: 'system', 3: 'high_contrast'}
        theme = theme_map[self.theme_group.checkedId()]
        
        # Create temporary settings object
        from utils.settings_manager import SettingsManager, AppSettings
        temp_manager = SettingsManager()
        temp_manager.settings.theme = theme
        
        # Apply stylesheet
        self.parent().setStyleSheet(temp_manager.get_theme_stylesheet())
