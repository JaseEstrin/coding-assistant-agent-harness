from textual.app import ComposeResult
from textual.containers import Vertical
from textual.screen import Screen
from textual.widgets import Label, LoadingIndicator


class PreloadScreen(Screen):
    """Full window screen shown while agent loads into memory"""

    DEFAULT_CSS = """
    PreloadScreen { align: center middle; }
    #preload-box { width: 60; height: auto; }
    #preload-message { width: 100%; text-align: center; }
    #preload-spinner { height: 3; }
    """

    def __init__(self, model_name: str) -> None:
        super().__init__()
        self.model_name = model_name

    def compose(self) -> ComposeResult:
        with Vertical(id="preload-box"):
            yield Label(f"Preloading agent ({self.model_name})...", id="preload-message")
            yield LoadingIndicator(id="preload-spinner")

    def show_error(self, message: str) -> None:
        """Swap spinner for error message if something fails"""
        self.query_one("#preload-spinner").display = False
        self.query_one("#preload-message", Label).update(
            f"{message}\n\nCtrl+Q to quit."
        )