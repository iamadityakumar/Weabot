import uuid
import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional, List, Dict, Any
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, Field
from langchain_core.messages import HumanMessage

from backend.config import settings
from backend.graph import safety_advisor_graph
from backend.nodes.weather import get_sops_engine
from backend.nodes.location import get_weather_client
from backend.llm_factory import llm_factory

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
    model: Optional[str] = Field(None, description="Requested LLM model name")

class ChatResponse(BaseModel):
    thread_id: str
    response: str
    sop_citations: List[str]
    weather_data: Optional[Dict[str, Any]] = None
    session_facts: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None
    verdict: Optional[Dict[str, Any]] = None
    model_used: Optional[str] = None

@app.get("/api/health")
async def health_check():
    """System health check and status."""
    engine = get_sops_engine()
    models = llm_factory.get_available_models()
    return {
        "status": "healthy",
        "llm_provider": settings.LLM_PROVIDER,
        "loaded_sops_count": len(engine.sops),
        "required_weather_fields": engine.get_required_weather_fields(),
        "available_models": models
    }

@app.get("/api/models")
async def get_models():
    """
    List all LLM models currently available to the application,
    strictly verified by active API keys in the environment.
    """
    models = llm_factory.get_available_models()
    return {
        "count": len(models),
        "models": models
    }

@app.get("/api/sops")
async def list_sops():
    """List all currently active Standard Operating Procedures."""
    engine = get_sops_engine()
    return {
        "count": len(engine.sops),
        "sops": list(engine.sops.values())
    }

class SOPPayload(BaseModel):
    id: str = Field(..., description="Unique SOP identifier, e.g. SOP-013")
    title: str = Field(..., description="Short descriptive title")
    category: str = Field(..., description="Category of hazard")
    severity: str = Field(..., description="Severity level: high, moderate, or low")
    applies_to: List[str] = Field(default_factory=list, description="Activities this SOP applies to")
    conditions: Dict[str, Any] = Field(default_factory=dict, description="Threshold conditions for weather variables")
    advice: str = Field(..., description="Guidance and action items to return")
    override_keywords: Optional[List[str]] = None
    override_priority: Optional[int] = None

@app.post("/api/sops")
async def create_or_update_sop(sop: SOPPayload):
    """Create a new SOP or update an existing one, saving to disk and hot-reloading."""
    import yaml
    engine = get_sops_engine()
    clean_id = sop.id.strip().upper()
    if not clean_id.startswith("SOP-"):
        clean_id = f"SOP-{clean_id}"

    data = {
        "id": clean_id,
        "title": sop.title.strip(),
        "category": sop.category.strip(),
        "severity": sop.severity.strip().lower(),
        "applies_to": sop.applies_to,
        "conditions": sop.conditions,
        "advice": sop.advice.strip(),
    }
    if sop.override_keywords:
        data["override_keywords"] = sop.override_keywords
    if sop.override_priority is not None:
        data["override_priority"] = sop.override_priority

    file_path = settings.SOPS_DIR / f"{clean_id}.yaml"
    try:
        with open(file_path, "w", encoding="utf-8") as f:
            yaml.dump(data, f, sort_keys=False, default_flow_style=False, allow_unicode=True)
        count = engine.reload()
        return {
            "status": "success",
            "message": f"Successfully saved {clean_id}",
            "count": count,
            "sop": data
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to write SOP file: {str(e)}")

@app.put("/api/sops/{sop_id}")
async def update_sop_endpoint(sop_id: str, sop: SOPPayload):
    """Update an existing SOP."""
    return await create_or_update_sop(sop)

@app.delete("/api/sops/{sop_id}")
async def delete_sop(sop_id: str):
    """Delete an SOP file from disk and hot-reload."""
    engine = get_sops_engine()
    clean_id = sop_id.strip().upper()
    file_path = settings.SOPS_DIR / f"{clean_id}.yaml"
    alt_path = settings.SOPS_DIR / f"{clean_id}.yml"

    target_file = file_path if file_path.exists() else (alt_path if alt_path.exists() else None)
    if not target_file:
        raise HTTPException(status_code=404, detail=f"SOP {sop_id} not found on disk.")

    try:
        target_file.unlink()
        count = engine.reload()
        return {
            "status": "success",
            "message": f"Successfully deleted {clean_id}",
            "count": count
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to delete SOP: {str(e)}")

@app.post("/api/sops/reload")
async def reload_sops(request: Request):
    """
    Hot-reload all SOP YAML policies from disk without rebooting.
    Protected by X-Admin-Key header if ADMIN_API_KEY is configured.
    Enforces fail-closed protection: returns HTTP 422 if canary check fails,
    reporting the error while confirming last-good policy set remains active.
    """
    if settings.ADMIN_API_KEY:
        admin_key = request.headers.get("X-Admin-Key")
        if admin_key != settings.ADMIN_API_KEY:
            raise HTTPException(status_code=401, detail="Unauthorized: Invalid or missing X-Admin-Key header.")

    engine = get_sops_engine()
    count = engine.reload()

    if getattr(engine, "last_reload_error", None):
        raise HTTPException(
            status_code=422,
            detail={
                "status": "canary_validation_failed",
                "message": engine.last_reload_error,
                "active_sops_count": count,
                "policy_state": "preserved_last_good_set",
                "skipped_files": getattr(engine, "skipped_files", [])
            }
        )

    return {
        "status": "success",
        "message": f"Successfully reloaded {count} SOPs from sops directory",
        "count": count,
        "skipped_files": getattr(engine, "skipped_files", []),
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
    requested_model = request.model or settings.GEMINI_MODEL

    try:
        initial_input = {
            "messages": [HumanMessage(content=request.message.strip())],
            "requested_model": requested_model,
        }
        result = await safety_advisor_graph.ainvoke(initial_input, config=config)

        final_response = result.get("final_response") or "No response could be generated."
        citations = result.get("sop_citations") or []
        weather_data = result.get("weather_data")
        session_facts = result.get("session_facts")
        err_msg = result.get("error_message")
        verdict = result.get("verdict")

        # Resolve friendly model name for client display
        req_norm = (requested_model or "").lower()
        if "qwen" in req_norm:
            display_model_name = "Qwen 3.8 27B (Groq)"
        elif "120b" in req_norm:
            display_model_name = "GPT-OSS 120B (Groq)"
        elif "20b" in req_norm:
            display_model_name = "GPT-OSS 20B (Groq)"
        elif "pro" in req_norm:
            display_model_name = "Gemini 1.5 Pro"
        elif "gemini" in req_norm or "flash" in req_norm or "3.8" in req_norm:
            display_model_name = "Gemini 3.8 Flash"
        elif "deterministic" in req_norm:
            display_model_name = "Open-Meteo Deterministic"
        else:
            display_model_name = requested_model

        # Auto-persist conversation history to enable unique shareable URLs
        try:
            sessions_dir = settings.BASE_DIR / "sessions"
            sessions_dir.mkdir(parents=True, exist_ok=True)
            session_file = sessions_dir / f"{thread_id}.json"
            
            existing_data = {"thread_id": thread_id, "messages": []}
            if session_file.exists():
                try:
                    with open(session_file, "r", encoding="utf-8") as sf:
                        existing_data = json.load(sf)
                except Exception:
                    pass

            now_iso = datetime.now(timezone.utc).isoformat()
            user_msg = {
                "id": f"msg-{int(datetime.now(timezone.utc).timestamp() * 1000)}",
                "sender": "user",
                "text": request.message.strip(),
                "timestamp": now_iso
            }
            bot_msg = {
                "id": f"msg-{int(datetime.now(timezone.utc).timestamp() * 1000) + 1}",
                "sender": "advisor",
                "text": final_response,
                "sopCitations": citations,
                "weatherData": weather_data,
                "sessionFacts": session_facts,
                "verdict": verdict,
                "modelUsed": display_model_name,
                "timestamp": now_iso
            }
            existing_data.setdefault("messages", []).extend([user_msg, bot_msg])
            existing_data["updated_at"] = now_iso
            existing_data["model"] = display_model_name
            if "title" not in existing_data:
                clean_text = request.message.strip()
                existing_data["title"] = clean_text[:42] + ("..." if len(clean_text) > 42 else "")

            with open(session_file, "w", encoding="utf-8") as sf:
                json.dump(existing_data, sf, indent=2, ensure_ascii=False)
        except Exception as persist_err:
            print(f"[Main] Warning: Session persistence error ({persist_err})")

        return ChatResponse(
            thread_id=thread_id,
            response=final_response,
            sop_citations=citations,
            weather_data=weather_data,
            session_facts=session_facts,
            error_message=err_msg,
            verdict=verdict,
            model_used=display_model_name
        )

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Graph execution failed: {str(e)}")

@app.get("/api/chat/{thread_id}")
async def get_chat_session(thread_id: str):
    """
    Retrieve full conversation history for a unique chat session.
    Enables shareable chat links across users and browsers.
    """
    sessions_dir = settings.BASE_DIR / "sessions"
    session_file = sessions_dir / f"{thread_id}.json"
    if not session_file.exists():
        raise HTTPException(status_code=404, detail=f"Chat session '{thread_id}' not found.")
    try:
        with open(session_file, "r", encoding="utf-8") as sf:
            return json.load(sf)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to read session: {str(e)}")

class SessionSyncPayload(BaseModel):
    thread_id: str
    title: Optional[str] = None
    model: Optional[str] = None
    messages: List[Dict[str, Any]] = Field(default_factory=list)

@app.post("/api/chat/sync")
async def sync_chat_session(payload: SessionSyncPayload):
    """
    Sync complete session state from frontend for persistent sharing.
    """
    sessions_dir = settings.BASE_DIR / "sessions"
    sessions_dir.mkdir(parents=True, exist_ok=True)
    session_file = sessions_dir / f"{payload.thread_id}.json"
    now_iso = datetime.now(timezone.utc).isoformat()
    data = {
        "thread_id": payload.thread_id,
        "title": payload.title or "Outdoor Safety Advisory",
        "model": payload.model or settings.GEMINI_MODEL,
        "updated_at": now_iso,
        "messages": payload.messages
    }
    try:
        with open(session_file, "w", encoding="utf-8") as sf:
            json.dump(data, sf, indent=2, ensure_ascii=False)
        return {"status": "success", "thread_id": payload.thread_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to sync session: {str(e)}")

# Mount static frontend build if it exists
frontend_dist = Path(__file__).resolve().parent.parent / "frontend" / "dist"
if frontend_dist.exists():
    app.mount("/", StaticFiles(directory=str(frontend_dist), html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host=settings.HOST, port=settings.PORT, reload=settings.DEBUG)
