"""API tests: the model is stubbed, so no weights are ever downloaded."""

from __future__ import annotations

from typing import Any, Dict

import pytest
from fastapi.testclient import TestClient

import laya_mlx_http.app as app_module
from laya_mlx_http import Settings, create_app

PRESET = "triage"


class StubAgent:
    def __init__(self) -> None:
        self.calls: list[tuple[str, Dict[str, Any]]] = []

    def predict(self, state: str, questions: Dict[str, Any]):
        self.calls.append((state, questions))
        answers: Dict[str, Any] = {}
        for qid, question in questions.items():
            if question["type"] == "choice":
                options = list(question["criteria"])
                answers[qid] = {
                    "type": "choice",
                    "confidence": 0.9,
                    "choice": options[0],
                    "probabilities": {
                        option: 1.0 if index == 0 else 0.0
                        for index, option in enumerate(options)
                    },
                }
            elif question["type"] == "score":
                levels = len(question["criteria"])
                answers[qid] = {
                    "type": "score",
                    "confidence": 0.8,
                    "score": 0.0,
                    "probabilities": {str(i): 1.0 / levels for i in range(levels)},
                }
            else:
                answers[qid] = {"type": "noul", "confidence": 0.7, "noul": 0.42}
        return {
            "model": "laya-rl-agent",
            "answers": answers,
            "usage": {"input_tokens": 5, "output_tokens": 0},
        }


@pytest.fixture
def agent(monkeypatch: pytest.MonkeyPatch) -> StubAgent:
    stub = StubAgent()
    monkeypatch.setattr(app_module.laya, "load", lambda *args, **kwargs: stub)
    return stub


@pytest.fixture
def client(agent: StubAgent):
    app = create_app(Settings())
    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def guarded_client(agent: StubAgent):
    app = create_app(Settings(api_key="s3cret"))
    with TestClient(app) as test_client:
        yield test_client


def test_health_is_public_and_reports_readiness(guarded_client: TestClient):
    response = guarded_client.get("/health")
    assert response.status_code == 200
    assert response.json() == {
        "status": "ok",
        "model": Settings().model_id,
        "ready": True,
    }


def test_predict_requires_api_key(guarded_client: TestClient):
    payload = {"text": "please refund me", "preset": PRESET}
    assert guarded_client.post("/v1/predict", json=payload).status_code == 401

    wrong = guarded_client.post("/v1/predict", json=payload, headers={"X-API-Key": "nope"})
    assert wrong.status_code == 401

    ok = guarded_client.post("/v1/predict", json=payload, headers={"X-API-Key": "s3cret"})
    assert ok.status_code == 200


def test_bearer_token_is_accepted(guarded_client: TestClient):
    response = guarded_client.post(
        "/v1/predict",
        json={"text": "hi", "preset": PRESET},
        headers={"Authorization": "Bearer s3cret"},
    )
    assert response.status_code == 200


def test_get_requires_api_key(guarded_client: TestClient):
    assert guarded_client.get("/v1/predict", params={"text": "x", "preset": PRESET}).status_code == 401


def test_post_predict_with_preset(client: TestClient, agent: StubAgent):
    response = client.post(
        "/v1/predict",
        json={"text": "I want my money back", "preset": PRESET, "flat": True},
    )
    assert response.status_code == 200
    body = response.json()
    assert body["model"] == Settings().model_id
    assert body["answers"]["intent"]["type"] == "choice"
    assert body["flat"]["intent"] == "refund"
    assert body["flat"]["is_urgent"] == 0.42
    assert body["usage"]["input_tokens"] == 5
    assert agent.calls[-1][0] == "I want my money back"


def test_post_predict_echoes_requested_model(client: TestClient):
    response = client.post(
        "/v1/predict",
        json={"text": "hi", "preset": PRESET, "model": "laya-mlx"},
    )
    assert response.json()["model"] == "laya-mlx"


def test_post_predict_with_custom_questions(client: TestClient, agent: StubAgent):
    questions = {
        "wants_refund": {
            "type": "noul",
            "instructions": "Does the customer ask for money back?",
        }
    }
    response = client.post("/v1/predict", json={"text": "refund", "questions": questions})
    assert response.status_code == 200
    assert response.json()["answers"]["wants_refund"]["noul"] == 0.42
    assert agent.calls[-1][1] == questions


def test_post_predict_needs_questions_or_preset(client: TestClient):
    response = client.post("/v1/predict", json={"text": "hi"})
    assert response.status_code == 400
    assert "preset" in response.json()["detail"]


def test_unknown_preset_lists_alternatives(client: TestClient):
    response = client.post("/v1/predict", json={"text": "hi", "preset": "nope"})
    assert response.status_code == 400
    assert "triage" in response.json()["detail"]


def test_get_predict(client: TestClient):
    response = client.get(
        "/v1/predict",
        params={"text": "urgent outage", "preset": PRESET, "flat": "true"},
    )
    assert response.status_code == 200
    assert response.json()["flat"]["intent"] == "refund"


def test_get_predict_with_questions_json(client: TestClient):
    questions = '{"a": {"type": "noul", "instructions": "Is it urgent?"}}'
    response = client.get(
        "/v1/predict", params={"text": "soon please", "questions": questions}
    )
    assert response.status_code == 200
    assert response.json()["answers"]["a"]["noul"] == 0.42


def test_get_predict_rejects_invalid_questions_json(client: TestClient):
    response = client.get(
        "/v1/predict", params={"text": "x", "questions": "{not json"}
    )
    assert response.status_code == 400


def test_503_before_model_load():
    # No lifespan run: agent stays None.
    app = create_app(Settings())
    response = TestClient(app).post("/v1/predict", json={"text": "x", "preset": PRESET})
    assert response.status_code == 503
