import pytest

from app.core.cards import Card
from app.core.game import Action, PokerGame, Street


def cards(text: str) -> list[Card]:
    return [Card.parse(card) for card in text.split()]


def test_new_game_deals_cards_and_posts_blinds() -> None:
    game = PokerGame(["You", "Tight Bot", "Aggro Bot"], seed=11)

    assert len(game.players) == 3
    assert all(len(player.hole_cards) == 2 for player in game.players)
    assert game.pot == 30
    assert game.current_bet == 20
    assert game.street == Street.PREFLOP


def test_heads_up_button_posts_small_blind() -> None:
    game = PokerGame(["You", "Bot"], seed=11)

    assert game.players[0].current_bet == 10
    assert game.players[1].current_bet == 20
    assert game.current_player.id == "p0"


def test_three_player_blinds_start_left_of_button() -> None:
    game = PokerGame(["You", "Tight Bot", "Aggro Bot"], seed=11)

    assert game.players[0].current_bet == 0
    assert game.players[1].current_bet == 10
    assert game.players[2].current_bet == 20
    assert game.current_player.id == "p0"


def test_public_state_hides_opponent_cards_during_live_hand() -> None:
    game = PokerGame(["You", "Bot"], seed=2)

    state = game.to_public_state(viewer_id="p0")

    assert len(state["players"][0]["hole_cards"]) == 2
    assert state["players"][1]["hole_cards"] == []


def test_invalid_action_is_rejected() -> None:
    game = PokerGame(["You", "Bot"], seed=4)

    with pytest.raises(ValueError):
        game.apply_action(Action.CHECK)


def test_fold_awards_pot_to_remaining_player() -> None:
    game = PokerGame(["You", "Bot"], seed=8)
    starting_total = sum(player.stack for player in game.players) + game.pot

    game.apply_action(Action.FOLD)

    assert game.street == Street.COMPLETE
    assert game.pot == 0
    assert game.winners == ["p1"]
    assert sum(player.stack for player in game.players) == starting_total


def test_hand_can_advance_to_flop_after_calls() -> None:
    game = PokerGame(["You", "Bot", "Bot 2"], seed=9)

    game.apply_action(Action.CALL)
    game.apply_action(Action.CALL)
    game.apply_action(Action.CHECK)

    assert game.street == Street.FLOP
    assert len(game.board) == 3


def test_legal_action_state_exposes_all_in_details() -> None:
    game = PokerGame(["You", "Bot"], seed=12)

    legal = game.legal_action_state("p0")

    assert legal.can_call is True
    assert legal.call_amount == 10
    assert legal.can_all_in is True
    assert legal.all_in_amount == game.players[0].stack


def test_short_stack_call_is_legal_partial_all_in() -> None:
    game = PokerGame(["You", "Bot", "Bot 2"], seed=13)
    game.current_player_index = 0
    game.players[0].stack = 15
    game.players[0].current_bet = 0
    game.players[0].total_committed = 0
    game.current_bet = 40

    game.apply_action(Action.CALL)

    assert game.players[0].stack == 0
    assert game.players[0].current_bet == 15
    assert game.players[0].total_committed == 15
    assert game.players[0].all_in is True


def test_all_in_without_existing_bet_is_treated_as_bet() -> None:
    game = PokerGame(["You", "Bot"], seed=14)
    game.apply_action(Action.CALL)

    actor = game.current_player
    game.apply_action(Action.ALL_IN)

    assert actor.stack == 0
    assert actor.all_in is True
    assert game.current_bet == actor.current_bet


def test_short_all_in_raise_is_accepted() -> None:
    game = PokerGame(["You", "Bot", "Bot 2"], seed=15)
    game.current_player_index = 0
    game.players[0].stack = 35
    game.players[0].current_bet = 20
    game.players[0].total_committed = 20
    game.current_bet = 40
    game.last_full_raise = 40

    game.apply_action(Action.ALL_IN)

    assert game.players[0].stack == 0
    assert game.players[0].current_bet == 55
    assert game.current_bet == 55
    assert game.last_full_raise == 40


def test_side_pot_showdown_awards_each_pot_by_eligibility() -> None:
    game = PokerGame(["A", "B", "C"], seed=16)
    game.board = cards("2c 7d 9h Js Qc")
    game.players[0].hole_cards = cards("As Ah")
    game.players[1].hole_cards = cards("Ks Kh")
    game.players[2].hole_cards = cards("3s 4d")
    game.players[0].total_committed = 50
    game.players[1].total_committed = 100
    game.players[2].total_committed = 200
    game.players[0].stack = 0
    game.players[1].stack = 0
    game.players[2].stack = 800
    game.players[0].all_in = True
    game.players[1].all_in = True
    game.pot = 350
    game.street = Street.RIVER

    game._resolve_showdown()

    assert game.players[0].stack == 150
    assert game.players[1].stack == 100
    assert game.players[2].stack == 900
    assert game.pot == 0


def test_split_pot_odd_chip_goes_clockwise_from_button() -> None:
    game = PokerGame(["Button", "Winner 1", "Winner 2"], seed=17)
    game.board = cards("As Ks Qs Js Ts")
    game.players[0].hole_cards = cards("2c 3d")
    game.players[1].hole_cards = cards("4c 5d")
    game.players[2].hole_cards = cards("6c 7d")
    game.players[0].folded = True
    for player in game.players:
        player.total_committed = 1
        player.stack = 999
    game.pot = 3
    game.street = Street.RIVER

    game._resolve_showdown()

    assert game.players[1].stack == 1001
    assert game.players[2].stack == 1000
