"""Find out which part of the harness's request stops tool calls from working.

Sends the same question four ways: with and without the system prompt,
streamed and not streamed. Uses the harness's own options and tool schemas.
"""

import asyncio
from pathlib import Path
from typing import Any

from ollama import AsyncClient

from coding_assistant_agent_harness.agent import MODEL_OPTIONS, load_system_prompt
from coding_assistant_agent_harness.config import MODEL_NAME, SERVER_ADDRESS
from coding_assistant_agent_harness.tools import tool_schemas

QUESTION = "Read the file pyproject.toml"


async def check(client: AsyncClient, use_system_prompt: bool, stream: bool) -> None:
    messages = []
    if use_system_prompt:
        messages.append({"role": "system", "content": load_system_prompt(Path.cwd())})
    messages.append({"role": "user", "content": QUESTION})

    request: dict[str, Any] = {
        "model": MODEL_NAME,
        "messages": messages,
        "tools": tool_schemas(),
        "think": False,
        "options": MODEL_OPTIONS,
    }

    content = ""
    tool_calls = []
    if stream:
        async for chunk in await client.chat(**request, stream=True):
            content += chunk.message.content or ""
            tool_calls += chunk.message.tool_calls or []
    else:
        response = await client.chat(**request)
        content = response.message.content or ""
        tool_calls = response.message.tool_calls or []

    names = [call.function.name for call in tool_calls] or "NONE"
    label = f"system prompt={'yes' if use_system_prompt else 'no '}  stream={'yes' if stream else 'no '}"
    print(f"{label}  ->  tool_calls: {names}  content: {content[:80]!r}", flush=True)


async def main() -> None:
    client = AsyncClient(host=SERVER_ADDRESS)
    for use_system_prompt in (False, True):
        for stream in (False, True):
            await check(client, use_system_prompt, stream)


asyncio.run(main())