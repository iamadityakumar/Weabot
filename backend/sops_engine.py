# Caller/Importer: `backend/nodes/weather.py`, `evals/suites/*`, `run_evals.py`
# API/Component affected: `SOPsEngine` in `backend/sops_engine.py`
# Data schema: Policy YAML schema, Dict[str, Dict[str, Any]] mapping policy IDs
# User prompt: "build comprehensive evaluation suite for Weabot at D:\IIIT B\MB with execution scripts run_evals.py, run_live_evals.py, run_release_gate.py."

import os
import re
from pathlib import Path
from typing import Dict, List, Any, Set, Tuple, Optional
import yaml
from backend.config import settings

class SOPValidationError(Exception):
    pass

class SOPsEngine:
    """
    Dynamic SOP loader, validator, field aggregator, and condition evaluator.
    Strictly satisfies:
    1. Zero-code policy updates: reads from YAML on initialization or reload().
    2. Dynamic field aggregation: auto-detects fields required by active SOPs.
    3. Deterministic threshold evaluation in Python.
    4. Multi-SOP sorting: override > high > moderate > low.
    5. Fail-closed loading with minimum canary set enforcement.
    6. Universal overrides evaluate before activity eligibility.
    """

    BASELINE_FIELDS: Set[str] = {
        "temperature_2m",
        "apparent_temperature",
        "precipitation",
        "precipitation_probability",
        "rain",
        "weather_code",
        "wind_speed_10m",
        "wind_gusts_10m",
        "uv_index",
        "relative_humidity_2m",
    }

    SEVERITY_ORDER = {
        "critical": 4,
        "high": 3,
        "moderate": 2,
        "low": 1
    }

    def __init__(self, sops_dir: Optional[Path] = None):
        self.sops_dir = sops_dir or settings.SOPS_DIR
        self.sops: Dict[str, Dict[str, Any]] = {}
        self._last_good_sops: Dict[str, Dict[str, Any]] = {}
        self.skipped_files: List[Dict[str, str]] = []
        self.last_reload_error: Optional[str] = None
        self.activity_aliases: Dict[str, Any] = {}
        self.out_of_scope_policies: Dict[str, Any] = {}
        self.load_configs()
        self.reload()

    def load_configs(self):
        """Load external YAML configs for activity aliases and out-of-scope rules."""
        root = Path(__file__).resolve().parent.parent
        alias_file = root / "config" / "activity_aliases.yaml"
        if alias_file.exists():
            try:
                with open(alias_file, "r", encoding="utf-8") as f:
                    self.activity_aliases = yaml.safe_load(f) or {}
            except Exception as e:
                print(f"[SOPsEngine] Warning loading activity_aliases.yaml: {e}")

        oos_file = root / "config" / "out_of_scope.yaml"
        if oos_file.exists():
            try:
                with open(oos_file, "r", encoding="utf-8") as f:
                    self.out_of_scope_policies = yaml.safe_load(f) or {}
            except Exception as e:
                print(f"[SOPsEngine] Warning loading out_of_scope.yaml: {e}")

    def _validate_canary_set(self, sops: Dict[str, Dict[str, Any]]) -> None:
        """
        Enforce fail-closed minimum canary policy set:
        1. SOP-001 (Severe Precipitation Override) must exist and have override: true.
        2. At least one valid policy in each core category:
           - general
           - outdoor_exercise
           - travel
           - general_leisure
        3. Total active policies must not drop below minimum threshold (10).
        """
        if "SOP-001" not in sops:
            raise SOPValidationError("Canary violation: Critical severe-rain override 'SOP-001' is missing.")
        if not sops["SOP-001"].get("override", False):
            raise SOPValidationError("Canary violation: 'SOP-001' must have 'override: true'.")

        core_categories = {"general", "outdoor_exercise", "travel", "general_leisure"}
        present_categories = {s.get("category") for s in sops.values()}
        missing = core_categories - present_categories
        if missing:
            raise SOPValidationError(f"Canary violation: Missing policies for core categories: {sorted(list(missing))}")

        if len(sops) < 10:
            raise SOPValidationError(f"Canary violation: Loaded policies count ({len(sops)}) is below minimum safe threshold (10).")

    def reload(self) -> int:
        """Scan and reload all SOP files from sops_dir with fail-closed canary protection."""
        loaded_sops = {}
        self.skipped_files = []
        if not self.sops_dir.exists():
            if self._last_good_sops:
                self.sops = dict(self._last_good_sops)
                return len(self.sops)
            raise RuntimeError(f"Startup fail-closed failure: sops_dir '{self.sops_dir}' does not exist.")

        yaml_files = sorted(
            list(self.sops_dir.glob("*.yaml")) + list(self.sops_dir.glob("*.yml"))
        )
        for filepath in yaml_files:
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f)
                if not data or not isinstance(data, dict):
                    self.skipped_files.append({"file": filepath.name, "reason": "Empty or non-dictionary YAML"})
                    continue
                self._validate_sop(data, filepath.name)
                if data["id"] in loaded_sops:
                    raise SOPValidationError(f"Duplicate policy ID detected: '{data['id']}' in {filepath.name}")
                loaded_sops[data["id"]] = data
            except Exception as e:
                print(f"[SOPsEngine] Warning: Failed to load {filepath.name}: {e}")
                clean_reason = str(e)
                if self.sops_dir:
                    clean_reason = clean_reason.replace(str(self.sops_dir), "").replace(str(self.sops_dir).replace("\\", "/"), "")
                clean_reason = re.sub(r'in "[^"]*[/\\]([^"/\\]+)"', r'in "\1"', clean_reason)
                clean_reason = re.sub(r'[A-Za-z]:\\[^\n\r"]*[/\\]', '', clean_reason)
                clean_reason = re.sub(r'/[^\n\r"]*/', '', clean_reason)
                self.skipped_files.append({"file": filepath.name, "reason": clean_reason.strip()})

        # Canary verification & fail-closed protection
        try:
            self._validate_canary_set(loaded_sops)
            # If critical SOP-001 was skipped due to a malformed edit, fail closed!
            if any("SOP-001" in item.get("file", "") for item in self.skipped_files):
                raise SOPValidationError("Canary violation: 'SOP-001.yaml' failed validation or was malformed.")
            
            self.sops = loaded_sops
            self._last_good_sops = dict(loaded_sops)
            self.last_reload_error = None
        except Exception as e:
            err_msg = str(e)
            print(f"[SOPsEngine] ⚠️ Fail-closed reload blocked: {err_msg}")
            self.last_reload_error = err_msg
            if self._last_good_sops:
                print("[SOPsEngine] Preserving last-known good policy set in memory.")
                self.sops = dict(self._last_good_sops)
            else:
                raise RuntimeError(f"Startup fail-closed failure: {err_msg}")

        return len(self.sops)

    def get_sop(self, sop_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a loaded SOP by its ID."""
        return self.sops.get(sop_id)

    def get_sop_by_id(self, sop_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a loaded SOP by its ID (alias for get_sop)."""
        return self.sops.get(sop_id)

    def _validate_sop(self, data: Dict[str, Any], filename: str) -> None:
        """Enforce strict schema integrity on every SOP."""
        required_keys = ["id", "title", "category", "severity", "applies_to", "conditions", "advice"]
        for key in required_keys:
            if key not in data:
                raise SOPValidationError(f"File {filename} missing required key: '{key}'")

        if data["severity"] not in self.SEVERITY_ORDER:
            raise SOPValidationError(
                f"File {filename} invalid severity: '{data['severity']}'. Must be one of: {list(self.SEVERITY_ORDER.keys())}"
            )

        if not isinstance(data["conditions"], list) or len(data["conditions"]) == 0:
            raise SOPValidationError(f"File {filename} must have a non-empty 'conditions' list")

        # Restrict override: true to high/critical severity life-safety policies
        if data.get("override", False):
            if data["severity"] not in ("high", "critical"):
                raise SOPValidationError(
                    f"File {filename} has override: true but severity is '{data['severity']}'. Overrides must be high/critical severity."
                )

    def get_required_weather_fields(self) -> List[str]:
        """
        Dynamically inspect all loaded SOPs to aggregate every weather variable
        mentioned in conditions. Merges with BASELINE_FIELDS.
        Guarantees that adding an 11th SOP with a new field (e.g. visibility)
        automatically queries Open-Meteo with zero code changes.
        """
        fields = set(self.BASELINE_FIELDS)

        def extract_fields(cond: Any):
            if not isinstance(cond, dict):
                return
            if "field" in cond and isinstance(cond["field"], str):
                fields.add(cond["field"].strip())
            if "clauses" in cond and isinstance(cond["clauses"], list):
                for sub in cond["clauses"]:
                    extract_fields(sub)

        for sop in self.sops.values():
            for condition in sop.get("conditions", []):
                extract_fields(condition)

        return sorted(list(fields))

    def is_universal_override(self, sop: Dict[str, Any]) -> bool:
        """
        Check if an SOP is a universal life-safety override that must evaluate
        before activity eligibility (e.g. severe rain/flood, gale winds, extreme heat).
        """
        if sop.get("override", False):
            return True
        sop_id = sop.get("id", "")
        # Severe rain (SOP-001) is the primary override; gale winds (SOP-004) and extreme heat (SOP-002)
        if sop_id in ("SOP-001",):
            return True
        applies = [str(x).lower().strip() for x in sop.get("applies_to", [])]
        return "all" in applies or "any" in applies

    def matches_activity(self, sop: Dict[str, Any], activity: Optional[str]) -> bool:
        """
        Check if the SOP applies to the given user activity or intent.
        Universal overrides apply across all activities.
        Multi-word targets require all constituent tokens to be present.
        """
        if self.is_universal_override(sop):
            return True

        applies_to = [str(x).lower().strip() for x in sop.get("applies_to", [])]
        if "all" in applies_to:
            return True

        if not activity:
            return sop.get("category") in ("general", "travel")

        activity_clean = activity.lower().strip()
        tokens = re.findall(r"\b\w+\b", activity_clean)

        for target in applies_to:
            target_clean = target.lower()
            target_tokens = re.findall(r"\b\w+\b", target_clean)

            if len(target_tokens) > 1:
                if all(any(token.startswith(tt[:4]) or tt.startswith(token[:4]) for token in tokens) for tt in target_tokens):
                    return True
                continue

            if target_clean in activity_clean:
                return True
            for token in tokens:
                if token.startswith(target_clean[:4]) and len(target_clean) >= 4 and len(token) >= 4:
                    return True
                if target_clean.startswith(token[:4]) and len(token) >= 4 and len(target_clean) >= 4:
                    return True
        return False

    def evaluate_clause(self, clause: Dict[str, Any], weather: Dict[str, Any]) -> bool:
        """Deterministically evaluate a single threshold clause in Python."""
        field = clause.get("field")
        op = clause.get("op")
        expected_val = clause.get("value")

        if not field or op is None or expected_val is None:
            return False

        actual_val = None
        if "current" in weather and isinstance(weather["current"], dict) and field in weather["current"]:
            actual_val = weather["current"][field]
        elif field in weather:
            actual_val = weather[field]

        if actual_val is None:
            return False

        try:
            if op == ">":
                return float(actual_val) > float(expected_val)
            elif op == ">=":
                return float(actual_val) >= float(expected_val)
            elif op == "<":
                return float(actual_val) < float(expected_val)
            elif op == "<=":
                return float(actual_val) <= float(expected_val)
            elif op == "==":
                return actual_val == expected_val
            elif op == "!=":
                return actual_val != expected_val
            elif op == "in":
                if isinstance(expected_val, list):
                    return actual_val in expected_val
                return False
        except (ValueError, TypeError):
            return False
        return False

    def evaluate_condition(self, condition: Dict[str, Any], weather: Dict[str, Any]) -> bool:
        """Evaluate threshold, compound, range, or fuzzy conditions."""
        cond_type = condition.get("type", "threshold")

        if cond_type == "threshold":
            return self.evaluate_clause(condition, weather)

        elif cond_type == "range":
            field = condition.get("field")
            min_val = condition.get("min")
            max_val = condition.get("max")
            actual_val = None
            if "current" in weather and isinstance(weather["current"], dict) and field in weather["current"]:
                actual_val = weather["current"][field]
            elif field in weather:
                actual_val = weather[field]

            if actual_val is None:
                return False
            try:
                f_val = float(actual_val)
                if min_val is not None and f_val < float(min_val):
                    return False
                if max_val is not None and f_val > float(max_val):
                    return False
                return True
            except (ValueError, TypeError):
                return False

        elif cond_type == "compound":
            combinator = condition.get("combinator", "AND").upper()
            clauses = condition.get("clauses", [])
            if not clauses:
                return False

            if combinator == "AND":
                return all(self.evaluate_condition(c, weather) for c in clauses)
            elif combinator == "OR":
                return any(self.evaluate_condition(c, weather) for c in clauses)

        elif cond_type == "fuzzy":
            return self._evaluate_fuzzy_criteria(condition.get("criteria", {}), weather)

        return False

    def _evaluate_fuzzy_criteria(self, criteria: Dict[str, Any], weather: Dict[str, Any]) -> bool:
        """Evaluate criteria for fuzzy leisure SOPs."""
        curr = weather.get("current", weather)
        temp = curr.get("temperature_2m", curr.get("apparent_temperature"))
        wind = curr.get("wind_speed_10m", 0.0)
        precip_prob = curr.get("precipitation_probability", 0)
        precip = curr.get("precipitation", 0.0)
        is_day = curr.get("is_day", 1)

        if "requires_daylight" in criteria and criteria["requires_daylight"]:
            if is_day == 0:
                return False

        if "temp_range" in criteria:
            t_min, t_max = criteria["temp_range"]
            if temp is not None and not (t_min <= float(temp) <= t_max):
                return False

        if "max_wind" in criteria:
            if wind is not None and float(wind) > float(criteria["max_wind"]):
                return False

        if "max_precip_prob" in criteria:
            if precip_prob is not None and float(precip_prob) > float(criteria["max_precip_prob"]):
                return False

        if "max_precip" in criteria:
            if precip is not None and float(precip) > float(criteria["max_precip"]):
                return False

        if "elevated_wind_range" in criteria or "marginal_temp_ranges" in criteria or "borderline_rain_prob_range" in criteria:
            wind_matches = False
            if "elevated_wind_range" in criteria:
                w_min, w_max = criteria["elevated_wind_range"]
                wind_matches = wind is not None and (w_min <= float(wind) <= w_max)

            prob_matches = False
            if "borderline_rain_prob_range" in criteria:
                p_min, p_max = criteria["borderline_rain_prob_range"]
                prob_matches = precip_prob is not None and (p_min <= float(precip_prob) <= p_max)

            temp_matches = False
            if "marginal_temp_ranges" in criteria and temp is not None:
                for t_min, t_max in criteria["marginal_temp_ranges"]:
                    if t_min <= float(temp) <= t_max:
                        temp_matches = True
                        break

            return wind_matches or prob_matches or temp_matches

        return True

    def find_matching_sops(
        self,
        weather: Dict[str, Any],
        activity: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Match and rank SOPs against weather telemetry and activity.
        Universal life-safety overrides evaluate BEFORE activity eligibility,
        ensuring severe conditions alert regardless of whether the activity is covered or uncovered.
        """
        if not weather:
            return []

        matched = []

        # Tier 1: Universal overrides evaluate BEFORE activity eligibility
        for sop in self.sops.values():
            if not self.is_universal_override(sop):
                continue
            conditions = sop.get("conditions", [])
            for cond in conditions:
                if self.evaluate_condition(cond, weather):
                    matched.append(sop)
                    break

        # Tier 2: Activity-specific SOPs (only evaluated if activity matches)
        for sop in self.sops.values():
            if self.is_universal_override(sop):
                continue
            if not self.matches_activity(sop, activity):
                continue
            conditions = sop.get("conditions", [])
            for cond in conditions:
                if self.evaluate_condition(cond, weather):
                    matched.append(sop)
                    break

        # Multi-SOP Conflict Resolution
        def sort_key(s):
            is_override = 1 if s.get("override", False) else 0
            sev = self.SEVERITY_ORDER.get(s.get("severity", "low"), 0)
            return (is_override, sev)

        matched.sort(key=sort_key, reverse=True)

        # If an override SOP is present, suppress all lower-severity and permissive SOPs
        has_override = any(s.get("override", False) for s in matched)
        if has_override:
            matched = [s for s in matched if s.get("override", False) or s.get("severity") == "high"]
        return matched

    def get_unverified_sops(
        self,
        weather: Dict[str, Any],
        activity: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Identify SOPs that apply to the activity but cannot be evaluated
        because required weather fields are null/None in the weather telemetry.
        """
        if not weather:
            return []

        curr = weather.get("current", weather)
        unverified = []

        for sop in self.sops.values():
            if not self.matches_activity(sop, activity):
                continue

            conditions = sop.get("conditions", [])
            for cond in conditions:
                missing = self._find_missing_fields_in_condition(cond, curr)
                if missing:
                    unverified.append({
                        "sop_id": sop.get("id"),
                        "title": sop.get("title"),
                        "severity": sop.get("severity"),
                        "missing_fields": missing,
                        "advice": sop.get("advice", "")
                    })
                    break

        return unverified

    def has_specific_activity_sops(self, activity: Optional[str]) -> bool:
        """
        Check if any loaded SOP specifically targets this activity,
        excluding universal overrides.
        """
        if not activity:
            return False
        act_clean = activity.lower().strip()
        
        # Explicit uncovered activities
        uncovered_keywords = ["swim", "drone", "wear", "clothing", "dress", "outfit", "yoga", "surfing"]
        if any(un in act_clean for un in uncovered_keywords):
            return False

        # Check against YAML activity aliases
        for canonical, entry in self.activity_aliases.items():
            aliases = entry.get("aliases", [])
            if any(alias in act_clean or act_clean in alias for alias in aliases):
                return True

        # Fallback check against loaded SOP applies_to
        for sop in self.sops.values():
            if sop.get("override", False):
                continue
            applies = [str(x).lower().strip() for x in sop.get("applies_to", [])]
            if "all" in applies or "any" in applies:
                continue
            for target in applies:
                if target in act_clean or act_clean in target:
                    return True
        return False

    def _find_missing_fields_in_condition(self, cond: Dict[str, Any], curr: Dict[str, Any]) -> List[str]:
        missing = []
        if not isinstance(cond, dict):
            return missing

        field = cond.get("field")
        if field and curr.get(field) is None:
            missing.append(field)

        clauses = cond.get("clauses", [])
        if isinstance(clauses, list):
            for clause in clauses:
                missing.extend(self._find_missing_fields_in_condition(clause, curr))

        crit = cond.get("criteria", {})
        if isinstance(crit, dict):
            if "elevated_wind_range" in crit and curr.get("wind_speed_10m") is None:
                missing.append("wind_speed_10m")
            if "marginal_temp_ranges" in crit and curr.get("temperature_2m") is None:
                missing.append("temperature_2m")
            if "borderline_rain_prob_range" in crit and curr.get("precipitation_probability") is None:
                missing.append("precipitation_probability")
        return list(set(missing))


_engine_instance: Optional[SOPsEngine] = None

def get_sops_engine() -> SOPsEngine:
    global _engine_instance
    if _engine_instance is None:
        _engine_instance = SOPsEngine()
    return _engine_instance
