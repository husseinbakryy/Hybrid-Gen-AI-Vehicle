from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from typing import Any, Dict
from recommender import generate_recommendation
import uvicorn

app = FastAPI()

class TripInput(BaseModel):
    distance_km: float = Field(..., gt=0)
    battery_soc_start: float = Field(..., ge=0, le=100)
    road_type: str
    traffic_level: str

class TripRecommendationRequest(BaseModel):
    trip_input: TripInput
    user_context: Dict[str, Any] = Field(default_factory=dict)

@app.post("/api/trip/recommendation")
async def recommend_trip(request: TripRecommendationRequest):
    try:
        # Mock ML inference - replace with your actual model logic
        ml_results = {"recommended_mode": "ev", "cost": 1.50}
        
        # Call the recommender using .model_dump() (Pydantic v2 standard)
        advice = generate_recommendation(
            trip_input=request.trip_input.model_dump(),
            ml_output=ml_results,
            user_context=request.user_context
        )
        
        return {"ml_results": ml_results, "ai_advice": advice}
    except Exception as e:
        # This will give you the specific error in the terminal/response
        raise HTTPException(status_code=500, detail=str(e))
if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)