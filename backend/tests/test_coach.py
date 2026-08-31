from app.coach.equity import EquitySimulator
from app.coach.odds import pot_odds, stack_to_pot_ratio
from app.coach.recommender import PokerCoach
from app.core.cards import Card
from app.core.game import Action, PokerGame


def cards(text: str) -> list[Card]:
    return [Card.parse(card) for card in text.split()]


def test_pot_odds_for_call() -> None:
    assert pot_odds(amount_to_call=25, pot=75) == 0.25


def test_stack_to_pot_ratio_handles_empty_pot() -> None:
    assert stack_to_pot_ratio(stack=1000, pot=0) == float("inf")


def test_equity_simulator_estimates_strong_hand_above_average() -> None:
    simulator = EquitySimulator(simulations=300, seed=42)

    result = simulator.estimate(
        cards("As Ah"),
        board=[],
        opponents=1,
    )

    assert result.simulations == 300
    assert result.win_probability > 0.75


def test_equity_simulator_estimates_weak_hand_below_premium_pair() -> None:
    simulator = EquitySimulator(simulations=300, seed=42)

    premium = simulator.estimate(cards("As Ah"), board=[], opponents=1)
    weak = simulator.estimate(cards("7c 2d"), board=[], opponents=1)

    assert premium.win_probability > weak.win_probability


def test_coach_recommends_legal_action() -> None:
    game = PokerGame(["You", "Bot"], seed=12)
    coach = PokerCoach(EquitySimulator(simulations=100, seed=5))

    recommendation = coach.recommend(game, player_id="p0")

    assert recommendation.action in game.legal_actions("p0")
    assert 0 <= recommendation.equity <= 1
    assert 0 <= recommendation.pot_odds <= 1
    assert recommendation.reasons


def test_coach_does_not_need_opponent_hole_cards() -> None:
    game = PokerGame(["You", "Bot"], seed=17)
    coach = PokerCoach(EquitySimulator(simulations=100, seed=8))
    hidden_cards = list(game.players[1].hole_cards)

    game.players[1].hole_cards = []
    recommendation = coach.recommend(game, player_id="p0")

    assert recommendation.action in game.legal_actions("p0")
    game.players[1].hole_cards = hidden_cards


def test_coach_can_recommend_check_when_call_is_free() -> None:
    game = PokerGame(["You", "Bot"], seed=21)
    game.apply_action(Action.CALL)
    coach = PokerCoach(EquitySimulator(simulations=100, seed=9))

    recommendation = coach.recommend(game, player_id=game.current_player.id)

    assert recommendation.action in game.legal_actions(game.current_player.id)
