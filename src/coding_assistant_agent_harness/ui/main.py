from pathlib import Path

from textual import on, work
from textual.app import App, ComposeResult
from textual.containers import VerticalScroll
from textual.widgets import Footer, Header, Input, Markdown, Static

from ..agent import Agent
from ..config import MODEL_NAME
from ..events import AgentError, TextDelta, ThinkingDelta, TurnDone
from .screens import PreloadScreen


class AgentApp(App):
    CSS = """
    #log { height: 1fr; padding: 0 1; }
    .user { background: $boost; padding: 0 1; margin-top: 1; }
    .assistant { margin-top: 1; }
    """
    BINDINGS = [("ctrl+l", "clear", "Clear chat")]

    def on_mount(self) -> None:
        self.agent = Agent(Path.cwd())
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
        self.run_agent(prompt, reply)

    @work(exclusive=True)
    async def run_agent(self, prompt: str, reply: Markdown) -> None:
        log = self.query_one("#log", VerticalScroll)
        text = ""
        try:
            async for event in self.agent.run(prompt):
                match event:
                    case TextDelta(text=piece):
                        text += piece
                        await reply.update(text)
                        log.scroll_end(animate=False)
                    case ThinkingDelta():
                        pass
                    case AgentError(message=message):
                        await reply.update(f"**Error:** {message}")
                    case TurnDone():
                        pass
        finally:
            user_input = self.query_one(Input)
            user_input.disabled = False
            user_input.focus()

    def action_clear(self) -> None:
        self.query_one("#log").remove_children()
        self.agent.reset()  # forget the conversation, not just the screen


if __name__ == "__main__":
    AgentApp().run()