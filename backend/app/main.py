from __future__ import annotations

import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

from fastapi import FastAPI, File, Form, HTTPException, Query, UploadFile  # noqa: E402
from fastapi.middleware.cors import CORSMiddleware  # noqa: E402
from fastapi.responses import JSONResponse  # noqa: E402
from pydantic import BaseModel  # noqa: E402

from . import db, vision  # noqa: E402
from .bases import BASE_BUILDERS, all_bases, get_base  # noqa: E402
from .generator import BodyPlan, generate, keyword_plan  # noqa: E402
from .search import search  # noqa: E402

MAX_UPLOAD = 5 * 1024 * 1024  # Claude's per-image limit
USE_CLAUDE_FOR_TEXT = os.environ.get("ORIGAMI_CLAUDE_FOR_TEXT", "1") == "1"

app = FastAPI(title="Origami Pattern Studio API", version="0.1.0")
app.add_middleware(
    CORSMiddleware,
    allow_origins=os.environ.get("CORS_ORIGINS", "http://localhost:3000").split(","),
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)


class GenerateRequest(BaseModel):
    query: str


def _respond(plan: BodyPlan, warning: Optional[str] = None) -> dict:
    with db.connect() as conn:
        models = db.all_models(conn)
    matches = search(models, plan.subject, limit=12, extra_terms=plan.search_terms)
    return {
        "plan": plan.model_dump(),
        "generated": generate(plan),
        "matches": matches,
        "warning": warning,
    }


@app.get("/api/health")
def health() -> dict:
    with db.connect() as conn:
        count = conn.execute("SELECT COUNT(*) FROM models").fetchone()[0]
    return {"ok": True, "catalog_count": count, "vision": vision.available(),
            "vision_provider": vision.provider()}


@app.get("/api/search")
def search_catalog(q: str = Query(..., min_length=1, max_length=200), limit: int = Query(12, ge=1, le=50)) -> dict:
    with db.connect() as conn:
        models = db.all_models(conn)
    return {"query": q, "results": search(models, q, limit=limit)}


@app.post("/api/generate")
def generate_from_text(req: GenerateRequest) -> dict:
    query = req.query.strip()
    if not query or len(query) > 200:
        raise HTTPException(422, "Describe the object in 1-200 characters.")
    warning = None
    plan = keyword_plan(query)
    if USE_CLAUDE_FOR_TEXT and vision.available():
        try:
            plan = vision.plan_from_text(query)
        except vision.VisionUnavailable as e:
            warning = f"{e} Used keyword matching instead."
    return _respond(plan, warning)


@app.post("/api/generate/photo")
async def generate_from_photo(file: UploadFile = File(...), hint: str = Form("")) -> dict:
    data = await file.read()
    if len(data) > MAX_UPLOAD:
        raise HTTPException(413, "Image is larger than 5 MB; resize it and try again.")
    if not data:
        raise HTTPException(422, "The uploaded file is empty.")
    try:
        plan = vision.plan_from_image(data, file.content_type or "", hint[:200])
    except vision.VisionUnavailable as e:
        if hint.strip():
            return _respond(keyword_plan(hint), f"{e} Used your description instead.")
        raise HTTPException(503, str(e))
    return _respond(plan)


@app.get("/api/bases")
def list_bases() -> dict:
    return {"bases": all_bases()}


@app.get("/api/bases/{base_id}")
def base_detail(base_id: str) -> dict:
    if base_id not in BASE_BUILDERS:
        raise HTTPException(404, "Unknown base.")
    return get_base(base_id)


@app.get("/api/bases/{base_id}/fold")
def base_fold(base_id: str) -> JSONResponse:
    if base_id not in BASE_BUILDERS:
        raise HTTPException(404, "Unknown base.")
    return JSONResponse(
        get_base(base_id)["fold"],
        headers={"Content-Disposition": f'attachment; filename="{base_id}-base.fold"'},
    )


@app.get("/api/models/{model_id}")
def model_detail(model_id: int) -> dict:
    with db.connect() as conn:
        model = db.get_model(conn, model_id)
    if not model:
        raise HTTPException(404, "Model not found.")
    return model
