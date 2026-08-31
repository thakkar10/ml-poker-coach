import pytest

from app.core.cards import Card
from app.core.hand_evaluator import HandCategory, evaluate_best_hand


def cards(text: str) -> list[Card]:
    return [Card.parse(card) for card in text.split()]


@pytest.mark.parametrize(
    ("hand", "category"),
    [
        ("As Ks Qs Js Ts 2c 3d", HandCategory.STRAIGHT_FLUSH),
        ("As Ah Ac Ad 9s 2c 3d", HandCategory.FOUR_OF_A_KIND),
        ("As Ah Ac Kd Ks 2c 3d", HandCategory.FULL_HOUSE),
        ("As Js 9s 4s 2s Kd 3c", HandCategory.FLUSH),
        ("As Kd Qc Jh Ts 2c 3d", HandCategory.STRAIGHT),
        ("As Ah Ac Kd Qs 2c 3d", HandCategory.THREE_OF_A_KIND),
        ("As Ah Kc Kd Qs 2c 3d", HandCategory.TWO_PAIR),
        ("As Ah Kc Qd Js 2c 3d", HandCategory.PAIR),
        ("As Kh Qc 9d 7s 4c 2d", HandCategory.HIGH_CARD),
    ],
)
def test_evaluates_hand_categories(hand: str, category: HandCategory) -> None:
    assert evaluate_best_hand(cards(hand)).category == category


def test_wheel_straight_scores_as_five_high() -> None:
    rank = evaluate_best_hand(cards("As 2d 3c 4h 5s Kc Qd"))

    assert rank.category == HandCategory.STRAIGHT
    assert rank.kickers == (5,)


def test_better_pair_wins() -> None:
    aces = evaluate_best_hand(cards("As Ah Kc Qd Js 2c 3d"))
    kings = evaluate_best_hand(cards("Ks Kh Ac Qd Js 2c 3d"))

    assert aces > kings
