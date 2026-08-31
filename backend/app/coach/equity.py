from __future__ import annotations

from dataclasses import dataclass
import random

from app.core.cards import Card, Rank, Suit
from app.core.hand_evaluator import evaluate_best_hand


@dataclass(frozen=True)
class EquityResult:
    wins: int
    ties: int
    losses: int
    simulations: int

    @property
    def win_probability(self) -> float:
        if self.simulations == 0:
            return 0.0
        return (self.wins + 0.5 * self.ties) / self.simulations


class EquitySimulator:
    def __init__(self, *, simulations: int = 1_000, seed: int | None = None) -> None:
        if simulations < 1:
            raise ValueError("simulations must be positive")
        self.simulations = simulations
        self._rng = random.Random(seed)

    def estimate(
        self,
        hero_cards: list[Card],
        board: list[Card],
        *,
        opponents: int,
        dead_cards: list[Card] | None = None,
    ) -> EquityResult:
        if len(hero_cards) != 2:
            raise ValueError("hero must have exactly two hole cards")
        if len(board) > 5:
            raise ValueError("board cannot contain more than five cards")
        if opponents < 1:
            raise ValueError("at least one opponent is required")

        known_cards = [*hero_cards, *board, *(dead_cards or [])]
        if len(set(known_cards)) != len(known_cards):
            raise ValueError("known cards cannot contain duplicates")

        wins = ties = losses = 0
        for _ in range(self.simulations):
            deck = self._remaining_deck(known_cards)
            self._rng.shuffle(deck)

            opponent_hands = []
            cursor = 0
            for _opponent in range(opponents):
                opponent_hands.append(deck[cursor : cursor + 2])
                cursor += 2

            missing_board_cards = 5 - len(board)
            sampled_board = [*board, *deck[cursor : cursor + missing_board_cards]]

            hero_rank = evaluate_best_hand([*hero_cards, *sampled_board])
            opponent_ranks = [
                evaluate_best_hand([*hand, *sampled_board]) for hand in opponent_hands
            ]
            best_opponent_rank = max(opponent_ranks)

            if hero_rank > best_opponent_rank:
                wins += 1
            elif hero_rank == best_opponent_rank:
                ties += 1
            else:
                losses += 1

        return EquityResult(
            wins=wins,
            ties=ties,
            losses=losses,
            simulations=self.simulations,
        )

    def _remaining_deck(self, known_cards: list[Card]) -> list[Card]:
        known = set(known_cards)
        return [
            Card(rank, suit)
            for suit in Suit
            for rank in Rank
            if Card(rank, suit) not in known
        ]
