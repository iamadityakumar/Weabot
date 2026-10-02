# Weabot — Outdoor Activity Safety Advisor

A deterministic weather safety advisor powered by **LangGraph**, live **Open-Meteo** meteorological telemetry, and a versioned library of **Standard Operating Procedures (SOPs)**. Safety decisions are calculated deterministically in code—never hallucinated by an LLM.

---

## 1. Setup & Run Instructions

### Prerequisites
- **Python**: 3.11+ (tested on Python 3.12)
- **Node.js**: 18+ and npm
- **LLM API Key**: At least one key (Google Gemini, Groq, or OpenAI) for natural language understanding

---

### Backend Setup & Run

1. **Create and activate a virtual environment**:
   ```bash
   # Windows (PowerShell / CMD)
   python -m venv venv
   venv\Scripts\activate

   # Linux / macOS
   python3 -m venv venv
   source venv/bin/activate
   ```

2. **Install Python dependencies**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Configure environment variables**:
   ```bash
   # Copy example template
   cp .env.example .env
   ```
   Edit `.env` to set your LLM provider and API key (e.g. `GEMINI_API_KEY=AIza...` and `LLM_PROVIDER=gemini`, or `GROQ_API_KEY=gsk_...` and `LLM_PROVIDER=groq`). Open-Meteo weather API requires no key.

4. **Start the backend server**:
   ```bash
   uvicorn backend.main:app --host 127.0.0.1 --port 8000 --reload
   ```
   - API endpoints: `http://127.0.0.1:8000`
   - Interactive OpenAPI documentation: `http://127.0.0.1:8000/docs`

---

### Frontend Setup & Run

The frontend is built with React 19, Vite, and Tailwind CSS.

1. **Install dependencies**:
   ```bash
   cd frontend
   npm install
   ```

2. **Option A: Development Server** (with Vite hot-module reload):
   ```bash
   npm run dev
   ```
   Open `http://localhost:5173`. Vite automatically proxies `/api` calls to `http://127.0.0.1:8000`.

3. **Option B: Production Build** (served directly by FastAPI):
   ```bash
   npm run build
   ```
   Build artifacts are written to `frontend/dist`. When built, FastAPI mounts and serves the single-page application directly at `http://127.0.0.1:8000/`.

---

## 2. Standard Operating Procedures (SOPs)

> **Form Rationale**: SOPs are authored as standalone YAML files with machine-verifiable numeric thresholds because safety verdicts must be evaluated deterministically in code—never left to LLM probability or hallucination.

All 13 SOPs reside in [`sops/`](sops/):
- **Universal Overrides**: `SOP-001` (Severe Rain / Flooding), `SOP-006` (Fog / Low Visibility), `SOP-010` (Lightning / Thunderstorm)
- **Activity & Heat**: `SOP-002` (Extreme Heat), `SOP-003` (Moderate Heat), `SOP-004` (High Wind Two-Wheelers), `SOP-005` (Wet Road Travel)
- **Vulnerable Groups**: `SOP-007` (Extreme Cold / Frostbite), `SOP-008` (Extreme UV Children), `SOP-009` (Hot Pavement Pets), `SOP-013` (Moderate UV Playground)
- **Leisure & Gatherings**: `SOP-011` (Ideal Picnic), `SOP-012` (Marginal / Unsettled Gathering)

**Zero-Code Live Policy Updates**: Adding or updating a YAML file in `sops/` and calling `POST /api/sops/reload` immediately registers new conditions and telemetry fields without code changes or restarts.

---

## 3. LangGraph Implementation

The core execution graph is implemented in [`backend/graph.py`](backend/graph.py) using a compiled `StateGraph(AgentState)` with state checkpointing via `MemorySaver`.

```
START ──► route ─┬─► smalltalk_node ───────► END
                 ├─► about_node ───────────► END
                 ├─► meta_node ────────────► END
                 ├─► scope_node ───────────► END
                 ├─► needs_location_node ──► END
                 ├─► needs_activity_node ──► END
                 └─► resolve_location ──┬──► location_fail ─► END
                                        └──► resolve_time ──┬──► time_fail ─► END
                                                            └──► fetch_weather ──┬──► data_fail ─► END
                                                                                 └──► verify_payload ──┬──► data_fail ─► END
                                                                                                       └──► select_sops ──► evaluate_sops ──► resolve_precedence ──► render ──► guards ──► log_decision ──► END
```

- **Router**: Multi-tier intent classification (regex pre-filters + structured classifier) before executing weather lookups.
- **Deterministic Guards**:
  - `resolve_location` & `resolve_time`: Validates place via Open-Meteo geocoding; bounds forecasts to a 16-day horizon.
  - `verify_payload`: Validates coordinates within 0.5°, checks required telemetry units, and verifies non-null readings.
  - `evaluate_sops`: Deterministic Python AST-style condition evaluator with universal overrides evaluated first.
  - `guards`: Post-render regex whitelist ensuring every reported number matches live API telemetry.

---

## 4. Evaluation Suite & Verification

The test suite is located in [`evals/eval_suite.py`](evals/eval_suite.py) and can be executed standalone without running the web server:

```bash
# Run all 9 evaluation cases:
python -m evals.eval_suite
```

Full details and audit writeup are documented in [`evals/EVAL_REPORT.md`](evals/EVAL_REPORT.md). Machine-readable results are saved to [`evals/eval_results.json`](evals/eval_results.json).

### Results Matrix

| Case | Category | Query / Target | Result | Notes |
|:---|:---|:---|:---:|:---|
| **CASE-1** | SOP Applies (Keyword) | High Wind + Cycling (`SOP-004`) | ✅ PASS | Fires SOP-004, `UNSAFE` verdict, quotes wind speed. |
| **CASE-2** | SOP Applies (Keyword) | Extreme Heat + Running (`SOP-002`) | ✅ PASS | Fires SOP-002, `UNSAFE` verdict, quotes apparent temp. |
| **CASE-3** | Paraphrased Intent | Heavy Rain ("pedal new bicycle", "pouring nonstop") | ✅ PASS | Semantic mapping to cycling; fires `SOP-001` & `SOP-005`. |
| **CASE-4** | Paraphrased Intent | Elderly Heat ("grandma", "stroll", "sweltering") | ✅ PASS | Semantic mapping to elderly walk; fires `SOP-002`. |
| **CASE-5** | Live Severe Weather | Probes live Open-Meteo API across Indian cities | ✅ PASS | Fetches real API data; grounds response in live numbers. |
| **CASE-6** | No SOP Applies | Indoor yoga in Springfield | ✅ PASS | `NO_POLICY` verdict; does not hallucinate advice. |
| **CASE-7** | API Failure | Simulated weather API timeout / 500 error | ✅ PASS | `DATA_UNAVAILABLE` verdict; refuses to guess weather. |
| **CASE-8** | Adversarial Injection | Prompt injection attempting to inject fake `SOP-099` | ✅ PASS | Refutes `SOP-099` existence; refuses unsafe clearance. |
| **CASE-9** | Live SOP Hot-Reload | Runtime addition of temporary YAML with new field | ✅ PASS | Dynamically registers new field and restores cleanly. |

**Score: 9 / 9 Passed (100%)**

#### Honest Notes on Gaps & Limitations
1. **Case 5 Live Conditions**: Probe execution during nighttime/fair weather correctly returns `NO_HAZARD_MATCHED` with live numeric telemetry rather than firing an alert. To observe live alert triggering, run during an active daytime monsoon or squall event.
2. **Geocoding Ambiguity**: Open-Meteo geocoding can resolve ambiguous city names (e.g. "Kochi") to international equivalents (Kochi, Japan vs Kochi, India) if country context is omitted in the query.
3. **LLM Provider Quota**: Paraphrased intent extraction relies on LLM inference. If API rate limits are exceeded, the built-in fallback chain in `llm_factory.py` switches providers (Gemini → Groq → OpenAI/GPT-OSS).
