from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any
from uuid import uuid4

from app.core.cards import Card, Deck
from app.core.hand_evaluator import HandRank, evaluate_best_hand


class Action(str, Enum):
    FOLD = "fold"
    CHECK = "check"
    CALL = "call"
    RAISE = "raise"


class Street(str, Enum):
    PREFLOP = "preflop"
    FLOP = "flop"
    TURN = "turn"
    RIVER = "river"
    SHOWDOWN = "showdown"
    COMPLETE = "complete"


@dataclass
class GameConfig:
    small_blind: int = 10
    big_blind: int = 20
    starting_stack: int = 1_000


@dataclass
class PlayerState:
    id: str
    name: str
    stack: int
    hole_cards: list[Card] = field(default_factory=list)
    current_bet: int = 0
    folded: bool = False
    all_in: bool = False


@dataclass
class ActionRecord:
    player_id: str
    action: Action
    amount: int
    street: Street


class PokerGame:
    def __init__(
        self,
        player_names: list[str],
        *,
        config: GameConfig | None = None,
        seed: int | None = None,
    ) -> None:
        if len(player_names) < 2:
            raise ValueError("A poker game needs at least two players")

        self.id = str(uuid4())
        self.config = config or GameConfig()
        self.deck = Deck(seed=seed)
        self.players = [
            PlayerState(id=f"p{index}", name=name, stack=self.config.starting_stack)
            for index, name in enumerate(player_names)
        ]
        self.button_index = 0
        self.current_player_index = 0
        self.street = Street.PREFLOP
        self.board: list[Card] = []
        self.pot = 0
        self.current_bet = 0
        self.action_history: list[ActionRecord] = []
        self.winners: list[str] = []
        self.showdown_ranks: dict[str, HandRank] = {}

        self._deal_hole_cards()
        self._post_blinds()
        self.current_player_index = self._next_active_index(self._big_blind_index())

    @property
    def active_players(self) -> list[PlayerState]:
        return [player for player in self.players if not player.folded]

    @property
    def current_player(self) -> PlayerState:
        return self.players[self.current_player_index]

    def legal_actions(self, player_id: str | None = None) -> set[Action]:
        player = self._player(player_id) if player_id else self.current_player
        if self.street in {Street.SHOWDOWN, Street.COMPLETE} or player.folded or player.all_in:
            return set()

        to_call = self.current_bet - player.current_bet
        actions = {Action.FOLD}
        if to_call == 0:
            actions.add(Action.CHECK)
        else:
            actions.add(Action.CALL)
        if player.stack > to_call:
            actions.add(Action.RAISE)
        return actions

    def apply_action(self, action: Action, amount: int = 0) -> None:
        player = self.current_player
        legal = self.legal_actions(player.id)
        if action not in legal:
            raise ValueError(f"{action.value} is not legal for {player.name}")

        committed = 0
        if action == Action.FOLD:
            player.folded = True
        elif action == Action.CHECK:
            committed = 0
        elif action == Action.CALL:
            committed = self._commit_chips(player, self.current_bet - player.current_bet)
        elif action == Action.RAISE:
            if amount <= self.current_bet:
                raise ValueError("Raise amount must exceed the current table bet")
            committed = self._commit_chips(player, amount - player.current_bet)
            self.current_bet = player.current_bet

        self.action_history.append(ActionRecord(player.id, action, committed, self.street))
        self._resolve_or_advance()

    def to_public_state(self, *, viewer_id: str = "p0") -> dict[str, Any]:
        return {
            "id": self.id,
            "street": self.street.value,
            "pot": self.pot,
            "current_bet": self.current_bet,
            "board": [str(card) for card in self.board],
            "current_player_id": self.current_player.id if self.street != Street.COMPLETE else None,
            "button_player_id": self.players[self.button_index].id,
            "small_blind_player_id": self.players[self._small_blind_index()].id,
            "big_blind_player_id": self.players[self._big_blind_index()].id,
            "legal_actions": [action.value for action in sorted(self.legal_actions(), key=lambda item: item.value)],
            "players": [
                {
                    "id": player.id,
                    "name": player.name,
                    "stack": player.stack,
                    "current_bet": player.current_bet,
                    "folded": player.folded,
                    "all_in": player.all_in,
                    "hole_cards": [str(card) for card in player.hole_cards]
                    if player.id == viewer_id or self.street in {Street.SHOWDOWN, Street.COMPLETE}
                    else [],
                }
                for player in self.players
            ],
            "winners": self.winners,
            "showdown": {
                player_id: rank.label for player_id, rank in self.showdown_ranks.items()
            },
        }

    def _deal_hole_cards(self) -> None:
        for _ in range(2):
            for player in self.players:
                player.hole_cards.extend(self.deck.deal())

    def _post_blinds(self) -> None:
        small_blind = self.players[self._small_blind_index()]
        big_blind = self.players[self._big_blind_index()]
        self._commit_chips(small_blind, self.config.small_blind)
        self._commit_chips(big_blind, self.config.big_blind)
        self.current_bet = self.config.big_blind

    def _small_blind_index(self) -> int:
        if len(self.players) == 2:
            return self.button_index
        return (self.button_index + 1) % len(self.players)

    def _big_blind_index(self) -> int:
        if len(self.players) == 2:
            return (self.button_index + 1) % len(self.players)
        return (self.button_index + 2) % len(self.players)

    def _commit_chips(self, player: PlayerState, amount: int) -> int:
        if amount < 0:
            raise ValueError("Cannot commit a negative chip amount")
        committed = min(amount, player.stack)
        player.stack -= committed
        player.current_bet += committed
        self.pot += committed
        if player.stack == 0:
            player.all_in = True
        return committed

    def _resolve_or_advance(self) -> None:
        if len(self.active_players) == 1:
            self._award_folded_pot()
            return

        if self._betting_round_complete():
            self._advance_street()
            return

        self.current_player_index = self._next_active_index(self.current_player_index)

    def _betting_round_complete(self) -> bool:
        active_not_all_in = [player for player in self.active_players if not player.all_in]
        if not active_not_all_in:
            return True
        acted_ids = {
            record.player_id
            for record in self.action_history
            if record.street == self.street
        }
        return all(
            player.current_bet == self.current_bet and player.id in acted_ids
            for player in active_not_all_in
        )

    def _advance_street(self) -> None:
        for player in self.players:
            player.current_bet = 0
        self.current_bet = 0

        if self.street == Street.PREFLOP:
            self.board.extend(self.deck.deal(3))
            self.street = Street.FLOP
        elif self.street == Street.FLOP:
            self.board.extend(self.deck.deal(1))
            self.street = Street.TURN
        elif self.street == Street.TURN:
            self.board.extend(self.deck.deal(1))
            self.street = Street.RIVER
        elif self.street == Street.RIVER:
            self.street = Street.SHOWDOWN
            self._resolve_showdown()
            return

        self.current_player_index = self._next_active_index(self.button_index)

    def _resolve_showdown(self) -> None:
        self.showdown_ranks = {
            player.id: evaluate_best_hand([*player.hole_cards, *self.board])
            for player in self.active_players
        }
        best_rank = max(self.showdown_ranks.values())
        self.winners = [
            player_id for player_id, rank in self.showdown_ranks.items() if rank == best_rank
        ]
        split_pot = self.pot // len(self.winners)
        for winner_id in self.winners:
            self._player(winner_id).stack += split_pot
        self.pot = 0
        self.street = Street.COMPLETE

    def _award_folded_pot(self) -> None:
        winner = self.active_players[0]
        winner.stack += self.pot
        self.pot = 0
        self.winners = [winner.id]
        self.street = Street.COMPLETE

    def _next_active_index(self, start_index: int) -> int:
        for offset in range(1, len(self.players) + 1):
            index = (start_index + offset) % len(self.players)
            player = self.players[index]
            if not player.folded and not player.all_in:
                return index
        return start_index

    def _player(self, player_id: str) -> PlayerState:
        for player in self.players:
            if player.id == player_id:
                return player
        raise KeyError(f"Unknown player id: {player_id}")
