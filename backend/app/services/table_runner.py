from __future__ import annotations

from dataclasses import dataclass

from app.agents.base import AgentAction, BotAgent
from app.core.game import PokerGame, Street


@dataclass(frozen=True)
class BotActionLog:
    player_id: str
    player_name: str
    agent_name: str
    action: AgentAction
    state_before: dict
    state_after: dict


class TableRunner:
    def __init__(self, agents_by_player_id: dict[str, BotAgent]) -> None:
        self.agents_by_player_id = agents_by_player_id

    def play_until_user_turn_or_complete(
        self,
        game: PokerGame,
        *,
        user_player_id: str = "p0",
        max_actions: int = 100,
    ) -> list[BotActionLog]:
        logs: list[BotActionLog] = []

        for _ in range(max_actions):
            if game.street == Street.COMPLETE or game.current_player.id == user_player_id:
                return logs

            player = game.current_player
            agent = self.agents_by_player_id.get(player.id)
            if agent is None:
                return logs

            state_before = game.to_public_state(viewer_id=user_player_id)
            selected_action = agent.choose_action(game, player_id=player.id)
            if selected_action.action not in game.legal_actions(player.id):
                raise ValueError(
                    f"{agent.name} selected illegal action {selected_action.action.value}"
                )

            game.apply_action(selected_action.action, selected_action.amount)
            state_after = game.to_public_state(viewer_id=user_player_id)
            logs.append(
                BotActionLog(
                    player_id=player.id,
                    player_name=player.name,
                    agent_name=agent.name,
                    action=selected_action,
                    state_before=state_before,
                    state_after=state_after,
                )
            )

        raise RuntimeError("Bot turn runner exceeded max_actions")
