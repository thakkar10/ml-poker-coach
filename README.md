# ML Poker Coach

An interactive Texas Hold'em poker coaching system where users play against AI opponents while a strategy engine estimates hand equity, models opponent behavior, and recommends fold/call/raise decisions in real time.

## Product Vision

ML Poker Coach is designed as a portfolio-grade machine learning product, not just a notebook. The app combines a playable poker table, a rules engine, bot opponents, an AI coaching layer, and an ML pipeline for learning decision policies from simulated game states.

## Planned Milestones

1. Product requirements and system design
2. Deterministic Texas Hold'em game engine
3. AI coach v0 with equity and pot-odds recommendations
4. Bot opponents with different playing styles
5. Casino-style interactive web app
6. ML training and evaluation pipeline
7. Deployment and portfolio polish

## Branch Strategy

- `main`: stable project history
- `develop`: integration branch
- `feature/prd-and-system-design`: product requirements and technical architecture
- `feature/poker-engine`: core game rules and state machine
- `feature/ai-coach-v0`: equity simulation and baseline recommendations
- `feature/web-ui`: interactive poker table and coach interface
- `feature/ml-training-pipeline`: simulation data, training, and evaluation
