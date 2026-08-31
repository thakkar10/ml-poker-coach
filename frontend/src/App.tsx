import { useEffect, useMemo, useState } from "react";
import { Brain, CircleDollarSign, History, Loader2, Play, RotateCcw } from "lucide-react";
import { applyAction, BotAction, Coach, createGame, GameResponse, GameState, Player } from "./api";

const seatPositions = ["seat-user", "seat-left", "seat-top", "seat-right"];

export function App() {
  const [gameResponse, setGameResponse] = useState<GameResponse | null>(null);
  const [botHistory, setBotHistory] = useState<BotAction[]>([]);
  const [raiseAmount, setRaiseAmount] = useState(80);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const game = gameResponse?.game ?? null;
  const coach = gameResponse?.coach ?? null;
  const user = game?.players[0] ?? null;
  const canAct = game?.current_player_id === "p0" && game.street !== "complete";

  useEffect(() => {
    void startNewGame();
  }, []);

  async function startNewGame() {
    setLoading(true);
    setError(null);
    try {
      const nextGame = await createGame();
      setGameResponse(nextGame);
      setBotHistory(nextGame.bot_actions);
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
      setGameResponse(nextGame);
      setBotHistory((previous) => [...nextGame.bot_actions, ...previous].slice(0, 8));
    } catch (err) {
      setError(err instanceof Error ? err.message : "Action failed");
    } finally {
      setLoading(false);
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
    if (game.current_player_id === "p0") return "Your decision";
    const current = game.players.find((player) => player.id === game.current_player_id);
    return `${current?.name ?? "Opponent"} is thinking`;
  }, [game]);

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
            />
          ))}

          <div className="poker-table">
            <div className="board-row" aria-label="Community cards">
              {Array.from({ length: 5 }).map((_, index) => (
                <CardView key={index} card={game?.board[index]} />
              ))}
            </div>
            <div className="pot-display">
              <CircleDollarSign size={20} />
              Pot ${game?.pot ?? 0}
            </div>
            <div className="street-pill">{game?.street ?? "loading"}</div>
          </div>
        </div>

        <section className="action-dock" aria-label="Player actions">
          <div>
            <p className="status-label">Table Status</p>
            <strong>{tableStatus}</strong>
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
        <CoachPanel coach={coach} />
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
}: {
  player: Player;
  position: string;
  isCurrent: boolean;
  isUser: boolean;
  showdownLabel?: string;
}) {
  return (
    <article className={`player-seat ${position} ${isCurrent ? "is-current" : ""} ${player.folded ? "is-folded" : ""}`}>
      <div className="seat-meta">
        <strong>{player.name}</strong>
        <span>${player.stack}</span>
      </div>
      <div className="hole-cards">
        {[0, 1].map((index) => (
          <CardView key={index} card={player.hole_cards[index]} hidden={!player.hole_cards[index]} />
        ))}
      </div>
      <div className="seat-footer">
        <span>{player.folded ? "Folded" : isUser ? "Hero" : "AI Opponent"}</span>
        {player.current_bet > 0 && <b>Bet ${player.current_bet}</b>}
      </div>
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

function CoachPanel({ coach }: { coach: Coach | null }) {
  return (
    <section className="panel coach-panel">
      <div className="panel-title">
        <Brain size={20} />
        <h2>AI Coach</h2>
      </div>
      {coach ? (
        <>
          <div className="recommendation">
            <span>Recommended Action</span>
            <strong>
              {coach.action}
              {coach.amount > 0 ? ` $${coach.amount}` : ""}
            </strong>
          </div>
          <MetricBar label="Equity" value={coach.equity} />
          <MetricBar label="Pot Odds" value={coach.pot_odds} />
          <MetricBar label="Confidence" value={coach.confidence} />
          <ul className="reason-list">
            {coach.reasons.map((reason) => (
              <li key={reason}>{reason}</li>
            ))}
          </ul>
        </>
      ) : (
        <p className="empty-state">Coach advice appears when it is your turn to act.</p>
      )}
    </section>
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
