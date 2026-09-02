import { MutableRefObject, useEffect, useMemo, useRef, useState } from "react";
import {
  BookOpen,
  Brain,
  CircleDollarSign,
  History,
  Loader2,
  RotateCcw,
  Settings,
  TrendingUp,
  Volume2,
  X,
} from "lucide-react";
import { applyAction, BotAction, Coach, createGame, GameResponse, getGameReview, Player, PlayerReview } from "./api";

const seatPositions = ["seat-user", "seat-lower-left", "seat-upper-left", "seat-top", "seat-upper-right", "seat-lower-right"];
const ACTION_VISIBLE_MS = 1050;
const POST_ACTION_SETTLE_MS = 360;
const REVIEW_POT_AWARD_MS = 1800;
const REVIEW_COUNTDOWN_SECONDS = 4;
const ACTION_THINKING_DELAYS: Record<string, [number, number]> = {
  check: [800, 1400],
  fold: [900, 1600],
  call: [1000, 1700],
  bet: [1200, 2000],
  raise: [1400, 2300],
  all_in: [1500, 2500],
};

type VisualAction = Pick<BotAction, "player_id" | "player_name" | "action" | "amount"> & {
  id: string;
  eventId: string;
};

export function App() {
  const [gameResponse, setGameResponse] = useState<GameResponse | null>(null);
  const [botHistory, setBotHistory] = useState<BotAction[]>([]);
  const [raiseAmount, setRaiseAmount] = useState(80);
  const [loading, setLoading] = useState(false);
  const [replaying, setReplaying] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [visualActions, setVisualActions] = useState<VisualAction[]>([]);
  const [thinkingPlayerId, setThinkingPlayerId] = useState<string | null>(null);
  const [playerReview, setPlayerReview] = useState<PlayerReview | null>(null);
  const [reviewDismissed, setReviewDismissed] = useState(false);
  const [reviewCountdown, setReviewCountdown] = useState<number | null>(null);
  const didStartInitialGame = useRef(false);
  const actionLock = useRef(false);
  const visualEventSequence = useRef(0);
  const consumedVisualEventIds = useRef(new Set<string>());
  const reviewScheduledGameId = useRef<string | null>(null);
  const [historyOpen, setHistoryOpen] = useState(false);

  const game = gameResponse?.game ?? null;
  const coach = gameResponse?.coach ?? null;
  const user = game?.players[0] ?? null;
  const canAct = game?.current_player_id === "p0" && game.street !== "complete" && !replaying && !loading;
  const legalDetails = game?.legal_action_details;
  const toCall = legalDetails?.call_amount ?? 0;
  const maxRaise = legalDetails?.maximum_raise_to ?? (user ? user.stack + user.current_bet : 1000);
  const minRaise = game?.legal_actions.includes("bet")
    ? (legalDetails?.minimum_bet ?? 20)
    : (legalDetails?.minimum_raise_to ?? 40);
  const canRaise = Boolean(canAct && legalDetails?.can_raise);
  const canBet = Boolean(canAct && legalDetails?.can_bet);
  const canAggressiveAction = canRaise || canBet;
  const canAllIn = Boolean(canAct && legalDetails?.can_all_in);
  const allInIsExactCall = Boolean(
    legalDetails?.can_call &&
      legalDetails.can_all_in &&
      legalDetails.call_amount === legalDetails.all_in_amount &&
      !legalDetails.can_raise &&
      !legalDetails.can_bet,
  );
  const passiveLabel = legalDetails?.can_check
    ? "Check"
    : allInIsExactCall
      ? `Call $${toCall} - All In`
      : `Call $${toCall}`;
  const aggressiveLabel = canAggressiveAction
    ? (game?.current_bet ?? 0) > 0
      ? `Raise to $${raiseAmount}`
      : `Bet $${raiseAmount}`
    : "Raise";
  const quickBetSizes = useMemo(() => {
    const pot = game?.pot ?? 0;
    const stack = user?.stack ?? 0;
    const alreadyCommitted = user?.current_bet ?? 0;
    const sizes = [
      { label: "1/3 Pot", amount: Math.round(pot / 3), allIn: false },
      { label: "1/2 Pot", amount: Math.round(pot / 2), allIn: false },
      { label: "3/4 Pot", amount: Math.round((pot * 3) / 4), allIn: false },
      { label: "Pot", amount: pot, allIn: false },
      { label: "All In", amount: stack + alreadyCommitted, allIn: true },
    ];

    return sizes
      .filter((size) => !size.allIn || !allInIsExactCall)
      .map((size) => ({
        ...size,
        amount: clampBetSize(size.amount, minRaise, maxRaise),
      }));
  }, [allInIsExactCall, game?.pot, maxRaise, minRaise, user?.current_bet, user?.stack]);
  const handLesson = useMemo(() => explainStartingHand(user?.hole_cards ?? []), [user?.hole_cards]);
  const communityCards = useMemo(() => visibleCommunityCards(game), [game]);
  const visibleActions = useMemo(() => {
    const actions = new Map<string, VisualAction>();
    for (const action of visualActions) {
      if (!actions.has(action.player_id)) {
        actions.set(action.player_id, action);
      }
    }
    return actions;
  }, [visualActions]);
  const actingPlayerIds = useMemo(
    () => new Set(visualActions.map((action) => action.player_id)),
    [visualActions],
  );
  const winnerAmounts = useMemo(() => calculateWinnerAmounts(game), [game]);

  useEffect(() => {
    if (didStartInitialGame.current) return;
    didStartInitialGame.current = true;
    void startNewGame();
  }, []);

  useEffect(() => {
    setRaiseAmount((current) => clampBetSize(current, minRaise, maxRaise));
  }, [maxRaise, minRaise]);

  useEffect(() => {
    if (!game || game.street !== "complete" || replaying || playerReview || reviewScheduledGameId.current === game.id) {
      return;
    }

    reviewScheduledGameId.current = game.id;
    setReviewCountdown(null);

    const timers: number[] = [];
    for (let secondsLeft = REVIEW_COUNTDOWN_SECONDS; secondsLeft >= 1; secondsLeft -= 1) {
      const elapsed = REVIEW_POT_AWARD_MS + (REVIEW_COUNTDOWN_SECONDS - secondsLeft) * 1000;
      timers.push(window.setTimeout(() => setReviewCountdown(secondsLeft), elapsed));
    }
    timers.push(
      window.setTimeout(() => {
        setReviewCountdown(null);
        void loadReview(game.id);
      }, REVIEW_POT_AWARD_MS + REVIEW_COUNTDOWN_SECONDS * 1000),
    );

    return () => {
      timers.forEach((timer) => window.clearTimeout(timer));
    };
  }, [game, playerReview, replaying]);

  async function startNewGame() {
    if (actionLock.current) return;
    actionLock.current = true;
    setLoading(true);
    setError(null);
    try {
      const nextGame = await createGame();
      setGameResponse(nextGame.bot_actions[0]?.state_before ? withGameState(nextGame, nextGame.bot_actions[0].state_before) : nextGame);
      setBotHistory([]);
      setPlayerReview(null);
      setReviewDismissed(false);
      setReviewCountdown(null);
      reviewScheduledGameId.current = null;
      setThinkingPlayerId(null);
      setVisualActions([]);
      consumedVisualEventIds.current.clear();
      await replayActions(nextGame.bot_actions);
      setGameResponse(nextGame);
      setRaiseAmount(80);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not start game");
    } finally {
      actionLock.current = false;
      setLoading(false);
    }
  }

  async function chooseAction(action: string) {
    if (!game || !canAct || actionLock.current) return;
    actionLock.current = true;
    setLoading(true);
    setError(null);
    try {
      const nextGame = await applyAction(game.id, action, action === "raise" || action === "bet" ? raiseAmount : 0);
      const userAction = {
        player_id: "p0",
        player_name: "You",
        action,
        amount:
          action === "raise" || action === "bet"
            ? raiseAmount
            : action === "all_in"
              ? (legalDetails?.all_in_amount ?? 0)
              : action === "call"
                ? toCall
                : 0,
        agent_name: "Player",
        reason: "You chose this action.",
      };
      await replayActions([userAction, ...nextGame.bot_actions], {
        includeInLog: nextGame.bot_actions,
        immediatePlayerIds: new Set(["p0"]),
      });
      if (hasStreetAdvanced(game, nextGame.game)) {
        await sleep(900);
      }
      setGameResponse(nextGame);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Action failed");
    } finally {
      actionLock.current = false;
      setLoading(false);
    }
  }

  async function loadReview(gameId: string) {
    try {
      const review = await getGameReview(gameId);
      setPlayerReview(review);
      setReviewDismissed(false);
    } catch (err) {
      setError(err instanceof Error ? err.message : "Could not load game review");
    }
  }

  async function replayActions(
    actions: BotAction[],
    options: { includeInLog?: BotAction[]; immediatePlayerIds?: Set<string> } = {},
  ) {
    if (!actions.length) return;

    setReplaying(true);
    const loggable = options.includeInLog ?? actions;
    for (const action of actions) {
      const visualAction = toVisualAction(action, createVisualEventId(action, visualEventSequence));
      if (consumedVisualEventIds.current.has(visualAction.eventId)) {
        continue;
      }
      consumedVisualEventIds.current.add(visualAction.eventId);
      if (action.state_before) {
        await syncVisualGameState(action.state_before);
      }
      if (!options.immediatePlayerIds?.has(action.player_id)) {
        setThinkingPlayerId(action.player_id);
        await sleep(getActionThinkingDelay(action.action));
        setThinkingPlayerId(null);
      }
      setVisualActions([visualAction]);
      if (loggable.includes(action)) {
        setBotHistory((previous) => [action, ...previous].slice(0, 10));
      }
      await sleep(getActionVisibleDuration(action.action));
      setVisualActions([]);
      if (action.state_after) {
        await syncVisualGameState(action.state_after);
      }
      await sleep(POST_ACTION_SETTLE_MS);
    }
    setVisualActions([]);
    setThinkingPlayerId(null);
    setReplaying(false);
  }

  async function openReviewNow(gameId: string) {
    setReviewCountdown(null);
    await loadReview(gameId);
  }

  async function syncVisualGameState(nextState: GameResponse["game"]) {
    let shouldPauseForBoardReveal = false;
    setGameResponse((current) => {
      shouldPauseForBoardReveal = Boolean(current && hasNewCommunityCards(current.game, nextState));
      return withGameState(current, nextState);
    });
    if (shouldPauseForBoardReveal) {
      await sleep(950);
    }
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
    if (thinkingPlayerId) {
      const thinkingPlayer = game.players.find((player) => player.id === thinkingPlayerId);
      return `${thinkingPlayer?.name ?? "Opponent"} is thinking`;
    }
    if (replaying) return "Action is playing out";
    if (game.current_player_id === "p0") return "Your decision";
    const current = game.players.find((player) => player.id === game.current_player_id);
    return `${current?.name ?? "Opponent"} is thinking`;
  }, [game, replaying, thinkingPlayerId]);

  return (
    <main className="app-shell">
      <section className="game-surface" aria-label="Poker table">
        <header className="top-bar">
          <div>
            <p className="eyebrow">NL Hold'em · $10 / $20 · 6 Max</p>
            <h1>Texas Hold'em</h1>
          </div>
          <div className="table-tools" aria-label="Table controls">
            <button className="tool-button" type="button" aria-label="Sound effects">
              <Volume2 size={17} />
            </button>
            <button className="tool-button" type="button" aria-label="Settings">
              <Settings size={17} />
            </button>
            <button className="icon-button" onClick={startNewGame} disabled={loading} aria-label="Start new hand">
              {loading ? <Loader2 className="spin" size={18} /> : <RotateCcw size={18} />}
              New Hand
            </button>
          </div>
        </header>

        <div className="table-zone">
          {game?.players.map((player, index) => (
            <PlayerSeat
              key={player.id}
              player={player}
              position={seatPositions[index] ?? "seat-side"}
              isCurrent={game.current_player_id === player.id && !replaying}
              isThinking={thinkingPlayerId === player.id}
              isUser={player.id === "p0"}
              tableRole={tableRoleForPlayer(game, player.id)}
              showdownLabel={game.showdown[player.id]}
              lastAction={visibleActions.get(player.id)}
              isActing={actingPlayerIds.has(player.id)}
              isWinner={game.winners.includes(player.id)}
              isLoser={game.street === "complete" && game.winners.length > 0 && !game.winners.includes(player.id)}
              isShowdown={game.street === "complete"}
              winnings={winnerAmounts.get(player.id) ?? 0}
            />
          ))}

          <div className="poker-table">
            <div className="dealer-shoe" aria-hidden="true">DEALER</div>
            {game?.players.map((player, index) => (
              <BetStack
                key={`bet-${player.id}`}
                player={player}
                position={seatPositions[index] ?? "seat-side"}
              />
            ))}
            <div className="pot-display">
              <CircleDollarSign size={20} />
              Pot ${game?.pot ?? 0}
            </div>
            <div className="board-row" aria-label="Community cards">
              {Array.from({ length: 5 }).map((_, index) => (
                <CardView
                  key={communityCards[index] ?? `board-${index}`}
                  card={communityCards[index]}
                  variant="board"
                  delayIndex={index}
                />
              ))}
            </div>
            <div className="street-pill">{game?.street ?? "loading"}</div>
          </div>
          <ChipBursts actions={visualActions} />
          {game?.street === "complete" && <PotAward winnerId={game.winners[0]} />}
          {game?.street === "complete" && !playerReview && (
            <div className="review-countdown">
              <strong>{reviewCountdown ? `Reviewing hand in ${reviewCountdown}...` : "Awarding the pot..."}</strong>
              <button type="button" onClick={() => void openReviewNow(game.id)}>
                Review Hand
              </button>
            </div>
          )}
        </div>

        <section className="action-dock" aria-label="Player actions">
          <div className="bet-console">
            <div className="compact-status">
              <strong>{tableStatus}</strong>
              {replaying && <span>Table action playing...</span>}
              {error && <span className="error-text">{error}</span>}
            </div>
            <div className="quick-bets" aria-label="Quick bet sizes">
              {quickBetSizes.map((size) => (
                <button
                  key={size.label}
                  type="button"
                  onClick={() => (size.allIn ? chooseAction("all_in") : setRaiseAmount(size.amount))}
                  disabled={size.allIn ? !canAllIn || loading : !canAggressiveAction || loading}
                >
                  {size.label}
                </button>
              ))}
            </div>
            <label className="raise-control">
              <span>{game?.current_bet ? "Raise to" : "Bet"}</span>
              <input
                className="amount-input"
                type="number"
                min={minRaise}
                max={maxRaise}
                step="10"
                value={raiseAmount}
                onChange={(event) => setRaiseAmount(clampBetSize(Number(event.target.value), minRaise, maxRaise))}
                disabled={!canAggressiveAction || loading}
              />
              <input
                type="range"
                min={minRaise}
                max={Math.max(minRaise, maxRaise)}
                step="10"
                value={raiseAmount}
                onChange={(event) => setRaiseAmount(Number(event.target.value))}
                disabled={!canAggressiveAction || loading}
              />
            </label>
            <div className="actions">
              <button className="fold-button" onClick={() => chooseAction("fold")} disabled={!canAct || !game?.legal_actions.includes("fold") || loading}>
                Fold
              </button>
              <button onClick={() => chooseAction(legalDetails?.can_check ? "check" : "call")} disabled={!canAct || (!legalDetails?.can_check && !legalDetails?.can_call) || loading}>
                {passiveLabel}
              </button>
              {canAggressiveAction && (
                <button className="raise-button" onClick={() => chooseAction(game?.legal_actions.includes("bet") ? "bet" : "raise")} disabled={loading}>
                  {aggressiveLabel}
                </button>
              )}
            </div>
          </div>
        </section>
      </section>

      <aside className="side-panel">
        <LiveStatsPanel coach={coach} />
        <HandLessonPanel lesson={handLesson} />
        <button className="history-toggle" type="button" onClick={() => setHistoryOpen((open) => !open)}>
          <History size={16} />
          History
        </button>
        {historyOpen && <HistoryPanel botHistory={botHistory} />}
      </aside>
      {playerReview && !reviewDismissed && (
        <ReviewModal
          review={playerReview}
          onClose={() => setReviewDismissed(true)}
          onNewHand={startNewGame}
          loading={loading}
        />
      )}
    </main>
  );
}

function ReviewModal({
  review,
  onClose,
  onNewHand,
  loading,
}: {
  review: PlayerReview;
  onClose: () => void;
  onNewHand: () => void;
  loading: boolean;
}) {
  return (
    <div className="review-backdrop" role="presentation">
      <section className="review-modal" role="dialog" aria-modal="true" aria-labelledby="review-title">
        <header className="review-modal-header">
          <div>
            <p className="eyebrow">Machine Learning Coach</p>
            <h2 id="review-title">After-Hand Review</h2>
          </div>
          <button className="tool-button" type="button" onClick={onClose} aria-label="Close review">
            <X size={18} />
          </button>
        </header>
        <PlayerReviewPanel review={review} />
        <footer className="review-modal-footer">
          <p>This review is based on how you chose to fold, call, check, or raise during the hand.</p>
          <button className="icon-button" type="button" onClick={onNewHand} disabled={loading}>
            {loading ? <Loader2 className="spin" size={18} /> : <RotateCcw size={18} />}
            Play Next Hand
          </button>
        </footer>
      </section>
    </div>
  );
}

function PlayerSeat({
  player,
  position,
  isCurrent,
  isThinking,
  isUser,
  tableRole,
  showdownLabel,
  lastAction,
  isActing,
  isWinner,
  isLoser,
  isShowdown,
  winnings,
}: {
  player: Player;
  position: string;
  isCurrent: boolean;
  isThinking: boolean;
  isUser: boolean;
  tableRole?: string;
  showdownLabel?: string;
  lastAction?: VisualAction;
  isActing: boolean;
  isWinner: boolean;
  isLoser: boolean;
  isShowdown: boolean;
  winnings: number;
}) {
  return (
    <article
      className={`player-seat ${position} ${isCurrent ? "is-current" : ""} ${
        player.folded ? "is-folded" : ""
      } ${lastAction ? `action-${lastAction.action}` : ""} ${isThinking ? "is-thinking" : ""} ${
        isActing ? "is-acting" : ""
      } ${isWinner ? "is-winner" : ""} ${
        isLoser ? "is-loser" : ""
      } ${player.all_in ? "is-all-in" : ""}`}
    >
      {(isCurrent || isThinking) && <div className="action-timer" key={`${player.id}-${player.current_bet}-${isThinking}`} />}
      <div className="avatar-wrap">
        <div className="avatar" aria-hidden="true">{player.name.slice(0, 1)}</div>
        {tableRole && <span className="table-marker">{tableRole}</span>}
      </div>
      <div className="seat-meta">
        <strong>{player.name}</strong>
        <span>{player.all_in ? "ALL IN" : `$${player.stack}`}</span>
      </div>
      <div className="hole-cards">
        {[0, 1].map((index) => (
          <CardView
            key={player.hole_cards[index] ?? `${player.id}-${index}`}
            card={player.hole_cards[index]}
            hidden={!player.hole_cards[index]}
            variant={isShowdown && !isUser ? "showdown" : "hole"}
            delayIndex={index}
          />
        ))}
      </div>
      <div className="seat-footer">
        <span>{player.folded ? "Folded" : player.all_in ? "All In" : isUser ? "Hero" : "AI Opponent"}</span>
        {player.total_committed > 0 && <b>${player.total_committed} committed</b>}
      </div>
      {player.all_in && <p className="all-in-badge">All in</p>}
      {lastAction && (
        <p className={`action-badge ${lastAction.action === "fold" ? "fold-action" : ""}`}>
          {lastAction.action}
          {lastAction.amount > 0 ? ` $${lastAction.amount}` : ""}
        </p>
      )}
      {isWinner && (
        <p className="winner-badge">
          WINNER {winnings > 0 ? `+$${winnings}` : ""}
          {!showdownLabel && <span>Won uncontested</span>}
        </p>
      )}
      {showdownLabel && <p className="showdown-label">{showdownLabel}</p>}
    </article>
  );
}

function BetStack({ player, position }: { player: Player; position: string }) {
  if (player.current_bet <= 0) return null;

  return (
    <div className={`bet-stack bet-${position}`} aria-label={`${player.name} has bet ${player.current_bet}`}>
      <div className="mini-chips" aria-hidden="true">
        <span />
        <span />
        <span />
      </div>
      <strong>${player.current_bet}</strong>
    </div>
  );
}

function CardView({
  card,
  hidden = false,
  variant = "hole",
  delayIndex = 0,
}: {
  card?: string;
  hidden?: boolean;
  variant?: "hole" | "board" | "showdown";
  delayIndex?: number;
}) {
  if (!card && variant === "board") {
    return <div className="card card-empty" aria-label="Empty board card slot" />;
  }

  if (!card || hidden) {
    return <div className="card card-back" aria-label="Hidden card" style={{ animationDelay: `${delayIndex * 90}ms` }} />;
  }

  const suit = card.slice(1);
  const rank = card.slice(0, 1);
  const suitSymbol = suit === "s" ? "♠" : suit === "h" ? "♥" : suit === "d" ? "♦" : "♣";
  const suitClass = suit === "h" ? "heart" : suit === "d" ? "diamond" : suit === "c" ? "club" : "spade";

  return (
    <div
      className={`card ${suitClass} card-${variant}`}
      aria-label={`${rank}${suitSymbol}`}
      style={{ animationDelay: `${delayIndex * 110}ms` }}
    >
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
            <span>Decision Quality</span>
            <strong>{coach.equity > coach.pot_odds ? "Favorable" : "Marginal"}</strong>
          </div>
          <MetricBar label="Equity" value={coach.equity} />
          <MetricBar label="Pot Odds" value={coach.pot_odds} />
          <MetricBar label="Equity Edge" value={Math.max(0, coach.equity - coach.pot_odds)} />
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
  const moneyActions = actions.filter((action) => ["all_in", "bet", "call", "raise"].includes(action.action));
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

function PotAward({ winnerId }: { winnerId?: string }) {
  if (!winnerId) return null;

  return (
    <div className={`pot-award to-${winnerId}`} aria-hidden="true">
      <span />
      <span />
      <span />
      <span />
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

function createVisualEventId(action: BotAction, sequence: MutableRefObject<number>) {
  sequence.current += 1;
  return `${action.player_id}-${action.action}-${action.amount}-${sequence.current}`;
}

function toVisualAction(action: BotAction, eventId: string): VisualAction {
  return {
    id: eventId,
    eventId,
    player_id: action.player_id,
    player_name: action.player_name,
    action: action.action,
    amount: action.amount,
  };
}

function clampBetSize(value: number, min: number, max: number) {
  if (!Number.isFinite(value)) return min;
  return Math.min(Math.max(Math.round(value / 10) * 10, min), Math.max(min, max));
}

function tableRoleForPlayer(game: GameResponse["game"], playerId: string) {
  if (game.button_player_id === playerId) return "D";
  if (game.small_blind_player_id === playerId) return "SB";
  if (game.big_blind_player_id === playerId) return "BB";
  return undefined;
}

function calculateWinnerAmounts(game: GameResponse["game"] | null) {
  const awards = new Map<string, number>();
  if (!game) return awards;

  for (const pot of game.side_pots) {
    if (!pot.winner_ids.length) continue;

    const baseShare = Math.floor(pot.amount / pot.winner_ids.length);
    const oddChips = pot.amount % pot.winner_ids.length;
    pot.winner_ids.forEach((winnerId, index) => {
      const share = baseShare + (index < oddChips ? 1 : 0);
      awards.set(winnerId, (awards.get(winnerId) ?? 0) + share);
    });
  }

  if (!awards.size && game.winners.length === 1) {
    awards.set(game.winners[0], game.pot);
  }

  return awards;
}

function withGameState(response: GameResponse | null, game: GameResponse["game"]): GameResponse {
  return {
    game,
    coach: game.current_player_id === "p0" ? (response?.coach ?? null) : null,
    bot_actions: response?.bot_actions ?? [],
  };
}

function visibleCommunityCards(game: GameResponse["game"] | null) {
  const cards = Array<string | undefined>(5).fill(undefined);
  if (!game) return cards;

  const visibleCount = visibleBoardCardCount(game.street);
  game.board.slice(0, visibleCount).forEach((card, index) => {
    cards[index] = card;
  });
  return cards;
}

function visibleBoardCardCount(street: string) {
  if (street === "flop") return 3;
  if (street === "turn") return 4;
  if (street === "river" || street === "showdown" || street === "complete") return 5;
  return 0;
}

function hasNewCommunityCards(previousGame: GameResponse["game"], nextGame: GameResponse["game"]) {
  return visibleBoardCardCount(nextGame.street) > visibleBoardCardCount(previousGame.street)
    || nextGame.board.length > previousGame.board.length;
}

function hasStreetAdvanced(previousGame: GameResponse["game"], nextGame: GameResponse["game"]) {
  return previousGame.street !== nextGame.street || previousGame.board.length !== nextGame.board.length;
}

function getActionThinkingDelay(action: string) {
  const [min, max] = ACTION_THINKING_DELAYS[action] ?? [900, 1600];
  return Math.round(min + Math.random() * (max - min));
}

function getActionVisibleDuration(action: string) {
  if (action === "all_in") return ACTION_VISIBLE_MS + 450;
  if (action === "bet" || action === "raise") return ACTION_VISIBLE_MS + 250;
  return ACTION_VISIBLE_MS;
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
