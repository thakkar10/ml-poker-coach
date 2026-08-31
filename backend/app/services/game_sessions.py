from __future__ import annotations

from dataclasses import dataclass

from app.agents import AggressiveBot, BotAgent, EquityBot, RandomBot, TightBot
from app.coach import PokerCoach
from app.coach.equity import EquitySimulator
from app.core.game import Action, PokerGame, Street
from app.services.table_runner import BotActionLog, TableRunner


@dataclass
class GameSession:
    game: PokerGame
    runner: TableRunner
    coach: PokerCoach


class GameSessionStore:
    def __init__(self) -> None:
        self._sessions: dict[str, GameSession] = {}

    def create(self, player_names: list[str], *, seed: int | None = None) -> GameSession:
        game = PokerGame(player_names, seed=seed)
        session = GameSession(
            game=game,
            runner=TableRunner(_default_agents(game)),
            coach=PokerCoach(EquitySimulator(simulations=500, seed=seed)),
        )
        self._sessions[game.id] = session
        return session

    def get(self, game_id: str) -> GameSession:
        try:
            return self._sessions[game_id]
        except KeyError as exc:
            raise KeyError(f"Unknown game id: {game_id}") from exc

    def apply_user_action(
        self,
        game_id: str,
        *,
        action: Action,
        amount: int = 0,
        user_player_id: str = "p0",
    ) -> tuple[GameSession, list[BotActionLog]]:
        session = self.get(game_id)
        game = session.game

        if game.street == Street.COMPLETE:
            return session, []
        if game.current_player.id != user_player_id:
            raise ValueError("It is not currently the user's turn")

        game.apply_action(action, amount)
        bot_logs = session.runner.play_until_user_turn_or_complete(
            game,
            user_player_id=user_player_id,
        )
        return session, bot_logs


def serialize_bot_logs(logs: list[BotActionLog]) -> list[dict[str, object]]:
    return [
        {
            "player_id": log.player_id,
            "player_name": log.player_name,
            "agent_name": log.agent_name,
            "action": log.action.action.value,
            "amount": log.action.amount,
            "reason": log.action.reason,
        }
        for log in logs
    ]


def _default_agents(game: PokerGame) -> dict[str, BotAgent]:
    agent_cycle: list[BotAgent] = [
        TightBot(equity_simulator=EquitySimulator(simulations=250, seed=11)),
        AggressiveBot(equity_simulator=EquitySimulator(simulations=250, seed=13), seed=13),
        EquityBot(equity_simulator=EquitySimulator(simulations=250, seed=17)),
        RandomBot(seed=19),
        TightBot(equity_simulator=EquitySimulator(simulations=250, seed=23)),
    ]
    return {
        player.id: agent_cycle[index - 1]
        for index, player in enumerate(game.players)
        if index > 0
    }
