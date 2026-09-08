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
- Simple live stats panel with equity, pot odds, and extra safety.
- Bot action history panel.
- Animated chip bursts when a player calls or raises.
- Folded-seat treatment with dimmed cards.
- Current-player pulse.
- Action timer on the current player's seat.
- Action flash and latest-move badges when bots act.
- Pot-award animation and winner glow after showdown.
- Staggered board-card reveal and showdown flips.

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
Simple live stats appear
    |
    v
User folds, checks/calls, or raises
    |
    v
Bots act automatically
    |
    v
Updated table and post-hand coaching render
```

## Design Direction

The UI is intentionally built as a poker table first, not a generic dashboard. The dashboard information is present, but it supports the gameplay rather than replacing it.

## Current Limitations

- Browser state is not persisted after refresh.
- The backend stores games in memory.
- Card-dealing animations are basic and will become richer over time.
- Hand review is basic and will become richer after the evaluation layer exists.
