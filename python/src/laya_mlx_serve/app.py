"""FastAPI application exposing laya-mlx typed decisions over HTTP."""

from __future__ import annotations

import json
from contextlib import asynccontextmanager
from typing import Any, Dict, Optional

import laya_mlx as laya
from fastapi import APIRouter, Depends, FastAPI, Header, HTTPException, Query
from pydantic import BaseModel

from .settings import Settings

PRESETS: Dict[str, Any] = {
    "triage": laya.triage_questions,
    "email": laya.email_questions,
    "guard": laya.guard_questions,
    "moderation": laya.moderation_questions,
    "router": laya.router_questions,
}


def resolve_questions(
    questions: Optional[Dict[str, Any]], preset: Optional[str]
) -> Dict[str, Any]:
    if questions:
        return questions
    if preset:
        if preset not in PRESETS:
            raise HTTPException(
                status_code=400,
                detail=f"Unknown preset {preset!r}; available: {', '.join(PRESETS)}",
            )
        return PRESETS[preset]()
    raise HTTPException(
        status_code=400,
        detail="Provide 'questions' or a 'preset' (" + ", ".join(PRESETS) + ")",
    )


def _flatten(answers: Dict[str, Any]) -> Dict[str, Any]:
    flat: Dict[str, Any] = {}
    for qid, answer in answers.items():
        if "choice" in answer:
            flat[qid] = answer["choice"]
        elif "score" in answer:
            flat[qid] = answer["score"]
        elif "noul" in answer:
            flat[qid] = answer["noul"]
    return flat


class PredictRequest(BaseModel):
    text: str
    questions: Optional[Dict[str, Any]] = None
    preset: Optional[str] = None
    flat: bool = False
    model: Optional[str] = None


def create_app(settings: Optional[Settings] = None) -> FastAPI:
    """Build the FastAPI app. The model loads when the app starts (lifespan)."""
    settings = settings or Settings.from_env()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        print(f"Loading {settings.model_id} into MLX memory...", flush=True)
        app.state.agent = laya.load(settings.model_id, dtype=settings.dtype)
        print("Model ready for inference.", flush=True)
        yield
        app.state.agent = None

    app = FastAPI(title="Laya MLX API", version=settings.model_id, lifespan=lifespan)
    app.state.settings = settings
    app.state.agent = None

    async def require_api_key(
        x_api_key: Optional[str] = Header(default=None),
        authorization: Optional[str] = Header(default=None),
    ):
        if settings.api_key is None:
            return
        bearer = authorization[len("Bearer"):].strip() if authorization else None
        if x_api_key == settings.api_key or bearer == settings.api_key:
            return
        raise HTTPException(status_code=401, detail="Missing or invalid API key")

    def get_agent():
        if app.state.agent is None:
            raise HTTPException(status_code=503, detail="Model not loaded")
        return app.state.agent

    def run_predict(
        text: str,
        questions: Dict[str, Any],
        flat: bool,
        model_id: Optional[str] = None,
    ) -> Dict[str, Any]:
        result = dict(get_agent().predict(text, questions), model=model_id or settings.model_id)
        if flat:
            result = dict(result, flat=_flatten(result["answers"]))
        return result

    @app.get("/health")
    def health():
        return {
            "status": "ok",
            "model": settings.model_id,
            "ready": app.state.agent is not None,
        }

    api = APIRouter(prefix="/v1", dependencies=[Depends(require_api_key)])

    @api.get("/presets")
    def list_presets():
        return {"presets": {name: fn() for name, fn in PRESETS.items()}}

    @api.post("/predict")
    def predict_post(payload: PredictRequest):
        questions = resolve_questions(payload.questions, payload.preset)
        try:
            return run_predict(payload.text, questions, payload.flat, payload.model)
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    @api.get("/predict")
    def predict_get(
        text: str = Query(..., description="Input text to classify"),
        preset: Optional[str] = Query(default=None, description="Question preset name"),
        questions: Optional[str] = Query(
            default=None, description="Raw questions as a JSON string"
        ),
        flat: bool = Query(
            default=False, description="Add a flat answer map for easy templating"
        ),
    ):
        parsed = None
        if questions:
            try:
                parsed = json.loads(questions)
            except ValueError:
                raise HTTPException(status_code=400, detail="'questions' must be valid JSON")
        try:
            return run_predict(text, resolve_questions(parsed, preset), flat)
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(status_code=400, detail=str(e))

    app.include_router(api)
    return app


#: Env-configured instance: ``uvicorn laya_mlx_serve:app``.
app = create_app()
