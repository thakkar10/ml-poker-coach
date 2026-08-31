# Bot Opponents

Bot opponents make the poker game playable before the full web UI and ML policy exist. They also become baseline agents for future ML evaluation.

## Bot Types

### Random Bot

Chooses randomly from legal actions. This is useful as the simplest baseline.

### Tight Bot

Plays conservatively. It folds more often without a meaningful equity edge and raises mostly in premium spots.

### Aggressive Bot

Raises more often and sometimes applies pressure even with thinner equity. This makes gameplay less predictable and gives the coach a different opponent profile to reason about later.

### Equity Bot

Uses Monte Carlo equity and pot odds directly. It folds when equity is below the call price, calls with enough equity, and raises with a clear mathematical edge.

## Table Runner

The table runner coordinates bot turns after the user acts.

```text
User action
    |
    v
Apply action to game engine
    |
    v
Bot 1 chooses legal action
    |
    v
Bot 2 chooses legal action
    |
    v
Stop when user acts again or hand completes
```

This service will be used by the backend API. When the frontend sends a user action, the API can apply that action, let bots respond, and return the updated state plus bot action history.

## Design Rule

Bots can see their own hole cards and public game state. They should not depend on the user's hidden cards or other bots' hidden cards when making live decisions.

## Why This Matters For ML

The bot opponents serve three roles:

- Make the product playable.
- Generate simulated decision data.
- Provide baseline strategies to evaluate the future ML policy against.
