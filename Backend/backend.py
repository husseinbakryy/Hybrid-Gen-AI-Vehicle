from datetime import datetime, timezone
from pathlib import Path
from typing import Any
import sys

from fastapi import FastAPI, HTTPException
from dotenv import load_dotenv
from pydantic import BaseModel, Field


REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = Path(__file__).resolve().parent
load_dotenv(BACKEND_DIR / ".env")

MODELS_DIR = REPO_ROOT / "Models"
if str(MODELS_DIR) not in sys.path:
	sys.path.insert(0, str(MODELS_DIR))

from pipeline.config import FEATURES
from pipeline.inference import predict_trip_structured, load_assets
from recommender import generate_recommendation


class TripRecommendationRequest(BaseModel):
	trip_input: dict[str, Any] = Field(
		...,
		description="Raw trip features coming from dashboard form or client-side mapping.",
	)
	user_context: dict[str, Any] = Field(
		default_factory=dict,
		description="Optional user preferences, constraints, and session metadata.",
	)


class TripRecommendationResponse(BaseModel):
	request_id: str
	timestamp_utc: str
	input: dict[str, Any]
	ml_output: dict[str, Any]
	genai_recommendation: dict[str, Any]


app = FastAPI(
	title="Hybrid Vehicle Recommendation API",
	version="0.1.0",
	description="Accepts dashboard trip inputs, runs ML models, and returns ML + GenAI recommendations.",
)


_ASSETS: tuple[Any, dict[str, Any]] | None = None


def _get_assets():
	global _ASSETS
	if _ASSETS is None:
		_ASSETS = load_assets()
	return _ASSETS


@app.get("/health")
def health():
	return {"status": "ok"}


@app.post("/api/trip/recommendation", response_model=TripRecommendationResponse)
def recommend_trip(request: TripRecommendationRequest):
	missing_features = [feature for feature in FEATURES if feature not in request.trip_input]
	if missing_features:
		raise HTTPException(
			status_code=400,
			detail={
				"message": "Missing required trip_input features.",
				"missing_features": missing_features,
			},
		)

	try:
		preprocessor, models = _get_assets()
		ml_bundle = predict_trip_structured(
			request.trip_input,
			preprocessor=preprocessor,
			models=models,
		)
		recommendation = generate_recommendation(
			trip_input=request.trip_input,
			ml_output=ml_bundle["raw"],
			user_context=request.user_context,
		)
	except FileNotFoundError as exc:
		raise HTTPException(status_code=500, detail=f"Model artifacts unavailable: {exc}") from exc
	except ValueError as exc:
		raise HTTPException(status_code=400, detail=str(exc)) from exc
	except Exception as exc:
		raise HTTPException(status_code=500, detail=f"Unexpected API error: {exc}") from exc

	request_id = datetime.now(timezone.utc).strftime("REQ-%Y%m%d%H%M%S%f")

	return TripRecommendationResponse(
		request_id=request_id,
		timestamp_utc=datetime.now(timezone.utc).isoformat(),
		input=request.trip_input,
		ml_output={
			"raw": ml_bundle["raw"],
			"formatted": ml_bundle["formatted"],
		},
		genai_recommendation=recommendation,
	)

