#!/usr/bin/env python3
"""
ECAD - Electrical CAD for Wiring Harness Design
Main application entry point
"""

import sys
from PyQt5.QtWidgets import QApplication
from PyQt5.QtGui import QIcon
from ui.main_window import MainWindow


def main():
    """Main entry point"""
    app = QApplication(sys.argv)
    app.setApplicationName("ECAD")
    app.setOrganizationName("ECAD")
    
    window = MainWindow()
    window.resize(1000, 800)
    window.show()
    
    sys.exit(app.exec_())


if __name__ == "__main__":
    main()
