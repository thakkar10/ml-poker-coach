# Product Requirements Document: ML Poker Coach

## Overview

ML Poker Coach is an interactive Texas Hold'em web app where a user plays poker against AI opponents while an AI coach recommends actions in real time. The coach does not know opponent hole cards. It uses public game information, poker math, opponent behavior signals, and eventually learned models to recommend fold, check, call, or raise decisions.

The project is intended to demonstrate product thinking, full-stack engineering, machine learning system design, simulation, decision modeling under uncertainty, and evaluation.

## Target User

The first target user is someone who understands basic poker rules and wants to improve decision-making by seeing probability, pot odds, and AI recommendations while playing.

## Product Goals

- Make Texas Hold'em playable against AI opponents in a browser.
- Give real-time coaching recommendations during each user decision.
- Explain recommendations using understandable poker concepts.
- Compare baseline strategy, probability-based strategy, and ML-based strategy.
- Provide a polished portfolio project with clear architecture, metrics, and deployment.

## Non-Goals For MVP

- Real-money gambling.
- Multiplayer networking.
- Perfect game-theory-optimal poker.
- Full no-limit tournament rules.
- User accounts or persistent cloud profiles.
- Solving poker with large-scale reinforcement learning.

## Core User Experience

1. User opens the app and starts a poker session.
2. The table deals hole cards to the user and bot opponents.
3. The user sees their cards, public board cards, chip stacks, pot, and legal actions.
4. When it is the user's turn, the AI coach recommends an action.
5. The coach explains the recommendation using equity, pot odds, hand strength, position, and opponent behavior.
6. Bot opponents act according to their configured strategies.
7. At showdown, hidden cards are revealed and the winner is determined.
8. The hand review summarizes key decisions and whether the user's choices aligned with the coach.

## MVP Features

### Poker Table

- Casino-style table layout.
- User seat and 2-4 bot seats.
- Hole cards, community cards, pot, chip stacks, and dealer marker.
- Action controls: fold, check/call, raise.
- Raise amount selector.
- Hand result overlay.

### Game Engine

- Deck generation and shuffling.
- Card dealing.
- Preflop, flop, turn, and river.
- Betting state.
- Legal action validation.
- Pot tracking.
- Fold and showdown resolution.
- Hand evaluation.

### Bot Opponents

- Random bot.
- Tight bot.
- Aggressive bot.
- Equity-aware bot.

### AI Coach v0

- Uses only legal live information.
- Computes hand equity through Monte Carlo simulation.
- Computes pot odds.
- Recommends fold, call/check, or raise.
- Provides explanation text and confidence score.

### Analysis

- Shows current equity.
- Shows pot odds.
- Shows opponent tendencies.
- Shows decision recommendation.
- Shows post-hand review.

## Machine Learning Goals

The first implementation will use a deterministic baseline coach. The ML layer will be added after the game engine is stable.

Planned ML capabilities:

- Simulate many poker decision states.
- Extract features from each decision point.
- Label decisions using heuristic expected value or self-play outcomes.
- Train a supervised policy model to recommend actions.
- Evaluate model decisions against baseline agents.
- Track win rate, expected value per hand, and action quality.

## Success Metrics

### Product Metrics

- A user can complete a full poker hand against bots.
- The coach gives a recommendation at every user decision.
- The recommendation is explainable in plain language.
- The UI feels like a poker game rather than a generic dashboard.

### Technical Metrics

- Game engine has deterministic tests for hand evaluation and betting transitions.
- API can return current game state and apply legal actions.
- Coach recommendation latency is acceptable for interactive play.
- ML model can be trained and evaluated from simulated data.

### ML Metrics

- Win rate against random, tight, and aggressive baselines.
- Average profit/loss per hand.
- Action agreement with heuristic labels.
- Decision quality by street: preflop, flop, turn, river.

## Privacy And Fairness Rules

- The coach cannot see opponent hole cards during live play.
- The coach cannot see future cards or deck order.
- Hidden cards may only be used after a hand ends for review and evaluation.
- The product is educational and simulation-only.

## Resume Positioning

**Machine Learning Poker Coach** — Built an interactive Texas Hold'em web app where users play against AI opponents while an ML strategy engine estimates hand equity, models opponent behavior, and recommends fold/call/raise decisions in real time under hidden information.
