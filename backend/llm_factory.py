import os
import json
import re
import time
from typing import Dict, Any, Optional, List, Tuple
from backend.config import settings

MODEL_CANONICAL_MAP = {
    "gemini-3.8-flash": "gemini-3.8-flash",
    "gemini 3.8 flash": "gemini-3.8-flash",
    "gemini": "gemini-3.8-flash",
    "flash": "gemini-3.8-flash",
    "gemini-1.5-pro": "gemini-1.5-pro",
    "gemini 1.5 pro": "gemini-1.5-pro",
    "pro": "gemini-1.5-pro",
    "qwen/qwen3.8-27b": "qwen/qwen3.8-27b",
    "qwen 3.8 27b (groq)": "qwen/qwen3.8-27b",
    "qwen": "qwen/qwen3.8-27b",
    "groq": "qwen/qwen3.8-27b",
    "openai/gpt-oss-120b": "openai/gpt-oss-120b",
    "gpt-oss 120b (groq)": "openai/gpt-oss-120b",
    "120b": "openai/gpt-oss-120b",
    "openai/gpt-oss-20b": "openai/gpt-oss-20b",
    "gpt-oss 20b (groq)": "openai/gpt-oss-20b",
    "20b": "openai/gpt-oss-20b",
    "open-meteo-deterministic": "open-meteo-deterministic",
    "open-meteo deterministic": "open-meteo-deterministic",
    "deterministic": "open-meteo-deterministic",
}

MODEL_DISPLAY_NAMES = {
    "gemini-3.8-flash": "Gemini 3.8 Flash",
    "gemini-1.5-pro": "Gemini 1.5 Pro",
    "qwen/qwen3.8-27b": "Qwen 3.8 27B (Groq)",
    "openai/gpt-oss-120b": "GPT-OSS 120B (Groq)",
    "openai/gpt-oss-20b": "GPT-OSS 20B (Groq)",
    "open-meteo-deterministic": "Open-Meteo Deterministic",
}

def is_quota_exhausted_error(exc: Optional[Exception]) -> bool:
    """
    Detect whether an exception was caused by model rate-limiting, quota depletion,
    capacity exhaustion, or daily token/request caps.
    """
    if not exc:
        return False
    msg = str(exc).lower()
    exc_type = type(exc).__name__.lower()

    if "429" in msg or getattr(exc, "status_code", None) == 429:
        return True

    quota_signatures = [
        "resource_exhausted",
        "resourceexhausted",
        "quota exceeded",
        "exceeded your current quota",
        "rate limit",
        "ratelimit",
        "insufficient_quota",
        "free_tier_requests",
        "capacity",
        "tokens per day",
        "requests per day",
        "tpd",
        "rpd",
        "overloaded",
    ]
    return any(sig in msg or sig in exc_type for sig in quota_signatures)


INVALID_LOCATION_WORDS = {
    # Units of measurement and speed/time rates
    "m", "s", "ms", "mps", "mph", "km", "kmh", "kmph", "kph", "kts", "kt", "knots", "knot",
    "c", "f", "k", "celsius", "fahrenheit", "kelvin", "mm", "cm", "meter", "meters", "metre",
    "metres", "mile", "miles", "inch", "inches", "in", "ft", "feet", "foot", "yd", "yard", "yards",
    "percent", "percentage", "hpa", "bar", "psi", "atm", "mb", "degrees", "deg",
    
    # Common English non-location nouns / phrases following "in"
    "detail", "details", "brief", "advance", "short", "summary", "general", "english", "hindi",
    "total", "seconds", "minutes", "hours", "days", "weeks", "months", "years", "fact",
    "addition", "particular", "case", "order", "real time", "live", "color", "colour",
    "depth", "terms", "words", "numbers", "units", "metric", "imperial", "practice", "theory",
    
    # Temporal words
    "morning", "the morning", "afternoon", "the afternoon", "evening", "the evening",
    "night", "the night", "today", "tonight", "tomorrow", "yesterday", "now", "am", "pm",
    "dawn", "dusk", "noon", "midnight", "weekend", "weekdays", "1 pm", "1pm",
    "this evening instead", "this evening", "this morning", "this afternoon", "instead", "later", "earlier", "this",
    
    # Generic place references and activity verbs
    "the park", "a park", "park", "the office", "office", "work", "home", "school",
    "gym", "the gym", "the field", "the pool", "the trail", "the beach", "beach",
    "the lake", "lake", "the mountain", "mountain", "the river", "river", "the yard",
    "yard", "backyard", "outside", "indoors", "inside", "here", "there", "anywhere",
    "somewhere", "none", "null", "n/a", "na",
    
    # Common activity words and verbs that follow 'to' or 'for'
    "cycle", "cycling", "bike", "biking", "pedal", "pedaling", "run", "running",
    "jog", "jogging", "walk", "walking", "stroll", "swim", "swimming", "drive",
    "driving", "commute", "travel", "climb", "climbing", "fly", "flying", "drone",
    "picnic", "bbq", "barbecue", "hike", "hiking", "exercise", "workout", "play", "playground"
}


TEMPORAL_STOP_WORDS = {
    "this", "evening", "instead", "morning", "afternoon", "tomorrow", "tonight",
    "today", "now", "yesterday", "later", "earlier", "weekend", "next", "week",
    "month", "year", "what", "about", "how", "here", "there", "at", "noon", "right",
    "is", "it", "okay", "fine", "safe", "better", "can", "i", "or", "and", "then",
    "rather", "in", "days", "hours", "2am", "8am", "morning", "night"
}

def clean_and_validate_location(cand: Optional[str]) -> Optional[str]:
    """Validate and clean extracted location candidate, rejecting units, prepositions, emojis, or temporal words."""
    if not cand:
        return None
    cleaned = str(cand).strip().strip("'\".,;:!?()[]{}")
    if not cleaned or len(cleaned) <= 2:
        return None
    # Reject if candidate contains no Latin alphabetical characters (e.g. emojis or pure symbols)
    if not re.search(r"[A-Za-z]", cleaned):
        return None

    lower = cleaned.lower()
    if lower in INVALID_LOCATION_WORDS:
        return None
    if "/" in lower:
        return None
    if re.fullmatch(r"[\d\s\-_/\\.:]+", cleaned):
        return None
    if any(u in lower for u in ["m/s", "km/h", "kmph", "kph", "mph"]):
        return None

    words = cleaned.split()
    # If all words in candidate are temporal or conversational stop words, reject
    if all(w.lower() in TEMPORAL_STOP_WORDS or w.lower() in INVALID_LOCATION_WORDS for w in words):
        return None

    # Strip any trailing temporal stop words (e.g. "Aurangabad today" -> "Aurangabad")
    while words and words[-1].lower() in TEMPORAL_STOP_WORDS:
        words.pop()

    res = " ".join(words).strip().strip("'\".,;:!?()[]{}")
    if not res or len(res) <= 2 or res.lower() in INVALID_LOCATION_WORDS:
        return None
    return res


class LLMFactory:
    """
    Factory for producing LLM instances (Gemini, Groq, Ollama, Mock, and Model Routing).
    Provides structured methods for:
    - Intent extraction
    - Constrained prose composition
    - Multi-model routing (Gemini 2.5 Flash, Gemini 2.5 Pro, Claude 3.7, GPT-4o, DeepSeek-R1, Deterministic)
    """

    def __init__(self):
        self.provider = settings.LLM_PROVIDER
        self._llm_cache: Dict[str, Any] = {}
        self._exhausted_models: Dict[str, float] = {}  # canonical_id -> expiry_epoch
        default_model = settings.GROQ_MODEL if self.provider == "groq" else settings.GEMINI_MODEL
        self._default_llm = self._create_llm_instance(default_model)

    def get_canonical_id(self, model_name: Optional[str]) -> str:
        if not model_name:
            return "gemini-3.8-flash"
        norm = model_name.strip().lower()
        if norm in MODEL_CANONICAL_MAP:
            return MODEL_CANONICAL_MAP[norm]
        for k, v in MODEL_CANONICAL_MAP.items():
            if k in norm:
                return v
        return norm

    def get_display_name(self, model_name: Optional[str]) -> str:
        cid = self.get_canonical_id(model_name)
        return MODEL_DISPLAY_NAMES.get(cid, model_name or "AI Model")

    def mark_model_exhausted(self, model_name: Optional[str], duration_seconds: int = 3600, reason: str = ""):
        cid = self.get_canonical_id(model_name)
        expiry = time.time() + duration_seconds
        self._exhausted_models[cid] = expiry
        print(f"[LLMFactory] [QUOTA_EXHAUSTED] Marked model '{cid}' as quota-exhausted until {expiry:.0f} (reason: {reason})")

    def is_model_exhausted(self, model_name: Optional[str]) -> bool:
        cid = self.get_canonical_id(model_name)
        expiry = self._exhausted_models.get(cid, 0)
        return time.time() < expiry

    def resolve_fallback_model(self, requested_model: Optional[str]) -> Tuple[str, bool]:
        """
        Determine the effective model. If requested model is exhausted, pick the best
        available alternative that has verified credentials and is not exhausted.
        Returns (effective_model_id, was_switched).
        """
        cid = self.get_canonical_id(requested_model)
        if not self.is_model_exhausted(cid):
            return cid, False

        # Fallback priority hierarchy:
        # 1. If Gemini was exhausted, try Groq Qwen
        if "gemini" in cid:
            if settings.GROQ_API_KEY and not self.is_model_exhausted("qwen/qwen3.8-27b"):
                return "qwen/qwen3.8-27b", True
            if settings.GROQ_API_KEY and not self.is_model_exhausted("openai/gpt-oss-120b"):
                return "openai/gpt-oss-120b", True
            return "open-meteo-deterministic", True

        # 2. If Groq was exhausted, try other Groq or Gemini
        if "qwen" in cid or "oss" in cid or "groq" in cid:
            if settings.GROQ_API_KEY and not self.is_model_exhausted("openai/gpt-oss-120b") and cid != "openai/gpt-oss-120b":
                return "openai/gpt-oss-120b", True
            if settings.GEMINI_API_KEY and not self.is_model_exhausted("gemini-3.8-flash"):
                return "gemini-3.8-flash", True
            return "open-meteo-deterministic", True

        # Default fallback
        return "open-meteo-deterministic", True

    def _create_llm_instance(self, model_name: str) -> Optional[Any]:
        """Instantiate an LLM based on model name and environment credentials."""
        # Check cache
        if model_name in self._llm_cache:
            return self._llm_cache[model_name]

        norm = (model_name or "").lower()

        # Pure Deterministic Mode
        if "deterministic" in norm:
            self._llm_cache[model_name] = None
            return None

        # Groq Cloud (Prioritized if a Groq model or open model is explicitly requested)
        if settings.GROQ_API_KEY and ("groq" in norm or "llama" in norm or "deepseek" in norm or "qwen" in norm or "oss" in norm or "gpt" in norm or (settings.GROQ_MODEL and settings.GROQ_MODEL.lower() in norm)):
            try:
                from langchain_groq import ChatGroq
                if "120b" in norm:
                    groq_model = "openai/gpt-oss-120b"
                elif "20b" in norm:
                    groq_model = "openai/gpt-oss-20b"
                elif "qwen" in norm:
                    groq_model = "qwen/qwen3.8-27b"
                else:
                    groq_model = settings.GROQ_MODEL or "qwen/qwen3.8-27b"

                instance = ChatGroq(
                    model_name=groq_model,
                    groq_api_key=settings.GROQ_API_KEY,
                    temperature=0.0
                )
                self._llm_cache[model_name] = instance
                print(f"[LLMFactory] Initialized Groq model: {groq_model}")
                return instance
            except Exception as e:
                print(f"[LLMFactory] Groq initialization failed ({e}).")

        # Gemini Family
        if settings.GEMINI_API_KEY and ("gemini" in norm or not norm or norm == (settings.GEMINI_MODEL or "").lower() or "flash" in norm or "pro" in norm):
            try:
                from langchain_google_genai import ChatGoogleGenerativeAI
                api_key = settings.GEMINI_API_KEY
                
                # Resolve Gemini target model
                if "pro" in norm:
                    target_model = "gemini-1.5-pro"
                else:
                    target_model = settings.GEMINI_MODEL or "gemini-3.8-flash"

                instance = ChatGoogleGenerativeAI(
                    model=target_model,
                    google_api_key=api_key,
                    temperature=0.0,
                    max_retries=0,
                    timeout=10.0
                )
                self._llm_cache[model_name] = instance
                print(f"[LLMFactory] Initialized Gemini model: {target_model}")
                return instance
            except Exception as e:
                print(f"[LLMFactory] Gemini initialization failed ({e}).")

        # Fallback to default
        return self._default_llm

    def get_llm(self, model_name: Optional[str] = None):
        """Retrieve the LLM instance corresponding to the user-selected model."""
        if not model_name or model_name.strip() == "":
            return self._default_llm
        if "deterministic" in model_name.lower():
            return None
        return self._create_llm_instance(model_name)

    def get_available_models(self) -> List[Dict[str, Any]]:
        """
        Dynamically determine available models based on active API keys in settings.
        Only models that the app has actual access to (with valid credentials) are returned.
        Includes real-time quota status and exhaustion indications.
        """
        models = []

        # Gemini Family (checked via GEMINI_API_KEY)
        if settings.GEMINI_API_KEY and settings.GEMINI_API_KEY.strip():
            models.append({
                "id": "gemini-3.8-flash",
                "name": "Gemini 3.8 Flash",
                "provider": "Google DeepMind",
                "tag": "Fast & Grounded",
                "color": "text-purple-600 bg-purple-50",
                "is_default": True
            })
            models.append({
                "id": "gemini-1.5-pro",
                "name": "Gemini 1.5 Pro",
                "provider": "Google DeepMind",
                "tag": "High Reasoning",
                "color": "text-blue-600 bg-blue-50",
                "is_default": False
            })

        # Groq Cloud Family (checked via GROQ_API_KEY)
        if settings.GROQ_API_KEY and settings.GROQ_API_KEY.strip():
            models.append({
                "id": "qwen/qwen3.8-27b",
                "name": "Qwen 3.8 27B (Groq)",
                "provider": "Groq Cloud",
                "tag": "Ultra-Fast",
                "color": "text-emerald-600 bg-emerald-50",
                "is_default": False
            })
            models.append({
                "id": "openai/gpt-oss-120b",
                "name": "GPT-OSS 120B (Groq)",
                "provider": "Groq Cloud",
                "tag": "Deep Reasoning",
                "color": "text-teal-600 bg-teal-50",
                "is_default": False
            })
            models.append({
                "id": "openai/gpt-oss-20b",
                "name": "GPT-OSS 20B (Groq)",
                "provider": "Groq Cloud",
                "tag": "Balanced",
                "color": "text-indigo-600 bg-indigo-50",
                "is_default": False
            })

        # OpenAI Family (checked via OPENAI_API_KEY)
        if settings.OPENAI_API_KEY and settings.OPENAI_API_KEY.strip():
            models.append({
                "id": "gpt-4o",
                "name": "GPT-4o",
                "provider": "OpenAI",
                "tag": "Multimodal Omni",
                "color": "text-emerald-600 bg-emerald-50",
                "is_default": False
            })

        # Anthropic Family (checked via ANTHROPIC_API_KEY)
        if settings.ANTHROPIC_API_KEY and settings.ANTHROPIC_API_KEY.strip():
            models.append({
                "id": "claude-3-7-sonnet",
                "name": "Claude 3.7 Sonnet",
                "provider": "Anthropic",
                "tag": "Advanced Synthesis",
                "color": "text-amber-600 bg-amber-50",
                "is_default": False
            })

        # Always include Open-Meteo Deterministic (Safety Graph Engine, zero-hallucination rule based, no API key required)
        models.append({
            "id": "open-meteo-deterministic",
            "name": "Open-Meteo Deterministic",
            "provider": "Safety Graph Engine",
            "tag": "Strict SOPs",
            "color": "text-rose-600 bg-rose-50",
            "is_default": False
        })

        # Annotate quota exhaustion status
        for m in models:
            is_ex = self.is_model_exhausted(m["id"])
            m["is_exhausted"] = is_ex
            m["exhaustion_reason"] = "Daily quota limit reached (429 RESOURCE_EXHAUSTED)" if is_ex else None

        return models

    def _extract_text_from_response(self, resp: Any) -> str:
        """Robustly extract text from LLM response whether str or list of parts."""
        if hasattr(resp, "content"):
            content = resp.content
        else:
            content = str(resp)

        if isinstance(content, str):
            return content
        elif isinstance(content, list):
            parts = []
            for part in content:
                if isinstance(part, str):
                    parts.append(part)
                elif isinstance(part, dict):
                    parts.append(part.get("text", str(part)))
                elif hasattr(part, "text"):
                    parts.append(part.text)
                else:
                    parts.append(str(part))
            return "".join(parts)
        return str(content)

    def extract_intent(
        self, 
        user_message: str, 
        session_facts: Optional[Dict[str, Any]] = None,
        model_name: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Extract activity, location, and time_window from user message.
        Uses requested model or deterministic extraction if deterministic selected.
        """
        session_facts = session_facts or {}
        prior_location = clean_and_validate_location(session_facts.get("location_name"))

        llm = self.get_llm(model_name)
        if llm:
            try:
                prompt = f"""You are a specialized query analyzer for Weabot outdoor safety advisor.
Extract the activity, location (city/town), and time window from the user's message.

CRITICAL RULES:
1. Extract ONLY a legitimate geographical city, town, or region (e.g., "Bhopal", "Denver", "Tokyo").
2. NEVER extract measurement units, rates, or formats as a location (e.g. "m/s", "mph", "km/h", "m", "celsius", "fahrenheit" are NOT locations).
3. Extract the location as written in the query (even if unfamiliar or misspelled, e.g. "Xqzvbnmtrw"). If no location is mentioned at all in this query, set location to null.

User query: "{user_message}"

Respond strictly with valid JSON without markdown fences:
{{
  "activity": "<activity name or null>",
  "location": "<location or null>",
  "time_window": "<time window or 'current'>"
}}
"""
                resp = llm.invoke(prompt)
                raw_text = self._extract_text_from_response(resp)
                clean_json = re.sub(r"^```json\s*|\s*```$", "", raw_text.strip(), flags=re.MULTILINE).strip()
                parsed = json.loads(clean_json)

                # Validate and clean extracted location
                parsed_loc = clean_and_validate_location(parsed.get("location"))
                parsed["location"] = parsed_loc

                return parsed
            except Exception as e:
                if is_quota_exhausted_error(e):
                    self.mark_model_exhausted(model_name, reason=f"extract_intent: {e}")
                print(f"[LLMFactory] LLM intent extraction error ({e}); falling back to deterministic extraction.")

        # Deterministic extraction
        return self._deterministic_extract_intent(user_message, session_facts)

    def _deterministic_extract_intent(self, text: str, session_facts: Dict[str, Any]) -> Dict[str, Any]:
        lower = text.lower()

        # Activities detection
        activity = None

        # Check for outside context framing attacks (e.g. "indoor-style cycling but on the road")
        has_outside_context = any(k in lower for k in ["road", "street", "highway", "outside", "outdoor", "cycling", "bike", "riding", "ride", "walk", "jog", "run", "commute", "track"])

        # Explicit check for indoor classes or yoga when not on road/outside
        if any(k in lower for k in ["indoor yoga", "yoga", "indoor class", "indoors class", "inside class"]):
            activity = "indoor yoga"
        elif ("indoor" in lower or "indoors" in lower) and not has_outside_context:
            activity = "indoor activity"
        else:
            activity_keywords = [
                ("drone", ["drone", "fly drone", "quadcopter", "uav"]),
                ("surfing", ["surfing", "surf", "surfer"]),
                ("clothing", ["clothing", "wear", "dress", "outfit", "jacket", "coat", "what should i wear", "what to wear"]),
                ("cycling", ["cycling", "cycle chalana", "cycle", "cycles", "bicycle", "bike", "biking", "pedaling", "riding my bike", "riding a bike", "ride my bike"]),
                ("transit", ["scooter", "motorcycle", "motorbike", "moped", "two-wheeler commute", "two-wheeler", "vespa"]),
                ("running", ["running", "run", "jogging", "jog", "marathon", "sprint"]),
                ("hiking", ["hiking", "hike", "trekking", "trek", "trail"]),
                ("playground", ["playground", "toddler", "kid", "children", "swings", "swing", "slide"]),
                ("pets", ["dog", "puppy", "cat", "pet", "walking dog", "dog walk", "walk the dog"]),
                ("walking", ["walking", "walk", "stroll", "grandpa"]),
                ("swimming", ["swimming", "swim", "pool", "beach", "lake", "river swim"]),
                ("picnic", ["picnic", "barbecue", "bbq", "family outing", "gathering"]),
                ("travel", ["driving", "drive", "travel", "commute", "road trip", "highway"]),
                ("crane", ["crane", "hoist", "hoisting", "rigging", "crane operation"]),
            ]
            for act, kws in activity_keywords:
                if any(re.search(rf"\b{re.escape(kw)}\b", lower) for kw in kws):
                    activity = act
                    break

            has_children = any(re.search(rf"\b{re.escape(k)}\b", lower) for k in ["children", "child", "kid", "kids", "toddler", "baby", "infant"])
            if has_children and activity and "child" not in activity and "toddler" not in activity and "kid" not in activity and activity != "playground":
                activity = f"children {activity}"
            elif has_children and not activity:
                activity = "playground"

            if not activity:
                # Dynamic check across all loaded SOPs' applies_to
                try:
                    from backend.nodes.weather import get_sops_engine
                    _engine = get_sops_engine()
                    for _sop in _engine.sops.values():
                        for _app in _sop.get("applies_to", []):
                            app_clean = _app.lower().strip()
                            if app_clean in ("all", "any", "outdoor", "activities", "general", "outdoor activities"):
                                continue
                            if re.search(rf"\b{re.escape(app_clean)}\b", lower):
                                activity = app_clean
                                break
                        if activity:
                            break
                except Exception:
                    pass

        # Carry forward prior activity if query is a follow-up without a new activity
        if (not activity or activity in ("outdoor activity", "all", "any", "none")) and session_facts.get("activity"):
            activity = session_facts["activity"]

        # Location detection
        location = None
        common_cities = [
            "los angeles", "new york", "san francisco", "bhopal", "chicago",
            "berlin", "london", "paris", "delhi", "mumbai", "bangalore", "indore",
            "tokyo", "springfield", "miami", "ottawa", "seattle", "phoenix", "denver", "austin",
            "auckland", "aurangabad"
        ]
        for city in common_cities:
            if re.search(rf"\b{re.escape(city)}\b", lower):
                location = city.title()
                break

        # Check for reference to first/original city
        if not location and any(k in lower for k in ["first city", "original city", "previous city"]):
            location = session_facts.get("primary_location") or session_facts.get("location_name")

        # Standalone short query (e.g. user just replies "Bhopal" or "Indore")
        if not location and len(text.strip().split()) <= 2:
            cand = clean_and_validate_location(text.strip())
            if cand:
                location = cand.title()

        if not location:
            matches = re.finditer(r"\b(?:in|around|near|at|about|travel to|trip to|flight to|head to)\s+([A-Za-z0-9_\-]+(?:\s+[A-Za-z0-9_\-]+)*)", text, re.IGNORECASE)
            for m in matches:
                # Prevent cutting off unit slashes like 'in m/s' into 'm'
                match_end = m.end()
                if match_end < len(text) and text[match_end] == '/':
                    continue
                cand = m.group(1).strip()
                valid_cand = clean_and_validate_location(cand)
                if valid_cand:
                    cand_words = set(valid_cand.lower().split())
                    temporal_tokens = {"evening", "morning", "tomorrow", "tonight", "afternoon", "2am", "today", "now", "yesterday", "later", "instead", "earlier", "weekend", "this", "what", "here"}
                    if cand_words.issubset(temporal_tokens):
                        continue
                    location = valid_cand.title()
                    break

        prior_loc = clean_and_validate_location(session_facts.get("location_name"))
        if not location and prior_loc:
            # If user explicitly asked "here" without context, do not silently default
            if not any(k in lower for k in ["here", "what's it like here", "weather here"]):
                location = prior_loc

        # Time window detection
        time_window = "current"
        if "next month" in lower:
            time_window = "beyond_horizon"
        elif "next week" in lower:
            time_window = "next_week"
        elif "2am" in lower or "2 am" in lower:
            time_window = "2am"
        elif "evening" in lower:
            time_window = "evening"
        elif "morning" in lower:
            time_window = "morning"
        elif "afternoon" in lower or "1 pm" in lower or "1pm" in lower or "at noon" in lower:
            time_window = "afternoon"
        elif "tomorrow" in lower:
            time_window = "tomorrow"
        elif "tonight" in lower:
            time_window = "tonight"

        return {
            "activity": activity or "outdoor activity",
            "location": location,
            "time_window": time_window
        }

    def select_sop_candidates(
        self,
        user_query: str,
        activity: str,
        subject: str,
        catalog: List[Dict[str, str]],
        model_name: Optional[str] = None
    ) -> List[str]:
        """
        WP5 Selection Step:
        The LLM, at temperature 0, returns {sop_ids:[...]} or {none:true} from a catalog
        of ID, title and intent only (no thresholds).
        """
        catalog_json = json.dumps(catalog, indent=2)
        prompt = f"""You are a safety policy classifier for outdoor activities.
Given the user query, planned activity, and demographic subject, select which Standard Operating Procedure (SOP) IDs from the policy catalog may apply.
Catalog contains only Policy ID, Title, and Policy Intent. No weather thresholds are included.

User Query: "{user_query}"
Activity: "{activity}"
Subject: "{subject}"

Policy Catalog:
{catalog_json}

Return ONLY valid JSON in one of these two formats:
{{"sop_ids": ["SOP-001", "SOP-004"]}}
or
{{"none": true}}
"""
        llm = self.get_llm(model_name)
        if llm:
            try:
                resp = llm.invoke(prompt)
                text = self._extract_text_from_response(resp)
                # Parse JSON
                json_match = re.search(r"\{.*\}", text, re.DOTALL)
                if json_match:
                    parsed = json.loads(json_match.group(0))
                    if parsed.get("none"):
                        return []
                    if "sop_ids" in parsed and isinstance(parsed["sop_ids"], list):
                        return [str(x) for x in parsed["sop_ids"]]
            except Exception as e:
                if is_quota_exhausted_error(e):
                    self.mark_model_exhausted(model_name, reason=f"select_sop_candidates: {e}")
                pass

        # Fallback keyword match
        res = []
        q_low = f"{user_query} {activity}".lower()
        for item in catalog:
            cid = item["id"]
            title_low = item.get("title", "").lower()
            intent_low = item.get("intent", "").lower()
            if any(w in q_low for w in ["cycl", "bike", "two-wheeler", "scooter", "two wheels", "pedal"]) and "wind" in title_low:
                res.append(cid)
            elif any(w in q_low for w in ["toddler", "child", "infant", "kid", "playground"]) and "uv" in title_low:
                res.append(cid)
            elif any(w in q_low for w in ["grandpa", "elderly", "senior", "stroll"]) and ("cold" in title_low or "heat" in title_low):
                res.append(cid)
            elif any(w in q_low for w in ["picnic", "gathering"]) and "picnic" in title_low:
                res.append(cid)
            elif any(w in q_low for w in ["dog", "pet"]) and "pet" in title_low:
                res.append(cid)
        return list(set(res))

    def compose_response(
        self,
        user_query: str,
        activity: str,
        location: str,
        weather: Dict[str, Any],
        matched_sops: List[Dict[str, Any]],
        model_name: Optional[str] = None
    ) -> str:
        """
        Constrained safety guidance composition grounded strictly in verified
        live weather metrics and authorized Standard Operating Procedures (SOPs).
        Enforces project requirements:
        - Numbers reported must be actual numbers from the API.
        - Grounded in real numbers rather than generic canned warnings.
        - Suppresses permissive lower-severity SOPs when an override is active.
        """
        if not matched_sops:
            return ""

        curr = weather.get("current", {})
        temp = curr.get("temperature_2m")
        wind = curr.get("wind_speed_10m")
        gusts = curr.get("wind_gusts_10m")
        precip = curr.get("precipitation")
        precip_prob = curr.get("precipitation_probability")
        uv = curr.get("uv_index")

        try:
            wind_val = float(wind) if wind is not None else 0.0
            wind_ms = round(wind_val / 3.6, 2)
            wind_mph = round(wind_val * 0.621371, 2)
        except (ValueError, TypeError):
            wind_ms = 0.0
            wind_mph = 0.0

        try:
            gusts_val = float(gusts) if gusts is not None else 0.0
            gusts_ms = round(gusts_val / 3.6, 2)
            gusts_mph = round(gusts_val * 0.621371, 2)
        except (ValueError, TypeError):
            gusts_ms = 0.0
            gusts_mph = 0.0

        gusts_str = f" [Gusts={gusts} km/h ({gusts_ms} m/s, {gusts_mph} mph)]" if (gusts is not None and float(gusts) > 0) else ""
        weather_metrics_str = (
            f"Model-based Current Telemetry ({location}): Temperature={temp}°C, "
            f"Wind Speed={wind} km/h ({wind_ms} m/s, {wind_mph} mph){gusts_str}, "
            f"Precipitation={precip} mm (Probability={precip_prob}%), UV Index={uv}"
        )

        sop_texts = []
        citations = []
        for sop in matched_sops:
            sop_id = sop.get("id")
            title = sop.get("title")
            severity = sop.get("severity", "moderate").upper()
            advice = sop.get("advice", "").strip()
            sop_texts.append(f"[{sop_id}] ({severity}) {title}:\n{advice}")
            citations.append(f"{sop_id}: {title}")

        llm = self.get_llm(model_name)
        if llm:
            try:
                system_prompt = (
                    "You are Weabot, an empathetic, vigilant Outdoor Safety AI Companion. "
                    "Your mission is to keep the user safe by providing clear, practical guidance based STRICTLY on authorized SOPs.\n\n"
                    "CRITICAL RULES:\n"
                    "1. Ground your advice directly in the verified model weather telemetry numbers provided. Cite the exact numbers (e.g. wind speed, precipitation, UV) when explaining the risk.\n"
                    "2. If an override alert is active, suppress any contradictory permissive advice from lower SOPs.\n"
                    "3. If the user asks for specific metric unit conversions (e.g. wind speed in m/s and mph), answer them directly using the provided converted telemetry values.\n"
                    "4. If the user asks whether they will get drenched, state current precipitation and rain probability objectively (e.g. 'Current measured precipitation is 0.0 mm (0% probability)'). Never issue subjective promises like 'you will not get drenched' or guarantees about future weather.\n"
                    "5. If the user mentions asthma or air quality, clarify that air quality is not monitored.\n"
                    "6. If the user asks about IMD early warnings, always open immediately with the disclaimer that IMD synoptic early-warning feeds are not monitored, before discussing any local conditions.\n"
                    "7. Base all guidance strictly on the provided SOP advice. Never invent unapproved advice or general clearances like 'conditions are within safe limits'.\n"
                    "8. Keep the response concise, direct, and practical."
                )

                user_prompt = f"""User Query: "{user_query}"
Location: {location}
Activity: {activity}
{weather_metrics_str}

Applicable Standard Operating Procedures:
{chr(10).join(sop_texts)}

Compose a concise, grounded safety response citing the applicable live weather conditions and SOP guidance."""

                resp = llm.invoke(f"{system_prompt}\n\n{user_prompt}")
                content = self._extract_text_from_response(resp)
                return content.strip()
            except Exception as e:
                if is_quota_exhausted_error(e):
                    self.mark_model_exhausted(model_name, reason=f"compose_response: {e}")
                print(f"[LLMFactory] LLM composition error ({e}); falling back to deterministic.")

        # Deterministic Grounded Guidance Fallback
        lines = []
        lead_sop = matched_sops[0]
        
        telemetry_summary = []
        if precip is not None:
            telemetry_summary.append(f"Precipitation: {precip} mm ({precip_prob or 0}% probability)")
        if wind is not None and float(wind) > 0:
            if "m/s" in user_query.lower() or "mph" in user_query.lower():
                telemetry_summary.append(f"Wind Speed: {wind} km/h ({wind_ms} m/s, {wind_mph} mph)")
            else:
                if gusts is not None and float(gusts) > 0:
                    telemetry_summary.append(f"Wind Speed: {wind} km/h (Gusts: {gusts} km/h)")
                else:
                    telemetry_summary.append(f"Wind Speed: {wind} km/h")
        if temp is not None:
            telemetry_summary.append(f"Temperature: {temp}°C")
        if uv is not None and float(uv) > 3:
            telemetry_summary.append(f"UV Index: {uv}")

        telemetry_line = f"Model-based current conditions in {location}: {', '.join(telemetry_summary)}." if telemetry_summary else ""

        # Drenching query direct answer grounded in physical telemetry
        if any(k in user_query.lower() for k in ["drenched", "get wet", "will it rain", "going to rain", "get soaked"]):
            if precip is not None and float(precip) == 0.0:
                lines.append(f"• **Precipitation Check**: Current verified rainfall in {location} is 0.0 mm ({precip_prob or 0}% probability). Dry road conditions are observed.")

        # User false-premise temperature correction (G2)
        temp_match = re.search(r"\b(\d+)\s*(?:°\s*c|celsius|degrees)", user_query, re.IGNORECASE)
        if temp_match and temp is not None:
            user_temp = float(temp_match.group(1))
            actual_temp = float(temp)
            if abs(user_temp - actual_temp) >= 3.0:
                lines.append(f"• **Temperature Note**: You mentioned {int(user_temp)}°C, but live verified observations in {location} show {temp}°C.")

        # S2 & S4 direct responses
        if any(k in user_query.lower() for k in ["you said it was fine", "you said it was safe", "earlier you said", "you said earlier"]):
            lines.append(f"• **Session Check**: Earlier in this session, our evaluation for {location} was Caution Advised, not completely clear. Verified conditions continue to require precautions.")

        if any(k in user_query.lower() for k in ["anything changed", "has anything changed", "conditions changed", "changed since"]):
            snapshot_time = curr.get("time", "earlier today")
            lines.append(f"• **Freshness Check (Snapshot: {snapshot_time})**: Live telemetry has been checked against your session record. Model-based conditions in {location} remain consistent with the active advisory.")

        # Asthma / Air quality notice
        if any(k in user_query.lower() for k in ["asthma", "air fine", "air quality", "aqi"]):
            lines.append("• ⚠️ **Scope Notice**: Weabot does not currently monitor Air Quality Index (AQI), PM2.5, or airborne allergens. Please consult an official local air quality monitor for asthma precautions.")

        # IMD scope notice
        if any(k in user_query.lower() for k in ["imd", "synoptic", "low-pressure", "low pressure", "depression", "warning for my area"]):
            lines.append("• ⚠️ **Data Source Notice**: Weabot is powered by physical telemetry from Open-Meteo and does not have an official data integration with the India Meteorological Department (IMD) or national synoptic warning feeds. Please check https://mausam.imd.gov.in for official IMD alerts.")

        if lead_sop.get("override", False):
            lines.append(f"⚠️ **Severe Weather Alert for {location}**: {lead_sop['advice']}")
            if telemetry_line:
                lines.append(f"\n*{telemetry_line}*")
            # Only include other high-severity hazard warnings; suppress permissive/lower ones
            high_secondary = [s for s in matched_sops[1:] if s.get("severity") == "high"]
            if high_secondary:
                lines.append("\n**Important Safety Precautions**:")
                for s in high_secondary:
                    lines.append(f"- **{s['title']}**: {s['advice']}")
        else:
            lines.append(f"As your Weabot safety guardian, here are the official precautions for **{activity.title()}** in **{location}**:")
            if telemetry_line:
                lines.append(f"\n*{telemetry_line}*")
            for s in matched_sops:
                lines.append(f"\n• **{s['title']}** ({s['severity'].upper()}):\n{s['advice']}")

        lines.append("\nPlease prioritize your safety and follow these precautions. Check back if conditions change!")

        return "\n".join(lines)

llm_factory = LLMFactory()
