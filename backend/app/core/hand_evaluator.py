from __future__ import annotations

from collections import Counter
from dataclasses import dataclass
from enum import IntEnum
from itertools import combinations

from app.core.cards import Card


class HandCategory(IntEnum):
    HIGH_CARD = 0
    PAIR = 1
    TWO_PAIR = 2
    THREE_OF_A_KIND = 3
    STRAIGHT = 4
    FLUSH = 5
    FULL_HOUSE = 6
    FOUR_OF_A_KIND = 7
    STRAIGHT_FLUSH = 8


@dataclass(frozen=True, order=True)
class HandRank:
    category: HandCategory
    kickers: tuple[int, ...]

    @property
    def label(self) -> str:
        return self.category.name.replace("_", " ").title()


def evaluate_best_hand(cards: list[Card]) -> HandRank:
    if len(cards) < 5:
        raise ValueError("At least five cards are required to evaluate a poker hand")
    if len(set(cards)) != len(cards):
        raise ValueError("Duplicate cards cannot be evaluated")

    return max(_evaluate_five(list(hand)) for hand in combinations(cards, 5))


def _evaluate_five(cards: list[Card]) -> HandRank:
    values = sorted((card.value for card in cards), reverse=True)
    counts = Counter(values)
    groups = sorted(counts.items(), key=lambda item: (item[1], item[0]), reverse=True)
    is_flush = len({card.suit for card in cards}) == 1
    straight_high = _straight_high(values)

    if is_flush and straight_high:
        return HandRank(HandCategory.STRAIGHT_FLUSH, (straight_high,))

    if groups[0][1] == 4:
        four = groups[0][0]
        kicker = max(value for value in values if value != four)
        return HandRank(HandCategory.FOUR_OF_A_KIND, (four, kicker))

    if groups[0][1] == 3 and groups[1][1] == 2:
        return HandRank(HandCategory.FULL_HOUSE, (groups[0][0], groups[1][0]))

    if is_flush:
        return HandRank(HandCategory.FLUSH, tuple(values))

    if straight_high:
        return HandRank(HandCategory.STRAIGHT, (straight_high,))

    if groups[0][1] == 3:
        trips = groups[0][0]
        kickers = sorted((value for value in values if value != trips), reverse=True)
        return HandRank(HandCategory.THREE_OF_A_KIND, (trips, *kickers))

    pair_values = sorted((value for value, count in counts.items() if count == 2), reverse=True)
    if len(pair_values) == 2:
        kicker = max(value for value in values if value not in pair_values)
        return HandRank(HandCategory.TWO_PAIR, (*pair_values, kicker))

    if len(pair_values) == 1:
        pair = pair_values[0]
        kickers = sorted((value for value in values if value != pair), reverse=True)
        return HandRank(HandCategory.PAIR, (pair, *kickers))

    return HandRank(HandCategory.HIGH_CARD, tuple(values))


def _straight_high(values: list[int]) -> int | None:
    unique_values = sorted(set(values), reverse=True)
    if 14 in unique_values:
        unique_values.append(1)

    for index in range(len(unique_values) - 4):
        window = unique_values[index : index + 5]
        if window[0] - window[4] == 4:
            return window[0]
    return None
