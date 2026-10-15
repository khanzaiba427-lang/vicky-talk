"""UI package for the Vicky Talk desktop app (PySide6)."""

from .orb import OrbWidget
from .command_center import CommandCenterWidget
from .agent_view import AgentView
from .notes_view import NotesView
from .brain_view import BrainView
from .setup_wizard import SetupWizard

__all__ = [
    "OrbWidget",
    "CommandCenterWidget",
    "AgentView",
    "NotesView",
    "BrainView",
    "SetupWizard",
]
