import { useState } from 'react';
import {
  CalendarDays,
  ChevronRight,
  Clock3,
  Layers,
  MapPin,
  Search,
  Siren,
} from 'lucide-react';
import { LAYERS, SUBDIVISION_CITIES, fciTier } from '../lib';

const LEADS = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10];

/**
 * Left Rail: Compact Forecast Controls on top, and Subdivisions & Cities taking
 * up the main scrollable height.
 */
export default function ControlPanel({
  dates,
  initDate,
  onInitDate,
  leadDay,
  onLeadDay,
  layer,
  onLayer,
  showPoly,
  onTogglePoly,
  regions,
  selected,
  onSelect,
}) {
  const [q, setQ] = useState('');
  const query = q.trim().toLowerCase();

  const filteredRegions = regions.filter((r) => {
    const nameMatch = r.subdivision_name.toLowerCase().includes(query);
    const cities = SUBDIVISION_CITIES[r.subdivision_id] || [];
    const cityMatch = cities.some((c) => c.toLowerCase().includes(query));
    return nameMatch || cityMatch;
  });

  return (
    <aside className="no-print slim-scroll flex flex-col gap-3 rounded-xl border border-slate-300/80 bg-[#f8fafc] p-3.5 shadow-sm lg:h-full lg:min-h-0">
      {/* 1. COMPACT FORECAST CONTROLS */}
      <div className="flex shrink-0 flex-col gap-2.5 rounded-lg border border-slate-200/90 bg-white/70 p-2.5 shadow-xs">
        {/* Cycle & Lead Header */}
        <div className="flex items-center justify-between gap-2">
          <div className="flex items-center gap-1.5 text-xs font-black uppercase tracking-wider text-navy-900">
            <Clock3 className="h-3.5 w-3.5 text-navy-700" />
            <span>Cycle & Lead</span>
          </div>
          <span className="rounded bg-navy-800 px-2 py-0.5 text-xs font-black text-white">
            Day {leadDay} (+{leadDay * 24}h)
          </span>
        </div>

        {/* Init Date Select */}
        <div className="flex items-center gap-2">
          <label className="text-[11px] font-bold text-slate-600 shrink-0">
            Cycle:
          </label>
          <select
            id="ctl-date"
            value={initDate}
            onChange={(e) => onInitDate(e.target.value)}
            className="w-full rounded-md border border-slate-300/90 bg-[#f1f5f9] px-2 py-1 text-xs font-semibold text-slate-800 focus:border-navy-600 focus:outline-none"
          >
            {dates.map((d) => (
              <option key={d} value={d}>
                {d === '2019-07-15'
                  ? '15 July 2019 · Active Monsoon Depression'
                  : `${d} · 00 UTC`}
              </option>
            ))}
          </select>
        </div>

        {/* Lead Day Pills */}
        <div className="grid grid-cols-10 gap-1" id="ctl-lead">
          {LEADS.map((l) => (
            <button
              key={l}
              onClick={() => onLeadDay(l)}
              title={`Lead Day ${l} (+${l * 24} hours)`}
              className={`rounded py-1 text-[11px] font-black transition ${
                l === leadDay
                  ? 'bg-navy-800 text-white shadow-xs'
                  : 'bg-slate-100 text-slate-700 hover:bg-slate-200'
              }`}
            >
              {l}
            </button>
          ))}
        </div>

        {/* Diagnostic Layer Selector */}
        <div className="flex flex-col gap-1.5 pt-1 border-t border-slate-200/80">
          <div className="flex items-center justify-between text-[11px]">
            <span className="font-bold text-slate-600 flex items-center gap-1">
              <Layers className="h-3 w-3 text-navy-700" />
              Map Layer:
            </span>
            <button
              onClick={onTogglePoly}
              className="flex items-center gap-1 font-semibold text-slate-600 hover:text-navy-900"
              title="Toggle warning polygons"
            >
              <Siren className={`h-3 w-3 ${showPoly ? 'text-red-600' : 'text-slate-400'}`} />
              <span className="text-[10px]">Polygons:</span>
              <span className={`text-[10px] font-black ${showPoly ? 'text-red-700' : 'text-slate-400'}`}>
                {showPoly ? 'ON' : 'OFF'}
              </span>
            </button>
          </div>

          <div className="grid grid-cols-3 gap-1" id="ctl-layer">
            <button
              onClick={() => onLayer('fci')}
              className={`rounded px-1 py-1 text-[11px] font-bold transition truncate ${
                layer === 'fci'
                  ? 'bg-navy-800 text-white shadow-xs'
                  : 'bg-slate-100 text-slate-700 hover:bg-slate-200'
              }`}
            >
              FCI Confidence
            </button>
            <button
              onClick={() => onLayer('prob')}
              className={`rounded px-1 py-1 text-[11px] font-bold transition truncate ${
                layer === 'prob'
                  ? 'bg-navy-800 text-white shadow-xs'
                  : 'bg-slate-100 text-slate-700 hover:bg-slate-200'
              }`}
            >
              P(Bust) Risk
            </button>
            <button
              onClick={() => onLayer('rain')}
              className={`rounded px-1 py-1 text-[11px] font-bold transition truncate ${
                layer === 'rain'
                  ? 'bg-navy-800 text-white shadow-xs'
                  : 'bg-slate-100 text-slate-700 hover:bg-slate-200'
              }`}
            >
              NWP Rainfall
            </button>
          </div>
        </div>
      </div>

      {/* 2. SUBDIVISIONS & CITIES LIST (Occupies all remaining vertical space!) */}
      <div className="flex min-h-0 flex-1 flex-col rounded-lg border border-slate-200/90 bg-white/70 p-2.5 shadow-xs">
        <div className="flex items-center justify-between pb-1.5 border-b border-saffron-500">
          <div className="flex items-center gap-1.5 text-xs font-black uppercase tracking-wider text-navy-900">
            <MapPin className="h-3.5 w-3.5 text-navy-700" />
            <span>Subdivisions & Cities</span>
          </div>
          <span className="rounded bg-slate-200/90 px-1.5 py-0.2 text-[10.5px] font-bold text-slate-700">
            {filteredRegions.length} of {regions.length}
          </span>
        </div>

        {/* Search input with immediate visibility */}
        <div className="relative mt-2 shrink-0">
          <Search className="pointer-events-none absolute left-2.5 top-1/2 h-3.5 w-3.5 -translate-y-1/2 text-slate-400" />
          <input
            value={q}
            onChange={(e) => setQ(e.target.value)}
            placeholder="Search city (Mumbai, Delhi...) or subdivision..."
            className="w-full rounded-md border border-slate-300 bg-[#f8fafc] py-1.5 pl-8 pr-2 text-xs text-slate-800 placeholder-slate-400 focus:border-navy-600 focus:bg-white focus:outline-none"
          />
        </div>

        {/* Scrollable list of cities & subdivisions */}
        <div className="slim-scroll mt-2 min-h-0 flex-1 overflow-y-auto pr-1">
          <div className="flex flex-col gap-1.5">
            {filteredRegions.map((r) => {
              const t = fciTier(r.confidence_index);
              const active = r.subdivision_id === selected;
              const cities = SUBDIVISION_CITIES[r.subdivision_id] || [];

              return (
                <button
                  key={r.subdivision_id}
                  onClick={() => onSelect(r.subdivision_id)}
                  className={`flex flex-col gap-0.5 rounded-lg border p-2 text-left transition ${
                    active
                      ? 'border-navy-800 bg-navy-50/90 shadow-xs'
                      : 'border-slate-200 bg-white hover:border-navy-600 hover:bg-slate-50'
                  }`}
                >
                  <div className="flex items-center justify-between gap-1">
                    <span className="flex min-w-0 items-center gap-1">
                      <ChevronRight
                        className={`h-3 w-3 shrink-0 ${active ? 'text-navy-800' : 'text-slate-400'}`}
                      />
                      <span className="truncate text-xs font-bold text-navy-900">
                        {r.subdivision_name}
                      </span>
                    </span>
                    <span
                      className="shrink-0 rounded px-1.5 py-0.2 text-[11px] font-black tabular-nums"
                      style={{
                        background: t.bg,
                        color: t.color,
                        border: `1px solid ${t.border}`,
                      }}
                    >
                      {r.confidence_index}%
                    </span>
                  </div>

                  {/* PROMINENT MAJOR CITIES DISPLAY */}
                  {cities.length > 0 && (
                    <div className="flex items-center gap-1 pl-3.5 text-[10.5px] font-medium text-slate-600">
                      <span className="truncate">
                        {cities.join(' · ')}
                      </span>
                    </div>
                  )}

                  <div className="flex items-center justify-between pl-3.5 text-[10px] text-slate-500">
                    <span>Rain: {r.forecast_precip_mm} mm</span>
                    <span>P(Bust): {(r.bust_probability * 100).toFixed(0)}%</span>
                  </div>
                </button>
              );
            })}

            {filteredRegions.length === 0 && (
              <p className="py-6 text-center text-xs text-slate-400">
                No subdivision or city matches “{q}”.
              </p>
            )}
          </div>
        </div>
      </div>
    </aside>
  );
}
