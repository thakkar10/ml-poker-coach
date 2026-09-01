from fastapi.testclient import TestClient

from app.main import app


client = TestClient(app)


def test_health_endpoint() -> None:
    response = client.get("/api/health")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_create_game_returns_public_state_and_coach() -> None:
    response = client.post(
        "/api/game/new",
        json={"player_names": ["You", "Tight Bot", "Aggressive Bot"], "seed": 101},
    )

    assert response.status_code == 200
    payload = response.json()

    assert payload["game"]["street"] == "preflop"
    assert payload["game"]["pot"] == 30
    assert len(payload["game"]["players"][0]["hole_cards"]) == 2
    assert payload["game"]["players"][1]["hole_cards"] == []
    assert payload["coach"]["action"] in payload["game"]["legal_actions"]


def test_create_four_player_game_runs_opening_bot_actions_until_user_turn() -> None:
    response = client.post(
        "/api/game/new",
        json={
            "player_names": ["You", "Tight Bot", "Aggressive Bot", "Equity Bot"],
            "seed": 222,
        },
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["game"]["current_player_id"] == "p0" or payload["game"]["street"] == "complete"
    assert payload["bot_actions"]


def test_get_game_by_id() -> None:
    created = client.post(
        "/api/game/new",
        json={"player_names": ["You", "Bot"], "seed": 102},
    ).json()
    game_id = created["game"]["id"]

    response = client.get(f"/api/game/{game_id}")

    assert response.status_code == 200
    assert response.json()["game"]["id"] == game_id


def test_apply_user_action_runs_bot_turns() -> None:
    created = client.post(
        "/api/game/new",
        json={"player_names": ["You", "Tight Bot", "Aggressive Bot"], "seed": 103},
    ).json()
    game_id = created["game"]["id"]
    action = "call" if "call" in created["game"]["legal_actions"] else "check"

    response = client.post(
        f"/api/game/{game_id}/action",
        json={"action": action, "amount": 0},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["game"]["id"] == game_id
    assert payload["game"]["current_player_id"] == "p0" or payload["game"]["street"] == "complete"
    assert isinstance(payload["bot_actions"], list)


def test_user_fold_allows_remaining_bots_to_finish_hand() -> None:
    created = client.post(
        "/api/game/new",
        json={"player_names": ["You", "Tight Bot", "Aggressive Bot", "Equity Bot"], "seed": 445},
    ).json()
    game_id = created["game"]["id"]

    response = client.post(
        f"/api/game/{game_id}/action",
        json={"action": "fold", "amount": 0},
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["game"]["street"] == "complete"
    assert payload["game"]["players"][0]["folded"] is True
    assert payload["bot_actions"]
    assert any(action["player_id"] != "p0" for action in payload["bot_actions"])


def test_review_endpoint_returns_player_style_after_decision() -> None:
    created = client.post(
        "/api/game/new",
        json={"player_names": ["You", "Tight Bot", "Aggressive Bot", "Equity Bot"], "seed": 445},
    ).json()
    game_id = created["game"]["id"]
    client.post(
        f"/api/game/{game_id}/action",
        json={"action": "fold", "amount": 0},
    )

    response = client.get(f"/api/game/{game_id}/review")

    assert response.status_code == 200
    payload = response.json()
    assert payload["decisions"] == 1
    assert payload["style"]
    assert payload["decision_log"][0]["action"] == "fold"
    assert "coach_alignment" in payload


def test_apply_unknown_action_returns_400() -> None:
    created = client.post(
        "/api/game/new",
        json={"player_names": ["You", "Bot"], "seed": 104},
    ).json()
    game_id = created["game"]["id"]

    response = client.post(
        f"/api/game/{game_id}/action",
        json={"action": "dance", "amount": 0},
    )

    assert response.status_code == 400


def test_unknown_game_returns_404() -> None:
    response = client.get("/api/game/not-a-real-game")

    assert response.status_code == 404
