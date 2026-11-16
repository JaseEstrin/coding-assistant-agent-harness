from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Vertical
from textual.screen import ModalScreen, Screen
from textual.widgets import Label, LoadingIndicator, OptionList
from textual.widgets.option_list import Option


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


class ModelPicker(ModalScreen[str | None]):
    """A pop-up list of downloaded models. Arrow keys move, Enter picks, Escape cancels"""

    DEFAULT_CSS = """
    ModelPicker { align: center middle; }
    #picker-box {
        width: 50; height: auto; max-height: 80%;
        border: thick $accent; background: $surface; padding: 1 2;
    }
    #picker-title { width: 100%; text-align: center; margin-bottom: 1; }
    #picker-hint { width: 100%; text-align: center; color: $text-muted; margin-top: 1; }
    #picker-list { height: auto; max-height: 20; }
    """

    BINDINGS = [Binding("escape", "cancel", "Cancel")]  # noqa: RUF012

    def __init__(self, models: list[str], current: str) -> None:
        super().__init__()
        self.models = models
        self.current = current

    def compose(self) -> ComposeResult:
        options = [
            Option(f"{name}  ● current" if name == self.current else name, id=name)
            for name in self.models
        ]
        with Vertical(id="picker-box"):
            yield Label("Switch model", id="picker-title")
            yield OptionList(*options, id="picker-list")
            yield Label("↑/↓ to move · Enter to switch · Esc to cancel", id="picker-hint")

    def on_mount(self) -> None:
        option_list = self.query_one(OptionList)
        if self.current in self.models:
            option_list.highlighted = self.models.index(self.current)
        option_list.focus()

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        self.dismiss(event.option.id)

    def action_cancel(self) -> None:
        self.dismiss(None)