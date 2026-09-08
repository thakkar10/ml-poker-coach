# Player Style Analysis

Player style analysis is the first ML-facing coaching feature in ML Poker Coach.

## Product Idea

During a hand, the app shows simple live stats. After the hand, the style analyzer looks across the user's decisions and answers a bigger question:

```text
How do you tend to play, and what should you improve?
```

## What Gets Logged

Each user decision captures:

- Street: preflop, flop, turn, or river.
- User action: fold, check, call, or raise.
- Reference strategy action at that moment.
- Equity estimate.
- Pot odds.
- Coach confidence.
- Pot size.
- Current bet.
- Number of active players.

## Current Analyzer

The v0 analyzer is a transparent statistical classifier. It computes:

- Fold rate.
- Call/check rate.
- Raise rate.
- Guide match rate.
- Average equity edge.

Then it classifies the user style:

- Loose Passive
- Loose Aggressive
- Tight Aggressive
- Tight Passive
- Tight
- Passive Caller
- Aggressive
- Balanced

## Coaching Output

The review returns:

- Playing style.
- Plain-English summary.
- What went well.
- What to improve.
- Clear next-step coaching advice.
- Decision log for future hand review.

## Why This Is ML-Ready

The current classifier is rule-based, but it is intentionally built around ML-style features. The next step is to train a supervised model on simulated sessions using the same decision logs.

Future model:

```text
decision sequence features -> style class + improvement recommendations
```

This turns the project from a poker game into a personalized ML coaching system.
