from __future__ import annotations

import random

from app.agents.base import AgentAction
from app.coach.equity import EquitySimulator
from app.coach.odds import pot_odds
from app.core.cards import Card
from app.core.game import Action, PokerGame


class RandomBot:
    name = "Random Bot"

    def __init__(self, *, seed: int | None = None) -> None:
        self._rng = random.Random(seed)

    def choose_action(self, game: PokerGame, *, player_id: str) -> AgentAction:
        legal = sorted(game.legal_actions(player_id), key=lambda action: action.value)
        action = self._rng.choice(legal)
        amount = _raise_amount(game, player_id) if action == Action.RAISE else 0
        return AgentAction(action, amount, "Chooses randomly from legal actions.")


class TightBot:
    name = "Tight Bot"

    def __init__(self, *, equity_simulator: EquitySimulator | None = None) -> None:
        self.equity_simulator = equity_simulator or EquitySimulator(simulations=300)

    def choose_action(self, game: PokerGame, *, player_id: str) -> AgentAction:
        legal = game.legal_actions(player_id)
        equity = _estimate_equity(self.equity_simulator, game, player_id)
        call_price = _amount_to_call(game, player_id)
        required_equity = pot_odds(call_price, game.pot)

        if call_price > 0 and equity < max(0.30, required_equity + 0.04):
            return AgentAction(Action.FOLD, reason="Tight bot folds without a strong enough equity edge.")
        if equity > 0.68 and Action.RAISE in legal:
            return AgentAction(Action.RAISE, _raise_amount(game, player_id), "Tight bot raises with a premium spot.")
        if Action.CALL in legal:
            return AgentAction(Action.CALL, reason="Tight bot continues with sufficient equity.")
        return AgentAction(Action.CHECK, reason="Tight bot checks without a strong value edge.")


class AggressiveBot:
    name = "Aggressive Bot"

    def __init__(
        self,
        *,
        equity_simulator: EquitySimulator | None = None,
        seed: int | None = None,
    ) -> None:
        self.equity_simulator = equity_simulator or EquitySimulator(simulations=300)
        self._rng = random.Random(seed)

    def choose_action(self, game: PokerGame, *, player_id: str) -> AgentAction:
        legal = game.legal_actions(player_id)
        equity = _estimate_equity(self.equity_simulator, game, player_id)
        call_price = _amount_to_call(game, player_id)
        required_equity = pot_odds(call_price, game.pot)

        if Action.RAISE in legal and (equity > 0.48 or self._rng.random() < 0.22):
            return AgentAction(Action.RAISE, _raise_amount(game, player_id), "Aggressive bot applies pressure.")
        if Action.CALL in legal and equity + 0.08 >= required_equity:
            return AgentAction(Action.CALL, reason="Aggressive bot continues with a playable edge.")
        if Action.CHECK in legal:
            return AgentAction(Action.CHECK, reason="Aggressive bot checks when raising is not attractive.")
        return AgentAction(Action.FOLD, reason="Aggressive bot gives up when the price is too high.")


class EquityBot:
    name = "Equity Bot"

    def __init__(self, *, equity_simulator: EquitySimulator | None = None) -> None:
        self.equity_simulator = equity_simulator or EquitySimulator(simulations=300)

    def choose_action(self, game: PokerGame, *, player_id: str) -> AgentAction:
        legal = game.legal_actions(player_id)
        equity = _estimate_equity(self.equity_simulator, game, player_id)
        call_price = _amount_to_call(game, player_id)
        required_equity = pot_odds(call_price, game.pot)

        if call_price > 0 and equity + 0.02 < required_equity:
            return AgentAction(Action.FOLD, reason="Equity bot folds because equity is below pot odds.")
        if equity > required_equity + 0.16 and Action.RAISE in legal:
            return AgentAction(Action.RAISE, _raise_amount(game, player_id), "Equity bot raises with a clear mathematical edge.")
        if Action.CALL in legal:
            return AgentAction(Action.CALL, reason="Equity bot calls because the price is profitable enough.")
        return AgentAction(Action.CHECK, reason="Equity bot checks when continuing is free.")


def _estimate_equity(
    simulator: EquitySimulator,
    game: PokerGame,
    player_id: str,
) -> float:
    player = _player(game, player_id)
    opponents = len([candidate for candidate in game.active_players if candidate.id != player_id])
    dead_cards = _dead_cards(game, player_id)
    return simulator.estimate(
        player.hole_cards,
        game.board,
        opponents=max(1, opponents),
        dead_cards=dead_cards,
    ).win_probability


def _dead_cards(game: PokerGame, player_id: str) -> list[Card]:
    # Folded players' cards are known to the engine but not to live decision makers.
    return [
        card
        for player in game.players
        if player.id != player_id and player.folded
        for card in player.hole_cards
    ]


def _amount_to_call(game: PokerGame, player_id: str) -> int:
    player = _player(game, player_id)
    return max(0, game.current_bet - player.current_bet)


def _raise_amount(game: PokerGame, player_id: str) -> int:
    player = _player(game, player_id)
    minimum_raise_to = max(game.config.big_blind, game.current_bet + game.config.big_blind)
    pressure_raise_to = game.current_bet + max(game.config.big_blind, game.pot // 2)
    all_in_raise_to = player.current_bet + player.stack
    return min(max(minimum_raise_to, pressure_raise_to), all_in_raise_to)


def _player(game: PokerGame, player_id: str):
    for player in game.players:
        if player.id == player_id:
            return player
    raise KeyError(f"Unknown player id: {player_id}")
