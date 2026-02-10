from PyQt5.QtWidgets import QUndoCommand

class MoveCommand(QUndoCommand):
    def __init__(self, item, old_pos, new_pos):
        super().__init__("Move Connector")
        self.item = item
        self.old = old_pos
        self.new = new_pos

    def undo(self):
        self.item.setPos(self.old)

    def redo(self):
        self.item.setPos(self.new)


def mouseReleaseEvent(self, event):
    new_pos = self.pos()
    if new_pos != self._old_pos:
        self.undo_stack.push(
            MoveCommand(self, self._old_pos, new_pos)
        )
    super().mouseReleaseEvent(event)