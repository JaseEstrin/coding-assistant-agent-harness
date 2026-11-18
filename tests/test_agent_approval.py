import asyncio
from types import SimpleNamespace
from typing import cast

from ollama import AsyncClient

from coding_assistant_agent_harness.agent import DECLINED_MESSAGE, Agent
from coding_assistant_agent_harness.events import ToolCallFinished


def _chunk(content="", tool_calls=None, done=False):
    message = SimpleNamespace(thinking=None, content=content, tool_calls=tool_calls)
    return SimpleNamespace(
        message=message, done=done, load_duration=0, prompt_eval_count=0,
        prompt_eval_duration=0, eval_count=0, eval_duration=0,
    )


class FakeClient:
    """First reply asks to run a command; the second is a plain answer."""

    def __init__(self, command):
        call = SimpleNamespace(function=SimpleNamespace(name="run_command", arguments={"command": command}))
        self.replies = [[_chunk(tool_calls=[call], done=True)], [_chunk("All done.", done=True)]]

    async def chat(self, **kwargs):
        chunks = self.replies.pop(0)

        async def stream():
            for chunk in chunks:
                yield chunk

        return stream()

def fake_client(command: str) -> AsyncClient:
    return cast(AsyncClient, FakeClient(command))

def _run_turn(agent):
    async def collect():
        return [event async for event in agent.run("please run it")]
    return asyncio.run(collect())


def test_declined_command_never_runs(tmp_path):
    asked = []

    async def deny(name, arguments):
        asked.append((name, arguments["command"]))
        return False

    agent = Agent(tmp_path, approve=deny, client=fake_client("touch created.txt"))
    events = _run_turn(agent)

    assert asked == [("run_command", "touch created.txt")]
    assert not (tmp_path / "created.txt").exists()
    finished = [event for event in events if isinstance(event, ToolCallFinished)]
    assert finished[0].result == DECLINED_MESSAGE


def test_approved_command_runs(tmp_path):
    async def allow(name, arguments):
        return True

    agent = Agent(tmp_path, approve=allow, client=fake_client("touch created.txt"))
    _run_turn(agent)
    assert (tmp_path / "created.txt").exists()


def test_no_approver_means_declined(tmp_path):
    agent = Agent(tmp_path, client=fake_client("touch created.txt"))
    _run_turn(agent)
    assert not (tmp_path / "created.txt").exists()