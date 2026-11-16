from asyncio import CancelledError
from pathlib import Path

from textual import on, work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import VerticalScroll
from textual.widgets import Footer, Header, Input, Markdown, Static

from ..agent import Agent
from ..config import MODEL_NAME
from ..events import AgentError, TextDelta, ThinkingDelta, TurnDone
from .screens import PreloadScreen
from .widgets import StatusBar


class AgentApp(App):
    CSS = """
    #log { height: 1fr; padding: 0 1; }
    .user { background: $boost; padding: 0 1; margin-top: 1; }
    .assistant { margin-top: 1; }
    """
    BINDINGS = [  # noqa: RUF012
        ("ctrl+l", "clear", "Clear chat"),
        Binding("escape", "stop", "Stop"),
    ]

    def on_mount(self) -> None:
        self.agent = Agent(Path.cwd())
        self.agent_worker = None
        self.preload_screen = PreloadScreen(MODEL_NAME)
        self.push_screen(self.preload_screen)
        self.preload_agent()

    @work(exclusive=True, group="preload")
    async def preload_agent(self) -> None:
        error = await self.agent.preload()
        if error:
            self.preload_screen.show_error(error)
            return
        self.pop_screen()
        self.query_one(Input).focus()

    def compose(self) -> ComposeResult:
        yield Header()
        yield VerticalScroll(id="log")
        yield StatusBar(MODEL_NAME)
        yield Input(placeholder="Ask the agent...")
        yield Footer()

    @on(Input.Submitted)
    async def handle_submit(self, event: Input.Submitted) -> None:
        prompt = event.value.strip()
        if not prompt:
            return
        event.input.clear()
        log = self.query_one("#log", VerticalScroll)
        await log.mount(Static(prompt, classes="user"))
        reply = Markdown(classes="assistant")
        await log.mount(reply)
        log.scroll_end(animate=False)
        event.input.disabled = True
        self.query_one(StatusBar).status = "thinking"
        self.agent_worker = self.run_agent(prompt, reply)

    @work(exclusive=True)
    async def run_agent(self, prompt: str, reply: Markdown) -> None:
        log = self.query_one("#log", VerticalScroll)
        status_bar = self.query_one(StatusBar)
        text = ""
        try:
            async for event in self.agent.run(prompt):
                match event:
                    case TextDelta(text=piece):
                        status_bar.status = "generating"
                        text += piece
                        await reply.update(text)
                        log.scroll_end(animate=False)
                    case ThinkingDelta():
                        status_bar.status = "thinking"
                    case AgentError(message=message):
                        await reply.update(f"**Error:** {message}")
                    case TurnDone():
                        pass
        except CancelledError:
            await reply.update(text + "\n\n*[stopped]*")
            raise
        finally:
            status_bar.status = "idle"
            user_input = self.query_one(Input)
            user_input.disabled = False
            user_input.focus()

    def action_stop(self) -> None:
        if self.agent_worker is not None and self.agent_worker.is_running:
            self.agent_worker.cancel()

    def action_clear(self) -> None:
        self.query_one("#log").remove_children()
        self.agent.reset()  # forget the conversation, not just the screen


if __name__ == "__main__":
    AgentApp().run()