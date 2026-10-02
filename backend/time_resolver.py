import re
from datetime import datetime, date, time as dt_time, timedelta, timezone
from typing import Dict, Any, Optional
import zoneinfo

class TimeTarget:
    def __init__(
        self,
        kind: str,
        iso: Optional[str] = None,
        assumed: Optional[str] = None,
        target_hour: Optional[str] = None,
        target_date: Optional[str] = None,
        display_target: Optional[str] = None
    ):
        self.kind = kind  # "now", "hour", "day", "past", "beyond_horizon"
        self.iso = iso
        self.assumed = assumed
        self.target_hour = target_hour
        self.target_date = target_date
        self.display_target = display_target or self._build_display()

    def _build_display(self) -> str:
        if self.kind == "now":
            return "Current model conditions"
        if self.kind == "beyond_horizon":
            return "Beyond 16-day forecast horizon"
        if self.kind == "past":
            return "Past elapsed time (Conditions already passed)"
        if self.target_hour:
            if self.assumed:
                return f"Forecast for {self.target_hour} ({self.assumed})"
            return f"Forecast for {self.target_hour}"
        if self.assumed:
            return f"Forecast ({self.assumed})"
        return "Forecast"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "kind": self.kind,
            "iso": self.iso,
            "assumed": self.assumed,
            "target_hour": self.target_hour,
            "target_date": self.target_date,
            "display_target": self.display_target
        }

    def __repr__(self) -> str:
        return f"TimeTarget(kind={self.kind}, iso={self.iso}, assumed={self.assumed}, target_hour={self.target_hour})"

def get_location_now(tz_name: Optional[str] = None, ref_dt: Optional[datetime] = None) -> datetime:
    """Get current datetime in the location's timezone."""
    if ref_dt is not None:
        if ref_dt.tzinfo is None:
            ref_dt = ref_dt.replace(tzinfo=timezone.utc)
        if tz_name:
            try:
                tz = zoneinfo.ZoneInfo(tz_name)
                return ref_dt.astimezone(tz)
            except Exception:
                pass
        return ref_dt

    if tz_name:
        try:
            tz = zoneinfo.ZoneInfo(tz_name)
            return datetime.now(tz)
        except Exception:
            pass
    return datetime.now(timezone.utc)

def resolve_time(
    expression: Optional[str] = None,
    query: Optional[str] = None,
    tz_name: Optional[str] = None,
    utc_offset_seconds: int = 0,
    ref_dt: Optional[datetime] = None,
    is_followup: bool = False,
    prior_target: Optional[Dict[str, Any]] = None
) -> TimeTarget:
    """
    Deterministic time resolver conforming to WP3:
    - kind is one of now, hour, day, past, beyond_horizon.
    - Uses location's own timezone.
    - Explicit time ("1pm", "noon", "8am", "2am") wins.
    - "Today" means location's local date.
    - "Next Friday" computed from local date.
    - Carry-over applies only to follow-ups with no time expression.
    - Past target gets "that time has already passed" plus current conditions.
    - Target beyond horizon (> 16 days, "three months", "next month") is refused with no data shown.
    - States target and any assumption (e.g. "Assuming tomorrow 12:00").
    """
    loc_now = get_location_now(tz_name, ref_dt)
    today_date = loc_now.date()

    text = f"{expression or ''} {query or ''}".strip().lower()

    # 1. Horizon check: beyond 16 days (e.g., next month, 3 months, 2 weeks+, 30 days)
    horizon_patterns = [
        r"\b(?:next\s+month|in\s+a\s+month|three\s+months|3\s+months|next\s+year|in\s+a\s+year)\b",
        r"\b(?:in\s+(?:1[7-9]|[2-9]\d+)\s+days)\b",
        r"\b(?:in\s+(?:[3-9]|\d{2,})\s+weeks)\b"
    ]
    if any(re.search(pat, text) for pat in horizon_patterns):
        return TimeTarget(
            kind="beyond_horizon",
            iso=None,
            assumed="Beyond 16-day forecast horizon",
            display_target="Forecast horizon exceeded (Beyond 16 days)"
        )

    # 2. Past check: e.g. yesterday, last night, last week, 2 days ago
    past_patterns = [
        r"\b(?:yesterday|last\s+night|last\s+week|earlier\s+today|past\s+weather|days?\s+ago)\b"
    ]
    if any(re.search(pat, text) for pat in past_patterns):
        return TimeTarget(
            kind="past",
            iso=None,
            assumed="That time has already passed",
            display_target="Past time elapsed (That time has already passed)"
        )

    # 3. Check for carry-over if this is a follow-up with no time expression
    has_time_phrase = bool(re.search(
        r"\b(?:today|tomorrow|yesterday|tonight|evening|morning|afternoon|noon|night|weekend|saturday|sunday|"
        r"monday|tuesday|wednesday|thursday|friday|next\s+[a-z]+|\d{1,2}\s*(?:am|pm)|at\s+\d{1,2}(?::\d{2})?)\b",
        text
    ))

    if is_followup and not has_time_phrase and prior_target:
        prior_kind = prior_target.get("kind", "now")
        if prior_kind in ("hour", "day"):
            return TimeTarget(
                kind=prior_kind,
                iso=prior_target.get("iso"),
                assumed=prior_target.get("assumed"),
                target_hour=prior_target.get("target_hour"),
                target_date=prior_target.get("target_date"),
                display_target=prior_target.get("display_target")
            )

    # If no temporal text at all, default to "now"
    if not has_time_phrase and not any(k in text for k in ["now", "right now", "currently", "at the moment"]):
        return TimeTarget(
            kind="now",
            iso=loc_now.strftime("%Y-%m-%dT%H:00"),
            target_date=today_date.isoformat(),
            target_hour=loc_now.strftime("%H:00"),
            display_target="Current model conditions"
        )

    if any(k in text for k in ["now", "right now", "currently", "at the moment"]):
        # If user explicitly asked for "right now"
        return TimeTarget(
            kind="now",
            iso=loc_now.strftime("%Y-%m-%dT%H:00"),
            target_date=today_date.isoformat(),
            target_hour=loc_now.strftime("%H:00"),
            display_target="Current model conditions"
        )

    # 4. Resolve Target Date
    target_date = today_date
    date_assumed = None

    if "tomorrow" in text:
        target_date = today_date + timedelta(days=1)
        date_assumed = "tomorrow"
    elif "this weekend" in text or "weekend" in text:
        # Next Saturday
        days_ahead = (5 - today_date.weekday()) % 7
        if days_ahead == 0 and loc_now.hour >= 18:
            days_ahead = 7
        target_date = today_date + timedelta(days=days_ahead)
        date_assumed = f"Saturday {target_date.strftime('%b %d')}"
    elif re.search(r"\bnext\s+(friday|saturday|sunday|monday|tuesday|wednesday|thursday)\b", text):
        m = re.search(r"\bnext\s+(friday|saturday|sunday|monday|tuesday|wednesday|thursday)\b", text)
        day_name = m.group(1).lower()
        target_weekday = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"].index(day_name)
        days_ahead = (target_weekday - today_date.weekday()) % 7
        if days_ahead == 0:
            days_ahead = 7
        target_date = today_date + timedelta(days=days_ahead)
        date_assumed = f"next {day_name.capitalize()}"
    elif re.search(r"\bin\s+(\d+)\s+days?\b", text):
        m = re.search(r"\bin\s+(\d+)\s+days?\b", text)
        num_days = int(m.group(1))
        if num_days > 16:
            return TimeTarget(kind="beyond_horizon", assumed="Beyond 16-day forecast horizon")
        target_date = today_date + timedelta(days=num_days)
        date_assumed = f"in {num_days} days"
    elif "today" in text:
        target_date = today_date
        date_assumed = "today"

    # 5. Resolve Explicit Target Hour
    # Explicit times win ("1pm", "noon", "8am", "2am", "11:00 am", "10:59 am", etc.)
    target_hour = None
    hour_assumed = None

    # Check for specific HH:MM am/pm or HH am/pm
    m_time = re.search(r"\b(\d{1,2})(?::(\d{2}))?\s*(am|pm)\b", text)
    if m_time:
        raw_h = int(m_time.group(1))
        raw_m = int(m_time.group(2) or 0)
        meridiem = m_time.group(3).lower()
        if meridiem == "pm" and raw_h < 12:
            raw_h += 12
        elif meridiem == "am" and raw_h == 12:
            raw_h = 0
        target_hour = f"{raw_h:02d}:00"
        hour_assumed = None  # Explicit hour, not assumed
    elif "noon" in text:
        target_hour = "12:00"
        hour_assumed = None
    elif "midnight" in text:
        target_hour = "00:00"
        hour_assumed = None
    elif "this evening" in text or "evening" in text or "tonight" in text:
        target_hour = "18:00"
        hour_assumed = "Assuming 18:00"
    elif "morning" in text:
        target_hour = "08:00"
        hour_assumed = "Assuming 08:00"
    elif "afternoon" in text:
        target_hour = "14:00"
        hour_assumed = "Assuming 14:00"

    # 6. Default Hour if only Date was given
    if not target_hour:
        # Rule: A target date with no explicit hour assumes 12:00
        target_hour = "12:00"
        if date_assumed:
            hour_assumed = f"Assuming {date_assumed} 12:00"
        else:
            hour_assumed = "Assuming 12:00"
        kind = "day"
    else:
        kind = "hour"
        # If target was for today, but explicit hour has already passed:
        if target_date == today_date:
            h_int = int(target_hour.split(":")[0])
            if h_int < loc_now.hour:
                # If user said "2am" without "today", e.g. "is it okay to cycle at 2am in Bhopal?",
                # they typically mean upcoming 2am (tomorrow early morning)
                if "today" not in text:
                    target_date = today_date + timedelta(days=1)
                    date_assumed = "tomorrow"
                else:
                    return TimeTarget(
                        kind="past",
                        iso=f"{today_date.isoformat()}T{target_hour}",
                        target_hour=target_hour,
                        target_date=today_date.isoformat(),
                        assumed="That time has already passed",
                        display_target=f"That time ({target_hour}) has already passed today"
                    )

    # Horizon check on resolved target date
    days_from_now = (target_date - today_date).days
    if days_from_now > 16:
        return TimeTarget(kind="beyond_horizon", assumed="Beyond 16-day forecast horizon")

    iso_str = f"{target_date.isoformat()}T{target_hour}"
    
    # Compose assumed explanation
    assumed_parts = []
    if date_assumed and date_assumed not in ["today"]:
        assumed_parts.append(date_assumed)
    if hour_assumed:
        assumed_text = hour_assumed
    elif date_assumed:
        assumed_text = f"Assuming {date_assumed} {target_hour}"
    else:
        assumed_text = f"Target {target_hour}"

    return TimeTarget(
        kind=kind,
        iso=iso_str,
        assumed=assumed_text,
        target_hour=target_hour,
        target_date=target_date.isoformat()
    )
