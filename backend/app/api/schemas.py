from __future__ import annotations

from pydantic import BaseModel, Field


class NewGameRequest(BaseModel):
    player_names: list[str] = Field(
        default_factory=lambda: ["You", "Tight Bot", "Aggressive Bot", "Equity Bot"],
        min_length=2,
        max_length=6,
    )
    seed: int | None = None


class ActionRequest(BaseModel):
    action: str
    amount: int = 0


class GameResponse(BaseModel):
    game: dict
    coach: dict | None = None
    bot_actions: list[dict] = Field(default_factory=list)


class ErrorResponse(BaseModel):
    detail: str
