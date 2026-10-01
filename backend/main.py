import uuid
from pathlib import Path
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from langchain_core.messages import HumanMessage

from backend.config import settings
from backend.graph import safety_advisor_graph
from backend.nodes.weather import get_sops_engine
from backend.nodes.location import get_weather_client

app = FastAPI(
    title="Outdoor Activity Safety Advisor API",
    description="Deterministic LangGraph-backed safety advisor with live Open-Meteo weather and versioned SOP policies.",
    version="1.0.0"
)

# CORS setup
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    message: str = Field(..., description="The user query or statement")
    thread_id: Optional[str] = Field(None, description="UUID session identifier for LangGraph MemorySaver")

class ChatResponse(BaseModel):
    thread_id: str
    response: str
    sop_citations: List[str]
    weather_data: Optional[Dict[str, Any]] = None
    session_facts: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None

@app.get("/api/health")
async def health_check():
    """System health check and status."""
    engine = get_sops_engine()
    return {
        "status": "healthy",
        "llm_provider": settings.LLM_PROVIDER,
        "loaded_sops_count": len(engine.sops),
        "required_weather_fields": engine.get_required_weather_fields()
    }

@app.get("/api/sops")
async def list_sops():
    """List all currently active Standard Operating Procedures."""
    engine = get_sops_engine()
    return {
        "count": len(engine.sops),
        "sops": list(engine.sops.values())
    }

@app.post("/api/sops/reload")
async def reload_sops():
    """Hot-reload all SOP YAML policies from disk without rebooting."""
    engine = get_sops_engine()
    count = engine.reload()
    return {
        "status": "success",
        "message": f"Successfully reloaded {count} SOPs from {engine.sops_dir}",
        "count": count,
        "required_weather_fields": engine.get_required_weather_fields()
    }

@app.get("/api/weather")
async def get_live_weather(city: Optional[str] = "Bhopal", lat: Optional[float] = None, lon: Optional[float] = None):
    """Retrieve live weather metrics for a given city or coordinates."""
    client = get_weather_client()
    engine = get_sops_engine()
    fields = engine.get_required_weather_fields()

    try:
        if lat is None or lon is None:
            if not city:
                raise HTTPException(status_code=400, detail="Either 'city' or 'lat' and 'lon' must be provided.")
            geo = await client.geocode(city)
            lat = geo["latitude"]
            lon = geo["longitude"]
            resolved_city = geo["name"]
        else:
            resolved_city = f"({lat}, {lon})"

        weather = await client.fetch_weather(lat, lon, fields)
        return {
            "location": resolved_city,
            "latitude": lat,
            "longitude": lon,
            "weather": weather
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/api/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    """
    Main conversational endpoint:
    Runs user query through the LangGraph safety advisor state machine.
    """
    if not request.message or not request.message.strip():
        raise HTTPException(status_code=400, detail="Message cannot be empty.")

    thread_id = request.thread_id or str(uuid.uuid4())
    config = {"configurable": {"thread_id": thread_id}}

    try:
        initial_input = {
            "messages": [HumanMessage(content=request.message.strip())]
        }
        result = await safety_advisor_graph.ainvoke(initial_input, config=config)

        return ChatResponse(
            thread_id=thread_id,
            response=result.get("final_response") or "No response could be generated.",
            sop_citations=result.get("sop_citations") or [],
            weather_data=result.get("weather_data"),
            session_facts=result.get("session_facts"),
            error_message=result.get("error_message")
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Graph execution failed: {str(e)}")

# Mount static frontend build if it exists
frontend_dist = Path(__file__).resolve().parent.parent / "frontend" / "dist"
if frontend_dist.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dist), html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host=settings.HOST, port=settings.PORT, reload=settings.DEBUG)
