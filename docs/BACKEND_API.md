# Backend API

The backend API exposes the poker engine, bot opponents, and AI coach to the future web app.

## Current Endpoints

```text
GET /api/health
```

Returns a basic health check.

```text
POST /api/game/new
```

Creates a new poker game.

Request:

```json
{
  "player_names": ["You", "Tight Bot", "Aggressive Bot", "Equity Bot"],
  "seed": 101
}
```

Response includes:

- Public game state.
- Current legal actions.
- Hidden opponent cards omitted during live play.
- AI coach recommendation when it is the user's turn.

```text
GET /api/game/{game_id}
```

Returns the current public state for an existing game.

```text
POST /api/game/{game_id}/action
```

Applies a user action, runs bot turns until the user acts again or the hand completes, then returns the updated game state.

Request:

```json
{
  "action": "call",
  "amount": 0
}
```

```text
GET /api/game/{game_id}/coach
```

Returns the current coach recommendation if one is available.

## MVP State Storage

Game sessions are stored in memory for now. This is enough for local development and the first playable demo.

Later options:

- Keep in-memory sessions for the portfolio demo.
- Add SQLite for local saved hands and analysis.
- Add Postgres only if user accounts or cloud persistence become important.

## Frontend Flow

```text
Start game
    |
    v
Render public game state
    |
    v
Show coach recommendation
    |
    v
User submits action
    |
    v
Backend applies user action
    |
    v
Bots act automatically
    |
    v
Frontend renders updated state
```

## Information Boundary

The API returns the user's hole cards during live play, but hides bot hole cards until showdown or hand completion.

This keeps the AI coach realistic because it recommends actions under the same hidden-information constraints as the user.
