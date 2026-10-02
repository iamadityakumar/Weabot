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
    <div className="my-2 bg-[#faf9fe] hover:bg-[#f7f5fd] border border-[#ede9f5] rounded-2xl p-3 text-gray-800 text-xs shadow-xs transition-all">
      <div
        className="flex items-center justify-between cursor-pointer select-none"
        onClick={() => setExpanded(!expanded)}
      >
        <div className="flex items-center gap-2 font-medium text-gray-700">
          <div className="w-6 h-6 rounded-lg bg-purple-100 flex items-center justify-center text-purple-700">
            <Compass className="w-3.5 h-3.5" />
          </div>
          <span>
            Live Open-Meteo Grounding: <strong className="text-gray-900 font-semibold">{locationName}</strong>
          </span>
        </div>
        <div className="flex items-center gap-2.5">
          <span className="font-semibold text-purple-700 text-sm">
            {temp !== undefined ? `${temp}°C` : ''}
          </span>
          <div className="w-5 h-5 rounded-md hover:bg-purple-100/60 flex items-center justify-center text-gray-400">
            {expanded ? <ChevronUp className="w-3.5 h-3.5" /> : <ChevronDown className="w-3.5 h-3.5" />}
          </div>
        </div>
      </div>

      {expanded && (
        <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 mt-3 pt-3 border-t border-purple-100/80 animate-fadeIn">
          <div className="flex items-center gap-2.5 p-2 bg-white rounded-xl border border-gray-100 shadow-2xs">
            <div className="p-1.5 rounded-lg bg-amber-50 text-amber-600">
              <Thermometer className="w-4 h-4" />
            </div>
            <div>
              <div className="text-[10px] text-gray-400 font-medium uppercase tracking-wider">Temp / Feels</div>
              <div className="font-semibold text-gray-800">{temp}°C / {apparentTemp ?? temp}°C</div>
            </div>
          </div>

          <div className="flex items-center gap-2.5 p-2 bg-white rounded-xl border border-gray-100 shadow-2xs">
            <div className="p-1.5 rounded-lg bg-sky-50 text-sky-600">
              <Wind className="w-4 h-4" />
            </div>
            <div>
              <div className="text-[10px] text-gray-400 font-medium uppercase tracking-wider">Wind / Gusts</div>
              <div className="font-semibold text-gray-800">{wind} km/h {gusts ? `(${gusts}g)` : ''}</div>
            </div>
          </div>

          <div className="flex items-center gap-2.5 p-2 bg-white rounded-xl border border-gray-100 shadow-2xs">
            <div className="p-1.5 rounded-lg bg-blue-50 text-blue-600">
              <CloudRain className="w-4 h-4" />
            </div>
            <div>
              <div className="text-[10px] text-gray-400 font-medium uppercase tracking-wider">Precip / Prob</div>
              <div className="font-semibold text-gray-800">{precip} mm ({precipProb ?? 0}%)</div>
            </div>
          </div>

          <div className="flex items-center gap-2.5 p-2 bg-white rounded-xl border border-gray-100 shadow-2xs">
            <div className="p-1.5 rounded-lg bg-orange-50 text-orange-600">
              <Sun className="w-4 h-4" />
            </div>
            <div>
              <div className="text-[10px] text-gray-400 font-medium uppercase tracking-wider">UV Index</div>
              <div className="font-semibold text-gray-800">{uv ?? 0.0}</div>
            </div>
          </div>

          {curr.time && (
            <div className="col-span-2 sm:col-span-4 text-[10px] text-gray-400 flex items-center gap-1.5 mt-1 pl-1">
              <Clock className="w-3 h-3 text-gray-400" />
              <span>Observation Time: {curr.time} (TZ: {weather.timezone || 'auto'})</span>
            </div>
          )}
        </div>
      )}
    </div>
  );
}
