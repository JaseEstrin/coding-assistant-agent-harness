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
class TurnDone:
    """The reply finished w/ no errors"""
    reply: str

# Everything the agent can emit. tool events will get added here
Event = TextDelta | ThinkingDelta | AgentError | TurnDone