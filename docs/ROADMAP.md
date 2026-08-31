# Roadmap

## Phase 0: Product And Architecture

Branch: `feature/prd-and-system-design`

- Define PRD.
- Define system design.
- Define ML approach.
- Define branch strategy and implementation roadmap.

## Phase 1: Poker Engine

Branch: `feature/poker-engine`

- Card and deck models.
- Player and table state.
- Dealing logic.
- Betting round state machine.
- Legal action validation.
- Pot and stack updates.
- Hand evaluator.
- Unit tests for core rules.

Acceptance criteria:

- A full hand can be simulated from deal to showdown.
- Invalid actions are rejected.
- Winner is correctly determined.

## Phase 2: AI Coach v0

Branch: `feature/ai-coach-v0`

- Monte Carlo equity simulator.
- Pot odds calculator.
- Rule-based recommendation engine.
- Explanation generator.
- Coach output API.

Acceptance criteria:

- Coach recommends an action from the legal action set.
- Coach never uses hidden opponent cards.
- Recommendation includes equity, pot odds, confidence, and explanation.

## Phase 3: Bot Opponents

Branch: `feature/bot-opponents`

- Random bot.
- Tight bot.
- Aggressive bot.
- Equity-aware bot.
- Bot action logging.

Acceptance criteria:

- User can play complete hands against multiple bot styles.
- Each bot has visibly different behavior.

## Phase 4: Web App

Branch: `feature/web-ui`

- Casino-style poker table.
- Player and bot seats.
- Cards and chip stacks.
- Action controls.
- Raise selector.
- Coach recommendation panel.
- Hand result and review view.

Acceptance criteria:

- User can play a hand through the browser.
- Coach panel updates during user turns.
- The app feels like a poker table rather than a generic dashboard.

## Phase 5: ML Training Pipeline

Branch: `feature/ml-training-pipeline`

- Simulation runner.
- Decision log dataset.
- Feature extraction.
- Baseline supervised model.
- Evaluation script.
- Saved model artifact.

Acceptance criteria:

- Training produces a saved model.
- Evaluation compares model against heuristic and bot baselines.
- Metrics are documented.

## Phase 6: Deployment And Portfolio Polish

Branch: `feature/deployment`

- API deployment.
- Web app deployment.
- README with architecture diagram.
- Demo screenshots.
- Resume bullets.
- Final project writeup.

Acceptance criteria:

- Deployed app is accessible.
- README explains product, architecture, ML approach, and how to run locally.
- Resume bullet is polished and truthful.
