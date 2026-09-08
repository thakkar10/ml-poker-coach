from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from app.api.schemas import ActionRequest, GameResponse, NewGameRequest
from app.coach.recommender import CoachRecommendation
from app.core.game import Action, Street
from app.services.game_sessions import GameSessionStore, serialize_bot_logs


app = FastAPI(
    title="ML Poker Coach API",
    description="API for an interactive Texas Hold'em coaching simulator.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

store = GameSessionStore()


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/game/new", response_model=GameResponse)
def create_game(request: NewGameRequest) -> GameResponse:
    session = store.create(request.player_names, seed=request.seed)
    bot_logs = session.runner.play_until_user_turn_or_complete(
        session.game,
        user_player_id="p0",
    )
    return _response(session, bot_actions=serialize_bot_logs(bot_logs))


@app.get("/api/game/{game_id}", response_model=GameResponse)
def get_game(game_id: str) -> GameResponse:
    session = _session_or_404(game_id)
    return _response(session)


@app.post("/api/game/{game_id}/action", response_model=GameResponse)
def apply_action(game_id: str, request: ActionRequest) -> GameResponse:
    try:
        action = Action(request.action)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail="Unknown action") from exc

    try:
        session, bot_logs = store.apply_user_action(
            game_id,
            action=action,
            amount=request.amount,
        )
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Game not found") from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return _response(session, bot_actions=serialize_bot_logs(bot_logs))


@app.get("/api/game/{game_id}/coach")
def get_coach_recommendation(game_id: str) -> dict[str, object]:
    session = _session_or_404(game_id)
    return _coach_or_none(session) or {"available": False}


@app.get("/api/game/{game_id}/review")
def get_game_review(game_id: str) -> dict[str, object]:
    try:
        return store.review(game_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Game not found") from exc


def _session_or_404(game_id: str):
    try:
        return store.get(game_id)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail="Game not found") from exc


def _response(session, *, bot_actions: list[dict] | None = None) -> GameResponse:
    return GameResponse(
        game=session.game.to_public_state(viewer_id="p0"),
        coach=_coach_or_none(session),
        bot_actions=bot_actions or [],
    )


def _coach_or_none(session) -> dict[str, object] | None:
    game = session.game
    if game.street == Street.COMPLETE or game.current_player.id != "p0":
        return None

    try:
        recommendation: CoachRecommendation = session.coach.recommend(game, player_id="p0")
    except ValueError:
        return None
    return recommendation.to_dict()
