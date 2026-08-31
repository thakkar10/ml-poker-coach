# AI Coach v0

AI Coach v0 is the first live recommendation layer for ML Poker Coach. It is intentionally a transparent hybrid system, not the final learned policy.

## What It Does

- Estimates the user's hand equity with Monte Carlo simulation.
- Computes pot odds for the current call price.
- Recommends fold, check, call, or raise from the legal action set.
- Suggests a raise amount when raising is preferred.
- Explains the recommendation in plain poker language.

## Information Boundary

During live play, the coach can use:

- User hole cards.
- Community cards.
- Pot size.
- Current bet and amount to call.
- Stack sizes.
- Number of active opponents.
- Legal actions.

During live play, the coach cannot use:

- Opponent hole cards.
- Future board cards.
- Deck order.

The equity simulator samples unknown opponent cards and future board cards from the remaining possible deck. This keeps the coach realistic under hidden information.

## Decision Logic

The first version uses this baseline policy:

```text
if checking is free and equity is not very strong:
    check
elif equity is below pot odds:
    fold
elif equity is clearly above pot odds:
    raise
else:
    call
```

## Why This Comes Before ML

The baseline coach gives us:

- A playable product quickly.
- A source of heuristic labels for supervised learning.
- A baseline to compare future ML models against.
- Explainable behavior that helps debug the game engine.

The future ML policy will learn from simulated decision states and can use the v0 coach as an initial expert heuristic.
