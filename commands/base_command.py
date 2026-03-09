from PyQt5.QtWidgets import QUndoCommand
from abc import ABC, abstractmethod, ABCMeta
from typing import Any, Dict, Optional
from datetime import datetime

QtMeta = type(QUndoCommand)

class CommandMeta(QtMeta, ABCMeta):
    pass
    
class BaseCommand(QUndoCommand, ABC, metaclass=CommandMeta):
    """Base class for all undo/redo commands"""
    
    def __init__(self, description: str = "Command"):
        super().__init__(description)
        self.timestamp = datetime.now()
        self._initialized = False
    
    @abstractmethod
    def undo(self):
        """Undo the command"""
        pass
    
    @abstractmethod
    def _initialize(self):
        """Called first time the command is executed"""
        pass
    
    @abstractmethod
    def _redo(self):
        """Called on subsequent redos"""
        pass
    
    def redo(self):
        """Public redo method that handles the initialization pattern"""
        if not self._initialized:
            self._initialized = True
            self._initialize()
        else:
            self._redo()
    
    def mergeWith(self, other) -> bool:
        """Allow merging of compatible commands (e.g., consecutive moves)"""
        return False
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize command for saving"""
        return {
            'type': self.__class__.__name__,
            'timestamp': self.timestamp.isoformat(),
            'description': self.text()
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any], scene) -> 'BaseCommand':
        """Deserialize command - override in subclasses"""
        raise NotImplementedError


class CompoundCommand(BaseCommand):
    """Command that groups multiple commands together"""
    
    def __init__(self, description: str = "Grouped Operation", commands=None):
        super().__init__(description)
        self.commands = commands or []
    
    def add_command(self, command: BaseCommand):
        """Add a command to the group"""
        self.commands.append(command)
    
    def _initialize(self):
        """First time execution of compound command"""
        self._redo()
    
    def _redo(self):
        """Execute all commands in order"""
        for cmd in self.commands:
            cmd.redo()
    
    def undo(self):
        """Undo all commands in reverse order"""
        for cmd in reversed(self.commands):
            cmd.undo()
    
    def to_dict(self) -> Dict[str, Any]:
        data = super().to_dict()
        data['commands'] = [cmd.to_dict() for cmd in self.commands]
        return data
