export type Player = {
  id: string;
  name: string;
  stack: number;
  current_bet: number;
  folded: boolean;
  all_in: boolean;
  hole_cards: string[];
};

export type Coach = {
  action: string;
  amount: number;
  equity: number;
  pot_odds: number;
  confidence: number;
  reasons: string[];
};

export type GameState = {
  id: string;
  street: string;
  pot: number;
  current_bet: number;
  board: string[];
  current_player_id: string | null;
  legal_actions: string[];
  players: Player[];
  winners: string[];
  showdown: Record<string, string>;
};

export type BotAction = {
  player_id: string;
  player_name: string;
  agent_name: string;
  action: string;
  amount: number;
  reason: string;
};

export type GameResponse = {
  game: GameState;
  coach: Coach | null;
  bot_actions: BotAction[];
};

export async function createGame(): Promise<GameResponse> {
  const response = await fetch("/api/game/new", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      player_names: ["You", "Tight Bot", "Aggressive Bot", "Equity Bot"],
    }),
  });
  return readResponse(response);
}

export async function applyAction(
  gameId: string,
  action: string,
  amount = 0,
): Promise<GameResponse> {
  const response = await fetch(`/api/game/${gameId}/action`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ action, amount }),
  });
  return readResponse(response);
}

async function readResponse(response: Response): Promise<GameResponse> {
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "Request failed" }));
    throw new Error(error.detail ?? "Request failed");
  }
  return response.json();
}
