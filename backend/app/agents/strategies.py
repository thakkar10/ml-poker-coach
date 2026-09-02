from __future__ import annotations

from dataclasses import dataclass
import random

from app.agents.base import AgentAction
from app.coach.equity import EquitySimulator
from app.coach.odds import pot_odds
from app.core.cards import Card
from app.core.game import Action, PlayerState, PokerGame, Street
from app.core.hand_evaluator import HandCategory, evaluate_best_hand


@dataclass(frozen=True)
class BotPersonality:
    name: str
    enter_threshold: float
    raise_threshold: float
    postflop_bet_threshold: float
    aggression: float
    bluff_frequency: float
    call_looseness: float
    mistake_rate: float
    slowplay_rate: float
    fear: float


@dataclass(frozen=True)
class DecisionContext:
    player: PlayerState
    legal: set[Action]
    equity: float
    call_price: int
    required_equity: float
    stack_bb: float
    effective_stack_bb: float
    stack_to_pot: float
    pressure: float
    opponents: int
    position_factor: float
    preflop_score: float
    made_strength: float
    draw_bonus: float


TIGHT_PASSIVE = BotPersonality(
    name="Tight-Passive Bot",
    enter_threshold=0.47,
    raise_threshold=0.72,
    postflop_bet_threshold=0.68,
    aggression=0.38,
    bluff_frequency=0.03,
    call_looseness=-0.02,
    mistake_rate=0.04,
    slowplay_rate=0.14,
    fear=0.12,
)
TIGHT_AGGRESSIVE = BotPersonality(
    name="Tight-Aggressive Bot",
    enter_threshold=0.43,
    raise_threshold=0.64,
    postflop_bet_threshold=0.61,
    aggression=0.66,
    bluff_frequency=0.08,
    call_looseness=0.01,
    mistake_rate=0.05,
    slowplay_rate=0.08,
    fear=0.04,
)
LOOSE_PASSIVE = BotPersonality(
    name="Loose-Passive Bot",
    enter_threshold=0.34,
    raise_threshold=0.70,
    postflop_bet_threshold=0.69,
    aggression=0.32,
    bluff_frequency=0.04,
    call_looseness=0.08,
    mistake_rate=0.10,
    slowplay_rate=0.10,
    fear=0.02,
)
LOOSE_AGGRESSIVE = BotPersonality(
    name="Loose-Aggressive Bot",
    enter_threshold=0.31,
    raise_threshold=0.56,
    postflop_bet_threshold=0.54,
    aggression=0.82,
    bluff_frequency=0.15,
    call_looseness=0.04,
    mistake_rate=0.08,
    slowplay_rate=0.05,
    fear=-0.03,
)
RECREATIONAL = BotPersonality(
    name="Recreational Bot",
    enter_threshold=0.36,
    raise_threshold=0.66,
    postflop_bet_threshold=0.63,
    aggression=0.48,
    bluff_frequency=0.09,
    call_looseness=0.06,
    mistake_rate=0.14,
    slowplay_rate=0.12,
    fear=0.03,
)


class HumanStyleBot:
    def __init__(
        self,
        personality: BotPersonality,
        *,
        equity_simulator: EquitySimulator | None = None,
        seed: int | None = None,
    ) -> None:
        self.personality = personality
        self.name = personality.name
        self.equity_simulator = equity_simulator or EquitySimulator(simulations=300, seed=seed)
        self._rng = random.Random(seed)

    def choose_action(self, game: PokerGame, *, player_id: str) -> AgentAction:
        context = _decision_context(self.equity_simulator, game, player_id)
        if game.street == Street.PREFLOP:
            return self._choose_preflop(game, context)
        return self._choose_postflop(game, context)

    def _choose_preflop(self, game: PokerGame, context: DecisionContext) -> AgentAction:
        personality = self.personality
        play_threshold = personality.enter_threshold + context.pressure * 0.22 - context.position_factor * 0.08
        raise_threshold = personality.raise_threshold + context.pressure * 0.12 - context.position_factor * 0.06
        score = context.preflop_score + context.equity * 0.22

        if self._should_shove(game, context):
            return AgentAction(Action.ALL_IN, reason=f"{self.name} shoves because the stack is short or the pot already commits them.")

        if context.call_price > 0:
            if context.preflop_score < personality.enter_threshold and context.pressure > 0.35:
                return _fold_or_check(context, f"{self.name} folds a weak offsuit-style hand to a serious raise.")
            if score < play_threshold and context.pressure > 0.30 + personality.call_looseness:
                return _fold_or_check(context, f"{self.name} folds a weak starting hand against a large raise.")

            if Action.RAISE in context.legal and score >= raise_threshold and not self._slowplays():
                return AgentAction(
                    Action.RAISE,
                    _normal_raise_amount(game, context.player, self.personality),
                    f"{self.name} uses a normal preflop raise size with a strong starting hand.",
                )

            priced_in = context.equity + personality.call_looseness >= context.required_equity
            playable = score >= play_threshold
            scared_by_size = context.pressure > 0.42 + personality.fear and score < 0.78
            if Action.CALL in context.legal and (priced_in or playable) and not scared_by_size:
                return AgentAction(Action.CALL, reason=f"{self.name} calls because the price is reasonable for this hand.")
            if Action.CALL in context.legal and self._makes_loose_call(context):
                return AgentAction(Action.CALL, reason=f"{self.name} makes a loose human call with a tempting hand.")
            return _fold_or_check(context, f"{self.name} folds a weak starting hand against pressure.")

        pressure_action = _pressure_action(context.legal)
        if pressure_action and score >= raise_threshold:
            return AgentAction(
                pressure_action,
                _normal_bet_amount(game, context.player, self.personality)
                if pressure_action == Action.BET
                else _normal_raise_amount(game, context.player, self.personality),
                f"{self.name} opens with a standard preflop size instead of overbetting.",
            )

        if Action.CHECK in context.legal:
            return AgentAction(Action.CHECK, reason=f"{self.name} checks and takes the free option.")
        return _fold_or_check(context, f"{self.name} lets a weak preflop hand go.")

    def _choose_postflop(self, game: PokerGame, context: DecisionContext) -> AgentAction:
        personality = self.personality
        value_score = context.equity * 0.62 + context.made_strength * 0.28 + context.draw_bonus
        pressure_adjusted_score = value_score - context.pressure * (0.32 + personality.fear)
        strong_value = value_score >= personality.postflop_bet_threshold
        can_bluff = (
            Action.BET in context.legal or Action.RAISE in context.legal
        ) and context.opponents <= 2 and context.stack_to_pot <= 5.5 and self._rng.random() < personality.bluff_frequency

        if self._should_shove(game, context):
            return AgentAction(Action.ALL_IN, reason=f"{self.name} goes all-in only because the pot and stack size justify it.")

        if context.call_price > 0:
            if Action.RAISE in context.legal and strong_value and context.pressure < 0.44 and not self._slowplays():
                return AgentAction(
                    Action.RAISE,
                    _normal_raise_amount(game, context.player, personality),
                    f"{self.name} raises for value with a strong postflop hand.",
                )
            if Action.CALL in context.legal and pressure_adjusted_score + personality.call_looseness >= context.required_equity:
                return AgentAction(Action.CALL, reason=f"{self.name} calls because the math and hand strength are close enough.")
            if Action.CALL in context.legal and self._makes_loose_call(context):
                return AgentAction(Action.CALL, reason=f"{self.name} gets attached and calls a little too wide.")
            return _fold_or_check(context, f"{self.name} gives up when the bet is too expensive for the hand.")

        pressure_action = _pressure_action(context.legal)
        if pressure_action and (strong_value or can_bluff):
            reason = "bets for value with a strong made hand" if strong_value else "takes a believable bluffing stab"
            amount = _normal_bet_amount(game, context.player, personality) if pressure_action == Action.BET else _normal_raise_amount(game, context.player, personality)
            return AgentAction(pressure_action, amount, f"{self.name} {reason} using a normal bet size.")
        if Action.CHECK in context.legal:
            return AgentAction(Action.CHECK, reason=f"{self.name} checks a marginal spot instead of forcing action.")
        return _fold_or_check(context, f"{self.name} cannot continue profitably.")

    def _should_shove(self, game: PokerGame, context: DecisionContext) -> bool:
        if Action.ALL_IN not in context.legal or context.player.stack <= 0:
            return False

        premium_preflop = game.street == Street.PREFLOP and context.preflop_score >= 0.86
        short_stack_push = game.street == Street.PREFLOP and context.effective_stack_bb <= 12 and context.preflop_score >= 0.58
        shallow_premium = premium_preflop and context.effective_stack_bb <= 28
        committed_call = context.call_price > 0 and context.call_price >= context.player.stack * 0.68 and context.equity >= context.required_equity + 0.05
        low_spr_value = game.street != Street.PREFLOP and context.stack_to_pot <= 1.15 and context.equity >= 0.62
        draw_pressure = (
            game.street in {Street.FLOP, Street.TURN}
            and context.stack_to_pot <= 1.35
            and context.draw_bonus >= 0.10
            and self._rng.random() < self.personality.bluff_frequency * 0.55
        )

        return short_stack_push or shallow_premium or committed_call or low_spr_value or draw_pressure

    def _slowplays(self) -> bool:
        return self._rng.random() < self.personality.slowplay_rate

    def _makes_loose_call(self, context: DecisionContext) -> bool:
        return (
            context.pressure < 0.36
            and context.preflop_score + context.equity > 0.62
            and self._rng.random() < self.personality.mistake_rate
        )


class RandomBot(HumanStyleBot):
    def __init__(self, *, seed: int | None = None) -> None:
        super().__init__(RECREATIONAL, seed=seed)


class LoosePassiveBot(HumanStyleBot):
    def __init__(self, *, equity_simulator: EquitySimulator | None = None, seed: int | None = None) -> None:
        super().__init__(LOOSE_PASSIVE, equity_simulator=equity_simulator, seed=seed)


class RecreationalBot(HumanStyleBot):
    def __init__(self, *, equity_simulator: EquitySimulator | None = None, seed: int | None = None) -> None:
        super().__init__(RECREATIONAL, equity_simulator=equity_simulator, seed=seed)


class TightBot(HumanStyleBot):
    def __init__(self, *, equity_simulator: EquitySimulator | None = None, seed: int | None = None) -> None:
        super().__init__(TIGHT_PASSIVE, equity_simulator=equity_simulator, seed=seed)


class AggressiveBot(HumanStyleBot):
    def __init__(
        self,
        *,
        equity_simulator: EquitySimulator | None = None,
        seed: int | None = None,
    ) -> None:
        super().__init__(LOOSE_AGGRESSIVE, equity_simulator=equity_simulator, seed=seed)


class EquityBot(HumanStyleBot):
    def __init__(self, *, equity_simulator: EquitySimulator | None = None, seed: int | None = None) -> None:
        super().__init__(TIGHT_AGGRESSIVE, equity_simulator=equity_simulator, seed=seed)


def _decision_context(
    simulator: EquitySimulator,
    game: PokerGame,
    player_id: str,
) -> DecisionContext:
    player = _player(game, player_id)
    legal = game.legal_actions(player_id)
    opponents = len([candidate for candidate in game.active_players if candidate.id != player_id])
    equity = _estimate_equity(simulator, game, player_id)
    call_price = _amount_to_call(game, player_id)
    required_equity = pot_odds(call_price, game.pot)
    effective_stack = _effective_stack(game, player)
    big_blind = max(1, game.config.big_blind)
    pot_after_call = max(1, game.pot + call_price)

    return DecisionContext(
        player=player,
        legal=legal,
        equity=equity,
        call_price=call_price,
        required_equity=required_equity,
        stack_bb=player.stack / big_blind,
        effective_stack_bb=effective_stack / big_blind,
        stack_to_pot=effective_stack / pot_after_call,
        pressure=call_price / pot_after_call,
        opponents=opponents,
        position_factor=_position_factor(game, player_id),
        preflop_score=_starting_hand_score(player.hole_cards),
        made_strength=_made_hand_strength(game, player),
        draw_bonus=_draw_bonus(game, player),
    )


def _estimate_equity(
    simulator: EquitySimulator,
    game: PokerGame,
    player_id: str,
) -> float:
    player = _player(game, player_id)
    opponents = len([candidate for candidate in game.active_players if candidate.id != player_id])
    dead_cards = _dead_cards(game, player_id)
    return simulator.estimate(
        player.hole_cards,
        game.board,
        opponents=max(1, opponents),
        dead_cards=dead_cards,
    ).win_probability


def _dead_cards(game: PokerGame, player_id: str) -> list[Card]:
    # Folded players' cards are known to the engine but not to live decision makers.
    return [
        card
        for player in game.players
        if player.id != player_id and player.folded
        for card in player.hole_cards
    ]


def _starting_hand_score(cards: list[Card]) -> float:
    if len(cards) < 2:
        return 0.0

    first, second = cards
    high, low = sorted((first.value, second.value), reverse=True)
    pair = high == low
    suited = first.suit == second.suit
    gap = high - low
    connected = gap <= 1 or (high == 14 and low == 5)
    broadway_count = sum(value >= 10 for value in (high, low))

    if pair:
        return min(1.0, 0.46 + high / 22)

    score = high / 26 + low / 38
    if suited:
        score += 0.08
    if connected:
        score += 0.07
    if gap >= 5:
        score -= 0.08
    if high == 14:
        score += 0.06
    if broadway_count == 2:
        score += 0.10
    if high >= 11 and low <= 5:
        score -= 0.08

    return max(0.05, min(1.0, score))


def _made_hand_strength(game: PokerGame, player: PlayerState) -> float:
    if len(game.board) < 3:
        return 0.0

    rank = evaluate_best_hand(player.hole_cards + game.board)
    category_strength = {
        HandCategory.HIGH_CARD: 0.18,
        HandCategory.PAIR: 0.43,
        HandCategory.TWO_PAIR: 0.64,
        HandCategory.THREE_OF_A_KIND: 0.76,
        HandCategory.STRAIGHT: 0.84,
        HandCategory.FLUSH: 0.88,
        HandCategory.FULL_HOUSE: 0.94,
        HandCategory.FOUR_OF_A_KIND: 0.98,
        HandCategory.STRAIGHT_FLUSH: 1.0,
    }[rank.category]
    return category_strength


def _draw_bonus(game: PokerGame, player: PlayerState) -> float:
    if game.street not in {Street.FLOP, Street.TURN}:
        return 0.0

    cards = player.hole_cards + game.board
    suit_counts: dict[str, int] = {}
    for card in cards:
        suit_counts[card.suit.value] = suit_counts.get(card.suit.value, 0) + 1

    flush_draw = max(suit_counts.values(), default=0) >= 4
    values = {card.value for card in cards}
    if 14 in values:
        values.add(1)
    straight_draw = any(len(values.intersection(range(start, start + 5))) >= 4 for start in range(1, 11))

    bonus = 0.0
    if flush_draw:
        bonus += 0.09
    if straight_draw:
        bonus += 0.07
    return bonus


def _effective_stack(game: PokerGame, player: PlayerState) -> int:
    opponent_stacks = [
        opponent.stack + opponent.current_bet
        for opponent in game.active_players
        if opponent.id != player.id
    ]
    if not opponent_stacks:
        return player.stack
    return min(player.stack + player.current_bet, max(opponent_stacks))


def _position_factor(game: PokerGame, player_id: str) -> float:
    eligible = [player for player in game.players if player.active and not player.folded and not player.all_in]
    if len(eligible) <= 1:
        return 0.0

    acting_order = []
    index = game.button_index
    for _ in range(len(game.players)):
        player = game.players[index]
        if player in eligible:
            acting_order.append(player.id)
        index = (index + 1) % len(game.players)

    try:
        return acting_order.index(player_id) / max(1, len(acting_order) - 1)
    except ValueError:
        return 0.0


def _amount_to_call(game: PokerGame, player_id: str) -> int:
    player = _player(game, player_id)
    return max(0, game.current_bet - player.current_bet)


def _normal_bet_amount(game: PokerGame, player: PlayerState, personality: BotPersonality) -> int:
    legal = game.legal_action_state(player.id)
    if game.street == Street.PREFLOP:
        target = round(game.config.big_blind * (2.4 + personality.aggression * 0.7))
    else:
        fractions = [0.33, 0.5, 0.66, 0.75]
        target = round(game.pot * _choose_sizing(fractions, personality.aggression))
    return _clamp_non_all_in(target, legal.minimum_bet, legal.maximum_raise_to)


def _normal_raise_amount(game: PokerGame, player: PlayerState, personality: BotPersonality) -> int:
    legal = game.legal_action_state(player.id)
    if game.street == Street.PREFLOP:
        if game.current_bet <= game.config.big_blind:
            target = round(game.config.big_blind * (2.4 + personality.aggression * 0.8))
        else:
            target = round(game.current_bet * (2.4 + personality.aggression * 0.7))
    else:
        raise_size = max(game.last_full_raise, round(game.pot * _choose_sizing([0.5, 0.66, 0.75, 1.0], personality.aggression)))
        target = game.current_bet + raise_size
    return _clamp_non_all_in(target, legal.minimum_raise_to, legal.maximum_raise_to)


def _choose_sizing(sizes: list[float], aggression: float) -> float:
    index = min(len(sizes) - 1, max(0, round(aggression * (len(sizes) - 1))))
    return sizes[index]


def _clamp_non_all_in(target: int, minimum: int, maximum: int) -> int:
    target = min(maximum, max(minimum, _round_to_chip(target)))
    if maximum > minimum and target >= maximum:
        return max(minimum, _round_to_chip(minimum + (maximum - minimum) * 0.62))
    return target


def _round_to_chip(amount: float) -> int:
    return max(1, int(round(amount / 10) * 10))


def _pressure_action(legal: set[Action]) -> Action | None:
    if Action.RAISE in legal:
        return Action.RAISE
    if Action.BET in legal:
        return Action.BET
    return None


def _fold_or_check(context: DecisionContext, reason: str) -> AgentAction:
    if Action.FOLD in context.legal:
        return AgentAction(Action.FOLD, reason=reason)
    if Action.CHECK in context.legal:
        return AgentAction(Action.CHECK, reason=reason.replace("folds", "checks"))
    return AgentAction(sorted(context.legal, key=lambda action: action.value)[0], reason=reason)


def _player(game: PokerGame, player_id: str) -> PlayerState:
    for player in game.players:
        if player.id == player_id:
            return player
    raise KeyError(f"Unknown player id: {player_id}")
