export type Player = {
  id: string;
  name: string;
  seat_position: number;
  stack: number;
  current_bet: number;
  total_committed: number;
  folded: boolean;
  all_in: boolean;
  active: boolean;
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
  button_player_id: string;
  small_blind_player_id: string;
  big_blind_player_id: string;
  legal_action_details: {
    can_fold: boolean;
    can_check: boolean;
    can_call: boolean;
    call_amount: number;
    can_bet: boolean;
    minimum_bet: number;
    can_raise: boolean;
    minimum_raise_to: number;
    maximum_raise_to: number;
    can_all_in: boolean;
    all_in_amount: number;
  };
  legal_actions: string[];
  players: Player[];
  winners: string[];
  showdown: Record<string, string>;
  side_pots: Array<{
    amount: number;
    eligible_player_ids: string[];
    winner_ids: string[];
  }>;
};

export type BotAction = {
  player_id: string;
  player_name: string;
  agent_name: string;
  action: string;
  amount: number;
  reason: string;
  state_before?: GameState;
  state_after?: GameState;
};

export type GameResponse = {
  game: GameState;
  coach: Coach | null;
  bot_actions: BotAction[];
};

export type DecisionReview = {
  street: string;
  action: string;
  recommended_action: string;
  equity: number;
  pot_odds: number;
  confidence: number;
  followed_coach: boolean;
};

export type PlayerReview = {
  style: string;
  summary: string;
  decisions: number;
  fold_rate: number;
  call_rate: number;
  raise_rate: number;
  coach_alignment: number;
  avg_equity_edge: number;
  leaks: string[];
  strengths: string[];
  next_steps: string[];
  decision_log: DecisionReview[];
};

export async function createGame(): Promise<GameResponse> {
  const response = await fetch("/api/game/new", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      player_names: ["HEET", "Stone Fox", "River Jay", "Nova", "Blaze", "Mira"],
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

export async function getGameReview(gameId: string): Promise<PlayerReview> {
  const response = await fetch(`/api/game/${gameId}/review`);
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "Review failed" }));
    throw new Error(error.detail ?? "Review failed");
  }
  return response.json();
}

async function readResponse(response: Response): Promise<GameResponse> {
  if (!response.ok) {
    const error = await response.json().catch(() => ({ detail: "Request failed" }));
    throw new Error(error.detail ?? "Request failed");
  }
  return response.json();
}
