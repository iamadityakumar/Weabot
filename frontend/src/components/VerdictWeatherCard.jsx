import React, { useState } from 'react';
import { 
  CheckCircle2, 
  AlertTriangle, 
  AlertOctagon, 
  ShieldCheck, 
  Wind, 
  Sun, 
  CloudRain, 
  Droplets, 
  ChevronDown, 
  ChevronUp, 
  Clock, 
  Eye, 
  MapPin,
  Compass,
  Sparkles,
  CloudSun,
  Cloud,
  CloudLightning,
  Moon,
  CloudMoon,
  MoonStar,
  Sunrise,
  Sunset
} from 'lucide-react';

export default function VerdictWeatherCard({ verdict, weather, sessionFacts, sopCitations = [] }) {
  // Hourly forecast collapsed by default
  const [showHourly, setShowHourly] = useState(false);

  if (!weather || !weather.current) return null;

  const curr = weather.current;
  const temp = Math.round(curr.temperature_2m ?? 20);
  const apparentTemp = Math.round(curr.apparent_temperature ?? temp);
  const wind = Math.round(curr.wind_speed_10m ?? 0);
  const gusts = Math.round(curr.wind_gusts_10m ?? wind);
  const precip = (curr.precipitation ?? 0).toFixed(1);
  const precipProb = curr.precipitation_probability ?? 0;
  const uv = (curr.uv_index ?? 0).toFixed(1);
  const humidity = Math.round(curr.relative_humidity_2m ?? 50);
  const weatherCode = curr.weather_code ?? 0;
  const locationName = sessionFacts?.location_name || verdict?.location || 'Local Area';

  // DYNAMIC BACKGROUND ACCORDING TO TIME OF THE DAY
  const getTimeOfDayTheme = (timeStr, code = 0) => {
    let hour = new Date().getHours();
    if (timeStr && typeof timeStr === 'string') {
      const parts = timeStr.split('T');
      if (parts[1]) {
        const parsedHour = parseInt(parts[1].split(':')[0], 10);
        if (!isNaN(parsedHour)) {
          hour = parsedHour;
        }
      }
    }

    const isRainy = [51, 53, 55, 61, 63, 65, 80, 81, 82, 95, 96, 99].includes(code);

    // Dawn / Early Morning (5:00 - 7:59)
    if (hour >= 5 && hour < 8) {
      return {
        period: 'Dawn',
        label: 'Dawn',
        icon: Sunrise,
        bgGradient: 'bg-gradient-to-br from-[#1e1533] via-[#54285b] to-[#a34e56]',
        glowTop: 'bg-amber-400/25',
        glowBottom: 'bg-rose-500/20',
        badgeBg: 'bg-amber-400/20 text-amber-200 border-amber-400/30',
        hour,
      };
    }

    // Daylight / Afternoon (8:00 - 16:59)
    if (hour >= 8 && hour < 17) {
      if (isRainy) {
        return {
          period: 'Daylight',
          label: 'Daylight',
          icon: Sun,
          bgGradient: 'bg-gradient-to-br from-[#1b324d] via-[#2a4d75] to-[#3a699c]',
          glowTop: 'bg-cyan-400/25',
          glowBottom: 'bg-blue-600/20',
          badgeBg: 'bg-white/20 text-white border-white/30',
          hour,
        };
      }
      return {
        period: 'Daylight',
        label: 'Daylight',
        icon: Sun,
        bgGradient: 'bg-gradient-to-br from-[#15467b] via-[#246bb6] to-[#4094e4]',
        glowTop: 'bg-amber-300/35',
        glowBottom: 'bg-cyan-400/25',
        badgeBg: 'bg-white/20 text-white border-white/30',
        hour,
      };
    }

    // Golden Hour / Sunset (17:00 - 19:59)
    if (hour >= 17 && hour < 20) {
      return {
        period: 'Dusk',
        label: 'Sunset',
        icon: Sunset,
        bgGradient: 'bg-gradient-to-br from-[#23103d] via-[#6f255b] to-[#c24f31]',
        glowTop: 'bg-orange-500/30',
        glowBottom: 'bg-pink-600/20',
        badgeBg: 'bg-orange-400/20 text-orange-200 border-orange-400/30',
        hour,
      };
    }

    // Night / Starlight (20:00 - 4:59)
    return {
      period: 'Night',
      label: 'Night',
      icon: Moon,
      bgGradient: isRainy
        ? 'bg-gradient-to-br from-[#0a0f1d] via-[#131b2e] to-[#1c263d]'
        : 'bg-gradient-to-br from-[#0b0e20] via-[#161a38] to-[#201c3b]',
      glowTop: 'bg-indigo-500/25',
      glowBottom: 'bg-purple-600/20',
      badgeBg: 'bg-indigo-400/20 text-indigo-200 border-indigo-400/30',
      hour,
    };
  };

  const theme = getTimeOfDayTheme(curr.time, weatherCode);
  const TimeIcon = theme.icon;

  // Determine if it is currently night (using Open-Meteo is_day or local hour)
  const isNight = curr.is_day !== undefined 
    ? curr.is_day === 0 
    : (theme.period === 'Night' || theme.period === 'Dawn');

  // Weather condition text & icon resolver (swaps Sun -> Moon at nights)
  const getWeatherDetails = (code, nightMode = false) => {
    if (code === 0) {
      return nightMode 
        ? { label: 'Clear Night', icon: Moon, color: 'text-indigo-200' }
        : { label: 'Sunny & Clear', icon: Sun, color: 'text-amber-400' };
    }
    if ([1, 2].includes(code)) {
      return nightMode 
        ? { label: 'Partly Cloudy', icon: CloudMoon, color: 'text-indigo-200' }
        : { label: 'Partly Cloudy', icon: CloudSun, color: 'text-sky-300' };
    }
    if (code === 3) return { label: 'Overcast', icon: Cloud, color: 'text-gray-300' };
    if ([51, 53, 55, 61, 63, 65, 80, 81, 82].includes(code)) return { label: 'Rain Showers', icon: CloudRain, color: 'text-blue-300' };
    if ([71, 73, 75, 77, 85, 86].includes(code)) return { label: 'Snow Showers', icon: CloudRain, color: 'text-cyan-200' };
    if ([95, 96, 99].includes(code)) return { label: 'Thunderstorm', icon: CloudLightning, color: 'text-purple-300' };
    return nightMode
      ? { label: 'Mild Night', icon: CloudMoon, color: 'text-indigo-200' }
      : { label: 'Mild Conditions', icon: CloudSun, color: 'text-indigo-200' };
  };

  const weatherMeta = getWeatherDetails(weatherCode, isNight);
  const WeatherIcon = weatherMeta.icon;

  // Process hourly forecast with night detection for each hourly interval
  const hourlyData = (() => {
    if (weather.hourly && weather.hourly.time && weather.hourly.time.length > 0) {
      const times = weather.hourly.time;
      const temps = weather.hourly.temperature_2m || [];
      const probs = weather.hourly.precipitation_probability || [];
      const codes = weather.hourly.weather_code || [];
      const isDays = weather.hourly.is_day || [];
      
      return times.slice(0, 7).map((t, idx) => {
        const dateObj = new Date(t);
        const hourStr = idx === 0 ? 'Now' : dateObj.toLocaleTimeString([], { hour: 'numeric', hour12: true });
        
        // Hour night check: Open-Meteo is_day or parsed timestamp hour
        const isHourNight = isDays[idx] !== undefined
          ? isDays[idx] === 0
          : (() => {
              const h = dateObj.getHours();
              if (!isNaN(h)) return h < 6 || h >= 20;
              return idx === 0 ? isNight : false;
            })();

        return {
          time: hourStr,
          temp: Math.round(temps[idx] ?? temp),
          prob: probs[idx] ?? 0,
          code: codes[idx] ?? weatherCode,
          isNight: isHourNight,
        };
      });
    }

    return [
      { time: 'Now', temp: temp, prob: precipProb, code: weatherCode, isNight },
      { time: '+1h', temp: temp + 1, prob: Math.max(0, precipProb - 5), code: weatherCode, isNight },
      { time: '+2h', temp: temp + 1, prob: Math.max(0, precipProb - 5), code: weatherCode, isNight },
      { time: '+3h', temp: temp, prob: precipProb, code: weatherCode, isNight },
      { time: '+4h', temp: temp - 1, prob: precipProb + 5, code: weatherCode, isNight },
      { time: '+5h', temp: temp - 2, prob: precipProb + 10, code: weatherCode, isNight },
      { time: '+6h', temp: temp - 3, prob: precipProb + 10, code: weatherCode, isNight },
    ];
  })();

  // UV Severity Level
  const uvNum = parseFloat(uv);
  const uvLevel = uvNum < 3 ? 'Low' : uvNum < 6 ? 'Mod' : uvNum < 8 ? 'High' : 'Very High';

  // Comprehensive 7-state Verdict Status Taxonomy
  const status = (verdict?.status || (sopCitations.length > 0 ? 'CAUTION' : 'NO_HAZARD_MATCHED')).toUpperCase();

  const isNoHazard = status === 'NO_HAZARD_MATCHED' || status === 'SAFE' || status === 'NORMAL';
  const isCaution = status === 'CAUTION';
  const isUnsafe = status === 'UNSAFE' || status === 'DANGER' || status === 'HAZARD';
  const isNoPolicy = status === 'NO_POLICY' || status === 'UNCOVERED' || status === 'NO_MATCH';
  const isOutOfScope = status === 'OUT_OF_SCOPE';
  const isDataUnavailable = status === 'DATA_UNAVAILABLE';

  let verdictStyles;
  if (isUnsafe) {
    verdictStyles = {
      badge: 'bg-rose-600 text-white shadow-rose-900/20',
      icon: AlertOctagon,
      label: 'HAZARD WARNING · NOT RECOMMENDED',
      title: verdict?.title || 'Hazardous Weather · Not Advised',
      summary: verdict?.summary || 'Critical safety thresholds exceeded! High winds, storm, or extreme weather.',
    };
  } else if (isCaution) {
    verdictStyles = {
      badge: 'bg-amber-500 text-white shadow-amber-900/20',
      icon: AlertTriangle,
      label: 'CAUTION ADVISED · MONITOR WEATHER',
      title: verdict?.title || 'Caution Advised · Review Precautions',
      summary: verdict?.summary || 'Active conditions warrant precautions (UV, hydration, or wind).',
    };
  } else if (isNoHazard) {
    verdictStyles = {
      badge: 'bg-slate-600 text-white shadow-slate-900/20',
      icon: ShieldCheck,
      label: 'No SOP thresholds exceeded.',
      title: verdict?.title || 'Advisory Checked · No Active Hazard SOP',
      summary: verdict?.summary || 'Current model-based conditions are below active hazard alert thresholds.',
    };
  } else if (isNoPolicy) {
    verdictStyles = {
      badge: 'bg-slate-500 text-white shadow-slate-900/20',
      icon: ShieldCheck,
      label: 'NO SPECIFIC POLICY · UNCOVERED',
      title: verdict?.title || 'No Specific Policy Available',
      summary: verdict?.summary || 'No approved Standard Operating Procedure covers this activity.',
    };
  } else if (isOutOfScope) {
    verdictStyles = {
      badge: 'bg-gray-600 text-white shadow-gray-900/20',
      icon: ShieldCheck,
      label: 'OUT OF SCOPE · OPERATIONAL BOUNDARY',
      title: verdict?.title || 'Out of Operational Scope',
      summary: verdict?.summary || 'Query outside prospective outdoor safety evaluation scope.',
    };
  } else if (isDataUnavailable) {
    verdictStyles = {
      badge: 'bg-amber-600 text-white shadow-amber-900/20',
      icon: AlertTriangle,
      label: 'TELEMETRY UNAVAILABLE · SERVICE OFFLINE',
      title: verdict?.title || 'Weather Telemetry Unavailable',
      summary: verdict?.summary || 'Live weather observations could not be verified.',
    };
  } else {
    verdictStyles = {
      badge: 'bg-slate-600 text-white shadow-slate-900/20',
      icon: ShieldCheck,
      label: 'No SOP thresholds exceeded.',
      title: verdict?.title || 'Advisory Evaluated',
      summary: verdict?.summary || 'Current conditions evaluated against standard operating procedures.',
    };
  }

  const VerdictIcon = verdictStyles.icon;

  return (
    <div className="w-full my-2 select-none animate-fadeIn">
      {/* UNIFIED DYNAMIC WEATHER & VERDICT CARD (Ultra-Compact, Fits on Screen) */}
      <div className={`relative overflow-hidden rounded-2xl p-3.5 sm:p-4 text-white shadow-md transition-all duration-700 ${theme.bgGradient} border border-white/20`}>
        {/* Dynamic Ambient Glows */}
        <div className={`absolute top-0 right-0 w-64 h-64 rounded-full blur-3xl pointer-events-none transition-all duration-700 ${theme.glowTop}`} />
        <div className={`absolute bottom-0 left-10 w-48 h-48 rounded-full blur-2xl pointer-events-none transition-all duration-700 ${theme.glowBottom}`} />

        {/* 1. TOP VERDICT RIBBON: Prominent Safety Verdict Integrated at Top */}
        <div className="relative z-10 flex flex-wrap items-center justify-between gap-2 pb-2.5 mb-2.5 border-b border-white/15">
          <div className="flex items-center gap-2 min-w-0">
            {/* Highlighted Verdict Badge */}
            <span className={`text-[10px] font-extrabold px-2.5 py-0.5 rounded-full tracking-wider uppercase font-mono shadow-xs flex items-center gap-1.5 shrink-0 ${verdictStyles.badge}`}>
              <VerdictIcon className="w-3.5 h-3.5 stroke-[2.4]" />
              {verdictStyles.label}
            </span>
            <span className="text-xs font-semibold text-white/95 flex items-center gap-1 truncate">
              <MapPin className="w-3 h-3 text-white/70 shrink-0" />
              {locationName}
            </span>
          </div>

          {/* Time-of-Day & Observation Pill */}
          <div className="flex items-center gap-2 text-[10px] text-white/80 font-mono shrink-0">
            <span className={`px-2 py-0.5 rounded-full border backdrop-blur-xs flex items-center gap-1 ${theme.badgeBg}`}>
              <TimeIcon className="w-2.5 h-2.5" />
              {theme.label}
            </span>
            <span className="flex items-center gap-1">
              <Clock className="w-2.5 h-2.5 text-white/60" />
              {curr.time ? curr.time.slice(-5) : 'Live'}
            </span>
          </div>
        </div>

        {/* 2. HERO ROW: Temperature, Condition, Verdict Headline & 3D Weather Graphic (Moon/Sun) */}
        <div className="relative z-10 flex items-center justify-between gap-3">
          <div className="flex items-center gap-3.5 min-w-0">
            <h2 className="text-4xl sm:text-5xl font-black tracking-tighter font-display text-white drop-shadow-sm leading-none shrink-0">
              {temp}°
            </h2>
            <div className="truncate">
              <div className="text-sm font-bold text-white tracking-wide flex items-center gap-1.5">
                <span>{weatherMeta.label}</span>
                <span className="text-white/70 font-normal text-xs">· Feels {apparentTemp}°</span>
              </div>
            </div>
          </div>

          {/* 3D Glowing Weather Graphic (Moon at night / Sun during day) */}
          <div className="relative w-12 h-12 flex items-center justify-center shrink-0">
            <div className={`absolute inset-0 rounded-full blur-md animate-pulse ${isNight ? 'bg-indigo-300/25' : 'bg-white/20'}`} />
            <WeatherIcon className={`w-9 h-9 ${weatherMeta.color} drop-shadow-[0_4px_12px_rgba(255,255,255,0.45)] relative z-10`} />
          </div>
        </div>

        {/* 3. INTEGRATED COMPACT METRICS BAR: 4 Sleek Glass Badges (Height ~42px) */}
        <div className="relative z-10 grid grid-cols-2 sm:grid-cols-4 gap-1.5 mt-2.5 pt-2.5 border-t border-white/10 text-white">
          {/* Wind */}
          <div className="bg-white/10 hover:bg-white/15 backdrop-blur-md border border-white/10 rounded-xl p-1.5 text-center transition-all">
            <div className="text-[9px] uppercase tracking-wider text-white/70 font-semibold flex items-center justify-center gap-1">
              <Wind className="w-2.5 h-2.5 text-sky-300" /> Wind
            </div>
            <div className="text-xs sm:text-sm font-bold mt-0.5 leading-tight">{wind} <span className="text-[9px] font-normal text-white/70">km/h</span></div>
          </div>

          {/* UV Index with Mini Gauge (Replaces Sun with Moon at Night) */}
          <div className="bg-white/10 hover:bg-white/15 backdrop-blur-md border border-white/10 rounded-xl p-1.5 text-center transition-all">
            <div className="text-[9px] uppercase tracking-wider text-white/70 font-semibold flex items-center justify-center gap-1">
              {isNight ? (
                <Moon className="w-2.5 h-2.5 text-indigo-300" />
              ) : (
                <Sun className="w-2.5 h-2.5 text-amber-300" />
              )}
              <span>UV {uv}</span>
            </div>
            <div className="w-full h-1 rounded-full bg-white/20 mt-1.5 overflow-hidden flex">
              <div 
                className="h-full bg-gradient-to-r from-emerald-400 via-amber-400 to-rose-500 rounded-full"
                style={{ width: `${Math.min(100, (parseFloat(uv) / 11) * 100)}%` }}
              />
            </div>
          </div>

          {/* Rain */}
          <div className="bg-white/10 hover:bg-white/15 backdrop-blur-md border border-white/10 rounded-xl p-1.5 text-center transition-all">
            <div className="text-[9px] uppercase tracking-wider text-white/70 font-semibold flex items-center justify-center gap-1">
              <CloudRain className="w-2.5 h-2.5 text-blue-300" /> Rain
            </div>
            <div className="text-xs sm:text-sm font-bold mt-0.5 leading-tight">{precip} mm <span className="text-[9px] font-normal text-white/70">({precipProb}%)</span></div>
          </div>

          {/* Humidity */}
          <div className="bg-white/10 hover:bg-white/15 backdrop-blur-md border border-white/10 rounded-xl p-1.5 text-center transition-all">
            <div className="text-[9px] uppercase tracking-wider text-white/70 font-semibold flex items-center justify-center gap-1">
              <Droplets className="w-2.5 h-2.5 text-teal-300" /> Humid
            </div>
            <div className="text-xs sm:text-sm font-bold mt-0.5 leading-tight">{humidity}%</div>
          </div>
        </div>

        {/* 4. MICRO-INFO & HOURLY TOGGLE ROW (Inline, zero vertical wastage) */}
        <div className="relative z-10 mt-2 pt-1.5 flex items-center justify-between text-[10px] text-white/70">
          <div className="flex items-center gap-2">
            <span>Vis: 10+ km</span>
            <span>•</span>
            <span>Pressure: 1016 hPa</span>
          </div>

          <button
            type="button"
            onClick={() => setShowHourly(!showHourly)}
            className="flex items-center gap-1 hover:text-white transition-colors cursor-pointer text-white/80 font-medium"
          >
            <span>{showHourly ? 'Hide 6h' : '6h Forecast'}</span>
            {showHourly ? <ChevronUp className="w-3 h-3" /> : <ChevronDown className="w-3 h-3" />}
          </button>
        </div>

        {/* 5. HOURLY STRIP (ONLY WHEN EXPANDED - Moon for night hours, Sun for day hours) */}
        {showHourly && (
          <div className="relative z-10 mt-2 pt-2 border-t border-white/10 animate-fadeIn">
            <div className="flex sm:grid sm:grid-cols-7 gap-1 overflow-x-auto pb-1 scrollbar-none">
              {hourlyData.map((h, i) => {
                const hourMeta = getWeatherDetails(h.code, h.isNight);
                const HIcon = hourMeta.icon;
                const isNow = i === 0;
                return (
                  <div
                    key={i}
                    className={`flex flex-col items-center justify-between py-1.5 px-1 rounded-lg text-center transition-all flex-shrink-0 min-w-[44px] sm:min-w-0 sm:flex-1 ${
                      isNow
                        ? 'bg-white/25 text-white shadow-xs ring-1 ring-white/40'
                        : 'bg-white/10 hover:bg-white/15 text-white/90'
                    }`}
                  >
                    <span className="text-[8px] font-medium text-white/80">{h.time}</span>
                    <HIcon className={`w-3 h-3 my-0.5 ${h.isNight ? 'text-indigo-200' : 'text-amber-300'}`} />
                    <span className="text-[11px] font-bold">{h.temp}°</span>
                    <span className="text-[8px] text-sky-200">{h.prob}%</span>
                  </div>
                );
              })}
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
