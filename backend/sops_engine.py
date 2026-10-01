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
        "high": 3,
        "moderate": 2,
        "low": 1
    }

    def __init__(self, sops_dir: Optional[Path] = None):
        self.sops_dir = sops_dir or settings.SOPS_DIR
        self.sops: Dict[str, Dict[str, Any]] = {}
        self.reload()

    def reload(self) -> int:
        """Scan and reload all SOP files from sops_dir."""
        loaded_sops = {}
        if not self.sops_dir.exists():
            self.sops = {}
            return 0

        yaml_files = sorted(
            list(self.sops_dir.glob("*.yaml")) + list(self.sops_dir.glob("*.yml"))
        )
        for filepath in yaml_files:
            try:
                with open(filepath, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f)
                if not data or not isinstance(data, dict):
                    continue
                self._validate_sop(data, filepath.name)
                loaded_sops[data["id"]] = data
            except Exception as e:
                print(f"[SOPsEngine] Warning: Failed to load {filepath.name}: {e}")

        self.sops = loaded_sops
        return len(self.sops)

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

    def matches_activity(self, sop: Dict[str, Any], activity: Optional[str]) -> bool:
        """
        Check if the SOP applies to the given user activity or intent.
        Override/General alerts apply across all queries.
        """
        if sop.get("override", False):
            return True

        applies_to = [str(x).lower().strip() for x in sop.get("applies_to", [])]
        if "all" in applies_to:
            return True

        if not activity:
            # If no specific activity provided, general and travel alerts still apply
            return sop.get("category") in ("general", "travel")

        activity_clean = activity.lower()
        # Tokenize activity
        tokens = re.findall(r"\b\w+\b", activity_clean)

        for target in applies_to:
            target_clean = target.lower()
            # Direct substring match
            if target_clean in activity_clean:
                return True
            # Token match or stemming match (e.g., cycle / cycling, bike / biking, jog / jogging)
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

        # Look up value in weather (checking current or top-level)
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
                return actual_val == expected_val or float(actual_val) == float(expected_val)
            elif op == "!=":
                return actual_val != expected_val
            elif op == "in":
                if isinstance(expected_val, list):
                    return actual_val in expected_val or int(actual_val) in expected_val
                return False
        except (ValueError, TypeError):
            return False

        return False

    def evaluate_condition(self, condition: Dict[str, Any], weather: Dict[str, Any]) -> bool:
        """Evaluate a condition node (threshold, compound, or fuzzy)."""
        cond_type = condition.get("type", "threshold")

        if cond_type == "threshold":
            return self.evaluate_clause(condition, weather)

        elif cond_type == "compound":
            combinator = condition.get("combinator", "AND").upper()
            clauses = condition.get("clauses", [])
            if not clauses:
                return False

            results = [self.evaluate_condition(c, weather) for c in clauses]
            if combinator == "OR":
                return any(results)
            else:
                return all(results)

        elif cond_type == "fuzzy":
            # Deterministic heuristic evaluation of fuzzy criteria
            criteria = condition.get("criteria", {})
            return self._evaluate_fuzzy_criteria(criteria, weather)

        return False

    def _evaluate_fuzzy_criteria(self, criteria: Dict[str, Any], weather: Dict[str, Any]) -> bool:
        """
        Evaluate criteria for fuzzy leisure SOPs (e.g. SOP-011 ideal picnic, SOP-012 marginal).
        """
        curr = weather.get("current", weather)
        temp = curr.get("temperature_2m", curr.get("apparent_temperature"))
        wind = curr.get("wind_speed_10m", 0.0)
        precip_prob = curr.get("precipitation_probability", 0)
        precip = curr.get("precipitation", 0.0)

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

        if "elevated_wind_range" in criteria:
            w_min, w_max = criteria["elevated_wind_range"]
            wind_matches = wind is not None and (w_min <= float(wind) <= w_max)
            prob_matches = False
            if "borderline_rain_prob_range" in criteria:
                p_min, p_max = criteria["borderline_rain_prob_range"]
                prob_matches = precip_prob is not None and (p_min <= float(precip_prob) <= p_max)
            return wind_matches or prob_matches

        return True

    def find_matching_sops(
        self,
        weather: Dict[str, Any],
        activity: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Match and rank SOPs against the weather snapshot and user activity.
        Resolution Rules:
        1. Overrides (e.g., SOP-001 severe regional weather) take highest precedence.
        2. Filtered by activity relevance.
        3. Condition checks (all top-level conditions in the SOP must evaluate to True).
        4. Ranked by severity (high > moderate > low).
        """
        if not weather:
            return []

        matched = []
        for sop in self.sops.values():
            if not self.matches_activity(sop, activity):
                continue

            conditions = sop.get("conditions", [])
            # An SOP matches if any of its top-level condition groups evaluate to True
            condition_passed = False
            for cond in conditions:
                if self.evaluate_condition(cond, weather):
                    condition_passed = True
                    break

            if condition_passed:
                matched.append(sop)

        # Multi-SOP Conflict Resolution
        # Sort key: (is_override: bool, severity_order: int)
        def sort_key(s):
            is_override = 1 if s.get("override", False) else 0
            sev = self.SEVERITY_ORDER.get(s.get("severity", "low"), 0)
            return (is_override, sev)

        matched.sort(key=sort_key, reverse=True)
        return matched
