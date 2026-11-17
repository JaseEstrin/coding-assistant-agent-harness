import asyncio
from collections.abc import AsyncIterator
from itertools import count
from pathlib import Path

from ollama import AsyncClient, ResponseError

from .config import (
    CONTEXT_LENGTH,
    KEEP_ALIVE,
    MAX_STEPS_PER_TURN,
    MODEL_NAME,
    SERVER_ADDRESS,
    THINKING,
)
from .events import (
    AgentError,
    Event,
    TextDelta,
    ThinkingDelta,
    ToolCallFinished,
    ToolCallStarted,
    TurnDone,
    TurnStats,
)
from .tools import run_tool, tool_schemas

PROMPT_PATH = Path(__file__).parent / "prompts" / "system.md"

MODEL_OPTIONS = {"num_ctx": CONTEXT_LENGTH}

NANOSECONDS = 1_000_000_000


def load_system_prompt(project_dir: Path) -> str:
    """Read the system prompt and fill project directory"""
    text = PROMPT_PATH.read_text(encoding="utf-8")
    return text.replace("{project_dir}", str(project_dir))

def write_debug_log(reply: str, tool_calls: list) -> None:
    """Append one step's raw output to a log file"""
    with open("/tmp/agent_debug.log", "a", encoding="utf-8") as log_file:
        log_file.write(f"--- reply ---\n{reply!r}\ntool_calls: {tool_calls!r}\n\n")

class Agent:
    """Holds the conversation and talks to the model. Doesn't know anything about the ui"""

    def __init__(self, project_dir: Path, client: AsyncClient | None = None) -> None:
        self.project_dir = project_dir
        self.client = client or AsyncClient(host=SERVER_ADDRESS) # optional
        self.system_prompt = load_system_prompt(project_dir)
        self.tools = tool_schemas()
        self.model = MODEL_NAME
        self.messages: list[dict] = []
        self._call_ids = count(1) # each tool call given a unique id for ui 
        self.reset()

    def reset(self) -> None:
        """Starts a fresh conversation, keeps system prompt"""
        self.messages = [{"role": "system", "content": self.system_prompt}]

    def set_model(self, name: str) -> None:
        """Switch models. History stays untouched"""
        self.model = name

    async def list_models(self) -> list[str]:
        """Names of the models ollama has downloaded"""
        response = await self.client.list()
        return sorted(model.model for model in response.models if model.model)

    async def preload(self) -> str | None:
        """Load model into memory without generating anything.
        Raises connection error if ollama isn't running"""
        try:
            await self.client.chat(model=self.model, messages=[], options=MODEL_OPTIONS, keep_alive=KEEP_ALIVE)
        except ConnectionError:
            return "Couldn't reach ollama. systemctl status ollama"
        except ResponseError as error:
            return f"ollama returned an error: {error.error}"
        return None

    async def unload(self) -> None:
        """Free the model's memory"""
        try:
            await self.client.chat(model=self.model, messages=[], keep_alive=0)
        except (ConnectionError, ResponseError):
            pass

    async def run(self, user_text: str) -> AsyncIterator[Event]:
        """Handle one user message, yielding events as the reply streams in. Run any tools it asks for"""
        turn_start = len(self.messages) # allows failed turn to roll back
        self.messages.append({"role": "user", "content": user_text})
        for _step in range(MAX_STEPS_PER_TURN):
            reply = ""
            tool_calls = []
            stats = None
 
            try:
                stream = await self.client.chat(
                    model=self.model,
                    messages=self.messages,
                    tools=self.tools,
                    stream=True,
                    think=THINKING,
                    options=MODEL_OPTIONS,
                    keep_alive=KEEP_ALIVE,
                )
                async for chunk in stream:
                    if chunk.message.thinking:
                        yield ThinkingDelta(chunk.message.thinking)
                    if chunk.message.content:
                        reply += chunk.message.content
                        yield TextDelta(chunk.message.content)
                    if chunk.message.tool_calls:
                        tool_calls.extend(chunk.message.tool_calls)
                    if chunk.done:
                        stats = TurnStats(
                            load_seconds=(chunk.load_duration or 0) / NANOSECONDS,
                            prompt_tokens=chunk.prompt_eval_count or 0,
                            prompt_seconds=(chunk.prompt_eval_duration or 0) / NANOSECONDS,
                            output_tokens=chunk.eval_count or 0,
                            output_seconds=(chunk.eval_duration or 0) / NANOSECONDS,
                        )
 
            except asyncio.CancelledError:
                # The user stopped generation. Keep whatever arrived so the history stays consistent then let the cancellation continue.
                del self.messages[turn_start:]
                if reply:
                    self.messages.append({"role": "user", "content": user_text})
                    self.messages.append({"role": "assistant", "content": reply})
                raise
    
            except ConnectionError:
                del self.messages[turn_start:]
                yield AgentError("Couldn't reach ollama. systemctl status ollama")
                return
 
            except ResponseError as error:
                del self.messages[turn_start:]
                yield AgentError(f"ollama returned an error: {error.error}")
                return

            # Record what the model said including tool requests
            assistant_message = {"role": "assistant", "content": reply}
            if tool_calls:
                assistant_message["tool_calls"] = tool_calls
            self.messages.append(assistant_message)
            await asyncio.to_thread(write_debug_log, reply, tool_calls)

            if not tool_calls:
                yield TurnDone(reply, stats)
                return

            for call in tool_calls:
                call_id = next(self._call_ids)
                name = call.function.name
                arguments = dict(call.function.arguments or {})
                yield ToolCallStarted(call_id, name, arguments)
                result = await run_tool(name, arguments, self.project_dir)
                self.messages.append({"role": "tool", "tool_name": name, "content": result})
                yield ToolCallFinished(call_id, name, result)

        yield AgentError(
            f"Stopped after {MAX_STEPS_PER_TURN} steps without a final answer. "
            "Make a more specific request"
        )