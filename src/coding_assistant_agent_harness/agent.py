import asyncio
from collections.abc import AsyncIterator
from pathlib import Path

from ollama import AsyncClient, ResponseError

from .config import (
    CONTEXT_LENGTH,
    MAX_STEPS_PER_TURN,
    MODEL_NAME,
    SERVER_ADDRESS,
    THINKING,
)
from .events import AgentError, Event, TextDelta, ThinkingDelta, TurnDone

PROMPT_PATH = Path(__file__).parent / "prompts" / "system.md"


def load_system_prompt(project_dir: Path) -> str:
    """Read the system prompt and fill project directory"""
    text = PROMPT_PATH.read_text(encoding="utf-8")
    return text.replace("{project_dir}", str(project_dir))


class Agent:
    """Holds the conversation and talks to the model. Doesn't know anything about the ui"""

    def __init__(self, project_dir: Path, client: AsyncClient | None = None) -> None:
        self.project_dir = project_dir
        self.client = client or AsyncClient(host=SERVER_ADDRESS) # optional
        self.system_prompt = load_system_prompt(project_dir)
        self.messages: list[dict] = []
        self.reset()

    def reset(self) -> None:
        """Starts a fresh conversation, keeps system prompt"""
        self.messages = [{"role": "system", "content": self.system_prompt}]

    async def preload(self) -> str | None:
        """Load model into memory without generating anything.
        Raises connection error if ollama isn't running"""
        try:
            await self.client.chat(model=MODEL_NAME, messages=[])
        except ConnectionError:
            return "Couldn't reach ollama. systemctl status ollama"
        except ResponseError as error:
            return f"ollama returned an error: {error.error}"
        return None

    async def run(self, user_text: str) -> AsyncIterator[Event]:
        """Handle one user message, yielding events as the reply streams in."""
        self.messages.append({"role": "user", "content": user_text})
        reply = ""
 
        try:
            stream = await self.client.chat(
                model=MODEL_NAME,
                messages=self.messages,
                stream=True,
                think=THINKING,
                options={"num_ctx": CONTEXT_LENGTH},
            )
            async for chunk in stream:
                if chunk.message.thinking:
                    yield ThinkingDelta(chunk.message.thinking)
                if chunk.message.content:
                    reply += chunk.message.content
                    yield TextDelta(chunk.message.content)
 
        except asyncio.CancelledError:
            # The user stopped generation. Keep whatever arrived so the history stays consistent then let the cancellation continue.
            if reply:
                self.messages.append({"role": "assistant", "content": reply})
            else:
                self.messages.pop()
            raise
 
        except ConnectionError:
            self.messages.pop()  # drop the unanswered message
            yield AgentError("Couldn't reach ollama. systemctl status ollama")
            return
 
        except ResponseError as error:
            self.messages.pop()
            yield AgentError(f"ollama returned an error: {error.error}")
            return
 
        self.messages.append({"role": "assistant", "content": reply})
        yield TurnDone(reply)