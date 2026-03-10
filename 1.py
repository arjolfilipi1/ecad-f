import sys
from PyQt5.QtWidgets import (QApplication, QDialog, QVBoxLayout, QHBoxLayout, 
                             QTableWidget, QTableWidgetItem, QPushButton, 
                             QHeaderView, QLabel, QLineEdit, QGroupBox)
from PyQt5.QtCore import Qt
import inspect

class AttributeViewerDialog(QDialog):
    def __init__(self, target_object, parent=None):
        super().__init__(parent)
        self.target_object = target_object
        self.setWindowTitle(f"Attributes of {target_object.__class__.__name__}")
        self.setMinimumSize(600, 400)
        
        # Create main layout
        layout = QVBoxLayout(self)
        
        # Add object info
        info_layout = QHBoxLayout()
        info_label = QLabel(f"<b>Object:</b> {target_object.__class__.__name__} at {hex(id(target_object))}")
        info_layout.addWidget(info_label)
        info_layout.addStretch()
        layout.addLayout(info_layout)
        
        # Create filter input
        filter_layout = QHBoxLayout()
        filter_label = QLabel("Filter:")
        self.filter_input = QLineEdit()
        self.filter_input.setPlaceholderText("Type to filter attributes...")
        self.filter_input.textChanged.connect(self.filter_attributes)
        filter_layout.addWidget(filter_label)
        filter_layout.addWidget(self.filter_input)
        layout.addLayout(filter_layout)
        
        # Create table for attributes
        self.table = QTableWidget()
        self.table.setColumnCount(4)
        self.table.setHorizontalHeaderLabels(["Attribute", "Type", "Value", "Category"])
        
        # Set column widths
        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(1, QHeaderView.ResizeToContents)
        header.setSectionResizeMode(2, QHeaderView.Stretch)
        header.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        
        layout.addWidget(self.table)
        
        # Buttons
        button_layout = QHBoxLayout()
        refresh_btn = QPushButton("Refresh")
        refresh_btn.clicked.connect(self.refresh_attributes)
        expand_btn = QPushButton("Expand All")
        expand_btn.clicked.connect(self.expand_all)
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        
        button_layout.addWidget(refresh_btn)
        button_layout.addWidget(expand_btn)
        button_layout.addStretch()
        button_layout.addWidget(close_btn)
        layout.addLayout(button_layout)
        
        # Store all attributes for filtering
        self.all_attributes = []
        
        # Load attributes
        self.load_attributes()
    
    def get_attribute_category(self, attr_name):
        """Determine the category of an attribute"""
        if attr_name.startswith('__') and attr_name.endswith('__'):
            return "Special Methods"
        elif attr_name.startswith('_'):
            return "Protected/Private"
        elif callable(getattr(self.target_object, attr_name, None)):
            return "Methods"
        else:
            return "Attributes"
    
    def get_attribute_value_str(self, value):
        """Convert attribute value to string representation"""
        try:
            if callable(value):
                return f"<function {value.__name__}>"
            elif isinstance(value, (str, int, float, bool, type(None))):
                return str(value)
            elif hasattr(value, '__class__'):
                return f"{value.__class__.__name__} object"
            else:
                return str(value)
        except Exception as e:
            return f"<Error: {str(e)}>"
    
    def load_attributes(self):
        """Load all attributes of the target object"""
        self.all_attributes = []
        
        # Get all attributes using inspect
        for attr_name in dir(self.target_object):
            try:
                value = getattr(self.target_object, attr_name)
                attr_type = type(value).__name__
                value_str = self.get_attribute_value_str(value)
                category = self.get_attribute_category(attr_name)
                
                self.all_attributes.append({
                    'name': attr_name,
                    'type': attr_type,
                    'value': value_str,
                    'category': category
                })
            except Exception as e:
                # Handle attributes that might raise exceptions when accessed
                self.all_attributes.append({
                    'name': attr_name,
                    'type': 'Error',
                    'value': f'<Error accessing: {str(e)}>',
                    'category': 'Error'
                })
        
        # Sort attributes by name
        self.all_attributes.sort(key=lambda x: x['name'])
        
        # Display all attributes
        self.display_attributes(self.all_attributes)
    
    def display_attributes(self, attributes):
        """Display attributes in the table"""
        self.table.setRowCount(len(attributes))
        
        for row, attr in enumerate(attributes):
            # Attribute name
            name_item = QTableWidgetItem(attr['name'])
            name_item.setFlags(name_item.flags() & ~Qt.ItemIsEditable)
            self.table.setItem(row, 0, name_item)
            
            # Type
            type_item = QTableWidgetItem(attr['type'])
            type_item.setFlags(type_item.flags() & ~Qt.ItemIsEditable)
            self.table.setItem(row, 1, type_item)
            
            # Value
            value_item = QTableWidgetItem(attr['value'])
            value_item.setFlags(value_item.flags() & ~Qt.ItemIsEditable)
            self.table.setItem(row, 2, value_item)
            
            # Category
            category_item = QTableWidgetItem(attr['category'])
            category_item.setFlags(category_item.flags() & ~Qt.ItemIsEditable)
            self.table.setItem(row, 3, category_item)
    
    def filter_attributes(self, filter_text):
        """Filter attributes based on text input"""
        filter_text = filter_text.lower()
        
        if not filter_text:
            self.display_attributes(self.all_attributes)
            return
        
        filtered = [attr for attr in self.all_attributes 
                   if filter_text in attr['name'].lower() 
                   or filter_text in attr['type'].lower()
                   or filter_text in attr['category'].lower()]
        
        self.display_attributes(filtered)
    
    def refresh_attributes(self):
        """Refresh the attribute list"""
        self.filter_input.clear()
        self.load_attributes()
    
    def expand_all(self):
        """Expand all rows (adjusts row heights)"""
        for row in range(self.table.rowCount()):
            self.table.setRowHeight(row, self.table.rowHeight(row))

# Example class to demonstrate the dialog
class Person:
    def __init__(self, name, age, city):
        self.name = name
        self.age = age
        self._private_id = 12345
        self.__very_private = "Secret"
        self.city = city
    
    def greet(self):
        return f"Hello, I'm {self.name}"
    
    def _internal_method(self):
        pass
    
    @property
    def full_info(self):
        return f"{self.name}, {self.age} from {self.city}"

# Example usage
if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    # Create a test object
    person = Person("Alice", 30, "New York")
    
    # Create and show the dialog
    dialog = AttributeViewerDialog(person)
    dialog.show()
    
    sys.exit(app.exec_())
