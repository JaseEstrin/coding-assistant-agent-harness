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

PROMPT_PATH = Path(__file__).parent / "prompts" / "system.md"

EXIT_COMMANDS = {"/bye", "/exit", "/quit"}


def load_system_prompt(project_dir: Path) -> str:
    """Read the system prompt and fill project directory"""
    text = PROMPT_PATH.read_text(encoding="utf-8")
    return text.replace("{project_dir}", str(project_dir))


class Agent:
    """Holds the conversation and talks to the model. Doesn't know anything about the ui"""

    def __init__(self, project_dir: Path) -> None:
        self.client = AsyncClient(host=SERVER_ADDRESS)
        # The model's entire memory is this list. Resent with every request
        self.messages = [{"role": "system", "content": load_system_prompt(project_dir)}]

    async def send(self, user_text: str) -> AsyncIterator[str]:
        """Add a user message, yield reply as it streams, then save it"""
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
                piece = chunk.message.content
                if piece:
                    reply += piece
                    yield piece
        except BaseException:
            # Failed or cancelled -- drop unanswered message
            self.messages.pop()
            raise
        self.messages.append({"role": "assistant", "content": reply})

    
async def main() -> None:
    agent = Agent(Path.cwd())

    print(f"Talking to {MODEL_NAME}. /bye, /exit, or /quit to quit.\n")

    while True:
        try:
            # input() blocks, run it in a thread to keep event loop free
            user_text = await asyncio.to_thread(input, "you> ")
        except (EOFError, KeyboardInterrupt): #ctrl+d or ctrl+c
            print()
            break

        user_text = user_text.strip()
        if not user_text:
            continue
        if user_text.lower() in EXIT_COMMANDS:
            break

        print("agent> ", end="", flush=True)
        try:
            async for piece in agent.send(user_text):
                print(piece, end="", flush=True)
            print()
        except ConnectionError:
            print("\nCouldn't connect to ollama -- systemctl status ollama")
        except ResponseError as error:
            print(f"\nollama error: {error}")


if __name__ == "__main__":
    asyncio.run(main())