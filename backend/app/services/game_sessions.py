from __future__ import annotations

from dataclasses import dataclass

from app.agents import AggressiveBot, BotAgent, EquityBot, LoosePassiveBot, RecreationalBot, TightBot
from app.coach import PokerCoach
from app.coach.equity import EquitySimulator
from app.core.game import Action, PokerGame, Street
from app.ml import DecisionLog, PlayerStyleAnalyzer
from app.services.table_runner import BotActionLog, TableRunner


@dataclass
class GameSession:
    game: PokerGame
    runner: TableRunner
    coach: PokerCoach
    decision_logs: list[DecisionLog]


class GameSessionStore:
    def __init__(self) -> None:
        self._sessions: dict[str, GameSession] = {}

    def create(self, player_names: list[str], *, seed: int | None = None) -> GameSession:
        game = PokerGame(player_names, seed=seed)
        session = GameSession(
            game=game,
            runner=TableRunner(_default_agents(game)),
            coach=PokerCoach(EquitySimulator(simulations=500, seed=seed)),
            decision_logs=[],
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

        recommendation = session.coach.recommend(game, player_id=user_player_id)
        player = _player(game, user_player_id)
        session.decision_logs.append(
            DecisionLog(
                street=game.street.value,
                action=action,
                amount=amount,
                recommended_action=recommendation.action,
                equity=recommendation.equity,
                pot_odds=recommendation.pot_odds,
                confidence=recommendation.confidence,
                pot=game.pot,
                current_bet=game.current_bet,
                active_players=len(game.active_players),
            )
        )
        game.apply_action(action, amount)
        bot_logs = session.runner.play_until_user_turn_or_complete(
            game,
            user_player_id=user_player_id,
        )
        return session, bot_logs

    def review(self, game_id: str) -> dict[str, object]:
        session = self.get(game_id)
        review = PlayerStyleAnalyzer().analyze(session.decision_logs)
        return {
            **review.to_dict(),
            "decision_log": [
                {
                    "street": decision.street,
                    "action": decision.action.value,
                    "recommended_action": decision.recommended_action.value,
                    "equity": round(decision.equity, 4),
                    "pot_odds": round(decision.pot_odds, 4),
                    "confidence": round(decision.confidence, 4),
                    "followed_coach": decision.followed_coach,
                }
                for decision in session.decision_logs
            ],
        }


def serialize_bot_logs(logs: list[BotActionLog]) -> list[dict[str, object]]:
    return [
        {
            "player_id": log.player_id,
            "player_name": log.player_name,
            "agent_name": log.agent_name,
            "action": log.action.action.value,
            "amount": log.action.amount,
            "reason": log.action.reason,
            "state_before": log.state_before,
            "state_after": log.state_after,
        }
        for log in logs
    ]


def _default_agents(game: PokerGame) -> dict[str, BotAgent]:
    agent_cycle: list[BotAgent] = [
        TightBot(equity_simulator=EquitySimulator(simulations=250, seed=11), seed=11),
        AggressiveBot(equity_simulator=EquitySimulator(simulations=250, seed=13), seed=13),
        EquityBot(equity_simulator=EquitySimulator(simulations=250, seed=17), seed=17),
        LoosePassiveBot(equity_simulator=EquitySimulator(simulations=250, seed=19), seed=19),
        RecreationalBot(equity_simulator=EquitySimulator(simulations=250, seed=23), seed=23),
    ]
    return {
        player.id: agent_cycle[index - 1]
        for index, player in enumerate(game.players)
        if index > 0
    }


def _player(game: PokerGame, player_id: str):
    for player in game.players:
        if player.id == player_id:
            return player
    raise KeyError(f"Unknown player id: {player_id}")
