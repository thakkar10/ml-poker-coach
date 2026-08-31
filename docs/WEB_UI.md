# Web UI

The web UI is the first playable product surface for ML Poker Coach.

## What This Slice Adds

- Casino-style Texas Hold'em table.
- User and AI opponent seats.
- Hidden opponent cards during live play.
- Community board cards.
- Pot and street display.
- Fold, check/call, and raise controls.
- Raise slider.
- AI coach recommendation panel.
- Equity, pot odds, and confidence bars.
- Bot action history panel.
- Animated chip bursts when a player calls or raises.
- Folded-seat treatment with dimmed cards.
- Current-player pulse.
- Action flash and latest-move badges when bots act.

## How It Connects

The frontend calls the FastAPI backend through `/api` routes.

```text
React app
    |
    v
Vite dev proxy
    |
    v
FastAPI backend
    |
    v
Poker engine + bots + coach
```

## User Flow

```text
Open app
    |
    v
New hand starts automatically
    |
    v
Coach recommends an action
    |
    v
User folds, checks/calls, or raises
    |
    v
Bots act automatically
    |
    v
Updated table and coach advice render
```

## Design Direction

The UI is intentionally built as a poker table first, not a generic dashboard. The dashboard information is present, but it supports the gameplay rather than replacing it.

## Current Limitations

- Browser state is not persisted after refresh.
- The backend stores games in memory.
- The first UI does not yet include card-dealing animations.
- Hand review is basic and will become richer after the evaluation layer exists.
