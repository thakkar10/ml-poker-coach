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
    BET = "bet"
    RAISE = "raise"
    ALL_IN = "all_in"


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
    seat_position: int
    hole_cards: list[Card] = field(default_factory=list)
    current_bet: int = 0
    total_committed: int = 0
    folded: bool = False
    all_in: bool = False
    active: bool = True


@dataclass
class ActionRecord:
    player_id: str
    action: Action
    amount: int
    street: Street
    full_raise: bool = False


@dataclass(frozen=True)
class LegalActionState:
    can_fold: bool
    can_check: bool
    can_call: bool
    call_amount: int
    can_bet: bool
    minimum_bet: int
    can_raise: bool
    minimum_raise_to: int
    maximum_raise_to: int
    can_all_in: bool
    all_in_amount: int

    def to_dict(self) -> dict[str, int | bool]:
        return {
            "can_fold": self.can_fold,
            "can_check": self.can_check,
            "can_call": self.can_call,
            "call_amount": self.call_amount,
            "can_bet": self.can_bet,
            "minimum_bet": self.minimum_bet,
            "can_raise": self.can_raise,
            "minimum_raise_to": self.minimum_raise_to,
            "maximum_raise_to": self.maximum_raise_to,
            "can_all_in": self.can_all_in,
            "all_in_amount": self.all_in_amount,
        }


@dataclass(frozen=True)
class Pot:
    amount: int
    eligible_player_ids: list[str]


class PokerGame:
    def __init__(
        self,
        player_names: list[str],
        *,
        config: GameConfig | None = None,
        seed: int | None = None,
    ) -> None:
        if not 2 <= len(player_names) <= 10:
            raise ValueError("A poker game needs between 2 and 10 players")

        self.id = str(uuid4())
        self.config = config or GameConfig()
        self.deck = Deck(seed=seed)
        self.players = [
            PlayerState(
                id=f"p{index}",
                name=name,
                stack=self.config.starting_stack,
                seat_position=index,
            )
            for index, name in enumerate(player_names)
        ]
        self.button_index = 0
        self.current_player_index = 0
        self.street = Street.PREFLOP
        self.board: list[Card] = []
        self.pot = 0
        self.current_bet = 0
        self.last_full_raise = self.config.big_blind
        self.small_blind_index = self._small_blind_index()
        self.big_blind_index = self._big_blind_index()
        self.action_history: list[ActionRecord] = []
        self.winners: list[str] = []
        self.showdown_ranks: dict[str, HandRank] = {}
        self.resolved_pots: list[dict[str, object]] = []

        self._deal_hole_cards()
        self._post_blinds()
        self.current_player_index = self._preflop_first_actor_index()

    @property
    def active_players(self) -> list[PlayerState]:
        return [player for player in self.players if player.active and not player.folded]

    @property
    def eligible_players(self) -> list[PlayerState]:
        return [player for player in self.players if player.active and player.stack > 0]

    @property
    def current_player(self) -> PlayerState:
        return self.players[self.current_player_index]

    def legal_action_state(self, player_id: str | None = None) -> LegalActionState:
        player = self._player(player_id) if player_id else self.current_player
        if (
            self.street in {Street.SHOWDOWN, Street.COMPLETE}
            or not player.active
            or player.folded
            or player.all_in
            or player.stack <= 0
        ):
            return LegalActionState(
                can_fold=False,
                can_check=False,
                can_call=False,
                call_amount=0,
                can_bet=False,
                minimum_bet=0,
                can_raise=False,
                minimum_raise_to=0,
                maximum_raise_to=player.current_bet,
                can_all_in=False,
                all_in_amount=0,
            )

        amount_to_call = max(0, self.current_bet - player.current_bet)
        maximum_raise_to = player.current_bet + player.stack
        minimum_bet = min(self.config.big_blind, player.stack)
        minimum_raise_to = self.current_bet + self.last_full_raise if self.current_bet > 0 else minimum_bet
        can_bet = self.current_bet == 0 and player.stack > 0
        can_raise = self.current_bet > 0 and player.stack > amount_to_call and maximum_raise_to >= minimum_raise_to

        return LegalActionState(
            can_fold=True,
            can_check=amount_to_call == 0,
            can_call=amount_to_call > 0,
            call_amount=min(amount_to_call, player.stack),
            can_bet=can_bet,
            minimum_bet=minimum_bet,
            can_raise=can_raise,
            minimum_raise_to=minimum_raise_to,
            maximum_raise_to=maximum_raise_to,
            can_all_in=player.stack > 0,
            all_in_amount=player.stack,
        )

    def legal_actions(self, player_id: str | None = None) -> set[Action]:
        legal = self.legal_action_state(player_id)
        actions: set[Action] = set()
        if legal.can_fold:
            actions.add(Action.FOLD)
        if legal.can_check:
            actions.add(Action.CHECK)
        if legal.can_call:
            actions.add(Action.CALL)
        if legal.can_bet:
            actions.add(Action.BET)
        if legal.can_raise:
            actions.add(Action.RAISE)
        if legal.can_all_in:
            actions.add(Action.ALL_IN)
        return actions

    def apply_action(self, action: Action, amount: int = 0) -> None:
        player = self.current_player
        legal = self.legal_actions(player.id)
        if action not in legal:
            raise ValueError(f"{action.value} is not legal for {player.name}")

        committed = 0
        full_raise = False
        if action == Action.FOLD:
            player.folded = True
        elif action == Action.CHECK:
            committed = 0
        elif action == Action.CALL:
            committed = self._commit_chips(player, self.current_bet - player.current_bet)
        elif action == Action.BET:
            committed, full_raise = self._apply_bet(player, amount)
        elif action == Action.RAISE:
            committed, full_raise = self._apply_raise(player, amount)
        elif action == Action.ALL_IN:
            action, committed, full_raise = self._apply_all_in(player)

        self.action_history.append(ActionRecord(player.id, action, committed, self.street, full_raise))
        self._resolve_or_advance()

    def perform_all_in(self, player_id: str | None = None) -> None:
        if player_id is not None and self.current_player.id != player_id:
            raise ValueError("It is not this player's turn")
        self.apply_action(Action.ALL_IN)

    def to_public_state(self, *, viewer_id: str = "p0") -> dict[str, Any]:
        return {
            "id": self.id,
            "street": self.street.value,
            "pot": self.pot,
            "current_bet": self.current_bet,
            "board": [str(card) for card in self.board],
            "current_player_id": self.current_player.id if self.street != Street.COMPLETE else None,
            "button_player_id": self.players[self.button_index].id,
            "small_blind_player_id": self.players[self.small_blind_index].id,
            "big_blind_player_id": self.players[self.big_blind_index].id,
            "legal_action_details": self.legal_action_state().to_dict(),
            "legal_actions": [action.value for action in sorted(self.legal_actions(), key=lambda item: item.value)],
            "players": [
                {
                    "id": player.id,
                    "name": player.name,
                    "seat_position": player.seat_position,
                    "stack": player.stack,
                    "current_bet": player.current_bet,
                    "total_committed": player.total_committed,
                    "folded": player.folded,
                    "all_in": player.all_in,
                    "active": player.active,
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
            "side_pots": self.resolved_pots,
        }

    def _deal_hole_cards(self) -> None:
        for _ in range(2):
            for player in self.players:
                player.hole_cards.extend(self.deck.deal())

    def _post_blinds(self) -> None:
        small_blind = self.players[self.small_blind_index]
        big_blind = self.players[self.big_blind_index]
        self._commit_chips(small_blind, self.config.small_blind)
        self._commit_chips(big_blind, self.config.big_blind)
        self.current_bet = max(player.current_bet for player in self.players)
        self.last_full_raise = self.config.big_blind

    def _small_blind_index(self) -> int:
        active_indices = self._eligible_indices()
        if len(active_indices) == 2:
            return self.button_index
        return self._next_eligible_index(self.button_index)

    def _big_blind_index(self) -> int:
        return self._next_eligible_index(self._small_blind_index())

    def _preflop_first_actor_index(self) -> int:
        if len(self._eligible_indices()) == 2:
            return self.button_index
        return self._next_active_index(self.big_blind_index)

    def _commit_chips(self, player: PlayerState, amount: int) -> int:
        if amount < 0:
            raise ValueError("Cannot commit a negative chip amount")
        committed = min(amount, player.stack)
        player.stack -= committed
        player.current_bet += committed
        player.total_committed += committed
        self.pot += committed
        if player.stack == 0:
            player.all_in = True
        return committed

    def _apply_bet(self, player: PlayerState, amount: int) -> tuple[int, bool]:
        if self.current_bet != 0:
            raise ValueError("Bet is only legal before betting has opened")
        target_total = player.current_bet + player.stack if amount <= 0 else amount
        target_total = min(target_total, player.current_bet + player.stack)
        if target_total <= player.current_bet:
            raise ValueError("Bet amount must add chips")
        if target_total < self.config.big_blind and target_total < player.current_bet + player.stack:
            raise ValueError("Bet must be at least the big blind unless all-in")

        committed = self._commit_chips(player, target_total - player.current_bet)
        self.current_bet = player.current_bet
        self.last_full_raise = max(self.last_full_raise, self.current_bet)
        return committed, committed >= self.config.big_blind

    def _apply_raise(self, player: PlayerState, amount: int) -> tuple[int, bool]:
        if self.current_bet == 0:
            return self._apply_bet(player, amount)

        target_total = min(amount, player.current_bet + player.stack)
        if target_total <= self.current_bet:
            raise ValueError("Raise amount must exceed the current table bet")

        minimum_raise_to = self.current_bet + self.last_full_raise
        if target_total < minimum_raise_to and target_total < player.current_bet + player.stack:
            raise ValueError("Raise must meet the minimum raise unless all-in")

        previous_bet = self.current_bet
        committed = self._commit_chips(player, target_total - player.current_bet)
        self.current_bet = max(self.current_bet, player.current_bet)
        raise_size = self.current_bet - previous_bet
        full_raise = raise_size >= self.last_full_raise
        if full_raise:
            self.last_full_raise = raise_size
        return committed, full_raise

    def _apply_all_in(self, player: PlayerState) -> tuple[Action, int, bool]:
        if player.stack <= 0:
            raise ValueError("Player has no chips left to wager")

        amount_to_call = max(0, self.current_bet - player.current_bet)
        all_in_total = player.current_bet + player.stack

        if self.current_bet == 0:
            committed, full_raise = self._apply_bet(player, all_in_total)
            return Action.BET, committed, full_raise

        if all_in_total <= self.current_bet:
            committed = self._commit_chips(player, amount_to_call)
            return Action.CALL, committed, False

        committed, full_raise = self._apply_raise(player, all_in_total)
        return Action.RAISE, committed, full_raise

    def _resolve_or_advance(self) -> None:
        if len(self.active_players) == 1:
            self._award_folded_pot()
            return

        if self._no_further_betting_possible():
            self._runout_to_showdown()
            return

        if self._betting_round_complete():
            self._advance_street()
            return

        self.current_player_index = self._next_active_index(self.current_player_index)

    def _no_further_betting_possible(self) -> bool:
        active_not_all_in = [player for player in self.active_players if not player.all_in]
        if active_not_all_in:
            return False
        return len(self.active_players) > 1

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
        self.last_full_raise = self.config.big_blind

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

        if self._no_further_betting_possible():
            self._runout_to_showdown()
            return

        self.current_player_index = self._next_active_index(self.button_index)

    def _runout_to_showdown(self) -> None:
        while self.street != Street.COMPLETE:
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
            elif self.street == Street.SHOWDOWN:
                self._resolve_showdown()

    def _resolve_showdown(self) -> None:
        self.showdown_ranks = {
            player.id: evaluate_best_hand([*player.hole_cards, *self.board])
            for player in self.active_players
        }
        awarded_winners: list[str] = []
        resolved_pots: list[dict[str, object]] = []

        for pot in self._build_pots():
            eligible_ranks = {
                player_id: self.showdown_ranks[player_id]
                for player_id in pot.eligible_player_ids
                if player_id in self.showdown_ranks
            }
            if not eligible_ranks:
                continue

            best_rank = max(eligible_ranks.values())
            pot_winners = [
                player_id for player_id, rank in eligible_ranks.items() if rank == best_rank
            ]
            share = pot.amount // len(pot_winners)
            odd_chips = pot.amount % len(pot_winners)
            ordered_winners = self._clockwise_order_from_button(pot_winners)
            for winner_id in pot_winners:
                self._player(winner_id).stack += share
            for winner_id in ordered_winners[:odd_chips]:
                self._player(winner_id).stack += 1

            for winner_id in ordered_winners:
                if winner_id not in awarded_winners:
                    awarded_winners.append(winner_id)
            resolved_pots.append(
                {
                    "amount": pot.amount,
                    "eligible_player_ids": pot.eligible_player_ids,
                    "winner_ids": ordered_winners,
                }
            )

        self.winners = awarded_winners
        self.resolved_pots = resolved_pots
        self.pot = 0
        self.street = Street.COMPLETE

    def _award_folded_pot(self) -> None:
        winner = self.active_players[0]
        winner.stack += self.pot
        self.pot = 0
        self.winners = [winner.id]
        self.resolved_pots = [
            {
                "amount": sum(player.total_committed for player in self.players),
                "eligible_player_ids": [winner.id],
                "winner_ids": [winner.id],
            }
        ]
        self.street = Street.COMPLETE

    def _build_pots(self) -> list[Pot]:
        pots: list[Pot] = []
        previous_level = 0
        contribution_levels = sorted(
            {
                player.total_committed
                for player in self.players
                if player.total_committed > 0
            }
        )

        for level in contribution_levels:
            contributors = [
                player
                for player in self.players
                if player.total_committed >= level
            ]
            amount = (level - previous_level) * len(contributors)
            if amount <= 0:
                previous_level = level
                continue

            eligible_player_ids = [
                player.id
                for player in contributors
                if player.active and not player.folded
            ]
            if len(contributors) == 1:
                contributors[0].stack += amount
            elif eligible_player_ids:
                pots.append(Pot(amount=amount, eligible_player_ids=eligible_player_ids))
            previous_level = level

        return pots

    def _clockwise_order_from_button(self, player_ids: list[str]) -> list[str]:
        wanted = set(player_ids)
        ordered: list[str] = []
        for offset in range(1, len(self.players) + 1):
            player = self.players[(self.button_index + offset) % len(self.players)]
            if player.id in wanted:
                ordered.append(player.id)
        return ordered

    def _next_active_index(self, start_index: int) -> int:
        for offset in range(1, len(self.players) + 1):
            index = (start_index + offset) % len(self.players)
            player = self.players[index]
            if player.active and not player.folded and not player.all_in:
                return index
        return start_index

    def _next_eligible_index(self, start_index: int) -> int:
        for offset in range(1, len(self.players) + 1):
            index = (start_index + offset) % len(self.players)
            player = self.players[index]
            if player.active and player.stack > 0:
                return index
        return start_index

    def _eligible_indices(self) -> list[int]:
        return [
            index
            for index, player in enumerate(self.players)
            if player.active and player.stack > 0
        ]

    def _player(self, player_id: str) -> PlayerState:
        for player in self.players:
            if player.id == player_id:
                return player
        raise KeyError(f"Unknown player id: {player_id}")
