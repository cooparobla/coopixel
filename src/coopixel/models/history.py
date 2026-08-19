"""
Undo / Redo history manager for Coopixel.

Design: The stack stores document states. Each push captures the state BEFORE an action.
- undo_stack[-1] is always the CURRENT state (what is currently shown).
- Calling undo() restores undo_stack[-2] and moves undo_stack[-1] to the redo stack.
- This makes undo/redo symmetrical and predictable.
"""

import copy
from typing import Any, Dict, List, Optional


class HistoryStack:
    """Manages document state snapshots for undo/redo capability.

    Usage:
        stack.push(state)  — call after every committed action (push the NEW state).
        stack.undo(current) — returns the previous state to restore to.
        stack.redo(current) — returns the next undone state.
    """

    def __init__(self, max_depth: int = 50):
        self.max_depth = max_depth
        # Stores a linear history of states. Index 0 = oldest, -1 = most recent.
        self.undo_stack: List[Dict[str, Any]] = []
        self.redo_stack: List[Dict[str, Any]] = []

    def push(self, doc_dict: Dict[str, Any]) -> None:
        """Pushes a new document state. Clears redo history."""
        self.undo_stack.append(copy.deepcopy(doc_dict))
        if len(self.undo_stack) > self.max_depth:
            self.undo_stack.pop(0)
        self.redo_stack.clear()

    def can_undo(self) -> bool:
        """True if there is a previous state to restore."""
        return len(self.undo_stack) > 1

    def can_redo(self) -> bool:
        return len(self.redo_stack) > 0

    def undo(self) -> Optional[Dict[str, Any]]:
        """Moves most recent state to redo stack and returns the previous state to restore.
        Returns None if nothing to undo.
        """
        if not self.can_undo():
            return None
        # Move the current (most recent) state to redo stack
        current = self.undo_stack.pop()
        self.redo_stack.append(current)
        # Return a copy of the now-most-recent state (the previous one)
        return copy.deepcopy(self.undo_stack[-1])

    def redo(self) -> Optional[Dict[str, Any]]:
        """Restores the most recently undone state.
        Returns None if nothing to redo.
        """
        if not self.can_redo():
            return None
        # Move the redo state back onto the undo stack
        redo_state = self.redo_stack.pop()
        self.undo_stack.append(copy.deepcopy(redo_state))
        return copy.deepcopy(redo_state)

    def clear(self) -> None:
        self.undo_stack.clear()
        self.redo_stack.clear()
