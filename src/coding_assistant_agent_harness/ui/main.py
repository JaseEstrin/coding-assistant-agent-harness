import asyncio
from pathlib import Path

from ollama import ResponseError
from textual import on, work
from textual.app import App, ComposeResult
from textual.containers import Vertical, VerticalScroll
from textual.widgets import Footer, Header, Input, Markdown, Static

from ..agent import Agent


class AgentApp(App):
    CSS = """
    #log { height: 1fr; padding: 0 1; }
    .user { background: $boost; padding: 0 1; margin-top: 1; }
    .assistant { margin-top: 1; }
    """
    BINDINGS = [("ctrl+l", "clear", "Clear chat")]

    def on_mount(self) -> None:
        self.agent = Agent(Path.cwd())

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
        event.input.disabled = True
        self.run_agent(prompt, reply)

    @work(exclusive=True)
    async def run_agent(self, prompt: str, reply: Markdown) -> None:
        self.query_one("#log", VerticalScroll).anchor()
        stream = Markdown.get_stream(reply)
        try:
            async for piece in self.agent.send(prompt):
                await stream.write(piece)
        except ConnectionError:
            await stream.write("\n\n**Couldn't connect to ollama** ('systemctl status ollama')")
        except ResponseError as error:
            await stream.write(f"\n\n**ollama error:** {error}")
        finally:
            await stream.stop()
            input_box = self.query_one(Input)
            input_box.disabled = False
            input_box.focus()

    def action_clear(self) -> None:
        self.query_one("#log").remove_children()


if __name__ == "__main__":
    AgentApp().run()