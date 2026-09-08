from app.core.game import Action
from app.ml import DecisionLog, PlayerStyleAnalyzer


def decision(
    action: Action,
    recommended: Action,
    *,
    equity: float,
    pot_odds: float,
) -> DecisionLog:
    return DecisionLog(
        street="flop",
        action=action,
        amount=20,
        recommended_action=recommended,
        equity=equity,
        pot_odds=pot_odds,
        confidence=0.7,
        pot=100,
        current_bet=20,
        active_players=3,
    )


def test_analyzer_classifies_loose_passive_caller() -> None:
    review = PlayerStyleAnalyzer().analyze(
        [
            decision(Action.CALL, Action.FOLD, equity=0.18, pot_odds=0.32),
            decision(Action.CALL, Action.CALL, equity=0.40, pot_odds=0.25),
            decision(Action.CHECK, Action.RAISE, equity=0.68, pot_odds=0),
            decision(Action.CALL, Action.FOLD, equity=0.20, pot_odds=0.35),
        ]
    )

    assert review.style == "Loose Passive"
    assert review.call_rate == 1
    assert any("too expensive" in leak for leak in review.leaks)
    assert any("calling less" in step for step in review.next_steps)


def test_analyzer_flags_overfolding() -> None:
    review = PlayerStyleAnalyzer().analyze(
        [
            decision(Action.FOLD, Action.CALL, equity=0.55, pot_odds=0.30),
            decision(Action.FOLD, Action.RAISE, equity=0.70, pot_odds=0.25),
        ]
    )

    assert "Tight" in review.style
    assert any("folded some hands" in leak for leak in review.leaks)
