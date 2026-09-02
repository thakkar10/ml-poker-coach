from app.agents import AggressiveBot, EquityBot, LoosePassiveBot, RandomBot, RecreationalBot, TightBot
from app.coach.equity import EquitySimulator
from app.core.cards import Card
from app.core.game import Action, PokerGame
from app.services import TableRunner


def cards(text: str) -> list[Card]:
    return [Card.parse(card) for card in text.split()]


def test_all_bot_strategies_choose_legal_actions() -> None:
    game = PokerGame(["You", "Random", "Tight", "Aggro", "Equity"], seed=31)
    simulator = EquitySimulator(simulations=50, seed=31)
    bots = {
        "p1": RandomBot(seed=1),
        "p2": TightBot(equity_simulator=simulator),
        "p3": AggressiveBot(equity_simulator=simulator, seed=2),
        "p4": EquityBot(equity_simulator=simulator),
    }

    for player_id, bot in bots.items():
        action = bot.choose_action(game, player_id=player_id)

        assert action.action in game.legal_actions(player_id)


def test_tight_bot_folds_weak_hand_to_expensive_call() -> None:
    game = PokerGame(["You", "Tight"], seed=1)
    tight = TightBot(equity_simulator=EquitySimulator(simulations=80, seed=2))
    game.players[1].hole_cards = cards("7c 2d")
    game.current_player_index = 1
    game.players[0].current_bet = 200
    game.current_bet = 200
    game.pot = 260

    action = tight.choose_action(game, player_id="p1")

    assert action.action == Action.FOLD


def test_aggressive_bot_raises_premium_hand_more_often_than_tight_threshold() -> None:
    game = PokerGame(["You", "Aggro"], seed=1)
    aggro = AggressiveBot(
        equity_simulator=EquitySimulator(simulations=80, seed=3),
        seed=4,
    )
    game.players[1].hole_cards = cards("As Ah")
    game.current_player_index = 1
    game.players[1].current_bet = game.current_bet

    action = aggro.choose_action(game, player_id="p1")

    assert action.action == Action.RAISE
    assert action.amount > 0


def test_table_runner_plays_bots_until_user_turn() -> None:
    game = PokerGame(["You", "Tight", "Aggro"], seed=44)
    runner = TableRunner(
        {
            "p1": TightBot(equity_simulator=EquitySimulator(simulations=40, seed=5)),
            "p2": AggressiveBot(
                equity_simulator=EquitySimulator(simulations=40, seed=6),
                seed=7,
            ),
        }
    )

    game.apply_action(Action.CALL)
    logs = runner.play_until_user_turn_or_complete(game, user_player_id="p0")

    assert logs
    assert game.current_player.id == "p0" or game.street.value == "complete"
    assert all(log.action.reason for log in logs)


def test_table_runner_stops_immediately_on_user_turn() -> None:
    game = PokerGame(["You", "Bot", "Bot 2"], seed=44)
    runner = TableRunner({"p1": RandomBot(seed=1), "p2": RandomBot(seed=2)})

    logs = runner.play_until_user_turn_or_complete(game, user_player_id="p0")

    assert logs == []
    assert game.current_player.id == "p0"


def test_deep_stacked_bots_use_normal_raise_sizes_instead_of_open_shoving() -> None:
    game = PokerGame(["You", "Aggro"], seed=1)
    aggro = AggressiveBot(
        equity_simulator=EquitySimulator(simulations=80, seed=3),
        seed=4,
    )
    game.players[1].hole_cards = cards("As Ah")
    game.current_player_index = 1
    game.players[1].current_bet = game.current_bet

    action = aggro.choose_action(game, player_id="p1")

    assert action.action == Action.RAISE
    assert game.config.big_blind * 2 <= action.amount <= game.config.big_blind * 4
    assert action.amount < game.players[1].stack


def test_bots_do_not_call_or_shove_weak_offsuit_hands_deep_stacked() -> None:
    game = PokerGame(["You", "Loose Passive"], seed=12)
    bot = LoosePassiveBot(equity_simulator=EquitySimulator(simulations=80, seed=8), seed=8)
    game.players[1].hole_cards = cards("Jc 2d")
    game.current_player_index = 1
    game.players[0].current_bet = 180
    game.current_bet = 180
    game.pot = 240

    action = bot.choose_action(game, player_id="p1")

    assert action.action == Action.FOLD


def test_very_short_stacked_bot_can_push_reasonable_preflop_hand() -> None:
    game = PokerGame(["You", "Rec"], seed=33)
    bot = RecreationalBot(equity_simulator=EquitySimulator(simulations=80, seed=9), seed=9)
    game.players[1].hole_cards = cards("Ah Td")
    game.players[1].stack = 120
    game.players[1].current_bet = 0
    game.current_player_index = 1
    game.current_bet = 20
    game.pot = 30

    action = bot.choose_action(game, player_id="p1")

    assert action.action == Action.ALL_IN
