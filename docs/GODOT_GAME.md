# The Practice Room: first playable Godot slice

## Product direction

A quiet 16-bit card room with physical-feeling cards and chips and coaching after
the hand. The game opens at the table. No live strategy suggestions interrupt a
decision. The fixed scene uses pixel lettering, six original portraits, an
angular felt table, gold highlights and burgundy card backs.

The whole scene scales with letterboxing. The notebook may scroll inside its
modal; gameplay does not scroll. Small portrait screens remain a limitation.

## Responsibilities

| Layer | Responsibility |
| --- | --- |
| `game/scripts/table.gd` | Table, controls, sequential animation and review |
| `game/scripts/poker_card.gd` | Persistent card sprites and flips |
| `game/scripts/poker_api.gd` | HTTP transport and error handling |
| Python game engine | Deck, rules, legal bounds, side pots and settlement |
| Python table runner | Bot decisions and public before/after snapshots |
| Python coach | Monte Carlo equity, reference rules and feedback |
| `tools/serve_game.py` | Local web hosting and same-origin API proxy |

The engine advances multiple bot actions before returning an HTTP response.
Godot replays the authoritative snapshots one at a time. Controls stay locked
until presentation catches up. No poker rules or random dealing live in GDScript.

## Street barrier

1. Compare the next state's board with the five persistent sprites.
2. Check that previously revealed identities have not changed.
3. Flip only new cards in order, awaiting each animation.
4. Assign the public state, update labels, then start the next actor's delay.
5. At completion reveal non-folded opponents, show winners, animate the award,
   then fetch the review.

The server is ahead during replay. This barrier governs when the next bot action
is presented; it is not a server acknowledgment protocol. Real-time multiplayer
would need a different architecture.

An uncontested hand may finish before five board cards are dealt. Godot does not
invent a board for these hands. A contested showdown displays five cards.

## Feedback and integrity

Each hand owns its decision history. The previous global history mixed independent
players and has been removed. Invalid actions are logged only after the engine
accepts them. Reviews explain approximate equity and call cost and avoid assigning
a playing style from a few decisions. Equity uses possible unknown hands, not
actual private opponent cards. The reference strategy is a heuristic, not an
expert label or a trained model, and its advice can be wrong.

Requests time out and expose a reconnect control. Action POSTs are never retried
automatically: they can succeed even when the reply is lost. Reconnect fetches
the authoritative state. Backend restarts still lose games; durable storage and
recovery across restarts are future work.

## Progress

| Milestone | Status |
| --- | --- |
| Rules, evaluator, bot baseline, API | Existing implementation with tests |
| Godot playable hand, retro table, animations, review | Implemented |
| Local web and macOS exports | Build presets included |
| Multi-hand sessions, rotating dealer, persistent stacks | Next game milestone |
| Saved profiles and decision replay | Planned |
| Training dataset, learned policy, held-out evaluation | Planned |
| Public demo, hosted API, signed desktop release | Planned |

## ML milestone

Persist features at decision time: visible cards, position, stack depth, call
price, betting history and simulated equity. Split training and evaluation by
session, not by rows from the same hand. Establish a simple baseline first and
report what the labels actually mean.

Imitating heuristic actions measures imitation, not optimal poker skill. Evaluate
policy agreement separately from gameplay results, using multiple seeds and
uncertainty estimates. Player-style modeling needs repeated observations.

## Distribution

Godot 4.5.2 Compatibility renderer, single-threaded web export. Web requests use
the same-origin `/api` endpoint. Hosting needs HTTPS and a reverse proxy to a
deployed backend; `serve_game.py` is only a local development server.

References: [web export](https://docs.godotengine.org/en/4.5/tutorials/export/exporting_for_web.html)
and [macOS export](https://docs.godotengine.org/en/4.5/tutorials/export/exporting_for_macos.html).
