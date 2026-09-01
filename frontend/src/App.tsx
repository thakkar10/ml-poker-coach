import { useEffect, useMemo, useState } from "react";
import { BookOpen, Brain, CircleDollarSign, History, Loader2, RotateCcw, TrendingUp } from "lucide-react";
import { applyAction, BotAction, Coach, createGame, GameResponse, getGameReview, Player, PlayerReview } from "./api";

const seatPositions = ["seat-user", "seat-left", "seat-top", "seat-right"];
const ACTION_REPLAY_MS = 1250;

type VisualAction = Pick<BotAction, "player_id" | "player_name" | "action" | "amount"> & {
  id: string;
};

export function App() {
  const [gameResponse, setGameResponse] = useState<GameResponse | null>(null);
  const [botHistory, setBotHistory] = useState<BotAction[]>([]);
  const [raiseAmount, setRaiseAmount] = useState(80);
  const [loading, setLoading] = useState(false);
  const [replaying, setReplaying] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [visualActions, setVisualActions] = useState<VisualAction[]>([]);
  const [playerReview, setPlayerReview] = useState<PlayerReview | null>(null);

  const game = gameResponse?.game ?? null;
  const coach = gameResponse?.coach ?? null;
  const user = game?.players[0] ?? null;
  const canAct = game?.current_player_id === "p0" && game.street !== "complete" && !replaying;
  const handLesson = useMemo(() => explainStartingHand(user?.hole_cards ?? []), [user?.hole_cards]);
  const latestActions = useMemo(() => {
    const actions = new Map<string, BotAction>();
    for (const action of botHistory) {
      if (!actions.has(action.player_id)) {
        actions.set(action.player_id, action);
      }
    }
    return actions;
  }, [botHistory]);
  const actingPlayerIds = useMemo(
    () => new Set(visualActions.map((action) => action.player_id)),
    [visualActions],
  );

  useEffect(() => {
    if (!visualActions.length) return;

    const timeout = window.setTimeout(() => setVisualActions([]), ACTION_REPLAY_MS);
    return () => window.clearTimeout(timeout);
  }, [visualActions]);

  useEffect(() => {
    void startNewGame();
  }, []);

  async function startNewGame() {
    setLoading(true);
    setError(null);
    try {
      const nextGame = await createGame();
      setGameResponse(nextGame);
      setBotHistory([]);
      setPlayerReview(null);
      await replayActions(nextGame.bot_actions);
      if (nextGame.game.street === "complete") {
        await loadReview(nextGame.game.id);
      }
      setRaiseAmount(80);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not start game");
    } finally {
      setLoading(false);
    }
  }

  async function chooseAction(action: string) {
    if (!game || !canAct) return;
    setLoading(true);
    setError(null);
    try {
      const nextGame = await applyAction(game.id, action, action === "raise" ? raiseAmount : 0);
      const userAction = {
        player_id: "p0",
        player_name: "You",
        action,
        amount: action === "raise" ? raiseAmount : 0,
        agent_name: "Player",
        reason: "You chose this action.",
      };
      await replayActions([userAction, ...nextGame.bot_actions], { includeInLog: nextGame.bot_actions });
      setGameResponse(nextGame);
      if (nextGame.game.street === "complete") {
        await loadReview(nextGame.game.id);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "Action failed");
    } finally {
      setLoading(false);
    }
  }

  async function loadReview(gameId: string) {
    try {
      const review = await getGameReview(gameId);
      setPlayerReview(review);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load game review");
    }
  }

  async function replayActions(
    actions: BotAction[],
    options: { includeInLog?: BotAction[] } = {},
  ) {
    if (!actions.length) return;

    setReplaying(true);
    const loggable = options.includeInLog ?? actions;
    for (const action of actions) {
      setVisualActions(toVisualActions([action]));
      if (loggable.includes(action)) {
        setBotHistory((previous) => [action, ...previous].slice(0, 10));
      }
      await sleep(ACTION_REPLAY_MS);
    }
    setVisualActions([]);
    setReplaying(false);
  }

  const tableStatus = useMemo(() => {
    if (!game) return "Preparing table";
    if (game.street === "complete") {
      const names = game.winners
        .map((winnerId) => game.players.find((player) => player.id === winnerId)?.name)
        .filter(Boolean)
        .join(", ");
      return `${names || "Winner"} takes the pot`;
    }
    if (replaying) return "Action is playing out";
    if (game.current_player_id === "p0") return "Your decision";
    const current = game.players.find((player) => player.id === game.current_player_id);
    return `${current?.name ?? "Opponent"} is thinking`;
  }, [game, replaying]);

  return (
    <main className="app-shell">
      <section className="game-surface" aria-label="Poker table">
        <header className="top-bar">
          <div>
            <p className="eyebrow">ML Poker Coach</p>
            <h1>Texas Hold'em Strategy Table</h1>
          </div>
          <button className="icon-button" onClick={startNewGame} disabled={loading} aria-label="Start new hand">
            {loading ? <Loader2 className="spin" size={18} /> : <RotateCcw size={18} />}
            New Hand
          </button>
        </header>

        <div className="table-zone">
          {game?.players.map((player, index) => (
            <PlayerSeat
              key={player.id}
              player={player}
              position={seatPositions[index] ?? "seat-side"}
              isCurrent={game.current_player_id === player.id}
              isUser={player.id === "p0"}
              showdownLabel={game.showdown[player.id]}
              lastAction={latestActions.get(player.id)}
              isActing={actingPlayerIds.has(player.id)}
            />
          ))}

          <div className="poker-table">
            <div className="board-row" aria-label="Community cards">
              {Array.from({ length: 5 }).map((_, index) => (
                <CardView key={game?.board[index] ?? `board-${index}`} card={game?.board[index]} />
              ))}
            </div>
            <div className="pot-display">
              <CircleDollarSign size={20} />
              Pot ${game?.pot ?? 0}
            </div>
            <div className="street-pill">{game?.street ?? "loading"}</div>
          </div>
          <ChipBursts actions={visualActions} />
          <RecentActions actions={botHistory.slice(0, 3)} />
        </div>

        <section className="action-dock" aria-label="Player actions">
          <div>
            <p className="status-label">Table Status</p>
            <strong>{tableStatus}</strong>
            {replaying && <p className="replay-text">Letting the table play through each decision...</p>}
            {error && <p className="error-text">{error}</p>}
          </div>
          <div className="actions">
            <button onClick={() => chooseAction("fold")} disabled={!canAct || !game?.legal_actions.includes("fold") || loading}>
              Fold
            </button>
            <button onClick={() => chooseAction(game?.legal_actions.includes("check") ? "check" : "call")} disabled={!canAct || loading}>
              {game?.legal_actions.includes("check") ? "Check" : "Call"}
            </button>
            <label className="raise-control">
              <span>Raise to ${raiseAmount}</span>
              <input
                type="range"
                min="40"
                max={Math.max(100, user?.stack ?? 1000)}
                step="10"
                value={raiseAmount}
                onChange={(event) => setRaiseAmount(Number(event.target.value))}
                disabled={!canAct || !game?.legal_actions.includes("raise") || loading}
              />
            </label>
            <button onClick={() => chooseAction("raise")} disabled={!canAct || !game?.legal_actions.includes("raise") || loading}>
              Raise
            </button>
          </div>
        </section>
      </section>

      <aside className="side-panel">
        <LiveStatsPanel coach={coach} />
        {playerReview && <PlayerReviewPanel review={playerReview} />}
        <HandLessonPanel lesson={handLesson} />
        <HistoryPanel botHistory={botHistory} />
      </aside>
    </main>
  );
}

function PlayerSeat({
  player,
  position,
  isCurrent,
  isUser,
  showdownLabel,
  lastAction,
  isActing,
}: {
  player: Player;
  position: string;
  isCurrent: boolean;
  isUser: boolean;
  showdownLabel?: string;
  lastAction?: BotAction;
  isActing: boolean;
}) {
  return (
    <article
      className={`player-seat ${position} ${isCurrent ? "is-current" : ""} ${
        player.folded ? "is-folded" : ""
      } ${isActing ? "is-acting" : ""}`}
    >
      <div className="seat-meta">
        <strong>{player.name}</strong>
        <span>${player.stack}</span>
      </div>
      <div className="hole-cards">
        {[0, 1].map((index) => (
          <CardView
            key={player.hole_cards[index] ?? `${player.id}-${index}`}
            card={player.hole_cards[index]}
            hidden={!player.hole_cards[index]}
          />
        ))}
      </div>
      <div className="seat-footer">
        <span>{player.folded ? "Folded" : isUser ? "Hero" : "AI Opponent"}</span>
        {player.current_bet > 0 && <b>Bet ${player.current_bet}</b>}
      </div>
      {lastAction && (
        <p className={`action-badge ${lastAction.action === "fold" ? "fold-action" : ""}`}>
          Last move: {lastAction.action}
          {lastAction.amount > 0 ? ` $${lastAction.amount}` : ""}
        </p>
      )}
      {showdownLabel && <p className="showdown-label">{showdownLabel}</p>}
    </article>
  );
}

function CardView({ card, hidden = false }: { card?: string; hidden?: boolean }) {
  if (!card || hidden) {
    return <div className="card card-back" aria-label="Hidden card" />;
  }

  const suit = card.slice(1);
  const rank = card.slice(0, 1);
  const suitSymbol = suit === "s" ? "♠" : suit === "h" ? "♥" : suit === "d" ? "♦" : "♣";
  const red = suit === "h" || suit === "d";

  return (
    <div className={`card ${red ? "red" : "black"}`} aria-label={`${rank}${suitSymbol}`}>
      <span>{rank}</span>
      <strong>{suitSymbol}</strong>
    </div>
  );
}

function LiveStatsPanel({ coach }: { coach: Coach | null }) {
  return (
    <section className="panel coach-panel">
      <div className="panel-title">
        <Brain size={20} />
        <h2>Live Stats</h2>
      </div>
      {coach ? (
        <>
          <div className="recommendation">
            <span>Hand situation</span>
            <strong>{coach.equity > coach.pot_odds ? "Playable" : "Risky"}</strong>
          </div>
          <MetricBar label="Equity" value={coach.equity} />
          <MetricBar label="Pot Odds" value={coach.pot_odds} />
          <MetricBar label="Extra Safety" value={Math.max(0, coach.equity - coach.pot_odds)} />
          <div className="stat-explainer">
            <p>
              <strong>Equity</strong> means your estimated chance to win this hand.
            </p>
            <p>
              <strong>Pot odds</strong> means the minimum chance you need for a call to make sense.
            </p>
            <p>The app saves your choice and reviews your play after the hand.</p>
          </div>
        </>
      ) : (
        <p className="empty-state">Live stats appear when it is your turn to act.</p>
      )}
    </section>
  );
}

function PlayerReviewPanel({ review }: { review: PlayerReview }) {
  return (
    <section className="panel review-panel">
      <div className="panel-title">
        <TrendingUp size={20} />
        <h2>After-Hand Review</h2>
      </div>
      <div className="review-summary">
        <span>Your current style</span>
        <strong>{review.style}</strong>
        <p>{review.summary}</p>
      </div>
      <div className="review-metrics">
        <MiniMetric label="Fold" value={review.fold_rate} />
        <MiniMetric label="Call/Check" value={review.call_rate} />
        <MiniMetric label="Raise" value={review.raise_rate} />
        <MiniMetric label="Matched Guide" value={review.coach_alignment} />
      </div>
      <ReviewList title="What to improve" items={review.leaks} />
      <ReviewList title="What went well" items={review.strengths} />
      <ReviewList title="Try this next" items={review.next_steps} />
    </section>
  );
}

function MiniMetric({ label, value }: { label: string; value: number }) {
  return (
    <article>
      <span>{label}</span>
      <strong>{Math.round(value * 100)}%</strong>
    </article>
  );
}

function ReviewList({ title, items }: { title: string; items: string[] }) {
  return (
    <div className="review-list">
      <h3>{title}</h3>
      <ul>
        {items.map((item) => (
          <li key={item}>{item}</li>
        ))}
      </ul>
    </div>
  );
}

function HandLessonPanel({ lesson }: { lesson: HandLesson }) {
  return (
    <section className="panel lesson-panel">
      <div className="panel-title">
        <BookOpen size={20} />
        <h2>Your Hand</h2>
      </div>
      <div className={`lesson-summary ${lesson.tone}`}>
        <span>{lesson.strength}</span>
        <strong>{lesson.title}</strong>
      </div>
      <ul className="reason-list">
        {lesson.reasons.map((reason) => (
          <li key={reason}>{reason}</li>
        ))}
      </ul>
      <div className="lesson-stats">
        {lesson.stats.map((stat) => (
          <article key={stat.label}>
            <span>{stat.label}</span>
            <strong>{stat.value}</strong>
            <p>{stat.description}</p>
          </article>
        ))}
      </div>
    </section>
  );
}

function RecentActions({ actions }: { actions: BotAction[] }) {
  if (!actions.length) return null;

  return (
    <div className="recent-actions" aria-label="Recent bot actions">
      {actions.map((action, index) => (
        <span key={`${action.player_id}-${index}`}>
          {action.player_name} {action.action}
          {action.amount > 0 ? ` $${action.amount}` : ""}
        </span>
      ))}
    </div>
  );
}

function ChipBursts({ actions }: { actions: VisualAction[] }) {
  const moneyActions = actions.filter((action) => action.action === "call" || action.action === "raise");
  if (!moneyActions.length) return null;

  return (
    <div className="chip-layer" aria-hidden="true">
      {moneyActions.slice(0, 5).map((action, index) => (
        <div
          className={`chip-burst from-${action.player_id}`}
          key={action.id}
          style={{ animationDelay: `${index * 120}ms` }}
        >
          <span />
          <span />
          <span />
        </div>
      ))}
    </div>
  );
}

function MetricBar({ label, value }: { label: string; value: number }) {
  return (
    <div className="metric">
      <div>
        <span>{label}</span>
        <strong>{Math.round(value * 100)}%</strong>
      </div>
      <div className="track">
        <span style={{ width: `${Math.max(3, Math.round(value * 100))}%` }} />
      </div>
    </div>
  );
}

function toVisualActions(actions: BotAction[]): VisualAction[] {
  const timestamp = Date.now();
  return actions.map((action, index) => ({
    id: `${action.player_id}-${timestamp}-${index}-${action.action}`,
    player_id: action.player_id,
    player_name: action.player_name,
    action: action.action,
    amount: action.amount,
  }));
}

function sleep(ms: number) {
  return new Promise((resolve) => window.setTimeout(resolve, ms));
}

type HandLesson = {
  title: string;
  strength: string;
  tone: "premium" | "playable" | "caution";
  reasons: string[];
  stats: Array<{ label: string; value: string; description: string }>;
};

const rankValues: Record<string, number> = {
  "2": 2,
  "3": 3,
  "4": 4,
  "5": 5,
  "6": 6,
  "7": 7,
  "8": 8,
  "9": 9,
  T: 10,
  J: 11,
  Q: 12,
  K: 13,
  A: 14,
};

const rankNames: Record<string, string> = {
  "2": "Two",
  "3": "Three",
  "4": "Four",
  "5": "Five",
  "6": "Six",
  "7": "Seven",
  "8": "Eight",
  "9": "Nine",
  T: "Ten",
  J: "Jack",
  Q: "Queen",
  K: "King",
  A: "Ace",
};

function explainStartingHand(cards: string[]): HandLesson {
  if (cards.length < 2) {
    return {
      title: "Waiting for cards",
      strength: "No hand yet",
      tone: "caution",
      reasons: ["Start a new hand to see a beginner-friendly explanation of your cards."],
      stats: [],
    };
  }

  const [first, second] = cards;
  const firstRank = first[0];
  const secondRank = second[0];
  const firstSuit = first[1];
  const secondSuit = second[1];
  const values = [rankValues[firstRank], rankValues[secondRank]].sort((a, b) => b - a);
  const high = values[0];
  const low = values[1];
  const pair = firstRank === secondRank;
  const suited = firstSuit === secondSuit;
  const gap = Math.abs(high - low);
  const connected = gap === 1 || (high === 14 && low === 5);
  const broadwayCount = values.filter((value) => value >= 10).length;
  const names = `${rankNames[firstRank]}-${rankNames[secondRank]}`;

  if (pair && high === 14) {
    return {
      title: "Pocket aces are the best starting hand",
      strength: "Premium",
      tone: "premium",
      reasons: [
        "You already have the highest possible pair before the flop.",
        "Most opponents need to improve to two pair, trips, a straight, or a flush to beat you.",
        "This hand usually wants to raise because strong hands make money by building the pot against worse hands.",
      ],
      stats: [
        {
          label: "Heads-up equity",
          value: "about 85%",
          description: "Against one random hand, pocket aces win roughly 85 out of 100 times.",
        },
        {
          label: "Set on flop",
          value: "about 12%",
          description: "Any pocket pair flops three of a kind about once every 8 flops.",
        },
      ],
    };
  }

  if (pair) {
    const premiumPair = high >= 11;
    return {
      title: `${rankNames[firstRank]} pair starts ahead`,
      strength: premiumPair ? "Strong" : "Playable",
      tone: premiumPair ? "premium" : "playable",
      reasons: [
        "A pocket pair is already a made hand, which is better than hoping to pair later.",
        premiumPair
          ? "High pairs can often win without improving."
          : "Small and medium pairs are useful, but they become much stronger when they flop a set.",
        "Pairs lose value against many opponents because more players means more chances someone improves.",
      ],
      stats: [
        {
          label: "Set on flop",
          value: "about 12%",
          description: "This is why small pairs often want a cheap flop instead of a huge pot.",
        },
        {
          label: "Made hand",
          value: "yes",
          description: "You already have a pair before any community cards are dealt.",
        },
      ],
    };
  }

  const weakKicker = high >= 11 && low <= 5;
  const veryWeak = high <= 11 && low <= 6 && !suited && !connected;
  const strongBroadway = broadwayCount === 2;
  const tone: HandLesson["tone"] = strongBroadway || (suited && connected && high >= 10) ? "premium" : veryWeak || weakKicker ? "caution" : "playable";

  return {
    title: `${names}${suited ? " suited" : " offsuit"}`,
    strength: tone === "premium" ? "Strong draw potential" : tone === "playable" ? "Playable with caution" : "Weak starting hand",
    tone,
    reasons: [
      strongBroadway
        ? "Two high cards can make strong top-pair hands after the flop."
        : weakKicker
          ? "One high card with a very low kicker is easy to dominate. If you pair the high card, another player may have the same pair with a better kicker."
          : "Unpaired hands usually need help from the community cards.",
      suited
        ? "Being suited gives you a chance to make a flush, but that chance is still small."
        : "Offsuit cards have less flush potential, so they need more help in other ways.",
      connected
        ? "Connected cards can make straights more easily than hands with big gaps."
        : gap >= 5
          ? "Big gaps make straights unlikely, which lowers the hand's playability."
          : "Small gaps can still make some straight draws, but they are weaker than connected cards.",
    ],
    stats: [
      {
        label: "Pair on flop",
        value: "about 32%",
        description: "Two unpaired cards hit at least one pair on the flop roughly one-third of the time.",
      },
      {
        label: "Flush by river",
        value: suited ? "about 6%" : "not available",
        description: suited
          ? "Suited cards can make a flush by the river, but it does not happen often enough by itself to make weak cards great."
          : "Offsuit starting cards cannot make a two-card flush using both hole cards.",
      },
    ],
  };
}

function HistoryPanel({ botHistory }: { botHistory: BotAction[] }) {
  return (
    <section className="panel">
      <div className="panel-title">
        <History size={20} />
        <h2>Table Log</h2>
      </div>
      {botHistory.length ? (
        <div className="history-list">
          {botHistory.map((entry, index) => (
            <article key={`${entry.player_id}-${index}`}>
              <strong>
                {entry.player_name}: {entry.action}
                {entry.amount > 0 ? ` $${entry.amount}` : ""}
              </strong>
              <p>{entry.reason}</p>
            </article>
          ))}
        </div>
      ) : (
        <p className="empty-state">Bot decisions will appear here after you act.</p>
      )}
    </section>
  );
}
