import time
from asyncio import CancelledError
from pathlib import Path

from textual import on, work
from textual.app import App, ComposeResult
from textual.binding import Binding
from textual.containers import VerticalScroll
from textual.widgets import Footer, Header, Input, Markdown, Static

from ..agent import Agent
from ..events import (
    AgentError,
    TextDelta,
    ThinkingDelta,
    ToolCallFinished,
    ToolCallStarted,
    TurnDone,
)
from .screens import ApproveTool, DirectoryPicker, ModelPicker, PreloadScreen
from .widgets import StatusBar, ToolCallView


class AgentApp(App):
    CSS = """
    #log { height: 1fr; padding: 0 1; }
    .user { background: $boost; padding: 0 1; margin-top: 1; }
    .assistant { margin-top: 1; }
    """
    BINDINGS = [  # noqa: RUF012
        ("ctrl+l", "clear", "Clear chat"),
        Binding("escape", "stop", "Stop"),
        Binding("ctrl+o", "switch_model", "Switch Model"),
        Binding("ctrl+g", "change_directory", "Change directory")
    ]

    def on_mount(self) -> None:
        self.agent: Agent | None = None
        self.agent_worker = None
        self.start_up()


    @work(exclusive=True, group="preload")
    async def start_up(self) -> None:
        # ask what directory the agent can work in
        project_dir = await self.push_screen_wait(DirectoryPicker(Path.cwd()))
        if project_dir is None:
            self.exit()
            return
        agent = Agent(project_dir, approve=self.approve_tool)
        self.agent = agent
        self.sub_title = str(project_dir)

        # load the model, show loading screen
        self.preload_screen = PreloadScreen(agent.model)
        await self.push_screen(self.preload_screen)
        error = await agent.preload()
        if error:
            self.preload_screen.show_error(error)
            return
        self.pop_screen()
        self.query_one(StatusBar).set_model(agent.model)
        self.query_one(Input).focus()

    async def approve_tool(self, name: str, arguments: dict) -> bool:
        """Called by agent mid turn before any tool that needs approval"""
        status_bar = self.query_one(StatusBar)
        status_bar.status = "approval"
        approved = await self.push_screen_wait(ApproveTool(name, arguments))
        status_bar.status = "tool" if approved else "thinking"
        return bool(approved)

    def action_change_directory(self) -> None:
        if self.agent is None:
            return
        if self.agent_worker is not None and self.agent_worker.is_running:
            self.notify("Wait for the reply to finish (or press Esc to stop it) first.")
            return
        self.change_folder()

    @work(exclusive=True, group="folders")
    async def change_folder(self) -> None:
        agent = self.agent
        if agent is None:
            return
        chosen = await self.push_screen_wait(DirectoryPicker(agent.project_dir, cancellable=True))
        if chosen is None:
            return
        if chosen.resolve() == agent.project_dir.resolve():
            self.notify("That's the current directory. Conversation kept.")
            return

        agent.set_project_dir(chosen)
        self.query_one("#log").remove_children()
        self.sub_title = str(chosen)
        self.notify(f"Now working in {chosen}. Conversation cleared.")
        self.query_one(Input).focus()

    def action_switch_model(self) -> None:
        if self.agent is None:
            return
        if self.agent_worker is not None and self.agent_worker.is_running:
            self.notify("Wait for the reply to finish (or press Esc to stop it) first.")
            return
        self.choose_model()

    @work(exclusive=True, group="models")
    async def choose_model(self) -> None:
        agent = self.agent
        if agent is None:
            return
        try:
            models = await agent.list_models()
        except ConnectionError:
            self.notify("Couldn't reach ollama. systemctl status ollama", severity="error")
            return
        if not models:
            self.notify("No downloaded models. ollama pull")
            return

        # Shows the picker then waits until user picks or cancels
        choice = await self.push_screen_wait(ModelPicker(models, agent.model))
        if choice is None or choice == agent.model:
            return

        previous = agent.model
        agent.set_model(choice)
        self.preload_screen = PreloadScreen(choice)
        await self.push_screen(self.preload_screen)
        error = await agent.preload()
        self.pop_screen()

        if error:
            agent.set_model(previous) # fallback so chat keeps working
            self.notify(f"Couldn't load {choice}: {error} Still using {previous}", severity="error", timeout=10)
            return

        self.query_one(StatusBar).set_model(choice)
        self.notify(f"Switched to {choice}. Your conversation was kept.")
        self.query_one(Input).focus()

    def compose(self) -> ComposeResult:
        yield Header()
        yield VerticalScroll(id="log")
        yield StatusBar("")
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
        agent = self.agent
        if agent is None:
            return       
        log = self.query_one("#log", VerticalScroll)
        status_bar = self.query_one(StatusBar)
        text = ""
        last_render = 0.0
        tool_views: dict[int, ToolCallView] = {} # call_id = its widget
        try:
            async for event in agent.run(prompt):
                match event:
                    case TextDelta(text=piece):
                        status_bar.status = "generating"
                        text += piece
                        now = time.monotonic()
                        if now - last_render >= 0.1:
                            last_render - now
                            await reply.update(text)
                            log.scroll_end(animate=False)
                    case ThinkingDelta():
                        status_bar.status = "thinking"
                    case ToolCallStarted(call_id=call_id, name=name, arguments=arguments):
                        status_bar.status = "tool"
                        if text:
                            await reply.update(text)
                        else:
                            await reply.remove()
                        view = ToolCallView(name, arguments)
                        tool_views[call_id] = view
                        await log.mount(view)
                        reply = Markdown(classes="assistant")
                        await log.mount(reply)
                        text = ""
                        log.scroll_end(animate=False)
                    case ToolCallFinished(call_id=call_id, result=result):
                        tool_views[call_id].set_result(result)
                        status_bar.status = "thinking"
                    case AgentError(message=message):
                        await reply.update(f"**Error:** {message}")
                    case TurnDone(stats=stats):
                        await reply.update(text)
                        log.scroll_end(animate=False)
                        if stats:
                            self.notify(
                                f"load {stats.load_seconds:.1f}s · "
                                f"prompt {stats.prompt_tokens} tok in {stats.prompt_seconds:.1f}s"
                                f"({stats.prompt_rate:.0f} tok/s) · "
                                f"output {stats.output_rate:.1f} tok/s",
                                timeout=8,
                            )
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

    async def action_quit(self) -> None:
        """Ctrl+Q unloads the model so its ram is freed instantly"""
        if self.agent is not None:
            self.notify("Unloading model...")
            await self.agent.unload()
        self.exit()

    def action_clear(self) -> None:
        self.query_one("#log").remove_children()
        if self.agent is not None:
            self.agent.reset()  # forget the conversation, not just the screen


if __name__ == "__main__":
    AgentApp().run()