from pathlib import Path

from rich.markup import escape
from textual.app import ComposeResult
from textual.binding import Binding
from textual.containers import Horizontal, Vertical
from textual.screen import ModalScreen, Screen
from textual.widgets import Button, Label, LoadingIndicator, OptionList, Static
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
    """A pop-up list of downloaded models. arrow keys move, enter picks, escape cancels"""

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


class DirectoryPicker(Screen[Path]):
    """Full-window folder browser shown at startup and returns the chosen folder"""

    DEFAULT_CSS = """
    DirectoryPicker { align: center middle; }
    #dir-box {
        width: 80%; max-width: 100; height: 80%;
        border: thick $accent; background: $surface; padding: 1 2;
    }
    #dir-title { width: 100%; text-align: center; }
    #dir-path { width: 100%; color: $accent; margin: 1 0; }
    #dir-list { height: 1fr; }
    #dir-hint { width: 100%; text-align: center; color: $text-muted; margin-top: 1; }
    """

    BINDINGS = [  # noqa: RUF012
        Binding("tab", "open_folder", "Open folder", priority=True),
        Binding("escape", "go_up", "Up a level", priority=True),
        Binding("ctrl+g", "cancel", "Cancel", priority=True),
    ]

    def __init__(self, start: Path, cancellable: bool = False) -> None:
        super().__init__()
        self.current = start.resolve()
        self.cancellable = cancellable

    def compose(self) -> ComposeResult:
        with Vertical(id="dir-box"):
            yield Label("Choose the working directory", id="dir-title")
            yield Label("", id="dir-path", markup=False)
            yield OptionList(id="dir-list")
            hint = "↑/↓ move · Tab open folder · Esc up a level · Enter choose"
            if self.cancellable:
                hint += " · Ctrl+G cancel"
            yield Label(hint, id="dir-hunt")

    def on_mount(self) -> None:
        self._show(self.current)

    def _show(self, folder: Path, highlight: str | None = None) -> None:
        """Display the subfolders of folder, stays put if can't be opened"""
        try:
            subfolders = sorted(
                (
                    entry for entry in folder.iterdir() 
                    if entry.is_dir() and not entry.name.startswith(".")
                ),
                key=lambda entry: entry.name.lower(),
            )
        except PermissionError:
            self.notify(f"Can't open {folder}: permission denied.", severity="warning")
            return

        self.current = folder
        self.query_one("#dir-path", Label).update(str(folder))

        option_list = self.query_one(OptionList)
        option_list.clear_options()
        option_list.add_option(Option(f"./   (choose{escape(folder.name or str(folder))})", id="."))
        for entry in subfolders:
            option_list.add_option(Option(escape(f"{entry.name}/"), id=entry.name))

        names = ["."] + [entry.name for entry in subfolders]
        option_list.highlighted = names.index(highlight) if highlight in names else 0
        option_list.focus()

    def _highlighted_name(self) -> str | None:
        option_list = self.query_one(OptionList)
        if option_list.highlighted is None:
            return None
        return option_list.get_option_at_index(option_list.highlighted).id

    def action_open_folder(self) -> None:
        name = self._highlighted_name()
        if name and name != ".":
            self._show(self.current / name)

    def action_cancel(self) -> None:
        if self.cancellable:
            self.dismiss(None)

    def action_go_up(self) -> None:
        parent = self.current.parent
        if parent != self.current:
            self._show(parent, highlight=self.current.name)

    def on_option_list_option_selected(self, event: OptionList.OptionSelected) -> None:
        name = event.option.id
        if name is None: 
            return
        chosen = self.current if name == "." else self.current / name
        if chosen == Path(chosen.anchor):
            self.notify("The directory is too broad. Choose a project folder", severity="warning")
            return
        self.dismiss(chosen)


class ApproveTool(ModalScreen[bool]):
    """Asks the user to allow or deny one tool call"""
    DEFAULT_CSS = """
    #approve-box {
        width: 80%; max-width: 100; height: auto;
        border: thick $error; background: $surface; padding: 1 2;
    }
    #approve-title { text-style: bold; margin-bottom: 1; }
    #approve-detail {
        background: $boost; padding: 1 2; margin-bottom: 1;
        max-height: 15; overflow-y: auto;
    }
    #approve-note { color: $text-muted; margin-bottom: 1; }
    #approve-buttons { height: auto; align-horizontal: center; }
    #approve-buttons Button { margin: 0 2; }
    """

    BINDINGS = [  # noqa: RUF012
        Binding("y", "allow", "Allow"),
        Binding("n", "deny", "Deny"),
        Binding("escape", "deny", "Deny", priority=True),
    ]

    def __init__(self, name: str, arguments: dict) -> None:
        super().__init__()
        self.tool_name = name
        self.arguments = arguments

    def compose(self) -> ComposeResult:
        if self.tool_name == "run_command":
            title = "The agent wants to run this command:"
            detail = str(self.arguments.get("command", ""))
        else:
            title = f"The agent wants to use {self.tool_name}:"
            detail = "\n".join(f"{key}: {value}" for key, value in self.arguments.items())
        with Vertical(id="approve-box"):
            yield Label(title, id="approve-title")
            yield Static(detail, id="approve-detail", markup=False)
            yield Label("It runs in your project folder with your permissions.", id="approve-note")
            with Horizontal(id="approve-buttons"):
                yield Button("Allow (Y)", variant="success", id="allow")
                yield Button("Deny (N)", variant="error", id="deny")

    def on_mount(self) -> None:
        self.query_one("#deny", Button).focus()

    def on_button_press(self, event: Button.Pressed) -> None:
        self.dismiss(event.button.id == "allow")

    def action_allow(self) -> None:
        self.dismiss(True)

    def action_deny(self) -> None:
        self.dismiss(False)