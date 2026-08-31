# Gameplay Animations

The gameplay animation layer makes bot decisions and betting feel visible at the table.

## Current Animations

- Chip bursts fly from a player seat toward the pot when a player calls or raises.
- Folded players have dimmed, shifted cards.
- The current player's seat pulses.
- Seats flash briefly when a player acts.
- Latest-action badges pop onto player seats.
- Recent table actions rise into view near the table edge.

## Product Purpose

The backend resolves bot turns quickly, which is technically correct but can feel invisible. The UI now treats each returned action as a visual event so the player can understand what just happened.

## Future Improvements

- Sequential bot turn playback instead of showing all resolved actions at once.
- Dealing animations for hole cards and community cards.
- Pot-award animation at showdown.
- Sound effects with a mute toggle.
- Post-hand replay timeline.
