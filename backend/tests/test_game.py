import pytest

from app.core.game import Action, PokerGame, Street


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
