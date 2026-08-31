from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from app.core.game import Action, PokerGame


@dataclass(frozen=True)
class AgentAction:
    action: Action
    amount: int = 0
    reason: str = ""


class BotAgent(Protocol):
    name: str

    def choose_action(self, game: PokerGame, *, player_id: str) -> AgentAction:
        """Choose one legal action for the given player."""
