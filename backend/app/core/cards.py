from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
import random


class Suit(str, Enum):
    CLUBS = "c"
    DIAMONDS = "d"
    HEARTS = "h"
    SPADES = "s"


class Rank(str, Enum):
    TWO = "2"
    THREE = "3"
    FOUR = "4"
    FIVE = "5"
    SIX = "6"
    SEVEN = "7"
    EIGHT = "8"
    NINE = "9"
    TEN = "T"
    JACK = "J"
    QUEEN = "Q"
    KING = "K"
    ACE = "A"


RANK_VALUES: dict[Rank, int] = {
    Rank.TWO: 2,
    Rank.THREE: 3,
    Rank.FOUR: 4,
    Rank.FIVE: 5,
    Rank.SIX: 6,
    Rank.SEVEN: 7,
    Rank.EIGHT: 8,
    Rank.NINE: 9,
    Rank.TEN: 10,
    Rank.JACK: 11,
    Rank.QUEEN: 12,
    Rank.KING: 13,
    Rank.ACE: 14,
}


@dataclass(frozen=True, order=True)
class Card:
    rank: Rank
    suit: Suit

    @property
    def value(self) -> int:
        return RANK_VALUES[self.rank]

    @classmethod
    def parse(cls, text: str) -> Card:
        if len(text) != 2:
            raise ValueError(f"Invalid card: {text!r}")

        rank_text, suit_text = text[0].upper(), text[1].lower()
        try:
            return cls(Rank(rank_text), Suit(suit_text))
        except ValueError as exc:
            raise ValueError(f"Invalid card: {text!r}") from exc

    def __str__(self) -> str:
        return f"{self.rank.value}{self.suit.value}"


class Deck:
    def __init__(self, *, seed: int | None = None) -> None:
        self._rng = random.Random(seed)
        self.cards = [Card(rank, suit) for suit in Suit for rank in Rank]
        self.shuffle()

    def shuffle(self) -> None:
        self._rng.shuffle(self.cards)

    def deal(self, count: int = 1) -> list[Card]:
        if count < 1:
            raise ValueError("count must be positive")
        if count > len(self.cards):
            raise ValueError("Cannot deal more cards than remain in the deck")

        dealt = self.cards[:count]
        self.cards = self.cards[count:]
        return dealt
