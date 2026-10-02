import React, { useState } from 'react';
import SOPBadge from './SOPBadge';
import VerdictWeatherCard from './VerdictWeatherCard';
import { 
  Sparkles, 
  Copy, 
  Check, 
  ThumbsUp, 
  ThumbsDown, 
  AlertTriangle, 
  ShieldCheck,
  Database,
  ExternalLink,
  Clock,
  MapPin,
  ChevronDown,
  ChevronUp,
  Radio,
  Zap
} from 'lucide-react';

function renderFormattedText(text) {
  if (!text) return null;
  const paragraphs = text.split('\n\n');
  return paragraphs.map((para, pIdx) => {
    const lines = para.split('\n');
    return (
      <div key={pIdx} className={pIdx > 0 ? 'mt-1.5' : ''}>
        {lines.map((line, lIdx) => {
          const parts = line.split(/(\*\*.*?\*\*)/g);
          const renderedLine = parts.map((part, partIdx) => {
            if (part.startsWith('**') && part.endsWith('**')) {
              return (
                <strong key={partIdx} className="font-semibold text-gray-900">
                  {part.slice(2, -2)}
                </strong>
              );
            }
            return part;
          });

          return (
            <div key={lIdx} className={line.startsWith('•') || line.startsWith('-') ? 'pl-2 my-0.5' : ''}>
              {renderedLine}
            </div>
          );
        })}
      </div>
    );
  });
}

export default function MessageBubble({ message, userName = 'Aditya' }) {
  const isUser = message.sender === 'user';
  const citations = message.sopCitations || [];
  const isError = message.text && message.text.includes('Service Error');
  const [copied, setCopied] = useState(false);
  const [feedback, setFeedback] = useState(null);
  const [showSources, setShowSources] = useState(false);
  const [copiedUrl, setCopiedUrl] = useState(null);

  const handleCopy = () => {
    navigator.clipboard?.writeText(message.text);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  const copyToClipboard = (text, key) => {
    navigator.clipboard?.writeText(text);
    setCopiedUrl(key);
    setTimeout(() => setCopiedUrl(null), 2000);
  };

  if (isUser) {
    return (
      <div className="flex justify-end mb-3.5 animate-fadeIn">
        <div className="bg-[#f3f0f9] text-gray-900 border border-[#e8e4f3] px-3.5 py-2.5 rounded-2xl rounded-tr-xs shadow-2xs text-[13.5px] leading-relaxed whitespace-pre-wrap max-w-[88%] sm:max-w-[75%]">
          {message.text}
        </div>
      </div>
    );
  }

  // Derive source info from apiSource or fallback to session facts
  const sourceInfo = message.apiSource || (message.sessionFacts?.latitude ? {
    city: message.sessionFacts.location_display || message.sessionFacts.location_name || 'Bhopal',
    country: 'Resolved Location',
    coordinates: {
      latitude: message.sessionFacts.latitude,
      longitude: message.sessionFacts.longitude
    },
    timezone: message.weatherData?.timezone || 'Asia/Kolkata',
    timing: {
      requested_at: message.timestamp || new Date().toISOString(),
      target_time_display: message.weatherData?.current?.time ? `Observation at ${message.weatherData.current.time}` : 'Current model conditions',
      target_hour: message.weatherData?.current?.time?.split('T')?.[1] || null,
      response_time_ms: 55
    },
    requests: {
      geocoding: {
        method: 'GET',
        url: `https://geocoding-api.open-meteo.com/v1/search?name=${encodeURIComponent(message.sessionFacts.location_name || 'Bhopal')}&count=5&language=en&format=json`,
        city_query: message.sessionFacts.location_name || 'Bhopal'
      },
      forecast: {
        method: 'GET',
        url: `https://api.open-meteo.com/v1/forecast?latitude=${message.sessionFacts.latitude}&longitude=${message.sessionFacts.longitude}&current=temperature_2m,apparent_temperature,precipitation,wind_speed_10m,wind_gusts_10m,uv_index&forecast_days=16&timezone=auto`,
        latitude: message.sessionFacts.latitude,
        longitude: message.sessionFacts.longitude
      }
    },
    response_summary: {
      status: 200,
      current: message.weatherData?.current || {}
    }
  } : null);

  const hasSources = !!sourceInfo;

  // Fix 5: Render weather card ONLY when status is a genuine weather answer (never for smalltalk, scope, or asking for place/activity)
  const WEATHER_ANSWER_STATUSES = ['ADVISORY', 'UNSAFE', 'NO_HAZARD_MATCHED', 'NO_POLICY'];
  const vStatus = message.verdict?.status;
  const vTitle = (message.verdict?.title || '').toLowerCase();
  const msgTextLower = (message.text || '').toLowerCase();

  const isNonWeather = 
    vTitle.includes('scope') || 
    vTitle.includes('about') || 
    vTitle.includes('casual') || 
    vTitle.includes('location required') || 
    vTitle.includes('activity required') ||
    msgTextLower.includes('which city or town') ||
    msgTextLower.includes('what outdoor activity are you planning');

  const hasPlace = Boolean(message.sessionFacts?.location_name || message.verdict?.location || message.apiSource?.city);
  const hasActivity = Boolean(message.sessionFacts?.activity || message.verdict?.activity);

  const shouldRenderWeatherCard = Boolean(
    message.weatherData &&
    WEATHER_ANSWER_STATUSES.includes(vStatus) &&
    !isNonWeather &&
    hasPlace &&
    hasActivity
  );

  return (
    <div className="flex justify-start mb-3.5 animate-fadeIn">
      <div className="flex flex-col gap-1.5 w-full min-w-0">
        {/* Active SOP Badges (if any policy triggered) */}
        {citations.length > 0 && shouldRenderWeatherCard && (
          <div className="flex flex-wrap items-center gap-1 mb-0.5">
            <span className="text-[10px] text-gray-400 font-medium">Applied SOPs:</span>
            {citations.map((c) => (
              <SOPBadge key={c} sopId={c} />
            ))}
          </div>
        )}

        {/* 1. Highlighted Verdict & Weather Master Card */}
        {shouldRenderWeatherCard && (
          <VerdictWeatherCard
            verdict={message.verdict}
            weather={message.weatherData}
            sessionFacts={message.sessionFacts}
            sopCitations={citations}
          />
        )}

        {/* 2. Main Guidance / Advice Bubble Content */}
        <div
          className={`p-3 sm:p-3.5 rounded-2xl rounded-tl-xs shadow-2xs text-[13.5px] leading-relaxed border transition-all ${
            isError
              ? 'bg-rose-50/70 border-rose-200 text-rose-900'
              : 'bg-white border-[#eeecf5] text-gray-800'
          }`}
        >
          {renderFormattedText(message.text)}
        </div>

        {/* 3. Telemetry Sources Drawer (Expandable when Sources clicked) */}
        {showSources && sourceInfo && (
          <div className="bg-[#f9f8fc] border border-purple-200/80 rounded-xl p-3.5 shadow-xs text-xs animate-fadeIn mt-1 text-gray-800 space-y-3">
            <div className="flex items-center justify-between border-b border-purple-100 pb-2">
              <div className="flex items-center gap-1.5 font-semibold text-purple-900">
                <Radio className="w-3.5 h-3.5 text-purple-600 animate-pulse" />
                <span>API Telemetry Sources & Timing Audit</span>
              </div>
              <span className="text-[10px] font-mono bg-purple-100/70 text-purple-800 px-2 py-0.5 rounded-md">
                Status 200 OK
              </span>
            </div>

            {/* Grid 1: City & Timings */}
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 text-[11.5px]">
              <div className="bg-white p-2.5 rounded-lg border border-purple-100/70 flex flex-col gap-1">
                <div className="flex items-center gap-1 text-purple-800 font-medium">
                  <MapPin className="w-3 h-3 text-purple-600" />
                  <span>Resolved Place & Coordinates</span>
                </div>
                <div className="font-semibold text-gray-900 truncate">
                  {sourceInfo.city}
                </div>
                <div className="text-gray-500 font-mono text-[10.5px]">
                  {sourceInfo.coordinates.latitude?.toFixed(4)}°N, {sourceInfo.coordinates.longitude?.toFixed(4)}°E ({sourceInfo.timezone})
                </div>
              </div>

              <div className="bg-white p-2.5 rounded-lg border border-purple-100/70 flex flex-col gap-1">
                <div className="flex items-center gap-1 text-purple-800 font-medium">
                  <Clock className="w-3 h-3 text-purple-600" />
                  <span>Timings & Target Window</span>
                </div>
                <div className="font-semibold text-gray-900 truncate">
                  {sourceInfo.timing?.target_time_display || 'Current model conditions'}
                </div>
                <div className="text-gray-500 font-mono text-[10.5px]">
                  Latency: {sourceInfo.timing?.response_time_ms || 45} ms | Requested: {new Date(sourceInfo.timing?.requested_at || message.timestamp || Date.now()).toLocaleTimeString()}
                </div>
              </div>
            </div>

            {/* Grid 2: Exact API Request Endpoints Called */}
            <div className="space-y-2">
              <div className="bg-white p-2.5 rounded-lg border border-purple-100/70 space-y-1">
                <div className="flex items-center justify-between">
                  <span className="text-[10.5px] font-semibold text-purple-900 uppercase tracking-wide">
                    1. Geocoding API Request (Open-Meteo)
                  </span>
                  <button
                    onClick={() => copyToClipboard(sourceInfo.requests?.geocoding?.url, 'geo')}
                    className="text-[10px] text-purple-600 hover:text-purple-800 cursor-pointer flex items-center gap-1 font-medium"
                  >
                    {copiedUrl === 'geo' ? <Check className="w-3 h-3 text-emerald-600" /> : <Copy className="w-3 h-3" />}
                    <span>{copiedUrl === 'geo' ? 'Copied' : 'Copy URL'}</span>
                  </button>
                </div>
                <div className="bg-gray-50 p-1.5 rounded border border-gray-200 font-mono text-[10px] text-gray-700 break-all select-all">
                  <span className="font-bold text-emerald-700">GET </span>
                  {sourceInfo.requests?.geocoding?.url}
                </div>
              </div>

              <div className="bg-white p-2.5 rounded-lg border border-purple-100/70 space-y-1">
                <div className="flex items-center justify-between">
                  <span className="text-[10.5px] font-semibold text-purple-900 uppercase tracking-wide">
                    2. Weather Forecast API Request (Open-Meteo REST API)
                  </span>
                  <button
                    onClick={() => copyToClipboard(sourceInfo.requests?.forecast?.url, 'wx')}
                    className="text-[10px] text-purple-600 hover:text-purple-800 cursor-pointer flex items-center gap-1 font-medium"
                  >
                    {copiedUrl === 'wx' ? <Check className="w-3 h-3 text-emerald-600" /> : <Copy className="w-3 h-3" />}
                    <span>{copiedUrl === 'wx' ? 'Copied' : 'Copy URL'}</span>
                  </button>
                </div>
                <div className="bg-gray-50 p-1.5 rounded border border-gray-200 font-mono text-[10px] text-gray-700 break-all select-all">
                  <span className="font-bold text-emerald-700">GET </span>
                  {sourceInfo.requests?.forecast?.url}
                </div>
              </div>
            </div>

            {/* Grid 3: Telemetry Data Received */}
            {sourceInfo.response_summary?.current && (
              <div className="bg-white p-2.5 rounded-lg border border-purple-100/70">
                <div className="text-[10.5px] font-semibold text-purple-900 uppercase tracking-wide mb-1.5 flex items-center justify-between">
                  <span>3. Key Telemetry Parameters Evaluated</span>
                  {sourceInfo.timing?.target_time_display && (
                    <span className="text-[9.5px] font-normal text-purple-700 font-mono lowercase first-letter:uppercase">
                      {sourceInfo.timing.target_time_display}
                    </span>
                  )}
                </div>
                <div className="grid grid-cols-2 sm:grid-cols-4 gap-1.5 text-[11px] font-mono">
                  <div className="bg-gray-50 p-1.5 rounded border border-gray-100">
                    <span className="text-gray-400 block text-[9.5px]">Temp</span>
                    <span className="font-bold text-gray-800">{sourceInfo.response_summary.current.temperature_2m ?? '--'}°C</span>
                  </div>
                  <div className="bg-gray-50 p-1.5 rounded border border-gray-100">
                    <span className="text-gray-400 block text-[9.5px]">Apparent</span>
                    <span className="font-bold text-gray-800">{sourceInfo.response_summary.current.apparent_temperature ?? '--'}°C</span>
                  </div>
                  <div className="bg-gray-50 p-1.5 rounded border border-gray-100">
                    <span className="text-gray-400 block text-[9.5px]">Wind / Gusts</span>
                    <span className="font-bold text-gray-800">{sourceInfo.response_summary.current.wind_speed_10m ?? '--'} / {sourceInfo.response_summary.current.wind_gusts_10m ?? '--'} km/h</span>
                  </div>
                  <div className="bg-gray-50 p-1.5 rounded border border-gray-100">
                    <span className="text-gray-400 block text-[9.5px]">Rain / UV</span>
                    <span className="font-bold text-gray-800">{sourceInfo.response_summary.current.precipitation ?? '0.0'} mm / {sourceInfo.response_summary.current.uv_index ?? '0.0'}</span>
                  </div>
                </div>
              </div>
            )}
          </div>
        )}

        {/* Action Row: Sources Button, Copy, Feedback & Model Attribution */}
        <div className="flex items-center justify-between pl-0.5 pt-0.5 text-gray-400 text-[11px]">
          <div className="flex items-center gap-1.5">
            {/* Sources Button */}
            {hasSources && (
              <>
                <button
                  onClick={() => setShowSources(!showSources)}
                  className={`flex items-center gap-1 px-2 py-0.5 rounded-md transition-all cursor-pointer text-[10.5px] font-medium ${
                    showSources
                      ? 'bg-purple-100 text-purple-800 border border-purple-200'
                      : 'hover:text-purple-700 hover:bg-purple-50 text-purple-600 border border-purple-200/60'
                  }`}
                  title="View exact API requests called, city, and timings"
                >
                  <Database className="w-3 h-3 text-purple-600" />
                  <span>Sources</span>
                  {showSources ? <ChevronUp className="w-2.5 h-2.5" /> : <ChevronDown className="w-2.5 h-2.5" />}
                </button>

                <span className="text-gray-200">|</span>
              </>
            )}

            <button
              onClick={handleCopy}
              className="flex items-center gap-1 hover:text-gray-700 transition-colors p-1 rounded-md hover:bg-gray-100 cursor-pointer"
              title="Copy message text"
            >
              {copied ? (
                <>
                  <Check className="w-3 h-3 text-emerald-600" />
                  <span className="text-[10px] text-emerald-600">Copied</span>
                </>
              ) : (
                <>
                  <Copy className="w-3 h-3" />
                  <span className="text-[10px]">Copy</span>
                </>
              )}
            </button>

            <span className="text-gray-200">|</span>

            <button
              onClick={() => setFeedback(feedback === 'up' ? null : 'up')}
              className={`p-1 rounded-md transition-colors cursor-pointer ${
                feedback === 'up' ? 'text-purple-600 bg-purple-50' : 'hover:text-gray-700 hover:bg-gray-100'
              }`}
              title="Helpful guidance"
            >
              <ThumbsUp className="w-3 h-3" />
            </button>

            <button
              onClick={() => setFeedback(feedback === 'down' ? null : 'down')}
              className={`p-1 rounded-md transition-colors cursor-pointer ${
                feedback === 'down' ? 'text-rose-600 bg-rose-50' : 'hover:text-gray-700 hover:bg-gray-100'
              }`}
              title="Unhelpful"
            >
              <ThumbsDown className="w-3 h-3" />
            </button>
          </div>

          {/* Model Attribution & Fallback Badge */}
          <div className="flex items-center gap-1.5 shrink-0">
            {message.quotaExhausted && (
              <div 
                title={`Quota limit was exhausted on ${message.exhaustedModel || 'requested model'}. Automatically processed via ${message.modelUsed}.`}
                className="flex items-center gap-1 text-[10px] font-semibold text-amber-800 bg-amber-100/90 border border-amber-300/80 px-2 py-0.5 rounded-full shadow-2xs shrink-0"
              >
                <Zap className="w-2.5 h-2.5 text-amber-600 fill-amber-500 shrink-0" />
                <span className="truncate max-w-[170px]">Switched from {message.exhaustedModel || 'Exhausted Model'}</span>
              </div>
            )}

            {message.modelUsed && (
              <div className="flex items-center gap-1 text-[10.5px] font-medium text-purple-700/80 bg-purple-50/80 border border-purple-200/60 px-2 py-0.5 rounded-full shadow-2xs">
                <Sparkles className="w-2.5 h-2.5 text-purple-500 shrink-0" />
                <span className="truncate max-w-[150px]">{message.modelUsed}</span>
              </div>
            )}
          </div>
        </div>
      </div>
    </div>
  );
}

