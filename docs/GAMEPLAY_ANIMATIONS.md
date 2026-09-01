# Gameplay Animations

The gameplay animation layer makes bot decisions and betting feel visible at the table.

## Current Animations

- Chip bursts fly from a player seat toward the pot when a player calls or raises.
- Folded players have dimmed, shifted cards.
- The current player's seat pulses.
- Seats flash briefly when a player acts.
- Latest-action badges pop onto player seats.
- Recent table actions rise into view near the table edge.
- Bot actions replay one at a time at a slower table pace.
- Newly revealed cards deal into view instead of appearing statically.

## Product Purpose

The backend resolves bot turns quickly, which is technically correct but can feel invisible. The UI now treats each returned action as a visual event so the player can understand what just happened. After a user folds, the remaining bots still play out the hand and the UI replays those decisions before showing the final result.

## Future Improvements

- Dealing animations for hole cards and community cards.
- Pot-award animation at showdown.
- Sound effects with a mute toggle.
- Post-hand replay timeline.
