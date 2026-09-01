from __future__ import annotations

from dataclasses import dataclass

from app.core.game import Action


@dataclass(frozen=True)
class DecisionLog:
    street: str
    action: Action
    amount: int
    recommended_action: Action
    equity: float
    pot_odds: float
    confidence: float
    pot: int
    current_bet: int
    active_players: int

    @property
    def followed_coach(self) -> bool:
        return self.action == self.recommended_action

    @property
    def equity_edge(self) -> float:
        return self.equity - self.pot_odds


@dataclass(frozen=True)
class StyleReview:
    style: str
    summary: str
    decisions: int
    fold_rate: float
    call_rate: float
    raise_rate: float
    coach_alignment: float
    avg_equity_edge: float
    leaks: list[str]
    strengths: list[str]
    next_steps: list[str]

    def to_dict(self) -> dict[str, object]:
        return {
            "style": self.style,
            "summary": self.summary,
            "decisions": self.decisions,
            "fold_rate": round(self.fold_rate, 4),
            "call_rate": round(self.call_rate, 4),
            "raise_rate": round(self.raise_rate, 4),
            "coach_alignment": round(self.coach_alignment, 4),
            "avg_equity_edge": round(self.avg_equity_edge, 4),
            "leaks": self.leaks,
            "strengths": self.strengths,
            "next_steps": self.next_steps,
        }


class PlayerStyleAnalyzer:
    def analyze(self, decisions: list[DecisionLog]) -> StyleReview:
        if not decisions:
            return StyleReview(
                style="Not enough data",
                summary="Play a few decisions to generate a coaching review.",
                decisions=0,
                fold_rate=0,
                call_rate=0,
                raise_rate=0,
                coach_alignment=0,
                avg_equity_edge=0,
                leaks=[],
                strengths=[],
                next_steps=["Play more hands so the coach can learn your decision patterns."],
            )

        total = len(decisions)
        fold_rate = _rate(decisions, Action.FOLD)
        call_rate = _rate(decisions, Action.CALL) + _rate(decisions, Action.CHECK)
        raise_rate = _rate(decisions, Action.RAISE)
        coach_alignment = sum(decision.followed_coach for decision in decisions) / total
        avg_edge = sum(decision.equity_edge for decision in decisions) / total

        loose = call_rate > 0.58 and fold_rate < 0.28
        tight = fold_rate >= 0.45
        aggressive = raise_rate > 0.24
        passive = raise_rate < 0.12 and call_rate > 0.40

        if loose and passive:
            style = "Loose Passive"
        elif loose and aggressive:
            style = "Loose Aggressive"
        elif tight and aggressive:
            style = "Tight Aggressive"
        elif tight and passive:
            style = "Tight Passive"
        elif tight:
            style = "Tight"
        elif passive:
            style = "Passive Caller"
        elif aggressive:
            style = "Aggressive"
        else:
            style = "Balanced"

        leaks = self._detect_leaks(decisions)
        strengths = self._detect_strengths(decisions, coach_alignment, avg_edge, raise_rate)
        next_steps = self._next_steps(style, leaks)

        return StyleReview(
            style=style,
            summary=self._summary(style, coach_alignment, avg_edge),
            decisions=total,
            fold_rate=fold_rate,
            call_rate=call_rate,
            raise_rate=raise_rate,
            coach_alignment=coach_alignment,
            avg_equity_edge=avg_edge,
            leaks=leaks,
            strengths=strengths,
            next_steps=next_steps,
        )

    def _detect_leaks(self, decisions: list[DecisionLog]) -> list[str]:
        leaks: list[str] = []
        bad_calls = [
            decision
            for decision in decisions
            if decision.action in {Action.CALL, Action.CHECK}
            and decision.pot_odds > 0
            and decision.equity + 0.03 < decision.pot_odds
        ]
        missed_value = [
            decision
            for decision in decisions
            if decision.action in {Action.CALL, Action.CHECK}
            and decision.recommended_action == Action.RAISE
        ]
        overfolds = [
            decision
            for decision in decisions
            if decision.action == Action.FOLD and decision.equity > decision.pot_odds + 0.08
        ]

        if bad_calls:
            leaks.append("You called in spots where your equity was below the price of calling.")
        if missed_value:
            leaks.append("You passed up some raise spots where the coach saw a clear equity edge.")
        if overfolds:
            leaks.append("You folded some hands that had enough equity to continue profitably.")
        if not leaks:
            leaks.append("No major leak detected yet, but the sample is still small.")
        return leaks

    def _detect_strengths(
        self,
        decisions: list[DecisionLog],
        coach_alignment: float,
        avg_edge: float,
        raise_rate: float,
    ) -> list[str]:
        strengths: list[str] = []
        good_folds = [
            decision
            for decision in decisions
            if decision.action == Action.FOLD and decision.equity + 0.03 < decision.pot_odds
        ]

        if coach_alignment >= 0.65:
            strengths.append("You often chose the same action as the strategy coach.")
        if avg_edge >= 0:
            strengths.append("On average, you entered decisions with equity at or above the required pot odds.")
        if raise_rate > 0.18:
            strengths.append("You showed willingness to raise instead of only calling.")
        if good_folds:
            strengths.append("You avoided at least one low-equity call.")
        if not strengths:
            strengths.append("The coach needs more hands to identify reliable strengths.")
        return strengths

    def _next_steps(self, style: str, leaks: list[str]) -> list[str]:
        steps: list[str] = []
        if "Loose Passive" in style or "Passive" in style:
            steps.append("Call less often with weak hands; either fold bad prices or raise strong edges.")
        if "Aggressive" in style:
            steps.append("Keep pressure high, but check whether raises are backed by equity and pot odds.")
        if "Tight" in style:
            steps.append("Look for profitable call or raise spots instead of folding every uncomfortable hand.")
        if any("price of calling" in leak for leak in leaks):
            steps.append("Before calling, compare equity to pot odds. Equity should usually be higher.")
        if any("raise spots" in leak for leak in leaks):
            steps.append("When equity is far above pot odds, consider raising for value instead of calling.")
        if not steps:
            steps.append("Play more hands so the coach can build a more confident style profile.")
        return steps

    def _summary(self, style: str, coach_alignment: float, avg_edge: float) -> str:
        alignment = "high" if coach_alignment >= 0.65 else "moderate" if coach_alignment >= 0.40 else "low"
        edge_text = "positive" if avg_edge >= 0 else "negative"
        return (
            f"Your current profile looks like {style}. Coach alignment is {alignment}, "
            f"and your average equity edge is {edge_text} across reviewed decisions."
        )


def _rate(decisions: list[DecisionLog], action: Action) -> float:
    return sum(decision.action == action for decision in decisions) / len(decisions)
