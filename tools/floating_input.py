from PyQt5.QtWidgets import QLineEdit, QFrame, QVBoxLayout, QLabel
from PyQt5.QtCore import Qt, QPoint, pyqtSignal, QEvent
from PyQt5.QtGui import QFont, QColor, QPalette, QCursor

class FloatingInputWindow(QFrame):
    """Floating input window that follows cursor (like AutoCAD)"""
    
    value_entered = pyqtSignal(float)
    cancelled = pyqtSignal()
    
    def __init__(self, parent=None, prompt="Enter length:"):
        super().__init__(parent)
        self.setWindowFlags(Qt.Tool | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFocusPolicy(Qt.StrongFocus)
        
        # Style
        self.setStyleSheet("""
            QFrame {
                background-color: rgba(40, 40, 40, 220);
                border: 2px solid #0078d4;
                border-radius: 5px;
            }
            QLineEdit {
                background-color: rgba(60, 60, 60, 200);
                color: white;
                border: 1px solid #555;
                border-radius: 3px;
                padding: 5px;
                font-size: 12px;
                min-width: 150px;
            }
            QLabel {
                color: #aaa;
                font-size: 10px;
                padding: 2px 5px;
            }
        """)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        
        # Prompt label
        self.prompt_label = QLabel(prompt)
        self.prompt_label.setStyleSheet("color: #aaa; font-size: 10px;")
        layout.addWidget(self.prompt_label)
        
        # Input field
        self.input_field = QLineEdit()
        self.input_field.setPlaceholderText("Enter value...")
        self.input_field.returnPressed.connect(self.on_enter)
        layout.addWidget(self.input_field)
        
        # Unit hint
        self.unit_label = QLabel("(mm)")
        self.unit_label.setStyleSheet("color: #666; font-size: 8px;")
        layout.addWidget(self.unit_label)
        
        self.setFixedSize(self.sizeHint())
        
        # Ensure input field gets focus
        self.input_field.setFocus()
    
    def show_at_cursor(self):
        """Show window at current cursor position"""
        cursor_pos = QCursor.pos()
        self.move(cursor_pos.x() + 20, cursor_pos.y() - self.height() // 2)
        self.show()
        self.raise_()
        self.activateWindow()
        self.input_field.setFocus()
        self.input_field.selectAll()
    
    def on_enter(self):
        """Handle enter key"""
        try:
            value = float(self.input_field.text())
            self.value_entered.emit(value)
            self.hide()
        except ValueError:
            # Invalid input, clear and show error
            self.input_field.clear()
            self.prompt_label.setStyleSheet("color: #ff5555;")
            self.prompt_label.setText("Invalid number! Enter length:")
            self.input_field.setFocus()
    
    def keyPressEvent(self, event):
        """Handle key events"""
        if event.key() == Qt.Key_Escape:
            self.cancelled.emit()
            self.hide()
        elif event.key() == Qt.Key_Return or event.key() == Qt.Key_Enter:
            self.on_enter()
        else:
            super().keyPressEvent(event)
    
    def focusOutEvent(self, event):
        """Handle focus out - don't hide automatically, let the tool decide"""
        # Don't hide on focus out - we want to keep it visible
        pass
