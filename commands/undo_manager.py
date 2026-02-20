from PyQt5.QtWidgets import QUndoStack, QUndoView, QDockWidget,QAction
from PyQt5.QtCore import Qt, pyqtSignal
from typing import Optional
from .base_command import BaseCommand
from PyQt5 import sip
class UndoManager:
    """Central manager for undo/redo operations"""
    
    def __init__(self, main_window):
        self.main_window = main_window
        self.undo_stack = QUndoStack(main_window)
        
        # Connect signals
        self.undo_stack.canUndoChanged.connect(self._update_undo_action)
        self.undo_stack.canRedoChanged.connect(self._update_redo_action)
        self.undo_stack.cleanChanged.connect(self._update_save_state)
    
    def push(self, command: BaseCommand):
        """Push a command onto the undo stack"""
        self.undo_stack.push(command)
        
        # Update status bar
        self.main_window.statusBar().showMessage(
            f"Performed: {command.text()}", 2000
        )
    
    def begin_macro(self, text: str):
        """Start a macro (group of commands)"""
        self.undo_stack.beginMacro(text)
    
    def end_macro(self):
        """End current macro"""
        self.undo_stack.endMacro()
    
    def undo(self):
        """Undo last command"""
        if self.undo_stack.canUndo():
            self.undo_stack.undo()
            self.main_window.statusBar().showMessage(
                f"Undo: {self.undo_stack.undoText()}", 2000
            )
    
    def redo(self):
        """Redo last undone command"""
        if self.undo_stack.canRedo():
            self.undo_stack.redo()
            self.main_window.statusBar().showMessage(
                f"Redo: {self.undo_stack.redoText()}", 2000
            )
    
    def clear(self):
        """Clear undo stack"""
        self.undo_stack.clear()
    
    def is_dirty(self) -> bool:
        """Check if there are unsaved changes"""
        return not self.undo_stack.isClean()
    
    def set_clean(self):
        """Mark current state as clean (after save)"""
        self.undo_stack.setClean()
    
    def create_undo_view(self) -> QDockWidget:
        """Create a dock widget showing undo history"""
        dock = QDockWidget("Undo History", self.main_window)
        undo_view = QUndoView(self.undo_stack)
        dock.setWidget(undo_view)
        return dock
    
    def _update_undo_action(self, can_undo: bool):
        """Update undo action state"""
        # Find undo action in main window
        if not sip.isdeleted(self.main_window):

            for action in self.main_window.findChildren(QAction):
                if action.text() == "&Undo":
                    action.setEnabled(can_undo)
                    if can_undo:
                        action.setText(f"&Undo {self.undo_stack.undoText()}")
                    else:
                        action.setText("&Undo")
                    break
    
    def _update_redo_action(self, can_redo: bool):
        """Update redo action state"""
        if not sip.isdeleted(self.main_window):
            for action in self.main_window.findChildren(QAction):
                if action.text().startswith("&Redo"):
                    action.setEnabled(can_redo)
                    if can_redo:
                        action.setText(f"&Redo {self.undo_stack.redoText()}")
                    else:
                        action.setText("&Redo")
                    break
        
    def _update_save_state(self, clean: bool):
        """Update window title to show unsaved changes"""
        title = self.main_window.windowTitle()
        if clean:
            if title.endswith("*"):
                self.main_window.setWindowTitle(title[:-2])
        else:
            if not title.endswith("*"):
                self.main_window.setWindowTitle(title + " *")
