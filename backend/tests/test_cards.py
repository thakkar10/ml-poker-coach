import pytest

from app.core.cards import Card, Deck, Rank, Suit


def test_deck_contains_52_unique_cards() -> None:
    deck = Deck(seed=7)

    assert len(deck.cards) == 52
    assert len(set(deck.cards)) == 52


def test_card_parse_and_string_round_trip() -> None:
    card = Card.parse("As")

    assert card.rank == Rank.ACE
    assert card.suit == Suit.SPADES
    assert str(card) == "As"


def test_deal_removes_cards_from_deck() -> None:
    deck = Deck(seed=3)

    dealt = deck.deal(5)

    assert len(dealt) == 5
    assert len(deck.cards) == 47


def test_deal_rejects_too_many_cards() -> None:
    deck = Deck(seed=3)

    with pytest.raises(ValueError):
        deck.deal(53)
