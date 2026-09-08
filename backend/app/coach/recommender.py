from __future__ import annotations

from dataclasses import dataclass

from app.coach.equity import EquitySimulator
from app.coach.odds import pot_odds, stack_to_pot_ratio
from app.core.game import Action, PlayerState, PokerGame


@dataclass(frozen=True)
class CoachRecommendation:
    action: Action
    amount: int
    equity: float
    pot_odds: float
    confidence: float
    reasons: list[str]

    def to_dict(self) -> dict[str, object]:
        return {
            "action": self.action.value,
            "amount": self.amount,
            "equity": round(self.equity, 4),
            "pot_odds": round(self.pot_odds, 4),
            "confidence": round(self.confidence, 4),
            "reasons": self.reasons,
        }


class PokerCoach:
    def __init__(self, equity_simulator: EquitySimulator | None = None) -> None:
        self.equity_simulator = equity_simulator or EquitySimulator(simulations=1_000)

    def recommend(self, game: PokerGame, *, player_id: str = "p0") -> CoachRecommendation:
        player = _player(game, player_id)
        legal_actions = game.legal_actions(player_id)
        if not legal_actions:
            raise ValueError("No legal actions are available for this player")

        amount_to_call = max(0, game.current_bet - player.current_bet)
        active_opponents = len([p for p in game.active_players if p.id != player_id])
        equity_result = self.equity_simulator.estimate(
            player.hole_cards,
            game.board,
            opponents=max(1, active_opponents),
        )
        equity = equity_result.win_probability
        required_equity = pot_odds(amount_to_call, game.pot)
        spr = stack_to_pot_ratio(player.stack, max(game.pot, 1))
        edge = equity - required_equity

        action = self._choose_action(
            legal_actions=legal_actions,
            equity=equity,
            required_equity=required_equity,
            amount_to_call=amount_to_call,
        )
        amount = self._raise_amount(game, player, action)
        confidence = min(0.95, max(0.05, 0.50 + abs(edge)))
        reasons = self._explain(
            action=action,
            equity=equity,
            required_equity=required_equity,
            amount_to_call=amount_to_call,
            active_opponents=active_opponents,
            spr=spr,
        )

        return CoachRecommendation(
            action=action,
            amount=amount,
            equity=equity,
            pot_odds=required_equity,
            confidence=confidence,
            reasons=reasons,
        )

    def _choose_action(
        self,
        *,
        legal_actions: set[Action],
        equity: float,
        required_equity: float,
        amount_to_call: int,
    ) -> Action:
        if amount_to_call == 0 and Action.CHECK in legal_actions:
            pressure_action = self._pressure_action(legal_actions)
            if equity >= 0.62 and pressure_action:
                return pressure_action
            return Action.CHECK

        if equity + 0.03 < required_equity and Action.FOLD in legal_actions:
            return Action.FOLD

        pressure_action = self._pressure_action(legal_actions)
        if equity >= required_equity + 0.18 and pressure_action:
            return pressure_action

        if Action.CALL in legal_actions:
            return Action.CALL

        return sorted(legal_actions, key=lambda item: item.value)[0]

    def _raise_amount(self, game: PokerGame, player: PlayerState, action: Action) -> int:
        if action not in {Action.BET, Action.RAISE}:
            return 0
        legal = game.legal_action_state(player.id)
        minimum_raise_to = legal.minimum_raise_to if action == Action.RAISE else legal.minimum_bet
        value_raise_to = game.current_bet + max(game.config.big_blind, game.pot // 2)
        affordable_raise_to = player.current_bet + player.stack
        return min(max(minimum_raise_to, value_raise_to), affordable_raise_to)

    def _pressure_action(self, legal_actions: set[Action]) -> Action | None:
        if Action.RAISE in legal_actions:
            return Action.RAISE
        if Action.BET in legal_actions:
            return Action.BET
        return None

    def _explain(
        self,
        *,
        action: Action,
        equity: float,
        required_equity: float,
        amount_to_call: int,
        active_opponents: int,
        spr: float,
    ) -> list[str]:
        reasons = [
            f"Estimated win probability is {equity:.0%} against {active_opponents} active opponent(s).",
        ]

        if amount_to_call > 0:
            reasons.append(f"Calling requires about {required_equity:.0%} equity based on pot odds.")
        else:
            reasons.append("Checking is free, so folding is unnecessary.")

        if action == Action.FOLD:
            reasons.append("The estimated equity is below the price of calling.")
        elif action == Action.CALL:
            reasons.append("The hand has enough equity to continue, but not enough edge to raise confidently.")
        elif action == Action.CHECK:
            reasons.append("The hand can continue for free without growing the pot.")
        elif action in {Action.BET, Action.RAISE}:
            reasons.append("The equity edge is strong enough to apply pressure or build value.")

        if spr < 3:
            reasons.append("Stack-to-pot ratio is low, so big decisions commit a meaningful part of the stack.")
        elif spr > 10:
            reasons.append("Stacks are deep relative to the pot, so the coach avoids overcommitting marginal hands.")

        return reasons


def _player(game: PokerGame, player_id: str) -> PlayerState:
    for player in game.players:
        if player.id == player_id:
            return player
    raise KeyError(f"Unknown player id: {player_id}")
