"""Events the agent emits. ui decides how to display each one"""

from dataclasses import dataclass


@dataclass(frozen=True)
class TextDelta:
    """A new piece of reply text"""
    text: str

@dataclass(frozen=True)
class ThinkingDelta:
    """A new piece of model reasoning (if THINKING=True)"""
    text: str

@dataclass(frozen=True)
class AgentError:
    """Something went wrong and turn ended with no reply"""
    message: str

@dataclass(frozen=True)
class TurnStats:
    """Timing figures ollama reports at the end of a reply (in seconds)"""
    load_seconds: float
    prompt_tokens: int
    prompt_seconds: float
    output_tokens: int
    output_seconds: float

    @property
    def output_rate(self) -> float:
        return self.output_tokens / self.output_seconds if self.output_seconds else 0.0

    @property
    def prompt_rate(self) -> float:
        return self.prompt_tokens / self.prompt_seconds if self.prompt_seconds else 0.0

@dataclass(frozen=True)
class TurnDone:
    """The reply finished w/ no errors"""
    reply: str
    stats: TurnStats | None = None

@dataclass
class ToolCallStarted:
    """The model asked to run a tool. call_id links it to ToolCallFinished"""
    call_id: int
    name: str
    arguments: dict

@dataclass
class ToolCallFinished:
    """A tool finished. result is the text the model will see"""
    call_id: int
    name: str
    result: str

# Everything the agent can emit. tool events will get added here
Event = TextDelta | ThinkingDelta | AgentError | TurnDone | ToolCallStarted | ToolCallFinished