# System Design: ML Poker Coach

## High-Level Architecture

```text
Interactive Web App
        |
        v
Backend API
        |
        v
Poker Game Engine <---- Bot Agents
        |
        v
AI Coach Service
        |
        +---- Hand Evaluator
        +---- Equity Simulator
        +---- Pot Odds Calculator
        +---- Opponent Model
        +---- ML Policy Model
```

## Main Components

### 1. Frontend

The frontend is the user-facing poker game.

Responsibilities:

- Render poker table, cards, chips, seats, and community board.
- Show legal action buttons.
- Send user actions to the backend.
- Display AI coach recommendations.
- Display post-hand review.
- Display model and strategy metrics.

Expected stack:

- React
- TypeScript
- Vite
- CSS or Tailwind

### 2. Backend API

The backend owns game state and model inference.

Responsibilities:

- Start a new game.
- Return current game state.
- Validate and apply user actions.
- Ask bot agents for actions.
- Advance streets and hands.
- Return coach recommendations.
- Return hand review and metrics.

Expected stack:

- Python
- FastAPI
- Pydantic

Candidate endpoints:

```text
POST /api/game/new
GET  /api/game/{game_id}
POST /api/game/{game_id}/action
GET  /api/game/{game_id}/coach
GET  /api/game/{game_id}/review
GET  /api/metrics
```

### 3. Poker Game Engine

The game engine is the deterministic rules layer.

Responsibilities:

- Model cards, deck, players, stacks, bets, pot, and board.
- Deal cards.
- Track betting rounds.
- Enforce legal actions.
- Move action between players.
- Detect folded hands and showdowns.
- Evaluate winners.

Important design rule:

The game engine should not contain ML logic. It should expose clean game state to agents and services.

### 4. Hand Evaluator

The hand evaluator scores poker hands.

Responsibilities:

- Evaluate best 5-card hand from hole cards and community cards.
- Compare players at showdown.
- Return hand category and tie-breakers.

Hand categories:

```text
High Card
Pair
Two Pair
Three of a Kind
Straight
Flush
Full House
Four of a Kind
Straight Flush
Royal Flush
```

### 5. Equity Simulator

The equity simulator estimates win probability from incomplete information.

Inputs:

- User hole cards.
- Community cards.
- Number of active opponents.
- Known folded cards, if any.
- Optional opponent hand range assumptions.

Process:

1. Remove known cards from deck.
2. Sample unknown opponent cards and future board cards.
3. Evaluate showdown result.
4. Repeat many times.
5. Estimate win/tie/loss probability.

The simulator must not use hidden live cards.

### 6. Bot Agents

Bots make decisions for opponents.

Baseline agents:

- Random agent.
- Tight agent.
- Aggressive agent.
- Equity agent.

Agent input:

- Public game state.
- Bot's own hole cards.
- Legal actions.
- Pot and call amount.
- Current street.

Agent output:

```json
{
  "action": "call",
  "amount": 20,
  "reason": "Equity is high enough to continue."
}
```

### 7. AI Coach Service

The coach recommends actions for the user.

Inputs:

- Public game state.
- User hole cards.
- Legal actions.
- Opponent behavior summary.

Outputs:

- Recommended action.
- Suggested raise amount, when relevant.
- Equity estimate.
- Pot odds.
- Confidence score.
- Explanation bullets.

Coach v0 logic:

```text
if equity < pot_odds:
    fold unless checking is free
elif equity is moderately above pot_odds:
    call/check
else:
    raise for value
```

Coach v1 logic:

```text
feature vector -> ML policy model -> action probabilities / EV estimates
```

### 8. Opponent Model

The opponent model summarizes visible behavior.

Tracked features:

- VPIP-like rate: how often opponent voluntarily enters pot.
- Raise frequency.
- Fold frequency.
- Aggression factor.
- Showdown frequency.
- Recent action pattern.

These features help the coach adapt recommendations.

### 9. ML Pipeline

The ML pipeline trains the policy model.

```text
Simulated Games
      |
      v
Decision Logs
      |
      v
Feature Extraction
      |
      v
Model Training
      |
      v
Evaluation
      |
      v
Saved Policy Model
      |
      v
Inference in Coach Service
```

Potential models:

- Logistic regression or random forest for action classification.
- Gradient boosting for action quality.
- Reinforcement learning policy for self-play.

Initial feature set:

- Street.
- Position.
- Number of active players.
- Stack-to-pot ratio.
- Amount to call.
- Pot odds.
- Hand strength.
- Monte Carlo equity.
- Board texture.
- Opponent aggression.
- Prior betting action count.

## Information Boundaries

Live coach can see:

- User hole cards.
- Community cards.
- Pot.
- Bets.
- Stack sizes.
- Position.
- Public action history.
- Opponent behavior statistics.

Live coach cannot see:

- Opponent hole cards.
- Future board cards.
- Deck order.

Post-hand analysis can see:

- Revealed showdown cards.
- Final outcome.
- Whether the recommendation was profitable in hindsight.

## Suggested Repository Structure

```text
ml-poker-coach/
  docs/
    PRD.md
    SYSTEM_DESIGN.md
    ML_APPROACH.md
    ROADMAP.md

  backend/
    app/
      api/
      core/
      agents/
      coach/
      ml/
      services/
    tests/

  frontend/
    src/
      components/
      pages/
      styles/

  data/
  models/
  notebooks/
```
