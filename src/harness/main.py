import asyncio
from textual import on, work
from textual.app import App, ComposeResult
from textual.containers import VerticalScroll, Vertical
from textual.widgets import Footer, Header, Input, Markdown, Static


async def fake_stream(prompt: str):
    for word in f"You said **{prompt}**. Here is a streamed reply.".split():
        await asyncio.sleep(0.08)
        yield word + " "


class AgentApp(App):
    CSS = """
    #log { height: 1fr; padding: 0 1; }
    .user { background: $boost; padding: 0 1; margin-top: 1; }
    .assistant { margin-top: 1; }
    """
    BINDINGS = [("ctrl+l", "clear", "Clear chat")]

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
        self.run_agent(prompt, reply)

    @work(exclusive=True)
    async def run_agent(self, prompt: str, reply: Markdown) -> None:
        text = ""
        async for chunk in fake_stream(prompt):
            text += chunk
            await reply.update(text)
            self.query_one("#log").scroll_end(animate=False)

    def action_clear(self) -> None:
        self.query_one("#log").remove_children()


if __name__ == "__main__":
    AgentApp().run()