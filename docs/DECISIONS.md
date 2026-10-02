# Architecture & Design Decisions Record (ADR)

This document records the foundational architectural decisions, rationale, trade-offs, and design principles implemented in the **Outdoor Activity Safety Advisor (Weabot)**.

---

## 1. Decision: Universal Overrides Evaluate Before Activity Eligibility

### Context
When a severe weather event occurs (such as torrential rainfall $\ge 15\text{ mm}$ or gale winds $\ge 40\text{ km/h}$), life safety hazards exist regardless of whether the user's outdoor activity is covered by a specific operational procedure (e.g. cycling, running) or uncovered (e.g. river swimming, flying a drone, outdoor yoga, surfing). Furthermore, adversarial users may attempt framing attacks such as *"Indoor-style cycling but on the road"* or *"I'm indoors, can I walk outside?"* to bypass activity filters.

### Decision
Universal life-safety policies (specifically `SOP-001` for severe rain/flooding, and any policy marked with `override: true`) are evaluated **before** checking activity eligibility. If an override condition is met:
1. The severe warning immediately fires with `status: "UNSAFE"` and `severity: "high"`.
2. All lower-severity or permissive policies are suppressed.
3. Framing attacks that mention outdoor road conditions or storms cannot evade the override.

### Trade-offs
- *Trade-off*: An activity that is completely indoors (e.g. indoor gym) might trigger an override if the query is ambiguously worded.
- *Mitigation*: The intake node checks whether the query contains road, outdoor, or travel context. True indoor activities without outdoor travel remain uncovered, while severe weather warnings protect anyone traveling outside.

---

## 2. Decision: Distinct Status Taxonomy Replacing Overloaded `UNCOVERED`

### Context
Previously, `UNCOVERED` was overloaded to represent multiple fundamentally distinct system states:
- Uncovered activities (e.g. swimming, drone flight).
- Weather outages and geocoding failures.
- Non-weather queries (e.g. stocks, extreme mountaineering).
- Activities where conditions were checked and no hazard thresholds were exceeded.

Reporting an API outage or missing data as `UNCOVERED/low` was misleading to monitoring systems and users alike.

### Decision
Adopt a strict 7-state verdict taxonomy:
1. **`UNSAFE`**: Active severe or high-hazard SOP threshold exceeded (`severity: "high"`).
2. **`CAUTION`**: Active moderate or low hazard advisory threshold exceeded (`severity: "moderate"` or `"low"`).
3. **`NO_HAZARD_MATCHED`**: Covered activity evaluated against live model telemetry; all parameters are below active hazard alert thresholds.
4. **`NO_POLICY`**: Uncovered activity with no applicable SOP. Refuses generic clearance without inventing unvalidated advice.
5. **`OUT_OF_SCOPE`**: Non-weather domain (finance/stocks), extreme high-altitude mountaineering, synoptic tracking, queries beyond the forecast horizon (>7–14 days), or retrospective queries for past elapsed time windows.
6. **`DATA_UNAVAILABLE`**: Live weather service offline/timeout, unresolvable geographical location, or required telemetry fields are null/missing (cannot verify safety).
7. **`REFUSED`**: Adversarial prompt injection or confidential system instruction extraction attempt refused under security policy.

---

## 3. Decision: Fail-Closed Policy Loading & Minimum Canary Set

### Context
A file system error or malformed YAML edit (e.g. syntax error in `SOP-001.yaml`) previously resulted in skipping the corrupted file while keeping the server running. If an operator accidentally broke `SOP-001.yaml`, the universal severe-rain override was silently deleted from memory.

### Decision
1. **Fail-Closed Canary Enforcement (`_validate_canary_set`)**:
   - `SOP-001` (Severe Precipitation Override) must exist and have `override: true`.
   - Core categories (`general`, `outdoor_exercise`, `travel`, `general_leisure`) must each have at least one active policy.
   - Total active policies must not drop below 10.
2. **Memory Preservation**: If a hot-reload encounters a canary violation or corrupt file, the engine rejects the update, preserves the `_last_good_sops` set in memory, and sets `last_reload_error`.
3. **HTTP 422 Reporting**: The `/api/sops/reload` endpoint reports HTTP 422 with the exact canary failure details while confirming the existing policy set remains intact.
4. **Endpoint Authentication**: Protected by optional `X-Admin-Key` header matching `ADMIN_API_KEY`.

---

## 4. Decision: Post-Render Runtime Number Guard

### Context
Even with strict system prompting, large language models (LLMs) can occasionally hallucinate metrics, extrapolate seasonal averages, or introduce unverified digits (e.g. claiming wind gusts of 88 km/h or rain probability of 99%).

### Decision
A post-render safety node (`validate_and_guard_numbers` in `backend/nodes/number_guard.py`) is wired between `compose`/`no_match` and `END`:
1. Extracts all integers and floating-point numbers from the model's generated text.
2. Whitelists:
   - Raw Open-Meteo telemetry numbers (current and target hourly).
   - Exact derived mathematical conversions ($\text{km/h} \to \text{m/s}$, $\text{km/h} \to \text{mph}$, $^\circ\text{C} \to ^\circ\text{F}$).
   - Literal numbers from active SOP conditions and advice text.
   - User-quoted numbers from the input prompt.
   - Standard structural numerals (timestamps, percentages, single digits).
3. **Safe Substitution**: If any unauthorized number is detected, the post-render node replaces the text with a 100% deterministic, verified template.

---

## 5. Decision: Time-Aware Hourly Grounding & Horizon Limits

### Context
Evaluating a question about "tomorrow morning" or "2 AM tonight" against current midday weather creates severe contradictions (e.g. issuing a heat warning for 2 AM, or evaluating Auckland noon using tomorrow's data).

### Decision
1. **Explicit Target Resolution**: Resolves expressions like *"this weekend"*, *"Saturday"*, *"Sunday"*, *"in 3 days"*, *"tomorrow morning"*, *"2am"*, *"this evening"* to exact target dates and hour strings.
2. **Hourly Slice Extraction**: Extracts the verified forecast slice from `hourly` into `effective_weather["current"]`. All threshold evaluations run against the target hour's telemetry.
3. **Past Elapsed Window Refusal**: Retrospective queries (e.g. *"yesterday"*, *"earlier today"*) return `status: "OUT_OF_SCOPE"` with title `"Historical Time Window · Past Elapsed Conditions"`.
4. **Horizon Exceeded Refusal**: Queries beyond 7–14 days return `status: "OUT_OF_SCOPE"` with title `"Forecast Horizon Exceeded"`.

---

## 6. Decision: Provenance-Backed Severe Storm Replay

### Context
Evaluating severe weather policies in live production often coincides with calm local conditions. Synthetic mock payloads lack real-world provenance.

### Decision
Fetched and committed real Open-Meteo Historical Archive API data for **Severe Cyclonic Storm Remal** (May 26–27, 2024, Kolkata: $22.57^\circ\text{N}, 88.36^\circ\text{E}$):
- File: `fixtures/recorded_severe_storm_cyclone_remal.json`
- Peak telemetry: 21.7 mm precipitation, 40.7 km/h wind speed, 74.5 km/h wind gusts, weather code 65.
- Includes complete provenance metadata header with exact REST query URL, parameters, and attribution to Open-Meteo under CC BY 4.0.

---

## 7. Decision: Policy-as-Data for Aliases and Out-of-Scope Domains

### Context
Hardcoding activity synonyms or out-of-scope domain lists in Python code violated the zero-code policy change directive.

### Decision
Externalized all taxonomies into versioned YAML configuration files:
- `config/activity_aliases.yaml`: Maps synonyms to canonical categories (`transit`, `cycling`, `running`, `walking`, `playground`, `pets`, `picnic`, `travel`, `industrial_safety`).
- `config/out_of_scope.yaml`: Defines out-of-scope policies for financial advice, extreme mountaineering, national early-warning feeds, synoptic systems, and prompt disclosure.

---

## 8. Decision: Strict Separation of Deterministic Core and LLM Intake

### Architectural Boundary
Weabot strictly minimizes LLM surface area to prevent hallucinated safety advice or unauthorized clearance endorsements:
- **LLM Responsibility (Intake Only, Temp = 0)**:
  - Dialogue act classification (`parse_turn`).
  - Candidate SOP ID selection from a catalog containing ONLY `id`, `title`, and `intent` (no weather thresholds exposed to the LLM).
  - Demographic subject extraction (child, elderly, pet, adult).
- **Deterministic Python Core (Zero LLM / Zero Hallucination)**:
  - State hygiene & session state persistence (`TurnState` vs `SessionState`).
  - Spatial verification & coordinate distance checking ($\le 0.5^\circ$).
  - Time resolution & forecast horizon bounding (16-day limit, timezone conversions).
  - Weather API querying & telemetry caching (10-minute TTL).
  - Payload verification (units, coordinates, non-null values).
  - SOP condition evaluation (pure Python math: threshold, compound, range, fuzzy).
  - Universal override evaluation & precedence ranking (severity sorting).
  - Advice rendering (verbatim insertion of YAML text, telemetry numbers, and headers).
  - Post-render guards (runtime number whitelist audit and banned phrase rejection).
  - Decision logging and freshness diff auditing.

---

## 9. Decision: Policy Calibration on SOP-003 (Owner Decision)

### Context & Observation
`SOP-003` (*Moderate Heat Exercise Caution and Hydration Protocol*) activates when apparent temperature is between $32.0^\circ\text{C}$ and $37.9^\circ\text{C}$. In central Indian cities like Bhopal and Indore, midday apparent temperatures routinely sit in the $32^\circ\text{C} - 38^\circ\text{C}$ band during spring, summer, and post-monsoon months. Consequently, `SOP-003` fires on nearly every daytime exercise query.

### Calibration Decision
This behavior is **deliberate and policy-calibrated**:
1. At apparent temperatures $\ge 32^\circ\text{C}$ ($89.6^\circ\text{F}$), standard occupational and sports medicine guidelines (ACGIH, OSHA, ACSM) classify thermal stress as "Caution to Extreme Caution", where continuous heavy aerobic exertion (cycling, distance running) carries substantial risk of heat exhaustion, cramping, and dehydration.
2. `SOP-003` does **not** forbid outdoor activity (its severity is `moderate`, not `high`/`critical`), but mandates sensible precautions: pacing exertion, reducing workout intensity by 20–30%, taking hydration breaks every 15–20 minutes, and rescheduling heavy endurance sessions to cooler early morning or late evening hours.
3. Tightening the threshold to $35^\circ\text{C}$ would dangerously omit the recognized physiological dehydration risk that begins at $32^\circ\text{C}$ under direct sun and high humidity. Therefore, the threshold remains calibrated at $32.0^\circ\text{C}$.

---

## 10. Known Gaps & Operational Limits

1. **Live Severe Weather Testing vs Local Calm**:
   - Live testing in target cities frequently encounters calm, clear weather. Real-time verification of severe storm overrides (`SOP-001`) relies on real Open-Meteo Archive API payloads (such as Cyclone Remal in Kolkata) and scripted per-city stubs.
2. **M3 Precipitation Probability Cliff**:
   - Open-Meteo models report precipitation probability in discrete percentage steps. Under $10.0\text{ mm}$ rainfall, a forecast probability of $69\%$ triggers moderate rain advisory (`SOP-005`), whereas $70\%$ triggers the severe flooding override (`SOP-001`). This discrete step is audited and documented in the test suite.
3. **Physical Condition vs Clock-Gated UV Trigger**:
   - `SOP-008` (UV radiation hazard) triggers when physical `uv_index >= 8.0`. Even if a user queries an edge time (e.g. 10:59 AM vs 11:00 AM), the policy evaluates solely based on the physical ultraviolet index rather than engine clock gates.
4. **Devanagari Script Boundary**:
   - Weabot currently accepts English and Latin transliterated inputs (e.g. *"Bhopal"*). Non-Latin scripts such as Devanagari (*"भोपाल"*) return an honest script limitation notice advising users to provide location in Latin characters.

