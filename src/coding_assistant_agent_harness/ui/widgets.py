from textual.reactive import reactive
from textual.widgets import Static


class StatusBar(Static):
    """Bar that shows the model and what the agent is doing"""

    DEFAULT_CSS = """
    StatusBar { height: 1; padding: 0 1; background: $panel; color: $text-muted; }
    StatusBar.-thinking { color: $warning; }
    StatusBar.-generating { color: $success; }
    """

    LABELS = {  # noqa: RUF012
        "idle": "● idle",
        "thinking": "◌ thinking...",
        "generating": "▶ generating...",
    }

    status: reactive[str] = reactive("idle")

    def __init__(self, model_name: str, **kwargs) -> None:
        super().__init__(**kwargs)
        self.model_name = model_name

    def watch_status(self, old: str, new: str) -> None:
        self.remove_class(f"-{old}")
        self.add_class(f"-{new}")
        self.update(f"{self.model_name}  {self.LABELS[new]}")