from rich.markup import escape
from textual.reactive import reactive
from textual.widgets import Collapsible, Static


class StatusBar(Static):
    """Bar that shows the model and what the agent is doing"""

    DEFAULT_CSS = """
    StatusBar { height: 1; padding: 0 1; background: $panel; color: $text-muted; }
    StatusBar.-thinking { color: $warning; }
    StatusBar.-generating { color: $success; }
    StatusBar.-tool { color: $accent; }
    StatusBar.-approval { color: $error; text-style: bold; }
    """

    LABELS = {  # noqa: RUF012
        "idle": "● idle",
        "thinking": "◌ thinking...",
        "generating": "▶ generating...",
        "tool": "⚙ running tool...",
        "approval": "? waiting for your approval",
    }

    status: reactive[str] = reactive("idle")

    def __init__(self, model_name: str, **kwargs) -> None:
        super().__init__(**kwargs)
        self.model_name = model_name

    def watch_status(self, old: str, new: str) -> None:
        self.remove_class(f"-{old}")
        self.add_class(f"-{new}")
        self._redraw()

    def set_model(self, model_name: str) -> None:
        """Show a different model name after switching models"""
        self.model_name = model_name
        self._redraw()

    def _redraw(self) -> None:
        self.update(f"{self.model_name}  {self.LABELS[self.status]}")


class ToolCallView(Collapsible):
    """A collapsed box showing one tool call. expand to see result"""

    DEFAULT_CSS = """
    ToolCallView { margin-top: 1; }
    ToolCallView .tool_output { color: $text-muted; }
    """

    def __init__(self, name: str, arguments: dict) -> None:
        shown_args = ", ".join(f"{key}={value!r}" for key, value in arguments.items())
        self.output = Static("running...", markup=False, classes="tool-output")
        super().__init__(self.output, title=escape(f"⚙ {name} ({shown_args})"), collapsed=True)

    def set_result(self, result: str) -> None:
        self.output.update(result)