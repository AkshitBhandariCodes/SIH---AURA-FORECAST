import {
  Brain,
  CloudRain,
  Download,
  Droplets,
  FileDown,
  Gauge as GaugeIcon,
  MapPin,
  Printer,
  Siren,
  Wind,
} from 'lucide-react';
import { SUBDIVISION_CITIES, advisoryFor, fciTier, pct1 } from '../lib';

const ARC_LEN = 267; // π × 85 for the r=85 semicircle

function Gauge({ fci }) {
  const v = Math.min(100, Math.max(0, Number(fci)));
  const off = ARC_LEN - (ARC_LEN * v) / 100;
  const color = v >= 80 ? '#15803d' : v >= 50 ? '#d97706' : '#dc2626';
  return (
    <svg
      viewBox="0 0 200 112"
      className="mx-auto block"
      width="220"
      height="124"
      role="img"
      aria-label={`Forecast confidence ${v.toFixed(1)} percent`}
    >
      <path
        d="M 15 100 A 85 85 0 0 1 185 100"
        fill="none"
        stroke="#e2e8f0"
        strokeWidth="16"
        strokeLinecap="round"
      />
      <path
        d="M 15 100 A 85 85 0 0 1 185 100"
        fill="none"
        stroke={color}
        strokeWidth="16"
        strokeLinecap="round"
        strokeDasharray={ARC_LEN}
        strokeDashoffset={off}
      />
      <text
        x="100"
        y="82"
        textAnchor="middle"
        fontSize="30"
        fontWeight="800"
        fill="#0b3d6b"
      >
        {v.toFixed(1)}%
      </text>
      <text x="100" y="100" textAnchor="middle" fontSize="10" fill="#5b6b7c">
        FORECAST CONFIDENCE (FCI %)
      </text>
    </svg>
  );
}

function Metric({ icon: Icon, label, value, accent }) {
  return (
    <div className="rounded-lg border border-slate-200/90 bg-slate-100/90 p-2.5">
      <div className="flex items-center gap-1 text-[10px] font-bold uppercase tracking-wider text-slate-500">
        <Icon className="h-3.5 w-3.5" />
        {label}
      </div>
      <div className={`mt-1 text-lg font-extrabold tabular-nums ${accent ?? 'text-navy-900'}`}>
        {value}
      </div>
    </div>
  );
}

/**
 * Right rail: Step 4 diagnosis (gauge + drivers + advisory) → Step 5 export.
 */
export default function Inspector({
  region,
  explain,
  initDate,
  leadDay,
  onPrint,
  onGeoJSON,
  onCSV,
}) {
  if (!region) {
    return (
      <aside className="flex min-h-[480px] items-center justify-center rounded-xl border border-slate-300/80 bg-[#f8fafc] p-6 text-sm text-slate-500">
        Loading regional diagnostics…
      </aside>
    );
  }
  const tier = fciTier(region.confidence_index);
  const factors = explain?.contributing_factors ?? [];
  const diagnosis =
    explain?.diagnosis ?? 'Synthesizing synoptic physics and ensemble spread metrics…';
  const cities = SUBDIVISION_CITIES[region.subdivision_id] || [];

  return (
    <aside className="slim-scroll flex min-h-[480px] flex-col gap-3.5 overflow-y-auto rounded-xl border border-slate-300/80 bg-[#f8fafc] p-4 shadow-sm lg:min-h-0">
      <h2 className="flex items-center justify-between border-b-2 border-saffron-500 pb-2 text-xs font-bold uppercase tracking-wider text-navy-800">
        <span className="flex items-center gap-1.5">
          <MapPin className="h-4 w-4 text-navy-700" />
          4 · Regional Reliability Inspector
        </span>
        <span className="font-normal normal-case tracking-normal text-slate-400">
          क्षेत्रीय विश्लेषण
        </span>
      </h2>

      {/* Gauge card */}
      <div className="rounded-xl border border-slate-300/80 bg-gradient-to-b from-navy-50/60 to-white/90 p-3.5 text-center shadow-xs">
        <div className="text-[17px] font-extrabold text-navy-900">
          {region.subdivision_name}
        </div>
        <div className="mb-1 mt-0.5 text-[11px] text-slate-500">
          Lat {region.lat_range[0]}°–{region.lat_range[1]}° · Lon{' '}
          {region.lon_range[0]}°–{region.lon_range[1]}° · Day {leadDay} ·{' '}
          {initDate}
        </div>
        <div className="mb-1 flex justify-center">
          {region.data_source === 'real-gefs-era5' ? (
            <span className="rounded-full border border-emerald-300 bg-emerald-50 px-2.5 py-0.5 text-[10px] font-extrabold uppercase tracking-wider text-emerald-700">
              ● Real data · GEFS + ERA5
            </span>
          ) : (
            <span className="rounded-full border border-slate-300 bg-slate-100 px-2.5 py-0.5 text-[10px] font-bold uppercase tracking-wider text-slate-500">
              Pilot synthetic
            </span>
          )}
        </div>

        {/* Major Cities / Observation Stations Display */}
        {cities.length > 0 && (
          <div className="mb-2 flex flex-wrap items-center justify-center gap-1">
            <span className="text-[10.5px] font-semibold text-slate-500">
              Key Stations:
            </span>
            {cities.map((city) => (
              <span
                key={city}
                className="rounded bg-slate-200/80 px-1.5 py-0.5 text-[10.5px] font-bold text-navy-800"
              >
                {city}
              </span>
            ))}
          </div>
        )}

        <Gauge fci={region.confidence_index} />
        <div
          className="mt-2 rounded-lg border px-2.5 py-1.5 text-xs font-extrabold"
          style={{
            background: tier.bg,
            color: tier.color,
            borderColor: tier.border,
          }}
        >
          {tier.longLabel}
        </div>
      </div>

      {/* Metrics */}
      <div className="grid grid-cols-2 gap-2">
        <Metric
          icon={GaugeIcon}
          label="P(Bust)"
          value={pct1(region.bust_probability)}
          accent={
            region.bust_probability >= 0.5
              ? 'text-red-700'
              : 'text-emerald-700'
          }
        />
        <Metric
          icon={CloudRain}
          label="Forecast rain"
          value={`${region.forecast_precip_mm} mm`}
        />
        <Metric
          icon={Wind}
          label="Lead day"
          value={`Day ${leadDay}`}
        />
        <Metric
          icon={Droplets}
          label="Observed (ERA5)"
          value={
            region.observed_precip_mm != null
              ? `${region.observed_precip_mm} mm`
              : '–'
          }
        />
      </div>

      {/* Diagnosis */}
      <div
        id="ctl-diagnosis"
        className={`rounded-r-lg border border-slate-300/80 p-3 text-[13px] leading-relaxed ${
          tier.key === 'high'
            ? 'border-l-4 border-l-emerald-600 bg-emerald-50/70 text-slate-800'
            : 'border-l-4 border-l-red-600 bg-red-50/70 text-slate-800'
        }`}
      >
        <h3 className="mb-1 flex items-center gap-1.5 text-xs font-bold uppercase tracking-wider text-navy-900">
          <Brain className="h-4 w-4" />
          Synoptic Meteorological Diagnosis
        </h3>
        {diagnosis}
      </div>

      {/* SHAP drivers */}
      <div className="rounded-lg border border-slate-300/80 bg-white/70 p-3">
        <h3 className="text-xs font-bold uppercase tracking-wider text-navy-900">
          Key Physical Forecast Drivers (TreeSHAP)
        </h3>
        <div className="mt-1 flex flex-col gap-2.5">
          {factors.map((f) => (
            <div key={f.feature}>
              <div className="flex items-center justify-between gap-2 text-[11px]">
                <b className="text-navy-900">{f.feature}</b>
                <span className="font-bold text-navy-800">
                  {f.importance_weight}
                </span>
              </div>
              <div className="mt-1 h-2 overflow-hidden rounded-full bg-slate-200">
                <div
                  className="h-full rounded-full bg-gradient-to-r from-amber-500 to-red-600"
                  style={{
                    width: `${Math.min(100, Math.round(f.importance_weight * 40))}%`,
                  }}
                />
              </div>
              <div className="mt-0.5 text-[11px] text-slate-600">
                {f.scientific_interpretation} <i>({f.direction})</i>
              </div>
            </div>
          ))}
          {factors.length === 0 && (
            <p className="text-xs text-slate-400">Loading drivers…</p>
          )}
        </div>
      </div>

      {/* Advisory */}
      <div className="rounded-lg border border-dashed border-navy-700/60 bg-navy-50/70 p-3 text-xs leading-relaxed text-slate-800">
        <h3 className="mb-1 flex items-center gap-1.5 text-xs font-bold uppercase tracking-wider text-navy-900">
          <Siren className="h-4 w-4 text-navy-700" />
          Forecaster Operational Advisory
        </h3>
        {advisoryFor(region, leadDay)}
      </div>

      {/* Step 5 — export */}
      <div id="ctl-export" className="rounded-lg">
        <h3 className="mb-1.5 text-xs font-bold uppercase tracking-wider text-navy-800">
          5 · Export Meteorological Bulletin
        </h3>
        <div className="flex gap-2">
          <button
            onClick={onPrint}
            className="flex flex-1 items-center justify-center gap-1.5 rounded-lg bg-navy-700 px-2 py-2.5 text-xs font-bold text-white shadow-xs hover:bg-navy-800"
          >
            <Printer className="h-4 w-4" />
            Print
          </button>
          <button
            onClick={onGeoJSON}
            className="flex flex-1 items-center justify-center gap-1.5 rounded-lg border border-navy-700/60 bg-white/90 px-2 py-2.5 text-xs font-bold text-navy-800 shadow-xs hover:bg-navy-50"
          >
            <Download className="h-4 w-4" />
            GeoJSON
          </button>
          <button
            onClick={onCSV}
            className="flex flex-1 items-center justify-center gap-1.5 rounded-lg border border-navy-700/60 bg-white/90 px-2 py-2.5 text-xs font-bold text-navy-800 shadow-xs hover:bg-navy-50"
          >
            <FileDown className="h-4 w-4" />
            CSV
          </button>
        </div>
      </div>
    </aside>
  );
}
