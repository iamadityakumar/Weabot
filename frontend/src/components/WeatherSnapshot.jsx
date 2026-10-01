import React, { useState } from 'react';
import { CloudRain, Wind, Thermometer, Sun, ChevronDown, ChevronUp, Clock, Compass } from 'lucide-react';

export default function WeatherSnapshot({ weather, sessionFacts }) {
  const [expanded, setExpanded] = useState(false);

  if (!weather || !weather.current) return null;

  const curr = weather.current;
  const temp = curr.temperature_2m;
  const apparentTemp = curr.apparent_temperature;
  const wind = curr.wind_speed_10m;
  const gusts = curr.wind_gusts_10m;
  const precip = curr.precipitation;
  const precipProb = curr.precipitation_probability;
  const uv = curr.uv_index;
  const locationName = sessionFacts?.location_name || 'Observed Location';

  return (
    <div className="my-2 p-3 bg-slate-900/60 border border-slate-700/60 rounded-xl text-slate-200 text-xs shadow-inner">
      <div
        className="flex items-center justify-between cursor-pointer select-none"
        onClick={() => setExpanded(!expanded)}
      >
        <div className="flex items-center gap-2 font-medium text-slate-300">
          <Compass className="w-4 h-4 text-cyan-400" />
          <span>Live Open-Meteo Weather Snapshot: <strong>{locationName}</strong></span>
        </div>
        <div className="flex items-center gap-3">
          <span className="font-semibold text-cyan-300">{temp !== undefined ? `${temp}°C` : ''}</span>
          {expanded ? <ChevronUp className="w-4 h-4 text-slate-400" /> : <ChevronDown className="w-4 h-4 text-slate-400" />}
        </div>
      </div>

      {expanded && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 mt-3 pt-3 border-t border-slate-800">
          <div className="flex items-center gap-2 p-2 bg-slate-800/40 rounded-lg">
            <Thermometer className="w-4 h-4 text-amber-400" />
            <div>
              <div className="text-[10px] text-slate-400 uppercase tracking-wider">Temp / Feels</div>
              <div className="font-semibold text-slate-100">{temp}°C / {apparentTemp ?? temp}°C</div>
            </div>
          </div>

          <div className="flex items-center gap-2 p-2 bg-slate-800/40 rounded-lg">
            <Wind className="w-4 h-4 text-sky-400" />
            <div>
              <div className="text-[10px] text-slate-400 uppercase tracking-wider">Wind / Gusts</div>
              <div className="font-semibold text-slate-100">{wind} km/h {gusts ? `(${gusts}g)` : ''}</div>
            </div>
          </div>

          <div className="flex items-center gap-2 p-2 bg-slate-800/40 rounded-lg">
            <CloudRain className="w-4 h-4 text-blue-400" />
            <div>
              <div className="text-[10px] text-slate-400 uppercase tracking-wider">Precip / Prob</div>
              <div className="font-semibold text-slate-100">{precip} mm ({precipProb ?? 0}%)</div>
            </div>
          </div>

          <div className="flex items-center gap-2 p-2 bg-slate-800/40 rounded-lg">
            <Sun className="w-4 h-4 text-orange-400" />
            <div>
              <div className="text-[10px] text-slate-400 uppercase tracking-wider">UV Index</div>
              <div className="font-semibold text-slate-100">{uv ?? 0.0}</div>
            </div>
          </div>

          {curr.time && (
            <div className="col-span-2 sm:col-span-4 text-[10px] text-slate-500 flex items-center gap-1 mt-1">
              <Clock className="w-3 h-3" />
              <span>Observation Timestamp: {curr.time} (Timezone: {weather.timezone || 'auto'})</span>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
