# Machine Learning Approach

## Core ML Question

The project asks:

> Given the current poker state and only legal live information, what action should the user take?

The model should recommend one of:

- Fold
- Check
- Call
- Raise

For raise spots, the system can also suggest a raise size.

## Why This Is Machine Learning

The coach combines deterministic poker math with learned strategy.

Deterministic inputs:

- Hand category.
- Pot odds.
- Monte Carlo equity.
- Legal actions.

Learned inputs:

- How similar game states performed in simulation.
- Which actions produced better long-term value.
- How opponent behavior changes optimal decisions.

## Training Data

The first dataset will be generated through simulation.

Each row represents one decision point:

```text
game_id
hand_id
player_id
street
position
hole_card_features
board_features
pot_size
amount_to_call
stack_size
active_players
equity
pot_odds
opponent_aggression
legal_actions
chosen_action
outcome_chips
label_action
```

## Labeling Strategy

### Phase 1: Heuristic Labels

Use a strong rule-based strategy to label decisions:

```text
equity < pot_odds -> fold
equity slightly above pot_odds -> call/check
equity strongly above pot_odds -> raise
```

This creates a supervised learning baseline.

### Phase 2: Outcome Labels

Train from simulated hand outcomes:

```text
state + action -> expected chip value
```

The model predicts the expected value of each action, then chooses the highest value legal action.

### Phase 3: Self-Play

Use repeated simulation to improve an agent policy over time.

This can be framed as reinforcement learning:

- State: poker decision state.
- Action: fold/call/raise.
- Reward: chip gain or loss.
- Policy: model that chooses actions.

## Model Options

### MVP Model

- Logistic regression or random forest classifier.
- Predicts fold/call/raise from engineered features.
- Easy to explain and evaluate.

### Stronger Model

- Gradient boosted trees.
- Predicts expected value or action quality.
- Handles nonlinear strategy interactions.

### Advanced Model

- Reinforcement learning agent trained through self-play.
- Compares learned policy against baseline bots.

## Evaluation

The model should be evaluated in two ways.

### Offline Metrics

- Action accuracy against heuristic labels.
- Cross-entropy or log loss for action probabilities.
- Confusion matrix for fold/call/raise.

### Simulation Metrics

- Win rate against each bot.
- Average chips won/lost per hand.
- Volatility.
- Fold/call/raise distribution.
- Performance by street.

Simulation metrics matter more than simple action accuracy because poker is about long-term expected value.

## Explainability

The UI should explain model recommendations using features the user understands:

- Equity.
- Pot odds.
- Hand strength.
- Opponent aggression.
- Position.
- Stack-to-pot ratio.

Example:

```text
Recommendation: Call

Your estimated equity is 38%, while calling only requires 25% pot odds.
Raising is not preferred because the opponent profile is tight and the board has possible stronger made hands.
```

## Guardrails

- Do not train or infer using opponent hole cards during live decision-making.
- Do not use future cards as model features.
- Keep simulation-only hidden information separate from live inference.
- Clearly distinguish baseline coach recommendations from ML model recommendations.
