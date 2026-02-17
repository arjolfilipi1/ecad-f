import json
import os
from pathlib import Path
from dataclasses import dataclass, field, asdict
from typing import Optional, Dict, Any
from enum import Enum

class Theme(Enum):
    LIGHT = "light"
    DARK = "dark"
    SYSTEM = "system"
    HIGH_CONTRAST = "high_contrast"

class GridStyle(Enum):
    DOTS = "dots"
    LINES = "lines"
    NONE = "none"

@dataclass
class AppSettings:
    """Application settings data class"""
    
    # File paths
    database_path: str = str(Path.home() / "ecad" / "connectors.db")
    dxf_library_path: str = str(Path.home() / "ecad" / "dxf_library")
    autosave_path: str = str(Path.home() / "ecad" / "autosave")
    recent_files: list = field(default_factory=list)
    max_recent_files: int = 10
    
    # Appearance
    theme: str = Theme.SYSTEM.value
    grid_style: str = GridStyle.LINES.value
    grid_size: int = 50
    show_grid: bool = True
    show_connector_labels: bool = True
    show_pin_numbers: bool = True
    antialiasing: bool = True
    
    # Behavior
    autosave_interval: int = 5  # minutes
    undo_limit: int = 50
    snap_to_grid: bool = True
    snap_to_pins: bool = True
    
    # Defaults for new designs
    default_wire_gauge: float = 0.5
    default_wire_color: str = "SW"
    default_connector_pin_count: int = 2
    
    # Auto-route settings
    auto_route_threshold: int = 2  # wires needed to create branch point
    use_curved_wires: bool = True
    bend_radius: float = 10.0
    
    # Manufacturing
    service_loop_percent: float = 7.0  # extra length for service loops
    output_units: str = "mm"  # mm or inch
    
    # Window state
    window_geometry: Optional[dict] = None
    toolbar_layout: Optional[dict] = None
    
    def to_dict(self) -> dict:
        """Convert to dictionary for JSON serialization"""
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> 'AppSettings':
        """Create from dictionary"""
        # Filter to only valid fields
        valid_fields = {k: v for k, v in data.items() 
                       if k in cls.__dataclass_fields__}
        return cls(**valid_fields)

class SettingsManager:
    """Manages application settings persistence"""
    
    def __init__(self, app_name: str = "ECAD"):
        self.app_name = app_name
        self.config_dir = self._get_config_dir()
        self.config_file = self.config_dir / "settings.json"
        self.settings = AppSettings()
        
        # Ensure directories exist
        self.config_dir.mkdir(parents=True, exist_ok=True)
        
        # Load settings
        self.load()
        
        # Create necessary directories
        self._ensure_directories()
    
    def _get_config_dir(self) -> Path:
        """Get platform-specific config directory"""
        import platform
        
        system = platform.system()
        
        if system == "Windows":
            base = Path(os.environ.get('APPDATA', Path.home() / 'AppData' / 'Roaming'))
        elif system == "Darwin":  # macOS
            base = Path.home() / 'Library' / 'Application Support'
        else:  # Linux/Unix
            base = Path.home() / '.config'
        
        return base / self.app_name
    
    def _ensure_directories(self):
        """Create all configured directories if they don't exist"""
        directories = [
            Path(self.settings.database_path).parent,
            Path(self.settings.dxf_library_path),
            Path(self.settings.autosave_path)
        ]
        
        for directory in directories:
            directory.mkdir(parents=True, exist_ok=True)
    
    def load(self):
        """Load settings from file"""
        if not self.config_file.exists():
            # Create default settings file
            self.save()
            return
        
        try:
            with open(self.config_file, 'r') as f:
                data = json.load(f)
                self.settings = AppSettings.from_dict(data)
        except Exception as e:
            print(f"Error loading settings: {e}")
            # Use defaults on error
    
    def save(self):
        """Save settings to file"""
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self.settings.to_dict(), f, indent=2)
        except Exception as e:
            print(f"Error saving settings: {e}")
    
    def get(self, key: str, default=None):
        """Get a setting value by key"""
        return getattr(self.settings, key, default)
    
    def set(self, key: str, value):
        """Set a setting value and save"""
        if hasattr(self.settings, key):
            setattr(self.settings, key, value)
            self.save()
    
    def add_recent_file(self, filepath: str):
        """Add a file to recent files list"""
        # Convert to string if Path
        filepath = str(filepath)
        
        # Remove if already exists
        if filepath in self.settings.recent_files:
            self.settings.recent_files.remove(filepath)
        
        # Add to front
        self.settings.recent_files.insert(0, filepath)
        
        # Trim to max size
        self.settings.recent_files = self.settings.recent_files[:self.settings.max_recent_files]
        
        self.save()
    
    def get_recent_files(self) -> list:
        """Get list of recent files"""
        return [f for f in self.settings.recent_files if Path(f).exists()]
    
    def get_theme_stylesheet(self) -> str:
        """Get Qt stylesheet for current theme"""
        if self.settings.theme == Theme.DARK.value:
            return self._get_dark_theme()
        elif self.settings.theme == Theme.HIGH_CONTRAST.value:
            return self._get_high_contrast_theme()
        else:
            return self._get_light_theme()
    
    def _get_light_theme(self) -> str:
        """Light theme stylesheet"""
        return """
        QMainWindow {
            background-color: #f0f0f0;
        }
        QDockWidget {
            titlebar-close-icon: url(close.png);
            titlebar-normal-icon: url(undock.png);
        }
        QToolBar {
            background-color: #e0e0e0;
            border: 1px solid #c0c0c0;
            spacing: 3px;
        }
        QTreeWidget {
            background-color: white;
            alternate-background-color: #f5f5f5;
        }
        QTreeWidget::item:selected {
            background-color: #0078d4;
            color: white;
        }
        QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {
            background-color: white;
            border: 1px solid #c0c0c0;
            padding: 3px;
            border-radius: 3px;
        }
        QLineEdit:focus, QComboBox:focus, QSpinBox:focus {
            border: 1px solid #0078d4;
        }
        QPushButton {
            background-color: #e0e0e0;
            border: 1px solid #c0c0c0;
            padding: 5px 10px;
            border-radius: 3px;
        }
        QPushButton:hover {
            background-color: #d0d0d0;
        }
        QPushButton:pressed {
            background-color: #c0c0c0;
        }
        QGroupBox {
            border: 1px solid #c0c0c0;
            border-radius: 5px;
            margin-top: 10px;
            font-weight: bold;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 5px 0 5px;
        }
        QTabWidget::pane {
            border: 1px solid #c0c0c0;
            background-color: white;
        }
        QTabBar::tab {
            background-color: #e0e0e0;
            border: 1px solid #c0c0c0;
            padding: 5px 10px;
            margin-right: 2px;
        }
        QTabBar::tab:selected {
            background-color: white;
            border-bottom-color: white;
        }
        """
    
    def _get_dark_theme(self) -> str:
        """Dark theme stylesheet"""
        return """
        QMainWindow {
            background-color: #2d2d30;
            color: #f0f0f0;
        }
        QDockWidget {
            color: #f0f0f0;

            
            titlebar-close-icon: url(close.png);
            titlebar-normal-icon: url(undock.png);
        }
        QAction{
            color: #f0f0f0;
        }
        
        QToolBar {
            background-color: #3c3c3c;
            border: 1px solid #555555;
            
            spacing: 3px;
        }
        QTreeWidget {
            background-color: #252526;
            alternate-background-color: #2a2a2b;
            color: #f0f0f0;
        }
        QTreeWidget::item:selected {
            background-color: #0078d4;
            color: white;
        }
        QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {
            background-color: #3c3c3c;
            border: 1px solid #555555;
            color: #f0f0f0;
            padding: 3px;
            border-radius: 3px;
        }
        QLineEdit:focus, QComboBox:focus, QSpinBox:focus {
            border: 1px solid #0078d4;
        }
        QPushButton {
            background-color: #3c3c3c;
            border: 1px solid #555555;
            color: #f0f0f0;
            padding: 5px 10px;
            border-radius: 3px;
        }
        QPushButton:hover {
            background-color: #4c4c4c;
        }
        QPushButton:pressed {
            background-color: #2c2c2c;
        }
        QGroupBox {
            border: 1px solid #555555;
            border-radius: 5px;
            margin-top: 10px;
            font-weight: bold;
            color: #f0f0f0;
        }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 10px;
            padding: 0 5px 0 5px;
        }
        QTabWidget::pane {
        
            border: 1px solid #555555;
            background-color: #252526;
        }
        QTabBar::tab {
        
            background-color: #3c3c3c;
            border: 1px solid #555555;
            color: #f0f0f0;
            padding: 5px 10px;
            margin-right: 2px;
        }
        QTabBar::tab:selected {
            background-color: #0078d4;
        }
        QLabel {
            color: #f0f0f0;
        }
        QCheckBox {
            color: #f0f0f0;
        }
        QRadioButton {
            color: #f0f0f0;
        }
        QWidget#properties{
            color: black;
            background-color: #2d2d30;
        }
        """
    
    def _get_high_contrast_theme(self) -> str:
        """High contrast theme for accessibility"""
        return """
        QMainWindow {
            background-color: black;
            color: white;
        }
        QDockWidget {
            color: white;
        }
        QToolBar {
            background-color: black;
            border: 2px solid white;
        }
        QTreeWidget {
            background-color: black;
            color: white;
            border: 2px solid white;
        }
        QTreeWidget::item:selected {
            background-color: white;
            color: black;
        }
        QLineEdit, QComboBox, QSpinBox, QDoubleSpinBox {
            background-color: black;
            border: 2px solid white;
            color: white;
        }
        QPushButton {
            background-color: black;
            border: 2px solid white;
            color: white;
            padding: 5px;
        }
        QPushButton:hover {
            background-color: #333333;
        }
        QGroupBox {
            border: 2px solid white;
            margin-top: 10px;
            color: white;
        }
        QTabWidget::pane {
            border: 2px solid white;
            background-color: black;
        }
        QTabBar::tab {
            background-color: black;
            border: 2px solid white;
            color: white;
            padding: 5px;
        }
        QTabBar::tab:selected {
            background-color: white;
            color: black;
        }
        QLabel, QCheckBox, QRadioButton {
            color: white;
        }
        """
